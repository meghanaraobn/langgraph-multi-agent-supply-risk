"""Shared contract for the two DataRepository backends (JSON, Postgres).

An ABC rather than a typing.Protocol on purpose: forgetting to implement one
of these methods on a new backend should fail loudly the moment it's
instantiated, not show up only as a mypy warning that's easy to miss.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from supplyguard.models import (
    Certification,
    Incident,
    Regulation,
    SanctionRecord,
    Supplier,
    SustainabilitySnapshot,
)


class SupplierNotFoundError(Exception):
    """Raised when a supplier id does not exist in the dataset."""


class BaseDataRepository(ABC):
    @abstractmethod
    def list_suppliers(self) -> list[Supplier]: ...

    @abstractmethod
    def get_supplier(self, supplier_id: str) -> Supplier: ...

    @abstractmethod
    def search_suppliers(self, query: str) -> list[Supplier]: ...

    @abstractmethod
    def get_certifications(self, supplier_id: str) -> list[Certification]: ...

    @abstractmethod
    def get_incidents(self, supplier_id: str) -> list[Incident]: ...

    @abstractmethod
    def list_sanctions(self) -> list[SanctionRecord]: ...

    @abstractmethod
    def get_confirmed_sanctions_matches(self, supplier_id: str) -> list[SanctionRecord]: ...

    @abstractmethod
    def search_sanctions_by_name(self, query: str) -> list[SanctionRecord]: ...

    @abstractmethod
    def get_sustainability(self, supplier_id: str) -> SustainabilitySnapshot | None: ...

    @abstractmethod
    def list_regulations(self) -> list[Regulation]: ...

    @abstractmethod
    def get_regulations_for_industry(self, industry: str) -> list[Regulation]: ...

    @abstractmethod
    def list_evaluation_cases(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_evaluation_case(self, case_id: str) -> dict[str, Any]: ...
