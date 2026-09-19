"""Real end-to-end test of the RAG ingestion pipeline against a live
Weaviate instance and the real embedding model -- no mocks.

Excluded by default (see the `integration` marker in pyproject.toml, mirroring
the existing `live` marker for the real Azure LLM). Run explicitly:

    docker compose up -d weaviate
    pytest -m integration tests/integration/test_rag_pipeline.py

Uses a dedicated supplier_id/document_id namespace (not any of the real
SUP-* demo suppliers) so it never collides with or pollutes the documents
ingested via scripts/generate_synthetic_pdfs.py + `python -m
supplyguard.rag.ingest`, and cleans up its own objects afterward.
"""
from __future__ import annotations

import pytest
from weaviate.classes.query import Filter

from supplyguard.rag.ingest import DEFAULT_DOCUMENTS_DIR, ingest_document
from supplyguard.rag.vector_store import _COLLECTION_NAME, get_client, get_chunk_by_id, search

pytestmark = pytest.mark.integration

_TEST_SUPPLIER_ID = "TEST-SUP-INTEGRATION"
_TEST_DOCUMENT_ID = "TEST-INTEGRATION-DOC"


@pytest.fixture
def ingested_test_document():
    pdf_path = DEFAULT_DOCUMENTS_DIR / "raw" / "SUP-001-audit-report.pdf"
    chunk_count = ingest_document(
        pdf_path,
        supplier_id=_TEST_SUPPLIER_ID,
        document_id=_TEST_DOCUMENT_ID,
        title="Integration Test Document",
    )
    yield chunk_count

    collection = get_client().collections.get(_COLLECTION_NAME)
    collection.data.delete_many(where=Filter.by_property("document_id").equal(_TEST_DOCUMENT_ID))


def test_ingest_then_search_finds_relevant_chunk(ingested_test_document):
    chunk_count = ingested_test_document
    assert chunk_count > 0

    results = search("fire extinguisher inspection", supplier_id=_TEST_SUPPLIER_ID, top_k=3)

    assert results
    assert any("extinguisher" in r["text"].lower() for r in results)
    assert all(r["document_id"] == _TEST_DOCUMENT_ID for r in results)


def test_search_is_isolated_by_supplier_id(ingested_test_document):
    results = search("fire extinguisher inspection", supplier_id="SUP-DOES-NOT-EXIST", top_k=3)

    assert results == []


def test_get_chunk_by_id_resolves_a_real_chunk(ingested_test_document):
    results = search("fire extinguisher inspection", supplier_id=_TEST_SUPPLIER_ID, top_k=1)
    chunk_id = results[0]["chunk_id"]

    resolved = get_chunk_by_id(chunk_id, _TEST_SUPPLIER_ID)

    assert resolved is not None
    assert resolved["chunk_id"] == chunk_id


def test_get_chunk_by_id_returns_none_for_unknown_chunk(ingested_test_document):
    assert get_chunk_by_id("no-such-chunk-id", _TEST_SUPPLIER_ID) is None


def test_hybrid_search_ranks_an_exact_proper_noun_match_first(ingested_test_document):
    """The whole point of hybrid over pure vector search: a literal proper
    noun (a specific place name here, standing in for a regulation,
    subcontractor, or certification code in a real query) should be an
    unambiguous top hit via BM25, not just "somewhere in the results" via
    an embedding that may blur it against paraphrases.
    """
    results = search("Hsinchu Science Park", supplier_id=_TEST_SUPPLIER_ID, top_k=3)

    assert results
    assert "Hsinchu" in results[0]["text"]


def test_hybrid_search_still_matches_a_paraphrase_with_no_shared_words(ingested_test_document):
    """Confirms the vector half of the fusion still carries semantic recall
    at alpha=0.7 -- this query shares no exact words with the source text
    ("fire extinguisher inspection tags... overdue").
    """
    results = search("overdue safety equipment checks", supplier_id=_TEST_SUPPLIER_ID, top_k=3)

    assert any("extinguisher" in r["text"].lower() for r in results)
