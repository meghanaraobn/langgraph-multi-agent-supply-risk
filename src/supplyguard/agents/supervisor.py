"""The Supervisor: reads the user's request and decides which specialist
agents are actually relevant, so the investigation doesn't waste time and
model calls running agents whose findings weren't asked for.

Deliberately a pure classification call, not a tool-calling loop -- routing
is a reasoning decision the model can make directly from the request text,
with no data lookup of its own required. Runs after the Supplier Agent: it
needs state["supplier"] to attach a supplier_id to the resulting plan.
"""
from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from supplyguard.agents.resilience import safe_node
from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate
from supplyguard.llm import get_llm
from supplyguard.models import InvestigationPlan

AgentName = Literal["compliance_agent", "risk_agent", "sustainability_agent", "rag_agent"]

_SYSTEM_PROMPT = (
    "You are the Supervisor for a supply chain risk investigation system. "
    "A supplier has already been identified; your only job is to read the "
    "user's request and decide which of four specialist agents are "
    "relevant to it:\n"
    "- compliance_agent: certifications and regulatory requirements\n"
    "- risk_agent: incidents and sanctions exposure\n"
    "- sustainability_agent: ESG / sustainability disclosures\n"
    "- rag_agent: audit reports and other unstructured supplier documents\n\n"
    "Default to running all four for a general or open-ended request (e.g. "
    "'investigate this supplier', 'full due diligence'). Only narrow the "
    "list when the request clearly asks about a specific dimension and "
    "nothing else (e.g. 'just check their certifications' means "
    "compliance_agent only). Do not include an agent whose findings weren't "
    "asked for and aren't implied by the request -- unnecessary agent runs "
    "cost time and money for no benefit."
)


class SupervisorDecision(BaseModel):
    agents_to_run: list[AgentName] = Field(min_length=1)
    reasoning: str


@safe_node("supervisor")
def supervisor_node(state: InvestigationState) -> InvestigationStateUpdate:
    supplier = state["supplier"]
    if supplier is None:
        return {"errors": ["supervisor: no supplier in state, cannot plan investigation"]}

    structured_llm = get_llm().with_structured_output(SupervisorDecision).with_retry()
    decision = structured_llm.invoke(
        [SystemMessage(_SYSTEM_PROMPT), HumanMessage(state["user_request"])]
    )

    plan = InvestigationPlan(
        investigation_id=state["investigation_id"],
        supplier_id=supplier.id,
        user_request=state["user_request"],
        agents_to_run=list(decision.agents_to_run),
        reasoning=decision.reasoning,
    )

    return {"investigation_plan": plan}
