"""Domain model for the merged risk assessment produced by the Risk Analyst.

`requires_human_review` is intentionally not a field the LLM gets to set. A
model_validator recomputes it from `risk_level` every time a RiskAssessment is
constructed, so a model that argues "critical risk, but no review needed" is
overridden by the deterministic threshold rule rather than trusted.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from supplyguard.models.findings import Finding, Severity

_HUMAN_REVIEW_THRESHOLD_LEVELS = frozenset({"high", "critical"})


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


IncidentType = Literal[
    "labor_violation",
    "wage_theft",
    "child_labor",
    "safety_accident",
    "forced_labor",
    "environmental_spill",
    "corruption",
    "strike",
    "fire",
]
IncidentStatus = Literal["open", "under_investigation", "resolved"]


class Incident(BaseModel):
    """Raw fixture record — a reported event, independent of the Risk Agent's
    interpretation of it. `severity` reuses Finding's Severity scale on
    purpose: it's the same concept (how bad), just asserted by the data
    source here instead of assessed by an agent.
    """

    id: str
    supplier_id: str
    incident_type: IncidentType
    date: date
    severity: Severity
    description: str
    source: str
    status: IncidentStatus
    resolution_notes: Optional[str] = None


SanctionEntityType = Literal["company", "individual"]
SanctionMatchConfidence = Literal["exact", "high", "low", "none"]
SanctionStatus = Literal["active", "delisted"]


class SanctionRecord(BaseModel):
    """Raw sanctions-screening row. `match_supplier_id` is the dataset's own
    pre-resolved answer; `match_confidence` is what an agent must actually
    reason about before trusting that answer — see search_sanctions_by_name
    in the repository, which returns these regardless of match status.
    """

    id: str
    entity_name: str
    entity_type: SanctionEntityType
    list_name: str
    match_supplier_id: Optional[str] = None
    match_confidence: SanctionMatchConfidence
    sanction_reason: str
    date_added: date
    country: str
    status: SanctionStatus


class RiskAssessment(BaseModel):
    risk_level: RiskLevel
    rationale: str
    contributing_findings: list[Finding] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    requires_human_review: bool = False

    @model_validator(mode="after")
    def _enforce_human_review_threshold(self) -> "RiskAssessment":
        self.requires_human_review = self.risk_level.value in _HUMAN_REVIEW_THRESHOLD_LEVELS
        return self
