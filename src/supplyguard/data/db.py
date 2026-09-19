"""SQLAlchemy engine/session setup for the Postgres-backed dataset.

This is the only module that knows the connection string. Everything else
(ORM models, the seed script, a future Postgres-backed repository) imports
`Base`, `engine`, or `SessionLocal` from here.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://supplyguard:supplyguard@localhost:5432/supplyguard",
)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
