"""Unit tests for the Risk Agent's tools -- including the sanctions
false-positive case the whole dataset was built around.
"""
from __future__ import annotations

from supplyguard.tools import check_sanctions, search_incidents


def test_search_incidents_exposes_severity_and_status_independently():
    incidents = search_incidents.invoke({"supplier_id": "SUP-005"})
    # INC-005 is a resolved, medium-severity fire; the tool must expose both
    # fields rather than collapsing them into one risk signal.
    fire = next(i for i in incidents if i["incident_type"] == "fire")
    assert fire["severity"] == "medium"
    assert fire["status"] == "resolved"


def test_check_sanctions_surfaces_false_positive_with_low_confidence():
    """SAN-004 is a real fixture row -- a name collision with Golden Thread
    Textiles that is NOT an actual match. The tool must still return it (a
    raw name search), flagged with low confidence, not silently filtered --
    reasoning about whether it's real is the agent's job, not the tool's.
    """
    hits = check_sanctions.invoke({"supplier_name": "Golden Thread"})
    assert len(hits) == 1
    assert hits[0]["match_confidence"] == "low"
    assert hits[0]["match_supplier_id"] is None


def test_check_sanctions_no_match_returns_empty_list():
    hits = check_sanctions.invoke({"supplier_name": "Totally Unrelated Company Name"})
    assert hits == []
