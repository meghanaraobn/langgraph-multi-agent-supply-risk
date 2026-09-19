"""The Compliance Agent: inspects certifications and regulatory requirements,
and identifies missing or expired certifications.

Unlike supplier_agent.py (a standalone function), this is a real LangGraph
node: it reads the already-identified supplier from shared InvestigationState
-- it does not resolve supplier identity itself, that's the Supplier Agent's
job -- and returns a partial state update for LangGraph to merge in.
"""
from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from supplyguard.agents.grounding import ground_findings
from supplyguard.agents.resilience import safe_node
from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate
from supplyguard.llm import get_llm
from supplyguard.models import Finding
from supplyguard.tools import COMPLIANCE_TOOLS

_TOOLS_BY_NAME = {t.name: t for t in COMPLIANCE_TOOLS}

_SYSTEM_PROMPT = (
    "You are the Compliance Agent for a supply chain risk investigation "
    "system. Your job is to inspect the supplier's certifications and the "
    "regulations applicable to its industry, and identify missing, expired, "
    "or suspended certifications as compliance findings. Every finding you "
    "report MUST cite evidence -- a specific certification or regulation "
    "record returned by your tools. Never invent a finding you cannot "
    "support with a tool result. If the supplier has no certifications on "
    "file at all, that absence is itself a finding to report, not a clean "
    "bill of health."
)


class ComplianceAgentOutput(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


@safe_node("compliance_agent")
def compliance_agent_node(state: InvestigationState) -> InvestigationStateUpdate:
    supplier = state["supplier"]
    if supplier is None:
        return {"errors": ["compliance_agent: no supplier in state, cannot proceed"]}

    llm_with_tools = get_llm().bind_tools(COMPLIANCE_TOOLS).with_retry()
    request = (
        f"Investigate compliance for supplier {supplier.id} ({supplier.name}), "
        f"industry: {supplier.industry}. Check its certifications and the "
        "regulations applicable to its industry, and report your findings."
    )
    messages: list[BaseMessage] = [SystemMessage(_SYSTEM_PROMPT), HumanMessage(request)]

    while True:
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            break

        for call in ai_message.tool_calls:
            tool = _TOOLS_BY_NAME[call["name"]]
            result = tool.invoke(call["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    structured_llm = get_llm().with_structured_output(ComplianceAgentOutput).with_retry()
    output = structured_llm.invoke(
        messages + [HumanMessage("Based on everything above, report your compliance findings.")]
    )

    grounded_findings, rejection_errors = ground_findings(supplier.id, output.findings)

    return {
        "compliance_findings": grounded_findings,
        "missing_information": output.missing_information,
        "errors": rejection_errors,
    }
