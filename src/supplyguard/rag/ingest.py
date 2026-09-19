"""Ingestion pipeline: PDF -> parse -> chunk -> embed -> upsert into Weaviate.

Run as a script (`python -m supplyguard.rag.ingest`) after the synthetic
PDFs exist in data/documents/raw/ (see scripts/generate_synthetic_pdfs.py)
and Weaviate is up (`docker compose up -d weaviate`). Reads
data/documents/manifest.json to know which PDF belongs to which supplier.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from supplyguard.rag.chunking import chunk_pages
from supplyguard.rag.embeddings import embed_documents
from supplyguard.rag.parsing import extract_pages
from supplyguard.rag.vector_store import upsert_chunks

logger = logging.getLogger(__name__)

DEFAULT_DOCUMENTS_DIR = Path(__file__).resolve().parents[3] / "data" / "documents"


def ingest_document(pdf_path: str | Path, supplier_id: str, document_id: str, title: str) -> int:
    """Parses, chunks, embeds, and upserts one PDF. Returns the chunk count.

    Re-running this for the same document_id is safe -- upsert_chunks
    deletes any existing objects for that document_id before inserting.
    """
    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages, document_id)
    if not chunks:
        logger.warning("%s produced no chunks (empty or unparsable PDF)", pdf_path)
        return 0

    vectors = embed_documents([chunk.text for chunk in chunks])
    return upsert_chunks(chunks, vectors, supplier_id=supplier_id, document_title=title)


def ingest_from_manifest(documents_dir: Path | str = DEFAULT_DOCUMENTS_DIR) -> None:
    documents_dir = Path(documents_dir)
    manifest = json.loads((documents_dir / "manifest.json").read_text())

    for entry in manifest:
        pdf_path = documents_dir / "raw" / entry["file"]
        count = ingest_document(
            pdf_path,
            supplier_id=entry["supplier_id"],
            document_id=entry["document_id"],
            title=entry["title"],
        )
        logger.info("Ingested %s: %d chunks (%s)", entry["file"], count, entry["supplier_id"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_from_manifest()
