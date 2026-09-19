"""LangChain tool for the RAG Agent: hybrid (keyword + semantic) search over
a supplier's ingested unstructured documents (audit reports, disclosures,
...).
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from supplyguard.rag.vector_store import search
from supplyguard.tools.resilience import safe_tool


@tool
@safe_tool
def search_documents(supplier_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search the unstructured documents ingested for a supplier (e.g.
    on-site audit reports) and return the most relevant passages. Combines
    keyword and semantic matching, so both a specific term (a regulation
    name, a subcontractor name, a certification code) and a paraphrased,
    natural-language description will surface relevant passages.

    Each result includes a chunk_id -- cite this exact string as
    Evidence.source_id (with source_type="document") for any finding you
    base on it, since that's what grounding verifies against. An empty list
    means no document has been ingested for this supplier yet, or nothing
    in it is relevant to the query -- not necessarily that nothing is wrong.

    Args:
        supplier_id: The exact supplier id, e.g. "SUP-003".
        query: A natural-language description of what to look for, e.g.
            "child labor findings", or a specific term you already suspect
            is relevant, e.g. a subcontractor or regulation name.
        top_k: Maximum number of passages to return (default 5).
    """
    return search(query, supplier_id=supplier_id, top_k=top_k)
