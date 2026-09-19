"""Unit tests for the RAG ingestion pipeline's chunking step. Pure function,
no external services (no PDF, no Weaviate, no embedding model)."""
from __future__ import annotations

from supplyguard.rag.chunking import chunk_pages
from supplyguard.rag.parsing import PageContent


def test_chunk_pages_empty_list_produces_no_chunks():
    assert chunk_pages([], "DOC-1") == []


def test_chunk_pages_short_page_produces_one_chunk_with_expected_id():
    pages = [PageContent(page_number=1, text="A short page of audit text.")]
    chunks = chunk_pages(pages, "SUP-001-audit")

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_id == "SUP-001-audit-p1-c0"
    assert chunk.document_id == "SUP-001-audit"
    assert chunk.page_number == 1
    assert chunk.text == "A short page of audit text."


def test_chunk_pages_long_page_splits_into_multiple_overlapping_chunks():
    # Well over the 800-char chunk size, so this must split into >1 chunk.
    long_text = " ".join(f"Sentence number {i} of the audit report." for i in range(80))
    pages = [PageContent(page_number=1, text=long_text)]

    chunks = chunk_pages(pages, "SUP-002-audit")

    assert len(chunks) > 1
    # Chunk ids are contiguous and stable, e.g. ...-p1-c0, ...-p1-c1, ...
    assert [c.chunk_id for c in chunks] == [
        f"SUP-002-audit-p1-c{i}" for i in range(len(chunks))
    ]
    # Overlap: consecutive chunks share some trailing/leading text, so no
    # chunk boundary silently drops content a query might need.
    for first, second in zip(chunks, chunks[1:]):
        overlap_candidates = [
            first.text[-40:][i:] for i in range(0, 40, 5)
        ]
        assert any(candidate and candidate in second.text for candidate in overlap_candidates)


def test_chunk_pages_keeps_page_boundaries_separate():
    pages = [
        PageContent(page_number=1, text="Content that belongs to page one."),
        PageContent(page_number=2, text="Different content that belongs to page two."),
    ]

    chunks = chunk_pages(pages, "SUP-003-audit")

    assert [c.page_number for c in chunks] == [1, 2]
    assert [c.chunk_id for c in chunks] == ["SUP-003-audit-p1-c0", "SUP-003-audit-p2-c0"]
    # A chunk never mixes text from two different pages.
    assert "page one" in chunks[0].text and "page two" not in chunks[0].text
    assert "page two" in chunks[1].text and "page one" not in chunks[1].text
