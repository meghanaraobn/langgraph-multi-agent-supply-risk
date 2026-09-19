"""LangChain tools for the Risk Agent: investigate incidents and sanctions
exposure. Every risk finding this agent produces must cite evidence from one
of these tools -- never assert a risk without a supporting record.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from supplyguard.data import get_repository
from supplyguard.tools.resilience import safe_tool


@tool
@safe_tool
def search_incidents(supplier_id: str) -> list[dict[str, Any]]:
    """Retrieve reported incidents (labor, safety, environmental, corruption,
    etc.) on file for a supplier.

    Each record includes `severity` and `status` (open, under_investigation,
    resolved) independently -- a resolved incident with verified corrective
    action is materially different from an open one of the same severity; do
    not treat them as equivalent risk. An empty list means no incidents are
    on file, not that the supplier is confirmed clean.

    Args:
        supplier_id: The exact supplier id, e.g. "SUP-003".
    """
    repo = get_repository()
    incidents = repo.get_incidents(supplier_id)
    return [i.model_dump(mode="json") for i in incidents]


@tool
@safe_tool
def check_sanctions(supplier_name: str) -> list[dict[str, Any]]:
    """Search sanctions watchlists (OFAC, EU, UK, UN) for entities whose name
    resembles the given supplier name.

    IMPORTANT: this performs a raw name search and returns every superficial
    match, including false positives -- a returned row is NOT confirmation of
    a real sanctions hit. You must inspect `match_confidence` and
    `sanction_reason` on each result yourself: "exact" or "high" confidence
    with a plausible reason supports a real match; "low" or "none" confidence,
    or a reason describing a clearly unrelated entity, means this is very
    likely a coincidental name collision and must NOT be reported as a
    sanctions finding. Never treat the mere presence of a result as a hit.

    Args:
        supplier_name: The supplier's name (or a close variant) to screen.
    """
    repo = get_repository()
    hits = repo.search_sanctions_by_name(supplier_name)
    return [h.model_dump(mode="json") for h in hits]
