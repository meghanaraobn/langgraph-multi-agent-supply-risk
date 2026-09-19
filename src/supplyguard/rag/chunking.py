"""Splits parsed PDF pages into embeddable chunks.

Chunking is done per page, not across the whole document, so each chunk's
page_number is unambiguous -- a cross-page splitter would need to track
character offsets back to page boundaries for no real benefit at the 2-3
page document sizes this project ingests.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from supplyguard.rag.parsing import PageContent

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 120


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    """Stable and human-readable, e.g. "SUP-003-audit-p2-c0" -- cited
    verbatim by rag_agent as Evidence.source_id, so it must be reproducible
    across re-ingestion (see vector_store.upsert_chunks)."""

    document_id: str
    page_number: int
    text: str


def chunk_pages(pages: list[PageContent], document_id: str) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE, chunk_overlap=_CHUNK_OVERLAP
    )

    chunks: list[Chunk] = []
    for page in pages:
        for index, piece in enumerate(splitter.split_text(page.text)):
            chunk_id = f"{document_id}-p{page.page_number}-c{index}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    page_number=page.page_number,
                    text=piece,
                )
            )

    return chunks
