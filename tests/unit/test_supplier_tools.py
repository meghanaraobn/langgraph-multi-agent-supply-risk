"""Unit tests for the Supplier Agent's tools. No LLM involved -- these are
plain functions wrapping repository queries, tested directly.
"""
from __future__ import annotations

from supplyguard.tools import get_supplier_by_id, search_supplier


def test_search_supplier_finds_by_partial_name():
    results = search_supplier.invoke({"query": "Cobalt"})
    assert len(results) == 1
    assert results[0]["id"] == "SUP-003"


def test_search_supplier_no_match_returns_empty_list():
    results = search_supplier.invoke({"query": "Definitely Not A Real Supplier Name"})
    assert results == []


def test_get_supplier_by_id_returns_full_record():
    result = get_supplier_by_id.invoke({"supplier_id": "SUP-011"})
    assert result["name"] == "Nordic Timber Group"
    assert "error" not in result


def test_get_supplier_by_id_unknown_id_returns_error_not_exception():
    result = get_supplier_by_id.invoke({"supplier_id": "SUP-999"})
    assert "error" in result
    assert "SUP-999" in result["error"]
