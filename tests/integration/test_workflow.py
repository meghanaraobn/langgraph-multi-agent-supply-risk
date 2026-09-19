"""Integration tests for the investigation graph's structure and routing
mechanics.

Full end-to-end runs (real LLM calls through every agent) are exercised
live by the evaluation harness (tests/evaluation/test_cases.py, marked
@pytest.mark.live). This file tests the graph's TOPOLOGY and fan-out
mechanics deterministically -- using the real routing functions with fake
specialist nodes -- without needing to mock seven different agent modules'
LLM calls individually.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from supplyguard.graph import build_investigation_graph
from supplyguard.graph.routing import route_to_specialists
from supplyguard.graph.state import InvestigationState, create_initial_state
from supplyguard.models import InvestigationPlan


def test_investigation_graph_has_the_expected_nodes() -> None:
    graph = build_investigation_graph()
    nodes = set(graph.get_graph().nodes.keys())
    assert nodes == {
        "__start__",
        "__end__",
        "supplier_agent",
        "supervisor",
        "compliance_agent",
        "risk_agent",
        "sustainability_agent",
        "rag_agent",
        "risk_analyst",
        "human_review",
    }


def test_parallel_fan_out_runs_only_the_planned_specialists() -> None:
    """Reuses the real route_to_specialists function against fake specialist
    nodes, proving LangGraph's fan-out mechanics route to exactly the
    planned subset -- not all three, not zero.
    """
    calls: list[str] = []

    def fake_specialist(name: str):
        state_key = f"{name.replace('_agent', '')}_findings"

        def node(state: InvestigationState) -> dict:
            calls.append(name)
            return {state_key: []}

        return node

    builder = StateGraph(InvestigationState)
    builder.add_node("supervisor", lambda state: {})  # plan is already set by the test
    builder.add_node("compliance_agent", fake_specialist("compliance_agent"))
    builder.add_node("risk_agent", fake_specialist("risk_agent"))
    builder.add_node("sustainability_agent", fake_specialist("sustainability_agent"))
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_to_specialists,
        ["compliance_agent", "risk_agent", "sustainability_agent", END],
    )
    for node_name in ("compliance_agent", "risk_agent", "sustainability_agent"):
        builder.add_edge(node_name, END)
    graph = builder.compile()

    state = create_initial_state("INV-TEST", "test")
    state["investigation_plan"] = InvestigationPlan(
        investigation_id="INV-TEST",
        supplier_id="SUP-001",
        user_request="test",
        agents_to_run=["compliance_agent", "risk_agent"],
        reasoning="narrow request",
    )

    graph.invoke(state)

    assert set(calls) == {"compliance_agent", "risk_agent"}
