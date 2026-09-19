"""Factory for the sentence-transformers embedding model used across
ingestion and retrieval.

BAAI/bge-* models are trained asymmetrically: a query benefits from an
instruction prefix ("Represent this sentence for searching relevant
passages: ") that document text should NOT get, or the two sides of a
search drift out of the embedding space the model was tuned for. That's why
this module exposes embed_documents/embed_query separately rather than one
generic embed() -- using the wrong one silently degrades retrieval quality
without ever raising an error.
"""
from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from supplyguard.config import get_settings

_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# bge-large-en-v1.5 is a ~1.3GB model -- batching in small groups keeps peak
# memory bounded on CPU instead of relying on encode()'s library default
# (32), which was tuned for smaller models.
_DEFAULT_BATCH_SIZE = 16


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model_name)


def embed_documents(texts: list[str], batch_size: int = _DEFAULT_BATCH_SIZE) -> list[list[float]]:
    vectors = get_embedder().encode(
        texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False
    )
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    vector = get_embedder().encode(_QUERY_INSTRUCTION + text, normalize_embeddings=True)
    return vector.tolist()
