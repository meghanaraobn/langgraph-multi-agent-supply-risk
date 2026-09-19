"""Domain model for a supplier's sustainability/ESG disclosure."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SustainabilitySnapshot(BaseModel):
    id: str
    supplier_id: str
    reporting_year: int
    carbon_emissions_tons_co2e: float
    scope_1_emissions: float
    scope_2_emissions: float
    scope_3_emissions: float
    renewable_energy_pct: float = Field(ge=0, le=100)
    water_usage_m3: float
    waste_recycled_pct: float = Field(ge=0, le=100)
    esg_score: float = Field(ge=0, le=100)
    has_sustainability_report: bool
    science_based_targets: bool
