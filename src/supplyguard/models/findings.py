"""Domain models for evidence and the findings specialist agents produce.

A Finding is the atomic unit of agent output in this system. It is deliberately
hard to construct without grounding: `evidence` cannot be empty. This turns
the spec requirement "the risk analyst must not invent evidence" into
something Pydantic enforces, rather than something a prompt merely requests.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

FindingCategory = Literal["compliance", "risk", "sustainability", "audit"]

EvidenceSourceType = Literal[
    "certification", "incident", "sanctions", "sustainability", "regulation", "supplier",
    "document",
]


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(str, Enum):
    """Categorical, not numeric — an LLM stating '0.87 confidence' is fabricated precision."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Evidence(BaseModel):
    """A pointer back to one specific record in the underlying dataset."""

    source_type: EvidenceSourceType
    source_id: str
    detail: str


class Finding(BaseModel):
    category: FindingCategory
    severity: Severity
    title: str
    description: str
    evidence: list[Evidence] = Field(default_factory=list, min_length=1)
    confidence: ConfidenceLevel
    source: str
    """Which agent produced this finding, e.g. "compliance_agent"."""
