"""LangChain tools for the Supplier Agent: identify a supplier and retrieve
its metadata. Per the spec, this agent must never invent supplier
information -- these tools only ever return what the repository actually has
on file, or an explicit "not found" result the LLM can react to.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from supplyguard.data import SupplierNotFoundError, get_repository
from supplyguard.tools.registry import register_tool
from supplyguard.tools.resilience import safe_tool


@register_tool("supplier")
@tool
@safe_tool
def search_supplier(query: str) -> list[dict[str, Any]]:
    """Search for suppliers by a partial name, country, or industry match.

    Use this when you have a supplier name (possibly partial or misspelled)
    or a general description like "textile suppliers in Bangladesh" and need
    to find the matching supplier record(s) before doing anything else.
    Returns zero or more supplier summaries; if zero, the supplier is not in
    the system under that name -- do not guess or invent a supplier id.

    Args:
        query: Partial or full supplier name, country, or industry to search for.
    """
    repo = get_repository()
    matches = repo.search_suppliers(query)
    return [s.model_dump(mode="json") for s in matches]


@register_tool("supplier")
@tool
@safe_tool
def get_supplier_by_id(supplier_id: str) -> dict[str, Any]:
    """Retrieve the full supplier record for a known, exact supplier id.

    Use this once you already have a confirmed supplier id (e.g. from
    search_supplier). Returns an error message if the id does not exist --
    treat that as a hard stop, never fabricate a supplier record.

    Args:
        supplier_id: The exact supplier id, e.g. "SUP-003".
    """
    repo = get_repository()
    try:
        supplier = repo.get_supplier(supplier_id)
    except SupplierNotFoundError:
        return {"error": f"No supplier found with id '{supplier_id}'."}
    return supplier.model_dump(mode="json")
