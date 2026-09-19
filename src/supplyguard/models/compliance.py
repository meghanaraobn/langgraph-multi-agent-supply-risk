"""Domain models for compliance reference data: certifications and regulations.

These are pass-through models for read-only fixture data — no business-rule
validators here, unlike Finding/RiskAssessment. Their job is to fail loudly at
load time if a record in certifications.json/regulations.json is malformed,
and to give every consumer (tools, agents, tests) real attribute access
instead of dict key lookups.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

CertificationStatus = Literal["active", "expired", "suspended", "revoked"]


class Certification(BaseModel):
    id: str
    supplier_id: str
    certification_type: str
    issuing_body: str
    issue_date: date
    expiry_date: date
    status: CertificationStatus
    scope: str


class Regulation(BaseModel):
    id: str
    regulation_name: str
    jurisdiction: str
    effective_date: date
    description: str
    applicable_industries: list[str]
    compliance_requirement: str
    penalty_for_noncompliance: str
