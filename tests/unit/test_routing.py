"""Unit tests for the graph's conditional edge functions -- pure functions
over state, no LLM or database involved.
"""
from __future__ import annotations

from langgraph.graph import END

from supplyguard.graph.routing import (
    route_after_human_review,
    route_after_risk_analyst,
    route_after_supplier,
    route_to_specialists,
)
from supplyguard.graph.state import create_initial_state
from supplyguard.models import (
    DecisionType,
    HumanDecision,
    InvestigationPlan,
    RiskAssessment,
    RiskLevel,
    Supplier,
    SupplierContact,
)


def _supplier(supplier_id: str = "SUP-001") -> Supplier:
    return Supplier(
        id=supplier_id,
        name="Test Co",
        country="US",
        industry="Testing",
        tier=1,
        founded_year=2000,
        employee_count=10,
        annual_revenue_usd=1.0,
        products=[],
        primary_contact=SupplierContact(name="A", title="B", email="a@example.com"),
        address="x",
        website="x",
        relationship_start_date="2020-01-01",
        criticality="low",
        parent_company=None,
    )


def test_route_after_supplier_goes_to_supervisor_when_found() -> None:
    state = create_initial_state("INV-1", "test")
    state["supplier"] = _supplier()
    assert route_after_supplier(state) == "supervisor"


def test_route_after_supplier_ends_when_not_found() -> None:
    state = create_initial_state("INV-1", "test")
    assert route_after_supplier(state) == END


def test_route_to_specialists_returns_the_planned_agents() -> None:
    state = create_initial_state("INV-1", "test")
    state["investigation_plan"] = InvestigationPlan(
        investigation_id="INV-1",
        supplier_id="SUP-001",
        user_request="test",
        agents_to_run=["compliance_agent", "risk_agent"],
        reasoning="x",
    )
    assert set(route_to_specialists(state)) == {"compliance_agent", "risk_agent"}


def test_route_to_specialists_ends_with_no_plan() -> None:
    state = create_initial_state("INV-1", "test")
    assert route_to_specialists(state) == [END]


def test_route_after_risk_analyst_pauses_for_human_review_when_required() -> None:
    state = create_initial_state("INV-1", "test")
    state["risk_assessment"] = RiskAssessment(risk_level=RiskLevel.CRITICAL, rationale="x")
    assert route_after_risk_analyst(state) == "human_review"


def test_route_after_risk_analyst_ends_when_not_required() -> None:
    state = create_initial_state("INV-1", "test")
    state["risk_assessment"] = RiskAssessment(risk_level=RiskLevel.LOW, rationale="x")
    assert route_after_risk_analyst(state) == END


def test_route_after_human_review_loops_back_on_request_more_information() -> None:
    state = create_initial_state("INV-1", "test")
    state["human_decision"] = HumanDecision(decision=DecisionType.REQUEST_MORE_INFORMATION)
    assert route_after_human_review(state) == "supervisor"


def test_route_after_human_review_ends_on_approve() -> None:
    state = create_initial_state("INV-1", "test")
    state["human_decision"] = HumanDecision(decision=DecisionType.APPROVE)
    assert route_after_human_review(state) == END
