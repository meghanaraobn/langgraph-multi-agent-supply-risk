"""Per-case scoring functions, one per dimension named in the spec:
supplier identification, tool selection, evidence grounding, structured
output validity, human-review routing, final risk classification, and
missing-information detection.

Each function takes the evaluation case (the answer key) and the raw dict
graph.invoke() returned, and returns a bool -- or, for the two dimensions
that don't apply uniformly to every case, None to mean "not applicable"
rather than a misleading pass/fail.
"""
from __future__ import annotations

from typing import Any

from supplyguard.models import RiskAssessment


def score_supplier_identification(case: dict[str, Any], result: dict[str, Any]) -> bool:
    supplier = result.get("supplier")
    return supplier is not None and supplier.id == case["supplier_id"]


def score_tool_selection(case: dict[str, Any], result: dict[str, Any]) -> bool:
    plan = result.get("investigation_plan")
    if plan is None:
        return False
    return set(plan.agents_to_run) == set(case["expected_agents_triggered"])


def score_structured_output_validity(result: dict[str, Any]) -> bool:
    return isinstance(result.get("risk_assessment"), RiskAssessment)


def score_human_review_routing(case: dict[str, Any], result: dict[str, Any]) -> bool:
    paused = "__interrupt__" in result
    expected_pause = case["expected_route"] == "human_review"
    return paused == expected_pause


def score_final_risk_classification(case: dict[str, Any], result: dict[str, Any]) -> bool:
    assessment = result.get("risk_assessment")
    if not isinstance(assessment, RiskAssessment):
        return False
    return assessment.risk_level.value == case["expected_risk_level"]


def count_grounding_rejections(result: dict[str, Any]) -> int:
    """Not pass/fail. A finding that fails grounding is already filtered out
    of state by ground_findings before this metric ever sees it (see
    agents/grounding.py) -- that's by design, and this dataset has no case
    where a fabricated finding is EXPECTED to survive. This instead counts
    how often the LLM attempted an ungrounded citation in the first place: a
    quality signal on the model's citation discipline, not a pipeline
    defect. Zero is good; a nonzero count means the guardrail did its job,
    not that the run failed.
    """
    return sum(1 for e in result.get("errors", []) if "does not resolve to a real record" in e)


def score_missing_information_detection(
    case: dict[str, Any], result: dict[str, Any]
) -> bool | None:
    """Best-effort: only a few cases in the dataset are explicitly about a
    missing-data gap (an expected_flags entry starting with "no_", or
    containing "missing"). Returns None for every other case rather than
    scoring something the case was never designed to test.
    """
    expects_gap = any(
        flag.startswith("no_") or "missing" in flag for flag in case.get("expected_flags", [])
    )
    if not expects_gap:
        return None
    return bool(result.get("missing_information"))
