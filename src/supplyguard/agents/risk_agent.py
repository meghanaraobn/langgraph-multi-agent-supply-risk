"""The Risk Agent: investigates incidents and sanctions exposure, providing
evidence for every risk finding.

check_sanctions returns raw name-search results including false positives --
the system prompt explicitly requires the model to evaluate match_confidence
itself rather than treating every hit as a real match. This is the agent
built around the dataset's deliberate sanctions-name-collision landmine.
"""
from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from supplyguard.agents.grounding import ground_findings
from supplyguard.agents.resilience import safe_node
from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate
from supplyguard.llm import get_llm
from supplyguard.models import Finding
from supplyguard.tools import RISK_TOOLS

_TOOLS_BY_NAME = {t.name: t for t in RISK_TOOLS}

_SYSTEM_PROMPT = (
    "You are the Risk Agent for a supply chain risk investigation system. "
    "Your job is to investigate reported incidents (labor, safety, "
    "environmental, corruption, etc.) and sanctions exposure for the given "
    "supplier. Every finding you report MUST cite evidence -- a specific "
    "incident or sanctions record returned by your tools. Never invent a "
    "finding you cannot support with a tool result.\n\n"
    "IMPORTANT on sanctions: check_sanctions performs a raw name search and "
    "returns every superficial match, including false positives. A returned "
    "row is NOT automatic confirmation of a real sanctions hit. You must "
    "inspect match_confidence and sanction_reason on each result yourself: "
    "'exact' or 'high' confidence with a plausible reason supports a real "
    "finding; 'low' or 'none' confidence, or a reason describing a clearly "
    "unrelated entity, means this is very likely a coincidental name "
    "collision and must NOT be reported as a sanctions finding.\n\n"
    "Also treat incident severity and status independently: a resolved "
    "incident with verified corrective action is materially different from "
    "an open incident of the same severity -- do not conflate them."
)


class RiskAgentOutput(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


@safe_node("risk_agent")
def risk_agent_node(state: InvestigationState) -> InvestigationStateUpdate:
    supplier = state["supplier"]
    if supplier is None:
        return {"errors": ["risk_agent: no supplier in state, cannot proceed"]}

    llm_with_tools = get_llm().bind_tools(RISK_TOOLS).with_retry()
    request = (
        f"Investigate risk for supplier {supplier.id} ({supplier.name}). "
        "Check its reported incidents and screen its name against sanctions "
        "watchlists, then report your risk findings."
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

    structured_llm = get_llm().with_structured_output(RiskAgentOutput).with_retry()
    output = structured_llm.invoke(
        messages + [HumanMessage("Based on everything above, report your risk findings.")]
    )

    grounded_findings, rejection_errors = ground_findings(supplier.id, output.findings)

    return {
        "risk_findings": grounded_findings,
        "missing_information": output.missing_information,
        "errors": rejection_errors,
    }
