"""The Sustainability Agent: inspects a supplier's disclosed sustainability
/ESG data and flags findings worth surfacing.

Note: the spec describes this agent as comparing supplier "claims" against
verified information. The current dataset has only one sustainability
source -- the disclosed ESG data itself -- with no separate "claims" source
to compare it against. This agent is scoped to what the data actually
supports: reporting on the verified data and flagging concerning findings,
not detecting a claims/reality mismatch that isn't representable yet.
"""
from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from supplyguard.agents.grounding import ground_findings
from supplyguard.agents.resilience import safe_node
from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate
from supplyguard.llm import get_llm
from supplyguard.models import Finding
from supplyguard.tools import SUSTAINABILITY_TOOLS

_TOOLS_BY_NAME = {t.name: t for t in SUSTAINABILITY_TOOLS}

_SYSTEM_PROMPT = (
    "You are the Sustainability Agent for a supply chain risk investigation "
    "system. Your job is to inspect the supplier's disclosed sustainability "
    "/ESG data and identify findings worth surfacing: a notably low ESG "
    "score, very low renewable energy usage, absence of science-based "
    "targets, or -- most importantly -- the complete absence of any "
    "sustainability disclosure on file, which is itself a finding, not "
    "evidence the supplier has no environmental impact. Do not report a "
    "finding just because a supplier's metrics are good; only report "
    "genuine gaps or concerns. Every finding you report MUST cite evidence "
    "-- the sustainability record returned by your tool. Never invent a "
    "finding you cannot support with a tool result."
)


class SustainabilityAgentOutput(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


@safe_node("sustainability_agent")
def sustainability_agent_node(state: InvestigationState) -> InvestigationStateUpdate:
    supplier = state["supplier"]
    if supplier is None:
        return {"errors": ["sustainability_agent: no supplier in state, cannot proceed"]}

    llm_with_tools = get_llm().bind_tools(SUSTAINABILITY_TOOLS).with_retry()
    request = (
        f"Investigate sustainability disclosures for supplier {supplier.id} "
        f"({supplier.name}) and report your findings."
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

    structured_llm = get_llm().with_structured_output(SustainabilityAgentOutput).with_retry()
    output = structured_llm.invoke(
        messages
        + [HumanMessage("Based on everything above, report your sustainability findings.")]
    )

    grounded_findings, rejection_errors = ground_findings(supplier.id, output.findings)

    return {
        "sustainability_findings": grounded_findings,
        "missing_information": output.missing_information,
        "errors": rejection_errors,
    }
