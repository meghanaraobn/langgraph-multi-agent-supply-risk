"""LangChain tools for the Compliance Agent: inspect certifications and
regulatory requirements, and identify missing or expired certifications.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from supplyguard.data import get_repository
from supplyguard.tools.registry import register_tool
from supplyguard.tools.resilience import safe_tool


@register_tool("compliance")
@tool
@safe_tool
def get_certifications(supplier_id: str) -> list[dict[str, Any]]:
    """Retrieve all certification records on file for a supplier.

    Each record includes its status (active, expired, suspended, revoked)
    and expiry_date. An empty list means the supplier has NO certifications
    on file at all -- that is itself a compliance gap to report, not a clean
    bill of health.

    Args:
        supplier_id: The exact supplier id, e.g. "SUP-002".
    """
    repo = get_repository()
    certs = repo.get_certifications(supplier_id)
    return [c.model_dump(mode="json") for c in certs]


@register_tool("compliance")
@tool
@safe_tool
def get_regulatory_requirements(industry: str) -> list[dict[str, Any]]:
    """Retrieve regulations applicable to a given supplier industry.

    Use the supplier's `industry` field (from get_supplier_by_id) as the
    input. Matches regulations tagged for that exact industry string or
    tagged as applicable to "all" industries. An empty list means no
    regulation in this dataset targets that industry string -- pass the
    supplier's industry exactly as returned by get_supplier_by_id rather
    than a paraphrase.

    Args:
        industry: The supplier's industry, e.g. "Mining - Cobalt & Copper".
    """
    repo = get_repository()
    regs = repo.get_regulations_for_industry(industry)
    return [r.model_dump(mode="json") for r in regs]
