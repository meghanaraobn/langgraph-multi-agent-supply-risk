"""The RAG Agent: searches a supplier's ingested unstructured documents
(on-site audit reports, disclosures, ...) for relevant findings.

Structurally identical to compliance_agent.py -- a real LangGraph node bound
to one tool (search_documents instead of the certification/regulation
lookups), same tool-calling loop, same structured-output + ground_findings
pattern. The difference is entirely in what it searches and what it cites:
Evidence.source_id here is a chunk_id from search_documents, source_type is
"document", and grounding.py resolves it against Weaviate instead of
Postgres/JSON.
"""
from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from supplyguard.agents.grounding import ground_findings
from supplyguard.agents.resilience import safe_node
from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate
from supplyguard.llm import get_llm
from supplyguard.models import Finding
from supplyguard.tools import RAG_TOOLS

_TOOLS_BY_NAME = {t.name: t for t in RAG_TOOLS}

_SYSTEM_PROMPT = (
    "You are the RAG Agent (Document Research Agent) for a supply chain risk "
    "investigation system. Your job is to search the supplier's ingested "
    "unstructured documents -- on-site audit reports and similar disclosures "
    "-- for anything relevant to the investigation, and report your findings "
    "as compliance, labor, safety, or environmental issues described in "
    "those documents. Run multiple searches with different queries if the "
    "first doesn't surface much -- a single narrow query can miss relevant "
    "passages. Every finding you report MUST cite the exact chunk_id "
    "returned by search_documents as its evidence -- never invent a finding "
    "you cannot support with a real search result. An empty search result "
    "means no document has been ingested for this supplier, or nothing "
    "relevant was found -- report that as missing information, not as a "
    "clean bill of health."
)


class RagAgentOutput(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


@safe_node("rag_agent")
def rag_agent_node(state: InvestigationState) -> InvestigationStateUpdate:
    supplier = state["supplier"]
    if supplier is None:
        return {"errors": ["rag_agent: no supplier in state, cannot proceed"]}

    llm_with_tools = get_llm().bind_tools(RAG_TOOLS).with_retry()
    request = (
        f"Investigate supplier {supplier.id} ({supplier.name}), industry: "
        f"{supplier.industry}, using its ingested documents. Search for audit "
        "findings, labor practices, safety incidents, and any other issue "
        "raised in its documents, and report your findings."
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

    structured_llm = get_llm().with_structured_output(RagAgentOutput).with_retry()
    output = structured_llm.invoke(
        messages + [HumanMessage("Based on everything above, report your findings.")]
    )

    grounded_findings, rejection_errors = ground_findings(supplier.id, output.findings)

    return {
        "rag_findings": grounded_findings,
        "missing_information": output.missing_information,
        "errors": rejection_errors,
    }
