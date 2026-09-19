from __future__ import annotations

import os
from functools import lru_cache

from supplyguard.data.base import BaseDataRepository, SupplierNotFoundError
from supplyguard.data.repository import JsonDataRepository

__all__ = [
    "BaseDataRepository",
    "SupplierNotFoundError",
    "JsonDataRepository",
    "get_repository",
]


@lru_cache(maxsize=1)
def get_repository() -> BaseDataRepository:
    """Process-wide singleton. Defaults to Postgres; set
    SUPPLYGUARD_DATA_BACKEND=json to run against the JSON fixtures directly
    (e.g. for tests that shouldn't depend on a running database).
    """
    backend = os.environ.get("SUPPLYGUARD_DATA_BACKEND", "postgres").lower()
    if backend == "json":
        return JsonDataRepository()

    from supplyguard.data.postgres_repository import PostgresDataRepository

    return PostgresDataRepository()
