"""Unit tests for deterministic risk rules -- the hard-coded business logic
that must hold regardless of what any LLM produces.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from supplyguard.agents.grounding import ground_findings
from supplyguard.models import ConfidenceLevel, Evidence, Finding, RiskAssessment, RiskLevel, Severity


def _finding(evidence: list[Evidence], severity: Severity = Severity.HIGH, title: str = "t") -> Finding:
    return Finding(
        category="risk",
        severity=severity,
        title=title,
        description="...",
        evidence=evidence,
        confidence=ConfidenceLevel.HIGH,
        source="risk_agent",
    )


class TestFindingEvidenceRequirement:
    def test_empty_evidence_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _finding(evidence=[])

    def test_non_empty_evidence_is_accepted(self) -> None:
        finding = _finding(
            evidence=[Evidence(source_type="incident", source_id="INC-001", detail="x")]
        )
        assert len(finding.evidence) == 1


class TestRiskAssessmentHumanReviewThreshold:
    """RiskAssessment._enforce_human_review_threshold (step 3) must win
    regardless of what value a caller (or an LLM's structured output)
    tries to set -- this is what makes step 16's routing trustworthy.
    """

    @pytest.mark.parametrize("level", [RiskLevel.HIGH, RiskLevel.CRITICAL])
    def test_high_and_critical_always_require_review(self, level: RiskLevel) -> None:
        assessment = RiskAssessment(risk_level=level, rationale="x", requires_human_review=False)
        assert assessment.requires_human_review is True

    @pytest.mark.parametrize("level", [RiskLevel.LOW, RiskLevel.MEDIUM])
    def test_low_and_medium_never_require_review(self, level: RiskLevel) -> None:
        assessment = RiskAssessment(risk_level=level, rationale="x", requires_human_review=True)
        assert assessment.requires_human_review is False


class TestGroundFindings:
    def test_real_evidence_passes(self) -> None:
        finding = _finding(
            evidence=[Evidence(source_type="certification", source_id="CERT-004", detail="x")]
        )
        grounded, rejections = ground_findings("SUP-002", [finding])
        assert grounded == [finding]
        assert rejections == []

    def test_fabricated_evidence_rejects_the_whole_finding(self) -> None:
        real = Evidence(source_type="certification", source_id="CERT-004", detail="x")
        fake = Evidence(source_type="certification", source_id="CERT-DOES-NOT-EXIST", detail="x")
        finding = _finding(evidence=[real, fake])  # one real, one fabricated citation

        grounded, rejections = ground_findings("SUP-002", [finding])

        assert grounded == []  # the whole finding is dropped, not trimmed to the real citation
        assert len(rejections) == 1
        assert "CERT-DOES-NOT-EXIST" in rejections[0]

    def test_supplier_self_reference_is_valid_evidence_for_absence_findings(self) -> None:
        """There's no real certification record to cite for 'zero
        certifications on file' -- citing the supplier's own record is the
        correct, non-fabricated citation for that case.
        """
        finding = _finding(
            evidence=[Evidence(source_type="supplier", source_id="SUP-012", detail="x")]
        )
        grounded, rejections = ground_findings("SUP-012", [finding])
        assert grounded == [finding]
        assert rejections == []
