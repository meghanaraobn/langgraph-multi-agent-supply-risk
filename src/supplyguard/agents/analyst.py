"""The Risk Analyst: combines specialist findings into one merged
RiskAssessment, identifies contradictions and additional missing
information, and determines the overall risk level.

Never re-generates or paraphrases Finding objects through the LLM -- the
findings from the three specialist agents are already grounded (passed
through ground_findings) and are reused as-is in contributing_findings. The
LLM's only job is reasoning: risk_level, rationale, conflicts, and any
missing_information gaps visible only from the combined picture. If there
are no findings at all, no LLM call is made -- "no risk found" is a
deterministic default given no evidence, not a creative decision to ask a
model for.

requires_human_review is NOT set here -- it's computed deterministically by
RiskAssessment's own model_validator (step 3) from risk_level, so neither
this node nor the LLM behind it can override that threshold either way.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from supplyguard.agents.resilience import safe_node
from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate
from supplyguard.llm import get_llm
from supplyguard.models import Finding, RiskAssessment, RiskLevel

_SYSTEM_PROMPT = (
    "You are the Risk Analyst for a supply chain risk investigation system. "
    "You will be given the combined findings already produced by the "
    "Compliance, Risk, Sustainability, and RAG (document research) "
    "specialist agents for one supplier. Your job is to:\n"
    "1. Determine an overall risk_level (low, medium, high, or critical) "
    "for the supplier based on the severity and number of findings.\n"
    "2. Identify any conflicts -- cases where findings from different "
    "agents appear to contradict each other (e.g. a valid certification "
    "alongside an active, unrelated investigation into the same issue the "
    "certification is supposed to cover).\n"
    "3. Identify any additional missing information visible only once you "
    "see the combined picture.\n\n"
    "You are reasoning over findings that have already been verified against "
    "real records -- do not add new findings or invent evidence of your own. "
    "Base your risk_level and rationale only on the findings provided."
)


class RiskAnalystOutput(BaseModel):
    risk_level: RiskLevel
    rationale: str
    conflicts: list[str] = Field(default_factory=list)
    additional_missing_information: list[str] = Field(default_factory=list)


def _format_finding(finding: Finding) -> str:
    evidence_desc = "; ".join(f"{e.source_type}:{e.source_id}" for e in finding.evidence)
    return (
        f"[{finding.source}] {finding.severity.value.upper()} - {finding.title}: "
        f"{finding.description} (confidence: {finding.confidence.value}, "
        f"evidence: {evidence_desc})"
    )


@safe_node("risk_analyst")
def risk_analyst_node(state: InvestigationState) -> InvestigationStateUpdate:
    all_findings = (
        state["compliance_findings"]
        + state["risk_findings"]
        + state["sustainability_findings"]
        + state["rag_findings"]
    )

    if not all_findings:
        assessment = RiskAssessment(
            risk_level=RiskLevel.LOW,
            rationale="No findings were reported by any specialist agent that ran.",
            contributing_findings=[],
            conflicts=[],
            missing_information=state["missing_information"],
        )
        return {"risk_assessment": assessment}

    supplier = state["supplier"]
    supplier_desc = f"{supplier.name} ({supplier.industry})" if supplier else "the supplier"
    findings_text = "\n".join(f"- {_format_finding(f)}" for f in all_findings)
    missing_text = (
        "\n".join(f"- {m}" for m in state["missing_information"])
        if state["missing_information"]
        else "(none reported by specialists)"
    )

    request = (
        f"Supplier under investigation: {supplier_desc}\n\n"
        f"Findings from specialist agents:\n{findings_text}\n\n"
        f"Missing information already noted by specialists:\n{missing_text}"
    )

    structured_llm = get_llm().with_structured_output(RiskAnalystOutput).with_retry()
    output = structured_llm.invoke([SystemMessage(_SYSTEM_PROMPT), HumanMessage(request)])

    assessment = RiskAssessment(
        risk_level=output.risk_level,
        rationale=output.rationale,
        contributing_findings=all_findings,
        conflicts=output.conflicts,
        missing_information=state["missing_information"] + output.additional_missing_information,
    )

    return {"risk_assessment": assessment}
