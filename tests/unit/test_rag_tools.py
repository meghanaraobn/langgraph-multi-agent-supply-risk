"""Unit tests for the RAG Agent's search_documents tool. vector_store.search
is monkeypatched -- no live Weaviate or embedding model needed, matching
this repo's other tool tests (e.g. test_compliance_tools.py), which hit a
real (but local, dependency-free) backend rather than a live external one.
"""
from __future__ import annotations

from supplyguard.tools import search_documents


def test_search_documents_returns_vector_store_results(monkeypatch):
    fake_results = [
        {"chunk_id": "SUP-003-audit-p1-c1", "page_number": 1, "text": "some finding", "distance": 0.31},
    ]
    calls = {}

    def fake_search(query, supplier_id, top_k=5):
        calls["args"] = (query, supplier_id, top_k)
        return fake_results

    monkeypatch.setattr("supplyguard.tools.rag.search", fake_search)

    result = search_documents.invoke(
        {"supplier_id": "SUP-003", "query": "child labor findings", "top_k": 3}
    )

    assert result == fake_results
    assert calls["args"] == ("child labor findings", "SUP-003", 3)


def test_search_documents_defaults_top_k_to_five(monkeypatch):
    calls = {}

    def fake_search(query, supplier_id, top_k=5):
        calls["top_k"] = top_k
        return []

    monkeypatch.setattr("supplyguard.tools.rag.search", fake_search)

    search_documents.invoke({"supplier_id": "SUP-001", "query": "anything"})

    assert calls["top_k"] == 5


def test_search_documents_no_results_returns_empty_list(monkeypatch):
    monkeypatch.setattr("supplyguard.tools.rag.search", lambda query, supplier_id, top_k=5: [])

    result = search_documents.invoke({"supplier_id": "SUP-099", "query": "anything"})

    assert result == []


def test_search_documents_failure_returns_error_dict_not_raise(monkeypatch):
    def raising_search(query, supplier_id, top_k=5):
        raise ConnectionError("weaviate unreachable")

    monkeypatch.setattr("supplyguard.tools.rag.search", raising_search)

    result = search_documents.invoke({"supplier_id": "SUP-003", "query": "anything"})

    assert "error" in result
    assert "ConnectionError" in result["error"]
