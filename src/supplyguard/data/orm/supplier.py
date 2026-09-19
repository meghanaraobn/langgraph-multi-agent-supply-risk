"""SQLAlchemy table definition for suppliers."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from supplyguard.data.db import Base

if TYPE_CHECKING:
    from supplyguard.data.orm.certification import CertificationORM
    from supplyguard.data.orm.incident import IncidentORM
    from supplyguard.data.orm.sustainability import SustainabilityORM


class SupplierORM(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str]
    country: Mapped[str]
    industry: Mapped[str]
    tier: Mapped[int]
    founded_year: Mapped[int]
    employee_count: Mapped[int]
    annual_revenue_usd: Mapped[float]
    products: Mapped[list[str]] = mapped_column(ARRAY(String))
    primary_contact_name: Mapped[str]
    primary_contact_title: Mapped[str]
    primary_contact_email: Mapped[str]
    address: Mapped[str]
    website: Mapped[str]
    relationship_start_date: Mapped[date]
    criticality: Mapped[str]
    parent_company: Mapped[Optional[str]]

    certifications: Mapped[list["CertificationORM"]] = relationship(back_populates="supplier")
    incidents: Mapped[list["IncidentORM"]] = relationship(back_populates="supplier")
    sustainability: Mapped[Optional["SustainabilityORM"]] = relationship(back_populates="supplier")
