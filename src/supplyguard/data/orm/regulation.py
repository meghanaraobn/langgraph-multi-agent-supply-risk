"""SQLAlchemy table definition for regulations. No supplier foreign key --
matched at query time by industry/jurisdiction, same as the JSON fixture.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from supplyguard.data.db import Base


class RegulationORM(Base):
    __tablename__ = "regulations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    regulation_name: Mapped[str]
    jurisdiction: Mapped[str]
    effective_date: Mapped[date]
    description: Mapped[str]
    applicable_industries: Mapped[list[str]] = mapped_column(ARRAY(String))
    compliance_requirement: Mapped[str]
    penalty_for_noncompliance: Mapped[str]
