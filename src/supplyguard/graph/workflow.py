"""Assembles the SupplyGuard investigation graph.

Flow: Supplier Agent resolves identity -> Supervisor decides which
specialists are relevant -> those specialists run in parallel (LangGraph
fans out automatically since route_to_specialists can return multiple node
names) -> Risk Analyst merges whatever findings came back into one
RiskAssessment -> if requires_human_review, pause at human_review (step 16)
and wait for a resume; otherwise -> END directly. A REQUEST_MORE_INFORMATION
resume loops back to supervisor (not supplier_agent -- identity is already
known) with the reviewer's notes folded into user_request, rather than
ending the investigation; APPROVE/REJECT end it. LangGraph's fan-in waits
only for the specialists that were actually scheduled this run, not all
three unconditionally, so a narrow single-specialist request still reaches
risk_analyst correctly, and this graph fully supports cycles -- the
loop-back is not a special case.

Compiled with a durable, Postgres-backed checkpointer (step 17) --
interrupt()/resume in human_review_node requires one to persist state
between the pause and the resume call, which may span a process restart.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from supplyguard.graph.checkpointer import get_checkpointer
from supplyguard.graph.routing import (
    route_after_human_review,
    route_after_risk_analyst,
    route_after_supplier,
    route_to_specialists,
)
from supplyguard.graph.state import InvestigationState


def build_investigation_graph():
    # Imported lazily, at call time rather than module load time: every
    # agent module imports supplyguard.graph.state, so if something imports
    # supplyguard.agents *before* supplyguard.graph has finished loading,
    # an eager import here would reenter the still-initializing agents
    # package via this very module and crash with a circular import --
    # confirmed directly by importing supplyguard.agents.resilience first
    # in a test script. Deferring to call time sidesteps it regardless of
    # which package a caller happens to touch first.
    from supplyguard.agents import (
        compliance_agent_node,
        human_review_node,
        rag_agent_node,
        risk_agent_node,
        risk_analyst_node,
        supervisor_node,
        supplier_agent_node,
        sustainability_agent_node,
    )

    builder = StateGraph(InvestigationState)

    builder.add_node("supplier_agent", supplier_agent_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("compliance_agent", compliance_agent_node)
    builder.add_node("risk_agent", risk_agent_node)
    builder.add_node("sustainability_agent", sustainability_agent_node)
    builder.add_node("rag_agent", rag_agent_node)
    builder.add_node("risk_analyst", risk_analyst_node)
    builder.add_node("human_review", human_review_node)

    builder.add_edge(START, "supplier_agent")
    builder.add_conditional_edges("supplier_agent", route_after_supplier, ["supervisor", END])
    builder.add_conditional_edges(
        "supervisor",
        route_to_specialists,
        ["compliance_agent", "risk_agent", "sustainability_agent", "rag_agent", END],
    )
    builder.add_edge("compliance_agent", "risk_analyst")
    builder.add_edge("risk_agent", "risk_analyst")
    builder.add_edge("sustainability_agent", "risk_analyst")
    builder.add_edge("rag_agent", "risk_analyst")
    builder.add_conditional_edges(
        "risk_analyst", route_after_risk_analyst, ["human_review", END]
    )
    builder.add_conditional_edges(
        "human_review", route_after_human_review, ["supervisor", END]
    )

    return builder.compile(checkpointer=get_checkpointer())
