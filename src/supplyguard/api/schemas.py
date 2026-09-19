"""Request/response models for the FastAPI investigation endpoints."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from supplyguard.models import DecisionType


class InvestigationRequest(BaseModel):
    query: str = Field(
        ...,
        description="Natural-language investigation request.",
        examples=["Investigate Cobalt Basin Mining. Full due diligence across compliance, risk, and sustainability."],
    )


class InvestigationCreatedResponse(BaseModel):
    investigation_id: str
    status: str = "running"


class InvestigationStatusResponse(BaseModel):
    investigation_id: str
    status: str
    """One of: "running", "awaiting_human_review", "completed"."""

    supplier: Optional[dict[str, Any]] = None
    risk_assessment: Optional[dict[str, Any]] = None
    human_review_request: Optional[dict[str, Any]] = None
    human_decision: Optional[dict[str, Any]] = None
    errors: list[str] = Field(default_factory=list)


class HumanReviewRequest(BaseModel):
    # DecisionType, not str: a malformed value (e.g. "MAYBE") used to pass
    # this validation, get dispatched to a background task, and crash
    # silently inside human_review_node (which is deliberately not wrapped
    # in @safe_node -- a malformed human decision should be visible, not
    # swallowed). Validating it here, at the actual system boundary, means
    # FastAPI rejects it with a clean 422 before it ever reaches the graph.
    decision: DecisionType = Field(..., examples=["APPROVE"])
    reviewer: Optional[str] = Field(default=None, examples=["Jane Doe"])
    notes: Optional[str] = Field(default=None, examples=["Approved with mitigation plan in progress."])
