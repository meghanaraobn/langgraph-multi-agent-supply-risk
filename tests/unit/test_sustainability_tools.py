"""Unit tests for the Sustainability Agent's tool."""
from __future__ import annotations

from supplyguard.tools import get_sustainability_information


def test_get_sustainability_information_returns_real_record():
    result = get_sustainability_information.invoke({"supplier_id": "SUP-011"})
    assert result["esg_score"] == 91.0
    assert "status" not in result


def test_get_sustainability_information_missing_record_reports_explicitly():
    result = get_sustainability_information.invoke({"supplier_id": "SUP-999"})
    assert result["status"] == "no_sustainability_data_on_file"
