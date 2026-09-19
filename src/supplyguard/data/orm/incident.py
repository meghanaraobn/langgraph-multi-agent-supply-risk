"""SQLAlchemy table definition for incidents."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from supplyguard.data.db import Base

if TYPE_CHECKING:
    from supplyguard.data.orm.supplier import SupplierORM


class IncidentORM(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    incident_type: Mapped[str]
    date: Mapped[date]
    severity: Mapped[str]
    description: Mapped[str]
    source: Mapped[str]
    status: Mapped[str]
    resolution_notes: Mapped[Optional[str]]

    supplier: Mapped["SupplierORM"] = relationship(back_populates="incidents")
