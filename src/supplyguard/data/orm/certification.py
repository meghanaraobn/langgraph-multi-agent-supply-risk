"""SQLAlchemy table definition for certifications."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from supplyguard.data.db import Base

if TYPE_CHECKING:
    from supplyguard.data.orm.supplier import SupplierORM


class CertificationORM(Base):
    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    certification_type: Mapped[str]
    issuing_body: Mapped[str]
    issue_date: Mapped[date]
    expiry_date: Mapped[date]
    status: Mapped[str]
    scope: Mapped[str]

    supplier: Mapped["SupplierORM"] = relationship(back_populates="certifications")
