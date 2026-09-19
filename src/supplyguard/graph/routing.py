"""Conditional edge functions for the investigation graph.

Both return either a single node name or a list of node names. LangGraph
fans out to every node in a returned list concurrently -- that's the entire
mechanism behind "parallel agent execution" here: no separate parallel API,
just a routing function returning more than one destination.
"""
from __future__ import annotations

from langgraph.graph import END

from supplyguard.graph.state import InvestigationState
from supplyguard.models import DecisionType


def route_after_supplier(state: InvestigationState) -> str:
    return "supervisor" if state["supplier"] is not None else END


def route_to_specialists(state: InvestigationState) -> list[str]:
    plan = state["investigation_plan"]
    if plan is None:
        return [END]
    return list(plan.agents_to_run)


def route_after_risk_analyst(state: InvestigationState) -> str:
    assessment = state["risk_assessment"]
    if assessment is not None and assessment.requires_human_review:
        return "human_review"
    return END


def route_after_human_review(state: InvestigationState) -> str:
    decision = state["human_decision"]
    if decision is not None and decision.decision == DecisionType.REQUEST_MORE_INFORMATION:
        return "supervisor"
    return END
