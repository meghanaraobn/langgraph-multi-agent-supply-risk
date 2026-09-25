"""LangChain tool for the Sustainability Agent: inspect a supplier's reported
sustainability/ESG data.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from supplyguard.data import get_repository
from supplyguard.tools.registry import register_tool
from supplyguard.tools.resilience import safe_tool


@register_tool("sustainability")
@tool
@safe_tool
def get_sustainability_information(supplier_id: str) -> dict[str, Any]:
    """Retrieve the sustainability/ESG disclosure on file for a supplier
    (emissions, renewable energy %, water use, waste recycled, ESG score).

    If no record exists, this returns an explicit "no data on file" result --
    that is a missing-information finding to report, not evidence the
    supplier has no sustainability impact.

    Args:
        supplier_id: The exact supplier id, e.g. "SUP-011".
    """
    repo = get_repository()
    record = repo.get_sustainability(supplier_id)
    if record is None:
        return {"supplier_id": supplier_id, "status": "no_sustainability_data_on_file"}
    return record.model_dump(mode="json")
