"""JSON-backed implementation of the shared DataRepository contract.

Every record is validated into a Pydantic model at load time, so a malformed
fixture fails loudly here, at startup, instead of silently producing bad tool
output deep inside an agent call later.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from supplyguard.data.base import BaseDataRepository, SupplierNotFoundError
from supplyguard.models import (
    Certification,
    Incident,
    Regulation,
    SanctionRecord,
    Supplier,
    SustainabilitySnapshot,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

ModelT = TypeVar("ModelT", bound=BaseModel)


class JsonDataRepository(BaseDataRepository):
    """Loads the synthetic dataset once and serves typed query methods over it."""

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
        self._data_dir = Path(data_dir)
        self._suppliers = self._load_typed("suppliers.json", Supplier)
        self._certifications = self._load_typed("certifications.json", Certification)
        self._incidents = self._load_typed("incidents.json", Incident)
        self._sanctions = self._load_typed("sanctions.json", SanctionRecord)
        self._sustainability = self._load_typed("sustainability.json", SustainabilitySnapshot)
        self._regulations = self._load_typed("regulations.json", Regulation)
        # Not modeled yet -- this file is the evaluation harness's own answer
        # key (step 19), not domain data agents query, so it stays raw dicts
        # until that milestone defines its shape.
        self._evaluation_cases = self._load_raw("evaluation_cases.json")

    def _load_raw(self, filename: str) -> list[dict[str, Any]]:
        path = self._data_dir / filename
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_typed(self, filename: str, model: type[ModelT]) -> list[ModelT]:
        return [model.model_validate(record) for record in self._load_raw(filename)]

    # -- suppliers ---------------------------------------------------------

    def list_suppliers(self) -> list[Supplier]:
        return list(self._suppliers)

    def get_supplier(self, supplier_id: str) -> Supplier:
        for supplier in self._suppliers:
            if supplier.id == supplier_id:
                return supplier
        raise SupplierNotFoundError(supplier_id)

    def search_suppliers(self, query: str) -> list[Supplier]:
        """Case-insensitive substring search across name, country, and industry."""
        needle = query.lower()
        return [
            s
            for s in self._suppliers
            if needle in s.name.lower() or needle in s.country.lower() or needle in s.industry.lower()
        ]

    # -- certifications ------------------------------------------------------

    def get_certifications(self, supplier_id: str) -> list[Certification]:
        return [c for c in self._certifications if c.supplier_id == supplier_id]

    # -- incidents -----------------------------------------------------------

    def get_incidents(self, supplier_id: str) -> list[Incident]:
        return [i for i in self._incidents if i.supplier_id == supplier_id]

    # -- sanctions -------------------------------------------------------------
    # Two distinct queries on purpose: a confirmed FK lookup, and a raw name
    # search that returns everything (including false positives) so a future
    # agent has to reason about match_confidence itself instead of trusting
    # match_supplier_id blindly.

    def list_sanctions(self) -> list[SanctionRecord]:
        return list(self._sanctions)

    def get_confirmed_sanctions_matches(self, supplier_id: str) -> list[SanctionRecord]:
        return [s for s in self._sanctions if s.match_supplier_id == supplier_id]

    def search_sanctions_by_name(self, query: str) -> list[SanctionRecord]:
        needle = query.lower()
        return [s for s in self._sanctions if needle in s.entity_name.lower()]

    # -- sustainability --------------------------------------------------------

    def get_sustainability(self, supplier_id: str) -> SustainabilitySnapshot | None:
        for record in self._sustainability:
            if record.supplier_id == supplier_id:
                return record
        return None

    # -- regulations -------------------------------------------------------------

    def list_regulations(self) -> list[Regulation]:
        return list(self._regulations)

    def get_regulations_for_industry(self, industry: str) -> list[Regulation]:
        return [
            r
            for r in self._regulations
            if industry in r.applicable_industries or "all" in r.applicable_industries
        ]

    # -- evaluation cases --------------------------------------------------------

    def list_evaluation_cases(self) -> list[dict[str, Any]]:
        return list(self._evaluation_cases)

    def get_evaluation_case(self, case_id: str) -> dict[str, Any]:
        for case in self._evaluation_cases:
            if case["id"] == case_id:
                return case
        raise KeyError(case_id)
