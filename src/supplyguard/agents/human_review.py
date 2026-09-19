"""Human review: pauses the investigation when the Risk Analyst's assessment
requires it, and resumes once a human submits a decision.

Uses LangGraph's interrupt(), which requires the graph to be compiled with a
checkpointer -- pausing and resuming only works if state can be persisted
between the interrupt call and the resume call, which may happen in an
entirely different process (e.g. a human reviewing hours later via an API).
Backed by the durable, Postgres-backed checkpointer from step 17.

Deliberately not wrapped in @safe_node: a malformed resume payload is a
caller error (typically already rejected earlier by the API's own
HumanReviewRequest validation, but this node has no way to assume it's
always reached that way) that should surface clearly, not be swallowed into
a silently "completed" investigation with no human decision ever recorded.
"""
from __future__ import annotations

from langgraph.types import interrupt

from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate
from supplyguard.models import DecisionType, HumanDecision


def human_review_node(state: InvestigationState) -> InvestigationStateUpdate:
    assessment = state["risk_assessment"]
    supplier = state["supplier"]

    payload = {
        "investigation_id": state["investigation_id"],
        "supplier": supplier.name if supplier else None,
        "risk_level": assessment.risk_level.value if assessment else None,
        "rationale": assessment.rationale if assessment else None,
        "message": (
            "This investigation requires human review before a final report "
            "can be issued. Respond with a decision: APPROVE, REJECT, or "
            "REQUEST_MORE_INFORMATION."
        ),
    }

    response = interrupt(payload)

    try:
        raw_decision = response["decision"]
        decision_type = DecisionType(raw_decision)
    except KeyError as exc:
        raise ValueError(
            f"Human review resume payload is missing 'decision': {response!r}"
        ) from exc
    except ValueError as exc:
        valid = [d.value for d in DecisionType]
        raise ValueError(
            f"Human review resume payload has an invalid 'decision' {raw_decision!r}; "
            f"expected one of {valid}"
        ) from exc

    decision = HumanDecision(
        decision=decision_type,
        reviewer=response.get("reviewer"),
        notes=response.get("notes"),
    )

    update: InvestigationStateUpdate = {"human_decision": decision}

    if decision.decision == DecisionType.REQUEST_MORE_INFORMATION:
        # Route back to the supervisor with the reviewer's ask folded into
        # the request -- see route_after_human_review in graph/routing.py.
        # Re-run specialists' findings accumulate with the first round's via
        # the operator.add reducers on the findings lists (step 9); nothing
        # here needs to merge that manually.
        follow_up = decision.notes or "Reviewer requested more information; re-investigate."
        update["user_request"] = (
            f"{state['user_request']}\n\nFollow-up requested by human reviewer: {follow_up}"
        )

    return update
