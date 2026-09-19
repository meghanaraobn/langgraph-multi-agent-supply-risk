"""The Supplier Agent: identifies a supplier and retrieves its official
record. Per spec, this agent's only job is identification -- it must never
invent supplier information, and it does no compliance/risk/sustainability
analysis of its own.

Two phases, deliberately kept separate: a tool-bound LLM loops (request a
tool -> we execute it -> feed the result back) until it stops asking for
tools, then a second, structured-output-bound call turns the finished
conversation into a validated SupplierIdentificationResult. Combining
bind_tools() and with_structured_output() in a single call is unreliable
across providers -- two distinct calls is the correct, standard pattern.
"""
from __future__ import annotations

from typing import Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel

from supplyguard.agents.resilience import safe_node
from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate
from supplyguard.llm import get_llm
from supplyguard.models import Supplier
from supplyguard.tools import SUPPLIER_TOOLS

_TOOLS_BY_NAME = {t.name: t for t in SUPPLIER_TOOLS}

_SYSTEM_PROMPT = (
    "You are the Supplier Identification Agent for a supply chain risk "
    "investigation system. Your only job is to identify the exact supplier "
    "being asked about and retrieve its official record using the tools "
    "available to you. You must NEVER invent or guess a supplier id, name, "
    "or any other detail. If no matching supplier can be found using the "
    "tools, report that clearly instead of fabricating a record."
)


class SupplierIdentificationResult(BaseModel):
    found: bool
    supplier: Optional[Supplier] = None
    notes: str


def run_supplier_agent(request: str) -> SupplierIdentificationResult:
    """Resolve a natural-language request to an exact supplier record, or
    report that none was found. Never fabricates a supplier.
    """
    llm_with_tools = get_llm().bind_tools(SUPPLIER_TOOLS).with_retry()
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

    structured_llm = get_llm().with_structured_output(SupplierIdentificationResult).with_retry()
    return structured_llm.invoke(
        messages + [HumanMessage("Based on everything above, give your final structured result.")]
    )


@safe_node("supplier_agent")
def supplier_agent_node(state: InvestigationState) -> InvestigationStateUpdate:
    """LangGraph node wrapper: translates the standalone agent's result into
    a partial InvestigationState update.
    """
    result = run_supplier_agent(state["user_request"])
    if not result.found or result.supplier is None:
        return {"errors": [f"supplier_agent: {result.notes}"]}
    return {"supplier": result.supplier}
