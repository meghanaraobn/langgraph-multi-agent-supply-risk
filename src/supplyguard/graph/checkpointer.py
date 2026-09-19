"""Durable, Postgres-backed checkpointer for the investigation graph.

Replaces the in-memory checkpointer from step 16 -- state now survives
process restarts, not just the lifetime of one Python process, which is
what actually makes an investigation "resumable" in the sense the spec
means (a human reviewing hours later, via a completely separate request).

Explicitly allow-lists our own domain models for msgpack (de)serialization.
LangGraph's default behavior for an unlisted type is to warn now and hard
-block it in a future version; since every one of these classes is our own
fully-trusted domain model (not arbitrary external data), allow-listing them
here is the correct fix, not a workaround.

Backed by a connection POOL, not a single shared connection. Every use of
this checkpointer up through step 20 was strictly one call at a time in one
process, so a single psycopg.connect() connection never got touched from
two places at once. The API layer (step 22) is the first thing that
actually runs concurrently -- a background task writing checkpoints while a
GET request reads the latest state, potentially from a different thread.
psycopg connections are explicitly not safe for concurrent use by multiple
threads; a ConnectionPool is the standard fix, handing each caller its own
connection for the duration of one operation.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg_pool import ConnectionPool

from supplyguard.data.db import DATABASE_URL
from supplyguard.models import (
    Certification,
    ConfidenceLevel,
    DecisionType,
    Evidence,
    Finding,
    HumanDecision,
    Incident,
    InvestigationPlan,
    Regulation,
    RiskAssessment,
    RiskLevel,
    SanctionRecord,
    Severity,
    Supplier,
    SupplierContact,
    SustainabilitySnapshot,
)

_ALLOWED_MODELS = [
    Supplier,
    SupplierContact,
    Certification,
    Incident,
    SanctionRecord,
    SustainabilitySnapshot,
    Regulation,
    Finding,
    Evidence,
    RiskAssessment,
    RiskLevel,
    Severity,
    ConfidenceLevel,
    InvestigationPlan,
    HumanDecision,
    DecisionType,
]


def _psycopg_dsn(sqlalchemy_url: str) -> str:
    """psycopg.connect() wants a plain postgresql:// DSN, not SQLAlchemy's
    driver-qualified postgresql+psycopg:// form used by DATABASE_URL."""
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://", 1)


@lru_cache(maxsize=1)
def get_checkpointer() -> PostgresSaver:
    pool = ConnectionPool(
        _psycopg_dsn(DATABASE_URL),
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True},
        open=True,
    )
    serde = JsonPlusSerializer(allowed_msgpack_modules=_ALLOWED_MODELS)
    checkpointer = PostgresSaver(conn=pool, serde=serde)
    checkpointer.setup()
    return checkpointer
