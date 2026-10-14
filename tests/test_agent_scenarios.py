"""Integration and acceptance scenario tests verifying PRD AC-001 through AC-004."""

import pytest

from ai_governance_harness.agent import MemberWealthInsightsAgent
from ai_governance_harness.cli import run_cli

pytestmark = pytest.mark.usefixtures("local_persona")


@pytest.fixture
def agent():
    """Return test agent running in offline mock mode."""
    return MemberWealthInsightsAgent(use_mock_backend=True)


def test_ac_001_profile_inspection_and_latency(agent):
    """AC-001: Profile view renders within latency budget (< 2.5 seconds) with required elements."""
    result = agent.inspect_member_profile("MEM-001")

    assert result["status"] == "success"
    assert result["latency_seconds"] <= 2.5, f"Latency {result['latency_seconds']} exceeds 2.5s budget"

    profile = result["profile"]
    assert profile["member_id"] == "MEM-001"
    assert "account" in profile
    assert profile["account"]["balance"] == 145000.0
    assert "option_allocation" in profile["account"]
    assert "recent_contributions" in profile

    # Disclosures present
    summary = result["formatted_summary"]
    assert "GENERAL ADVICE WARNING" in summary
    assert "IN-FUND DATA SCOPE" in summary


def test_ac_002_churn_diagnostic_attribution(agent):
    """AC-002: Churn diagnostic identifies primary drivers and relative baselines."""
    result = agent.diagnose_member_churn("MEM-002")

    assert result["status"] == "success"
    signals = result["signals"]
    assert signals["risk_level"] == "High"
    assert signals["churn_risk_score"] >= 0.7

    # Verify primary drivers
    factors = " ".join(signals["risk_factors"])
    assert "Contribution drop" in factors
    assert "Digital disengagement" in factors

    # Disclosures present
    report = result["formatted_report"]
    assert "GENERAL ADVICE WARNING" in report
    assert "IN-FUND DATA SCOPE" in report


def test_ac_003_fum_outflow_sizing(agent):
    """AC-003: FUM outflow summary calculates potential loss and cohort risk breakdown."""
    result = agent.analyze_cohort_fum_outflows()

    assert result["status"] == "success"
    fum = result["fum_metrics"]
    assert fum["total_fund_fum_aud"] > 0
    assert fum["high_risk_fum_aud"] > 0
    assert fum["fum_at_risk_percentage"] > 0
    assert "at_risk_fum_by_phase" in fum

    cohort = result["cohort_metrics"]
    assert "risk_distribution" in cohort
    assert cohort["risk_distribution"]["high_risk_count"] >= 1


def test_ac_004_closure_inquiry_immediate_outreach_trigger(agent):
    """AC-004: Explicit closure inquiry autonomously flags high-priority staff outreach."""
    result = agent.prepare_staff_interaction_briefing("MEM-003")

    assert result["status"] == "success"
    assert result["priority_outreach"] is True, "Closure inquiry must trigger immediate priority outreach"

    briefing = result["briefing_text"]
    assert "HIGH PRIORITY - IMMEDIATE OUTREACH REQUIRED" in briefing
    assert "TALKING POINTS" in briefing
    assert "COMPLIANCE NOTICE FOR CONSULTANT" in briefing
    assert "GENERAL ADVICE WARNING" in briefing
    assert "IN-FUND DATA SCOPE" in briefing


def test_cli_execution_commands(capsys):
    """Verify CLI commands execute cleanly with exit code 0."""
    assert run_cli(["profile", "MEM-001"]) == 0
    out_profile, _ = capsys.readouterr()
    assert "Alex Morgan" in out_profile
    assert "GENERAL ADVICE WARNING" in out_profile

    assert run_cli(["churn", "MEM-002"]) == 0
    out_churn, _ = capsys.readouterr()
    assert "CHURN DIAGNOSTIC REPORT" in out_churn

    assert run_cli(["prep", "MEM-003"]) == 0
    out_prep, _ = capsys.readouterr()
    assert "HIGH PRIORITY - IMMEDIATE OUTREACH REQUIRED" in out_prep

    assert run_cli(["fum-outflows"]) == 0
    out_fum, _ = capsys.readouterr()
    assert "COHORT FUNDS UNDER MANAGEMENT" in out_fum
