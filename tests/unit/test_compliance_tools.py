"""Unit tests for the Compliance Agent's tools."""
from __future__ import annotations

from supplyguard.tools import get_certifications, get_regulatory_requirements


def test_get_certifications_returns_expired_records():
    certs = get_certifications.invoke({"supplier_id": "SUP-002"})
    statuses = {c["status"] for c in certs}
    assert statuses == {"expired"}
    assert len(certs) == 2


def test_get_certifications_no_certs_on_file_returns_empty_list():
    """SUP-012 deliberately has zero certification records on file --
    absence is a real finding to report, not an error, so the tool must
    return [], not raise.
    """
    certs = get_certifications.invoke({"supplier_id": "SUP-012"})
    assert certs == []


def test_get_regulatory_requirements_matches_industry():
    regs = get_regulatory_requirements.invoke({"industry": "Mining - Cobalt & Copper"})
    names = {r["regulation_name"] for r in regs}
    assert "Uyghur Forced Labor Prevention Act (UFLPA)" in names


def test_get_regulatory_requirements_unknown_industry_excludes_industry_specific_ones():
    """Regulations tagged applicable_industries=["all"] (e.g. the UK Modern
    Slavery Act) correctly match any industry string, including a made-up
    one -- so the right assertion isn't "empty list", it's "no
    industry-specific regulation leaks in for an industry it doesn't apply
    to".
    """
    regs = get_regulatory_requirements.invoke({"industry": "Underwater Basket Weaving"})
    names = {r["regulation_name"] for r in regs}
    assert "Uyghur Forced Labor Prevention Act (UFLPA)" not in names
    assert all(
        "all" in r["applicable_industries"] or "Underwater Basket Weaving" in r["applicable_industries"]
        for r in regs
    )
