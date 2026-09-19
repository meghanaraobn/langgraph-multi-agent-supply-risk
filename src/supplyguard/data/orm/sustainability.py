"""SQLAlchemy table definition for sustainability/ESG disclosures."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from supplyguard.data.db import Base

if TYPE_CHECKING:
    from supplyguard.data.orm.supplier import SupplierORM


class SustainabilityORM(Base):
    __tablename__ = "sustainability"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), unique=True)
    reporting_year: Mapped[int]
    carbon_emissions_tons_co2e: Mapped[float]
    scope_1_emissions: Mapped[float]
    scope_2_emissions: Mapped[float]
    scope_3_emissions: Mapped[float]
    renewable_energy_pct: Mapped[float]
    water_usage_m3: Mapped[float]
    waste_recycled_pct: Mapped[float]
    esg_score: Mapped[float]
    has_sustainability_report: Mapped[bool]
    science_based_targets: Mapped[bool]

    supplier: Mapped["SupplierORM"] = relationship(back_populates="sustainability")
