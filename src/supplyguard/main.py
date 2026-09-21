"""FastAPI application entrypoint.

Investigations run entirely through the LangGraph checkpointer -- there is
no separate results table. POST /investigations starts a background task;
GET /investigations/{id} reads that same graph's persisted state back.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import nltk
from fastapi import FastAPI

from supplyguard.api import router
from supplyguard.graph.checkpointer import get_checkpointer

logger = logging.getLogger("supplyguard.main")


def _ensure_nltk_data() -> None:
    """chunk_pages' NLTKTextSplitter needs the punkt_tab sentence-boundary
    model; check at boot rather than failing on the first document upload."""
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError as exc:
        raise RuntimeError(
            "NLTK 'punkt_tab' tokenizer data is missing (required by "
            "supplyguard.rag.chunking). Run `python -m nltk.downloader punkt_tab`, "
            "or rebuild the Docker image so it's baked in."
        ) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_nltk_data()
    yield
    # Close the connection pool explicitly on shutdown rather than relying
    # on ConnectionPool.__del__ during interpreter finalization, which
    # raises PythonFinalizationError under Python 3.13+'s stricter shutdown
    # semantics. Wrapped defensively: this runs during shutdown, and a
    # failure here (e.g. the pool already closed) shouldn't mask whatever
    # else is happening during teardown -- log it and move on.
    try:
        get_checkpointer().conn.close()
    except Exception:  # noqa: BLE001 -- best-effort cleanup on shutdown
        logger.exception("Failed to close checkpointer connection pool during shutdown")


app = FastAPI(
    title="SupplyGuard AI",
    description=(
        "Multi-agent supply chain risk investigation API. Start an investigation, poll for "
        "status/result, and submit a human review decision when one is required. "
        "See docs/architecture.md in the repo for the full agent pipeline this drives."
    ),
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
