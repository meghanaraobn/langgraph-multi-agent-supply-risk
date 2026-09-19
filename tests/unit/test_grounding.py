"""Unit tests for agents/grounding.py's evidence-resolution check, focused
on the "document" evidence branch added for rag_agent. vector_store's
get_chunk_by_id is monkeypatched -- no live Weaviate needed, since this
branch's lazy import re-reads the module attribute on every call.
"""
from __future__ import annotations

from supplyguard.agents.grounding import ground_findings
from supplyguard.models import ConfidenceLevel, Evidence, Finding, Severity


def _finding_with_document_evidence(chunk_id: str = "SUP-003-audit-p1-c1") -> Finding:
    return Finding(
        category="audit",
        severity=Severity.HIGH,
        title="Underage workers observed at artisanal collection points",
        description="Auditors observed workers who appeared underage.",
        evidence=[
            Evidence(source_type="document", source_id=chunk_id, detail="Audit report excerpt"),
        ],
        confidence=ConfidenceLevel.HIGH,
        source="rag_agent",
    )


def test_document_evidence_grounded_when_chunk_exists(monkeypatch):
    monkeypatch.setattr(
        "supplyguard.rag.vector_store.get_chunk_by_id",
        lambda chunk_id, supplier_id: {"chunk_id": chunk_id, "supplier_id": supplier_id},
    )

    finding = _finding_with_document_evidence()
    grounded, rejections = ground_findings("SUP-003", [finding])

    assert grounded == [finding]
    assert rejections == []


def test_document_evidence_rejected_when_chunk_missing(monkeypatch):
    monkeypatch.setattr(
        "supplyguard.rag.vector_store.get_chunk_by_id",
        lambda chunk_id, supplier_id: None,
    )

    finding = _finding_with_document_evidence(chunk_id="SUP-003-audit-p9-c9")
    grounded, rejections = ground_findings("SUP-003", [finding])

    assert grounded == []
    assert len(rejections) == 1
    assert "SUP-003-audit-p9-c9" in rejections[0]


def test_document_evidence_lookup_is_scoped_to_the_investigated_supplier(monkeypatch):
    """A chunk_id that's real but belongs to a different supplier's document
    must not ground a finding for this supplier -- get_chunk_by_id is
    expected to filter by supplier_id itself, and this confirms
    ground_findings passes the right supplier_id through rather than just
    checking chunk existence in isolation.
    """
    seen_args = []

    def fake_get_chunk_by_id(chunk_id, supplier_id):
        seen_args.append((chunk_id, supplier_id))
        return None  # simulates: chunk exists, but not for this supplier

    monkeypatch.setattr("supplyguard.rag.vector_store.get_chunk_by_id", fake_get_chunk_by_id)

    finding = _finding_with_document_evidence(chunk_id="SUP-002-audit-p1-c0")
    grounded, rejections = ground_findings("SUP-003", [finding])

    assert grounded == []
    assert seen_args == [("SUP-002-audit-p1-c0", "SUP-003")]
