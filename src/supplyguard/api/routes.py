"""FastAPI routes for starting and checking supplier investigations.

POST /investigations kicks off a real investigation but does not block on
it -- graph.invoke() has taken anywhere from ~20s to ~100s in testing, far
too long for a synchronous HTTP request. It runs in a FastAPI background
task instead, and returns the investigation_id immediately.

GET /investigations/{id} does not read from any separate results store --
it reads the investigation graph's own persisted checkpoint state
(graph.get_state()) for that thread_id. This only works because step 17
made checkpointing durable (Postgres-backed) and step 22 made the
checkpointer's connection pool safe for concurrent access (the background
task writing while a GET request reads, potentially from a different
thread). "Not found" vs "completed" is distinguished by snapshot.values
being empty vs populated -- both have an empty snapshot.next, so next()
alone can't tell them apart; verified directly against a real paused,
completed, and never-invoked thread_id before writing this logic.
"""
from __future__ import annotations

import logging
import uuid
from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, HTTPException
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from langgraph.types import StateSnapshot

from supplyguard.api.schemas import (
    HumanReviewRequest,
    InvestigationCreatedResponse,
    InvestigationRequest,
    InvestigationStatusResponse,
)
from supplyguard.graph import build_investigation_graph, create_initial_state

logger = logging.getLogger("supplyguard.api")

router = APIRouter(tags=["investigations"])


@lru_cache(maxsize=1)
def _get_graph() -> CompiledStateGraph:
    return build_investigation_graph()


def _config(investigation_id: str) -> dict:
    return {"configurable": {"thread_id": investigation_id}}


def _get_snapshot_or_503(investigation_id: str) -> StateSnapshot:
    """get_state() reads through the checkpointer's connection pool -- if
    Postgres is genuinely unreachable, that raises a raw sqlalchemy/psycopg
    exception. Callers shouldn't see that leak through as an unexplained
    500; a 503 with a clear reason is the honest response for "the backing
    store is down", not "your request was invalid".
    """
    try:
        return _get_graph().get_state(_config(investigation_id))
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: any infra failure here maps to the same clean 503
        logger.exception("Failed to read investigation state for %s", investigation_id)
        raise HTTPException(
            status_code=503, detail="Investigation store temporarily unavailable"
        ) from exc


def _run_investigation(investigation_id: str, query: str) -> None:
    try:
        _get_graph().invoke(create_initial_state(investigation_id, query), config=_config(investigation_id))
    except Exception:  # noqa: BLE001 -- background task: nothing re-raises this to a client, so at least log it
        logger.exception("Investigation %s failed outside the per-node safety net", investigation_id)


def _run_resume(investigation_id: str, payload: dict) -> None:
    try:
        _get_graph().invoke(Command(resume=payload), config=_config(investigation_id))
    except Exception:  # noqa: BLE001 -- same rationale as _run_investigation
        logger.exception("Resuming investigation %s failed", investigation_id)


@router.post(
    "/investigations",
    response_model=InvestigationCreatedResponse,
    status_code=202,
    summary="Start a new supplier investigation",
    description=(
        "Kicks off the full agent pipeline (Supplier -> Supervisor -> specialist agents -> "
        "Risk Analyst) as a background task and returns immediately. Poll "
        "GET /investigations/{investigation_id} for progress and the final result."
    ),
)
def create_investigation(
    request: InvestigationRequest, background_tasks: BackgroundTasks
) -> InvestigationCreatedResponse:
    investigation_id = str(uuid.uuid4())
    background_tasks.add_task(_run_investigation, investigation_id, request.query)
    return InvestigationCreatedResponse(investigation_id=investigation_id, status="running")


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationStatusResponse,
    summary="Check investigation status / get the result",
    description=(
        "Reads the investigation graph's own persisted state for this ID. status is one of "
        "'running', 'awaiting_human_review' (see human_review_request), or 'completed' "
        "(see risk_assessment)."
    ),
)
def get_investigation(investigation_id: str) -> InvestigationStatusResponse:
    snapshot = _get_snapshot_or_503(investigation_id)

    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No investigation found with id '{investigation_id}'")

    values = snapshot.values
    supplier = values.get("supplier")
    risk_assessment = values.get("risk_assessment")
    human_decision = values.get("human_decision")

    if snapshot.interrupts:
        status = "awaiting_human_review"
        human_review_request = snapshot.interrupts[0].value
    elif snapshot.next:
        status = "running"
        human_review_request = None
    else:
        status = "completed"
        human_review_request = None

    return InvestigationStatusResponse(
        investigation_id=investigation_id,
        status=status,
        supplier=supplier.model_dump(mode="json") if supplier else None,
        risk_assessment=risk_assessment.model_dump(mode="json") if risk_assessment else None,
        human_review_request=human_review_request,
        human_decision=human_decision.model_dump(mode="json") if human_decision else None,
        errors=values.get("errors", []),
    )


@router.post(
    "/investigations/{investigation_id}/review",
    response_model=InvestigationCreatedResponse,
    status_code=202,
    summary="Submit a human review decision for a paused investigation",
    description=(
        "Only valid when status is 'awaiting_human_review' (409 otherwise). Resumes the graph "
        "with this decision as a background task; poll GET /investigations/{investigation_id} "
        "again for the final result."
    ),
)
def submit_human_review(
    investigation_id: str, request: HumanReviewRequest, background_tasks: BackgroundTasks
) -> InvestigationCreatedResponse:
    snapshot = _get_snapshot_or_503(investigation_id)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No investigation found with id '{investigation_id}'")
    if not snapshot.interrupts:
        raise HTTPException(
            status_code=409, detail="This investigation is not currently awaiting human review"
        )

    # mode="json", not the default "python": DecisionType is an Enum, and
    # this payload crosses into Command(resume=...) and the checkpointer's
    # serialization -- dumping it to its plain string value here avoids any
    # ambiguity about how an Enum instance round-trips through that layer.
    payload = request.model_dump(mode="json", exclude_none=True)
    background_tasks.add_task(_run_resume, investigation_id, payload)
    return InvestigationCreatedResponse(investigation_id=investigation_id, status="running")
