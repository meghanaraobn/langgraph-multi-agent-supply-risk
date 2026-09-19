"""Weaviate v4 client wrapper for the DocumentChunk collection.

Vectors are always supplied client-side (embeddings.py), never computed by
Weaviate itself -- the collection is created with self-provided vectors
(Configure.Vectors.self_provided()) so there's no dependency on a text2vec
inference module running inside Weaviate, just the base server plus
whatever the docker-compose ports expose.

search() uses Weaviate's hybrid search (BM25 keyword matching fused with
vector similarity via `alpha`), not pure vector search -- audit report text
contains exact terms (regulation names, subcontractor names, certification
codes) that a semantic-only search over a paraphrase-tuned embedding can
under-rank relative to a query that just names the term directly.

chunk_id (a human-readable string like "SUP-003-audit-p2-c0", not Weaviate's
own UUID primary key) is what rag_agent actually cites in Evidence.source_id
and what grounding.py looks records up by -- it's deterministically mapped
to the object's UUID via generate_uuid5, so re-ingesting the same document
overwrites the same objects instead of accumulating duplicates.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import Filter, MetadataQuery
from weaviate.util import generate_uuid5

from supplyguard.config import get_settings
from supplyguard.rag.chunking import Chunk
from supplyguard.rag.embeddings import embed_query

_COLLECTION_NAME = "DocumentChunk"

# 0.0 = pure BM25 keyword search, 1.0 = pure vector search. 0.7 leans toward
# semantic matching (rag_agent's queries are natural-language descriptions
# like "child labor findings", not exact terms) while still letting BM25
# pull in exact-term hits -- regulation names, subcontractor names,
# certification codes -- that a paraphrase-tuned embedding can blur.
_DEFAULT_HYBRID_ALPHA = 0.7


@lru_cache(maxsize=1)
def get_client() -> weaviate.WeaviateClient:
    settings = get_settings()
    return weaviate.connect_to_local(
        host=settings.weaviate_host,
        port=settings.weaviate_http_port,
        grpc_port=settings.weaviate_grpc_port,
    )


def ensure_collection() -> None:
    client = get_client()
    if client.collections.exists(_COLLECTION_NAME):
        return

    client.collections.create(
        _COLLECTION_NAME,
        vector_config=Configure.Vectors.self_provided(),
        properties=[
            Property(name="chunk_id", data_type=DataType.TEXT),
            Property(name="document_id", data_type=DataType.TEXT),
            Property(name="document_title", data_type=DataType.TEXT),
            Property(name="supplier_id", data_type=DataType.TEXT),
            Property(name="page_number", data_type=DataType.INT),
            Property(name="text", data_type=DataType.TEXT),
        ],
    )


def _to_dict(obj: Any, include_score: bool = False) -> dict[str, Any]:
    result = dict(obj.properties)
    if include_score and obj.metadata is not None:
        result["score"] = obj.metadata.score
    return result


def upsert_chunks(
    chunks: list[Chunk], vectors: list[list[float]], supplier_id: str, document_title: str
) -> int:
    if not chunks:
        return 0

    ensure_collection()
    collection = get_client().collections.get(_COLLECTION_NAME)

    document_id = chunks[0].document_id
    collection.data.delete_many(where=Filter.by_property("document_id").equal(document_id))

    with collection.batch.dynamic() as batch:
        for chunk, vector in zip(chunks, vectors):
            batch.add_object(
                properties={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "document_title": document_title,
                    "supplier_id": supplier_id,
                    "page_number": chunk.page_number,
                    "text": chunk.text,
                },
                uuid=generate_uuid5(chunk.chunk_id),
                vector=vector,
            )

    return len(chunks)


def search(
    query: str, supplier_id: str, top_k: int = 5, alpha: float = _DEFAULT_HYBRID_ALPHA
) -> list[dict[str, Any]]:
    """Hybrid search: BM25 keyword matching fused with vector similarity.

    vector is passed explicitly (not left for Weaviate to compute) because
    the collection has no server-side vectorizer module -- see
    ensure_collection. query is still passed alongside it so the BM25 half
    of the fusion runs against the literal query text.
    """
    ensure_collection()
    collection = get_client().collections.get(_COLLECTION_NAME)

    result = collection.query.hybrid(
        query=query,
        vector=embed_query(query),
        alpha=alpha,
        limit=top_k,
        filters=Filter.by_property("supplier_id").equal(supplier_id),
        return_metadata=MetadataQuery(score=True),
    )
    return [_to_dict(obj, include_score=True) for obj in result.objects]


def get_chunk_by_id(chunk_id: str, supplier_id: str) -> Optional[dict[str, Any]]:
    ensure_collection()
    collection = get_client().collections.get(_COLLECTION_NAME)

    result = collection.query.fetch_objects(
        filters=(
            Filter.by_property("chunk_id").equal(chunk_id)
            & Filter.by_property("supplier_id").equal(supplier_id)
        ),
        limit=1,
    )
    if not result.objects:
        return None
    return _to_dict(result.objects[0])
