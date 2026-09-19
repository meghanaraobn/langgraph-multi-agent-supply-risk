"""Runs evaluation cases through the real investigation graph and scores
each one against the dataset's ground truth.

A case whose expected_route is human_review is invoked once and checked for
the pause signal (__interrupt__ present in the result) -- the point of this
harness is scoring the routing/classification decisions made BEFORE that
pause, not exercising the full human-review round trip (that's covered
separately, live, in step 16's interrupt/resume tests). Each case gets its
own unique thread_id, so paused checkpoints from different cases never
collide.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from supplyguard.evaluation.dataset import load_evaluation_cases
from supplyguard.evaluation.metrics import (
    count_grounding_rejections,
    score_final_risk_classification,
    score_human_review_routing,
    score_missing_information_detection,
    score_structured_output_validity,
    score_supplier_identification,
    score_tool_selection,
)
from supplyguard.graph import build_investigation_graph, create_initial_state


@dataclass
class CaseResult:
    case_id: str
    supplier_id: str
    duration_s: float
    supplier_identification: bool
    tool_selection: bool
    structured_output_validity: bool
    human_review_routing: bool
    final_risk_classification: bool
    missing_information_detection: bool | None
    grounding_rejections: int
    error: str | None = None


def run_case(graph: Any, case: dict[str, Any]) -> CaseResult:
    thread_id = f"eval-{case['id']}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    start = time.time()
    try:
        result = graph.invoke(create_initial_state(case["id"], case["user_request"]), config=config)
        error = None
    except Exception as exc:  # noqa: BLE001 -- record and keep scoring the remaining cases
        result = {}
        error = f"{type(exc).__name__}: {exc}"
    duration = time.time() - start

    return CaseResult(
        case_id=case["id"],
        supplier_id=case["supplier_id"],
        duration_s=duration,
        supplier_identification=score_supplier_identification(case, result),
        tool_selection=score_tool_selection(case, result),
        structured_output_validity=score_structured_output_validity(result),
        human_review_routing=score_human_review_routing(case, result),
        final_risk_classification=score_final_risk_classification(case, result),
        missing_information_detection=score_missing_information_detection(case, result),
        grounding_rejections=count_grounding_rejections(result),
        error=error,
    )


def run_evaluation(case_ids: list[str] | None = None) -> list[CaseResult]:
    graph = build_investigation_graph()
    cases = load_evaluation_cases()
    if case_ids is not None:
        wanted = set(case_ids)
        cases = [c for c in cases if c["id"] in wanted]
    return [run_case(graph, case) for case in cases]


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    n = len(results)

    def rate(attr: str) -> float:
        return sum(1 for r in results if getattr(r, attr)) / n if n else 0.0

    applicable_missing = [r for r in results if r.missing_information_detection is not None]
    missing_rate = (
        sum(1 for r in applicable_missing if r.missing_information_detection)
        / len(applicable_missing)
        if applicable_missing
        else None
    )

    return {
        "n_cases": n,
        "supplier_identification_rate": rate("supplier_identification"),
        "tool_selection_rate": rate("tool_selection"),
        "structured_output_validity_rate": rate("structured_output_validity"),
        "human_review_routing_rate": rate("human_review_routing"),
        "final_risk_classification_rate": rate("final_risk_classification"),
        "missing_information_detection_rate": missing_rate,
        "missing_information_applicable_cases": len(applicable_missing),
        "total_grounding_rejections": sum(r.grounding_rejections for r in results),
        "errors": [f"{r.case_id}: {r.error}" for r in results if r.error],
    }
