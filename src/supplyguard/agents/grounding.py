"""Deterministic evidence-grounding check.

A Finding can be schema-valid (non-empty evidence, correct types) while still
citing an Evidence whose source_id doesn't resolve to any real record -- an
LLM can invent a plausible-looking id (or reuse the wrong one, e.g. a
supplier's own id in place of a nonexistent certification id) and nothing in
the Pydantic schema catches that, since source_id is just a free-text str.

This closes that gap with a real repository lookup per evidence item. Used
by every specialist agent node before it returns findings into shared state.
"""
from __future__ import annotations

from supplyguard.data import get_repository
from supplyguard.data.base import BaseDataRepository
from supplyguard.models import Evidence, Finding


def _record_exists(repo: BaseDataRepository, supplier_id: str, evidence: Evidence) -> bool:
    source_type = evidence.source_type
    source_id = evidence.source_id

    if source_type == "certification":
        return any(c.id == source_id for c in repo.get_certifications(supplier_id))
    if source_type == "incident":
        return any(i.id == source_id for i in repo.get_incidents(supplier_id))
    if source_type == "sanctions":
        return any(s.id == source_id for s in repo.list_sanctions())
    if source_type == "sustainability":
        record = repo.get_sustainability(supplier_id)
        return record is not None and record.id == source_id
    if source_type == "regulation":
        return any(r.id == source_id for r in repo.list_regulations())
    if source_type == "supplier":
        return source_id == supplier_id
    if source_type == "document":
        # Deferred import, matching graph/workflow.py's convention for
        # cross-package edges -- rag_agent.py already forces the rag
        # package to be importable via tools/__init__.py, so this doesn't
        # avoid that weight, just keeps the dependency out of this
        # module's top-level imports.
        from supplyguard.rag.vector_store import get_chunk_by_id

        return get_chunk_by_id(source_id, supplier_id) is not None
    return False


def ground_findings(supplier_id: str, findings: list[Finding]) -> tuple[list[Finding], list[str]]:
    """Split findings into (grounded, rejection_reasons).

    A finding is rejected in full -- not silently trimmed down to its valid
    evidence -- if ANY cited evidence fails to resolve. A finding partly
    supported by fabricated evidence is not one we can trust, even if some
    of its other citations are real.
    """
    repo = get_repository()
    grounded: list[Finding] = []
    rejection_reasons: list[str] = []

    for finding in findings:
        bad_evidence = [e for e in finding.evidence if not _record_exists(repo, supplier_id, e)]
        if bad_evidence:
            bad_desc = ", ".join(f"{e.source_type}:{e.source_id}" for e in bad_evidence)
            rejection_reasons.append(
                f"Rejected finding '{finding.title}' -- evidence does not resolve to a real "
                f"record: {bad_desc}"
            )
            continue
        grounded.append(finding)

    return grounded, rejection_reasons
