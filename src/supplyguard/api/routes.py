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

import asyncio
import json
import logging
import queue
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from langgraph.types import StateSnapshot

from supplyguard.api.schemas import (
    HumanReviewRequest,
    InvestigationCreatedResponse,
    InvestigationRequest,
    InvestigationStatusResponse,
)
from supplyguard.api.streaming import bus, json_safe
from supplyguard.graph import build_investigation_graph, create_initial_state

logger = logging.getLogger("supplyguard.api")

router = APIRouter(tags=["investigations"])

_VIEWER_HTML = (Path(__file__).parent / "static" / "viewer.html").read_text()


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


def _stream_and_publish(investigation_id: str, graph_input) -> None:
    """Runs the graph via .stream(..., stream_mode="updates") instead of
    .invoke() so each node's completion (and any interrupt) is published to
    the event bus as it happens -- .invoke() only returns once the whole run
    reaches an interrupt or END, which is too coarse for a live trace. The
    persisted checkpoint state ends up identical either way; this only adds
    a side-channel of "here's what just happened" events for any SSE
    subscriber watching this investigation_id.
    """
    step = 0
    try:
        for chunk in _get_graph().stream(
            graph_input, config=_config(investigation_id), stream_mode="updates"
        ):
            step += 1
            if "__interrupt__" in chunk:
                interrupt_obj = chunk["__interrupt__"][0]
                bus.publish(
                    investigation_id,
                    {"kind": "interrupt", "step": step, "request": json_safe(interrupt_obj.value)},
                )
                continue
            for node, update in chunk.items():
                bus.publish(
                    investigation_id,
                    {"kind": "node_update", "step": step, "node": node, "update": json_safe(update)},
                )
    except Exception as exc:  # noqa: BLE001 -- also report to any live watcher before the outer caller logs it
        bus.publish(investigation_id, {"kind": "error", "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        bus.publish(investigation_id, {"kind": "end"})


def _run_investigation(investigation_id: str, query: str) -> None:
    try:
        _stream_and_publish(investigation_id, create_initial_state(investigation_id, query))
    except Exception:  # noqa: BLE001 -- background task: nothing re-raises this to a client, so at least log it
        logger.exception("Investigation %s failed outside the per-node safety net", investigation_id)


def _run_resume(investigation_id: str, payload: dict) -> None:
    try:
        _stream_and_publish(investigation_id, Command(resume=payload))
    except Exception:  # noqa: BLE001 -- same rationale as _run_investigation
        logger.exception("Resuming investigation %s failed", investigation_id)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _status_response(investigation_id: str, snapshot: StateSnapshot) -> InvestigationStatusResponse:
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

    return _status_response(investigation_id, snapshot)


@router.get(
    "/investigations/{investigation_id}/stream",
    summary="Watch an investigation's agent steps live (SSE)",
    description=(
        "Server-Sent Events stream of the graph's node-by-node progress -- supplier_agent, "
        "supervisor, each specialist that was scheduled, risk_analyst, human_review -- as they "
        "happen, instead of repeatedly calling GET /investigations/{investigation_id} yourself. "
        "Sends one 'status' event immediately with the current state, then live 'node_update' / "
        "'interrupt' events until the investigation reaches 'completed' or "
        "'awaiting_human_review', at which point a final 'status' event is sent and the stream "
        "closes. Open /viewer in a browser for a rendered version of this stream."
    ),
)
async def stream_investigation(investigation_id: str, request: Request) -> StreamingResponse:
    # Subscribed before the first status check, deliberately -- an event
    # published between "check current snapshot" and "start listening"
    # would otherwise be silently missed. Any event that arrives before the
    # loop starts just sits in the queue until the loop reaches it.
    q = bus.subscribe(investigation_id)

    async def event_source():
        try:
            snapshot = await asyncio.to_thread(_get_snapshot_or_503, investigation_id)
            if not snapshot.values:
                yield _sse(
                    {"kind": "error", "error": f"No investigation found with id '{investigation_id}'"}
                )
                return

            status = _status_response(investigation_id, snapshot)
            yield _sse({"kind": "status", **status.model_dump(mode="json")})
            if status.status != "running":
                return

            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.to_thread(q.get, True, 15)
                except queue.Empty:
                    yield ": keepalive\n\n"
                    continue
                if event["kind"] == "end":
                    break
                yield _sse(event)

            final_snapshot = await asyncio.to_thread(_get_snapshot_or_503, investigation_id)
            if final_snapshot.values:
                final = _status_response(investigation_id, final_snapshot)
                yield _sse({"kind": "status", **final.model_dump(mode="json")})
        finally:
            bus.unsubscribe(investigation_id, q)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/viewer", response_class=HTMLResponse, include_in_schema=False)
def viewer() -> HTMLResponse:
    return HTMLResponse(_VIEWER_HTML)


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
