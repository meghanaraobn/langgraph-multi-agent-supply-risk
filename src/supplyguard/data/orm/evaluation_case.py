"""SQLAlchemy table definition for the evaluation harness's answer key."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from supplyguard.data.db import Base


class EvaluationCaseORM(Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    scenario_description: Mapped[str]
    expected_risk_level: Mapped[str]
    expected_route: Mapped[str]
    expected_flags: Mapped[list[str]] = mapped_column(ARRAY(String))
    expected_agents_triggered: Mapped[list[str]] = mapped_column(ARRAY(String))
    ground_truth_findings: Mapped[dict] = mapped_column(JSONB)
    notes: Mapped[Optional[str]]
