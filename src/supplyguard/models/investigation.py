"""Domain models tying a full investigation together: the supervisor's plan,
an optional human decision, and the final structured result returned to the
caller.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from supplyguard.models.findings import Evidence, Finding
from supplyguard.models.risk import RiskAssessment
from supplyguard.models.supplier import Supplier


class InvestigationPlan(BaseModel):
    """The supervisor's routing decision: which specialist agents should run, and why."""

    investigation_id: str
    supplier_id: str
    user_request: str
    agents_to_run: list[str]
    reasoning: str


class DecisionType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_INFORMATION = "REQUEST_MORE_INFORMATION"


class HumanDecision(BaseModel):
    decision: DecisionType
    reviewer: Optional[str] = None
    notes: Optional[str] = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InvestigationResult(BaseModel):
    """The full structured output of one investigation.

    `requires_human_review` lives on `risk_assessment` (computed deterministically
    there) rather than being duplicated here — one source of truth for that flag.
    """

    investigation_id: str
    supplier: Supplier
    evidence: list[Evidence] = Field(default_factory=list)
    compliance_findings: list[Finding] = Field(default_factory=list)
    incident_findings: list[Finding] = Field(default_factory=list)
    sanctions_findings: list[Finding] = Field(default_factory=list)
    sustainability_findings: list[Finding] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_assessment: Optional[RiskAssessment] = None
    human_decision: Optional[HumanDecision] = None
    final_report: Optional[str] = None
