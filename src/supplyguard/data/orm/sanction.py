"""SQLAlchemy table definition for sanctions-screening records.

No relationship() back to SupplierORM: match_supplier_id is nullable and, per
the fixture design, most rows either don't match a supplier at all or match
one only loosely (see search_sanctions_by_name in the repository) -- treating
it as a hard ORM relationship would suggest a certainty the data deliberately
doesn't have.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from supplyguard.data.db import Base


class SanctionORM(Base):
    __tablename__ = "sanctions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_name: Mapped[str]
    entity_type: Mapped[str]
    list_name: Mapped[str]
    match_supplier_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True, index=True
    )
    match_confidence: Mapped[str]
    sanction_reason: Mapped[str]
    date_added: Mapped[date]
    country: Mapped[str]
    status: Mapped[str]
