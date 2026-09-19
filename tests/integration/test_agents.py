"""Integration tests for agent nodes, with the LLM mocked.

Per the spec, unit-level tests mock LLM calls so they're deterministic and
free. These tests verify the WIRING inside each node -- the tool-calling
loop terminating correctly, the structured-output call happening, grounding
being applied, safe_node isolating a failure -- without ever hitting the
real Azure-hosted model. Full end-to-end runs against the real LLM are
exercised live by the evaluation harness (tests/evaluation/test_cases.py,
marked @pytest.mark.live).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from supplyguard.agents.compliance_agent import ComplianceAgentOutput, compliance_agent_node
from supplyguard.agents.supplier_agent import SupplierIdentificationResult, supplier_agent_node
from supplyguard.data import get_repository
from supplyguard.graph.state import create_initial_state
from supplyguard.models import Evidence, Finding


def _fake_llm(tool_call_responses: list[AIMessage], structured_output: object) -> MagicMock:
    """Test double for get_llm(). Supports exactly the method chain every
    agent uses: .bind_tools(...).with_retry().invoke(...) for the
    tool-calling loop, and .with_structured_output(...).with_retry().invoke(...)
    for the final structured result.
    """
    fake = MagicMock()

    tool_chain = MagicMock()
    tool_chain.invoke.side_effect = tool_call_responses
    fake.bind_tools.return_value.with_retry.return_value = tool_chain

    structured_chain = MagicMock()
    structured_chain.invoke.return_value = structured_output
    fake.with_structured_output.return_value.with_retry.return_value = structured_chain

    return fake


def test_compliance_agent_node_grounds_findings_before_returning() -> None:
    supplier = get_repository().get_supplier("SUP-002")
    state = create_initial_state("INV-TEST", "test")
    state["supplier"] = supplier

    # The model immediately decides it has enough to answer (no tool calls)
    # -- this test is about the node's shaping/grounding logic, not tool
    # selection reasoning (that's exercised live in the eval harness).
    final_message = AIMessage(content="done", tool_calls=[])

    real_finding = Finding(
        category="compliance",
        severity="high",
        title="Expired certification",
        description="...",
        evidence=[Evidence(source_type="certification", source_id="CERT-004", detail="x")],
        confidence="high",
        source="compliance_agent",
    )
    fabricated_finding = Finding(
        category="compliance",
        severity="high",
        title="Fabricated finding",
        description="...",
        evidence=[Evidence(source_type="certification", source_id="CERT-DOES-NOT-EXIST", detail="x")],
        confidence="high",
        source="compliance_agent",
    )
    structured_output = ComplianceAgentOutput(
        findings=[real_finding, fabricated_finding], missing_information=[]
    )

    fake_llm = _fake_llm([final_message], structured_output)

    with patch("supplyguard.agents.compliance_agent.get_llm", return_value=fake_llm):
        result = compliance_agent_node(state)

    assert [f.title for f in result["compliance_findings"]] == ["Expired certification"]
    assert any("Fabricated finding" in e for e in result["errors"])


def test_compliance_agent_node_isolates_llm_failure_via_safe_node() -> None:
    """A transient failure anywhere inside the node (here, get_llm() itself
    raising) must become a graceful {"errors": [...]} update, not an
    unhandled exception that would crash the whole graph invocation.
    """
    state = create_initial_state("INV-TEST", "test")
    state["supplier"] = get_repository().get_supplier("SUP-002")

    with patch(
        "supplyguard.agents.compliance_agent.get_llm",
        side_effect=RuntimeError("simulated transient API failure"),
    ):
        result = compliance_agent_node(state)

    assert "compliance_findings" not in result
    assert any("RuntimeError" in e for e in result["errors"])


def test_supplier_agent_node_reports_not_found_without_fabricating() -> None:
    final_message = AIMessage(content="done", tool_calls=[])
    structured_output = SupplierIdentificationResult(
        found=False, supplier=None, notes="No supplier record found for that name."
    )
    fake_llm = _fake_llm([final_message], structured_output)

    state = create_initial_state("INV-TEST", "Tell me about Zephyr Global Robotics Inc")

    with patch("supplyguard.agents.supplier_agent.get_llm", return_value=fake_llm):
        result = supplier_agent_node(state)

    assert "supplier" not in result
    assert any("No supplier record found" in e for e in result["errors"])
