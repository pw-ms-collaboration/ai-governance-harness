"""Unit tests for sandboxed MCP data gateway tools."""

import pytest
from ai_governance_harness.mcp_server import (
    MemberNotFoundError,
    get_member_profile,
    get_member_disengagement_signals,
    get_cohort_churn_analytics,
    get_fum_outflow_summary,
)


def test_get_member_profile_success():
    """Verify get_member_profile returns unified profile with in-fund provenance notice."""
    profile = get_member_profile("MEM-001")
    assert profile["member_id"] == "MEM-001"
    assert profile["full_name"] == "Alex Morgan"
    assert profile["account"]["balance"] > 0
    assert profile["data_source"] == "internal_superannuation_core"
    assert "in-fund" in profile["provenance_notice"].lower()


def test_get_member_profile_not_found():
    """Verify get_member_profile raises MemberNotFoundError on unknown ID."""
    with pytest.raises(MemberNotFoundError):
        get_member_profile("MEM-NONEXISTENT")


def test_get_member_disengagement_signals_mem002_churn():
    """Verify MEM-002 is correctly diagnosed with contribution drop and digital disengagement."""
    signals = get_member_disengagement_signals("MEM-002")
    assert signals["member_id"] == "MEM-002"
    assert signals["risk_level"] == "High"
    assert signals["contribution_analysis"]["drop_detected"] is True
    assert signals["digital_engagement"]["drop_detected"] is True
    assert signals["immediate_outreach_required"] is False


def test_get_member_disengagement_signals_mem003_closure():
    """Verify MEM-003 triggers immediate outreach requirement due to closure inquiry."""
    signals = get_member_disengagement_signals("MEM-003")
    assert signals["member_id"] == "MEM-003"
    assert signals["immediate_outreach_required"] is True
    assert signals["risk_level"] == "High"


def test_get_cohort_churn_analytics():
    """Verify cohort analytics aggregation across all members."""
    analytics = get_cohort_churn_analytics()
    assert analytics["total_cohort_members"] >= 3
    assert "MEM-003" in analytics["immediate_outreach_cohort"]
    assert "closure_or_transfer_inquiry" in analytics["primary_attrition_drivers"]


def test_get_fum_outflow_summary():
    """Verify aggregate FUM at risk and phase breakdown calculations."""
    fum = get_fum_outflow_summary()
    assert fum["total_fund_fum_aud"] > 0
    assert fum["high_risk_fum_aud"] > 0
    assert fum["fum_at_risk_percentage"] > 0
    assert fum["currency"] == "AUD"
    assert "Accumulation" in fum["at_risk_fum_by_phase"]
