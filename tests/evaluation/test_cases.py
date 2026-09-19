"""Evaluation tests -- a thin pytest wrapper around the evaluation harness
in supplyguard.evaluation.

Marked "live": these run real investigations through the real graph and the
real Azure-hosted LLM, at real cost and real latency (each of the 20 cases
takes roughly 20-40s). Excluded from a plain `pytest` run by this project's
default addopts; run explicitly with `pytest -m live tests/evaluation`.

The thresholds below are floors based on an actual full run (see
docs/architecture.md / conversation history for the analysis), not
aspirational targets -- they exist to catch a genuine regression, not to
demand perfection on dimensions with a known, already-diagnosed gap (e.g.
final_risk_classification, where some "clean" suppliers land on "medium"
instead of "low" because a regulation-applicability note gets treated as a
Finding -- a real, understood calibration question, not a bug this test
should chase).

IMPORTANT: every expected_* value in data/evaluation_cases.json is a
synthetic prediction authored for this project's fictional dataset -- not a
real compliance, sanctions, or risk determination about any real company.
"""
from __future__ import annotations

import pytest

from supplyguard.evaluation import run_evaluation, summarize

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def evaluation_summary() -> dict:
    """Runs the full 20-case suite exactly once per test session, since
    each case is a real, paid LLM call -- individual assertions below share
    this one run instead of re-running the dataset per test.
    """
    return summarize(run_evaluation())


def test_no_case_crashes(evaluation_summary: dict) -> None:
    assert evaluation_summary["errors"] == []


def test_supplier_identification_is_perfect(evaluation_summary: dict) -> None:
    assert evaluation_summary["supplier_identification_rate"] == 1.0


def test_tool_selection_is_perfect(evaluation_summary: dict) -> None:
    assert evaluation_summary["tool_selection_rate"] == 1.0


def test_structured_output_is_always_valid(evaluation_summary: dict) -> None:
    assert evaluation_summary["structured_output_validity_rate"] == 1.0


def test_human_review_routing_meets_baseline(evaluation_summary: dict) -> None:
    assert evaluation_summary["human_review_routing_rate"] >= 0.9


def test_final_risk_classification_meets_baseline(evaluation_summary: dict) -> None:
    assert evaluation_summary["final_risk_classification_rate"] >= 0.6
