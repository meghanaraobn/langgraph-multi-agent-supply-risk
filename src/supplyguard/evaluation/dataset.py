"""Loads the evaluation dataset.

Deliberately reads from the JSON-backed repository directly, not
get_repository()'s default (Postgres) -- the evaluation answer key should be
pinned to exactly what's authored on disk in data/evaluation_cases.json,
immune to whatever happens to be currently seeded in the database. Re-run
`python -m supplyguard.data.seed` separately if you also want Postgres in
sync with the latest cases.

IMPORTANT: every expected_* value in this dataset is a synthetic prediction
authored for this fictional dataset, produced by hand or by observing this
project's own agents during development. None of it is a real compliance,
sanctions, or risk determination about any real company -- see
docs/architecture.md for the synthetic-data disclosure.
"""
from __future__ import annotations

from typing import Any

from supplyguard.data.repository import JsonDataRepository


def load_evaluation_cases() -> list[dict[str, Any]]:
    return JsonDataRepository().list_evaluation_cases()
