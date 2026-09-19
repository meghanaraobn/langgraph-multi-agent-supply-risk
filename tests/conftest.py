"""Shared pytest configuration.

Sets SUPPLYGUARD_DATA_BACKEND=json before any test imports supplyguard.data,
so the whole non-live suite runs against the fast, hermetic JSON-backed
repository -- no Docker/Postgres required to run `pytest`. This is exactly
why the JSON backend was kept alongside Postgres in the first place: it's
the zero-dependency test backend, Postgres is the production one.
"""
from __future__ import annotations

import os

os.environ.setdefault("SUPPLYGUARD_DATA_BACKEND", "json")
