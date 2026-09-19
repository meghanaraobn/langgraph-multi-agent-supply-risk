"""Domain model for the supplier master record."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

Criticality = Literal["low", "medium", "high"]


class SupplierContact(BaseModel):
    name: str
    title: str
    email: str


class Supplier(BaseModel):
    id: str
    name: str
    country: str
    industry: str
    tier: int
    founded_year: int
    employee_count: int
    annual_revenue_usd: float
    products: list[str]
    primary_contact: SupplierContact
    address: str
    website: str
    relationship_start_date: date
    criticality: Criticality
    parent_company: Optional[str] = None
