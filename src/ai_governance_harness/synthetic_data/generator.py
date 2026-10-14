"""Deterministic synthetic superannuation data generator.

Generates realistic, schema-validated synthetic superannuation customer records
for internal decision support without exposing live member PII.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from ai_governance_harness.synthetic_data.schemas import (
    MemberRecord,
    AccountRecord,
    ContributionRecord,
    InteractionRecord,
    DigitalActivityRecord,
)
from ai_governance_harness.governance.retention import RetentionRecord

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"


def build_retention_records() -> list[dict]:
    """Generate explicit demo eligibility without inferring company thresholds."""
    scenarios: list[dict] = [
        {"member_id": "MEM-001", "cases": []},
        {"member_id": "MEM-002", "cases": [
            {"case_id": "CASE-002", "kind": "routine_retention", "status": "closed",
             "closure_outcome": "routine_cleared"},
        ]},
        {"member_id": "MEM-003", "cases": [
            {"case_id": "CASE-003", "kind": "specialist", "status": "open",
             "specialist_team": "complaints"},
        ]},
        {"member_id": "MEM-004", "cases": [
            {"case_id": "CASE-004", "kind": "routine_retention", "status": "open"},
        ]},
        {"member_id": "MEM-005", "cases": [
            {"case_id": "CASE-005", "kind": "specialist", "status": "closed",
             "closure_outcome": "review_required", "specialist_team": "hardship"},
        ]},
        {"member_id": "MEM-006", "account_status": "exit_completed", "cases": []},
        {"member_id": "MEM-007", "cases": [
            {"case_id": "CASE-007", "kind": "specialist", "status": "closed",
             "closure_outcome": "routine_cleared", "specialist_team": "member_support"},
        ]},
    ]
    return [
        RetentionRecord.model_validate({
            "account_status": "active",
            "new_signals_status": "satisfied",
            "contact_policy_status": "satisfied",
            "cooling_off_status": "satisfied",
            **scenario,
        }).model_dump(mode="json")
        for scenario in scenarios
    ]


def build_synthetic_dataset() -> Dict[str, List[dict]]:
    """Construct the complete synthetic superannuation dataset with defined test personas."""
    # 1. Members
    members: List[MemberRecord] = [
        MemberRecord(
            member_id="MEM-001",
            full_name="Alex Morgan",
            age=34,
            tenure_years=6.5,
            risk_profile="Growth",
            communication_pref="email",
            has_closure_inquiry=False,
        ),
        MemberRecord(
            member_id="MEM-002",
            full_name="Jordan Taylor",
            age=47,
            tenure_years=11.2,
            risk_profile="Balanced",
            communication_pref="email",
            has_closure_inquiry=False,
        ),
        MemberRecord(
            member_id="MEM-003",
            full_name="Casey Chen",
            age=52,
            tenure_years=14.0,
            risk_profile="Balanced",
            communication_pref="phone",
            has_closure_inquiry=True,
        ),
        MemberRecord(
            member_id="MEM-004",
            full_name="Riley Patel",
            age=29,
            tenure_years=3.0,
            risk_profile="High Growth",
            communication_pref="email",
            has_closure_inquiry=False,
        ),
        MemberRecord(
            member_id="MEM-005",
            full_name="Samira Khan",
            age=58,
            tenure_years=16.8,
            risk_profile="Balanced",
            communication_pref="phone",
            has_closure_inquiry=False,
        ),
        MemberRecord(
            member_id="MEM-006",
            full_name="Liam O'Connor",
            age=41,
            tenure_years=8.2,
            risk_profile="Growth",
            communication_pref="email",
            has_closure_inquiry=False,
        ),
        MemberRecord(
            member_id="MEM-007",
            full_name="Elena Rostova",
            age=55,
            tenure_years=13.5,
            risk_profile="High Growth",
            communication_pref="email",
            has_closure_inquiry=True,
        ),
    ]

    # 2. Accounts
    accounts: List[AccountRecord] = [
        AccountRecord(
            account_id="ACC-001",
            member_id="MEM-001",
            balance=145000.0,
            phase="Accumulation",
            option_allocation={"Growth": 0.70, "Australian Shares": 0.30},
        ),
        AccountRecord(
            account_id="ACC-002",
            member_id="MEM-002",
            balance=320000.0,
            phase="Accumulation",
            option_allocation={"Balanced": 0.80, "Cash": 0.20},
        ),
        AccountRecord(
            account_id="ACC-003",
            member_id="MEM-003",
            balance=580000.0,
            phase="Accumulation",
            option_allocation={"Balanced": 0.60, "Australian Shares": 0.20, "International Shares": 0.20},
        ),
        AccountRecord(
            account_id="ACC-004",
            member_id="MEM-004",
            balance=45000.0,
            phase="Accumulation",
            option_allocation={"High Growth": 1.00},
        ),
        AccountRecord(
            account_id="ACC-005",
            member_id="MEM-005",
            balance=720000.0,
            phase="Transition to Retirement",
            option_allocation={"Conservative": 0.40, "Balanced": 0.60},
        ),
        AccountRecord(
            account_id="ACC-006",
            member_id="MEM-006",
            balance=210000.0,
            phase="Accumulation",
            option_allocation={"Growth": 0.85, "Cash": 0.15},
        ),
        AccountRecord(
            account_id="ACC-007",
            member_id="MEM-007",
            balance=410000.0,
            phase="Accumulation",
            option_allocation={"High Growth": 0.75, "International Shares": 0.25},
        ),
    ]

    # 3. Contributions (Historical sequence)
    contributions: List[ContributionRecord] = [
        # MEM-001: Steady baseline contributions
        ContributionRecord(
            contribution_id="CONTR-101",
            account_id="ACC-001",
            member_id="MEM-001",
            date="2026-08-15",
            amount=1250.0,
            type="SG",
            usual_monthly_baseline=1250.0,
        ),
        ContributionRecord(
            contribution_id="CONTR-102",
            account_id="ACC-001",
            member_id="MEM-001",
            date="2026-09-15",
            amount=1250.0,
            type="SG",
            usual_monthly_baseline=1250.0,
        ),
        ContributionRecord(
            contribution_id="CONTR-103",
            account_id="ACC-001",
            member_id="MEM-001",
            date="2026-10-15",
            amount=1250.0,
            type="SG",
            usual_monthly_baseline=1250.0,
        ),
        # MEM-002: 50% drop relative to baseline (Churn risk)
        ContributionRecord(
            contribution_id="CONTR-201",
            account_id="ACC-002",
            member_id="MEM-002",
            date="2026-08-20",
            amount=2200.0,
            type="SG",
            usual_monthly_baseline=2200.0,
        ),
        ContributionRecord(
            contribution_id="CONTR-202",
            account_id="ACC-002",
            member_id="MEM-002",
            date="2026-09-20",
            amount=1100.0,
            type="SG",
            usual_monthly_baseline=2200.0,
        ),
        ContributionRecord(
            contribution_id="CONTR-203",
            account_id="ACC-002",
            member_id="MEM-002",
            date="2026-10-20",
            amount=1100.0,
            type="SG",
            usual_monthly_baseline=2200.0,
        ),
        # MEM-003: Stable contributions but has closure inquiry
        ContributionRecord(
            contribution_id="CONTR-301",
            account_id="ACC-003",
            member_id="MEM-003",
            date="2026-08-10",
            amount=2800.0,
            type="SG",
            usual_monthly_baseline=2800.0,
        ),
        ContributionRecord(
            contribution_id="CONTR-302",
            account_id="ACC-003",
            member_id="MEM-003",
            date="2026-09-10",
            amount=2800.0,
            type="SG",
            usual_monthly_baseline=2800.0,
        ),
        ContributionRecord(
            contribution_id="CONTR-303",
            account_id="ACC-003",
            member_id="MEM-003",
            date="2026-10-10",
            amount=2800.0,
            type="SG",
            usual_monthly_baseline=2800.0,
        ),
        # MEM-004: Normal accumulation
        ContributionRecord(
            contribution_id="CONTR-401",
            account_id="ACC-004",
            member_id="MEM-004",
            date="2026-10-05",
            amount=650.0,
            type="SG",
            usual_monthly_baseline=650.0,
        ),
        # MEM-005: 40% drop in contributions
        ContributionRecord(
            contribution_id="CONTR-501",
            account_id="ACC-005",
            member_id="MEM-005",
            date="2026-10-12",
            amount=1800.0,
            type="SG",
            usual_monthly_baseline=3000.0,
        ),
        # MEM-006: Normal contribution
        ContributionRecord(
            contribution_id="CONTR-601",
            account_id="ACC-006",
            member_id="MEM-006",
            date="2026-10-18",
            amount=1600.0,
            type="SG",
            usual_monthly_baseline=1600.0,
        ),
        # MEM-007: Normal contribution but closure inquiry
        ContributionRecord(
            contribution_id="CONTR-701",
            account_id="ACC-007",
            member_id="MEM-007",
            date="2026-10-22",
            amount=2400.0,
            type="SG",
            usual_monthly_baseline=2400.0,
        ),
    ]

    # 4. Frontline and Digital Interactions
    interactions: List[InteractionRecord] = [
        InteractionRecord(
            interaction_id="INT-101",
            member_id="MEM-001",
            timestamp="2026-09-14T09:30:00Z",
            channel="portal_chat",
            category="general_inquiry",
            notes="Member asked about annual statement dispatch date.",
            closure_inquiry_flag=False,
        ),
        InteractionRecord(
            interaction_id="INT-201",
            member_id="MEM-002",
            timestamp="2026-09-28T14:15:00Z",
            channel="phone",
            category="fee_query",
            notes="Member called inquiring about administration fees and comparison with industry funds.",
            closure_inquiry_flag=False,
        ),
        InteractionRecord(
            interaction_id="INT-301",
            member_id="MEM-003",
            timestamp="2026-10-02T11:45:00Z",
            channel="phone",
            category="closure_inquiry",
            notes="Member requested rollover out statement and transfer paperwork to external SMSF. Closure inquiry registered.",
            closure_inquiry_flag=True,
        ),
        InteractionRecord(
            interaction_id="INT-401",
            member_id="MEM-004",
            timestamp="2026-08-11T16:20:00Z",
            channel="portal_chat",
            category="investment_switch",
            notes="Completed online switch to 100% High Growth option.",
            closure_inquiry_flag=False,
        ),
        InteractionRecord(
            interaction_id="INT-501",
            member_id="MEM-005",
            timestamp="2026-09-19T10:10:00Z",
            channel="phone",
            category="retirement_planning",
            notes="Member asked about transition to retirement pension options.",
            closure_inquiry_flag=False,
        ),
        InteractionRecord(
            interaction_id="INT-701",
            member_id="MEM-007",
            timestamp="2026-10-08T15:00:00Z",
            channel="secure_mail",
            category="closure_inquiry",
            notes="Member submitted inquiry via secure portal regarding fund transfer process and exit requirements.",
            closure_inquiry_flag=True,
        ),
    ]

    # 5. Digital Activity
    digital_activity: List[DigitalActivityRecord] = [
        # MEM-001: Consistently high engagement
        DigitalActivityRecord(
            activity_id="DIG-101",
            member_id="MEM-001",
            month="2026-08",
            login_count=6,
            document_downloads=2,
            baseline_logins=5,
        ),
        DigitalActivityRecord(
            activity_id="DIG-102",
            member_id="MEM-001",
            month="2026-09",
            login_count=7,
            document_downloads=1,
            baseline_logins=5,
        ),
        DigitalActivityRecord(
            activity_id="DIG-103",
            member_id="MEM-001",
            month="2026-10",
            login_count=6,
            document_downloads=0,
            baseline_logins=5,
        ),
        # MEM-002: Steep drop in digital engagement (Churn risk)
        DigitalActivityRecord(
            activity_id="DIG-201",
            member_id="MEM-002",
            month="2026-08",
            login_count=7,
            document_downloads=2,
            baseline_logins=8,
        ),
        DigitalActivityRecord(
            activity_id="DIG-202",
            member_id="MEM-002",
            month="2026-09",
            login_count=2,
            document_downloads=0,
            baseline_logins=8,
        ),
        DigitalActivityRecord(
            activity_id="DIG-203",
            member_id="MEM-002",
            month="2026-10",
            login_count=1,
            document_downloads=0,
            baseline_logins=8,
        ),
        # MEM-003: Stable digital engagement (inquiry via phone)
        DigitalActivityRecord(
            activity_id="DIG-301",
            member_id="MEM-003",
            month="2026-08",
            login_count=4,
            document_downloads=1,
            baseline_logins=4,
        ),
        DigitalActivityRecord(
            activity_id="DIG-302",
            member_id="MEM-003",
            month="2026-09",
            login_count=4,
            document_downloads=2,
            baseline_logins=4,
        ),
        DigitalActivityRecord(
            activity_id="DIG-303",
            member_id="MEM-003",
            month="2026-10",
            login_count=3,
            document_downloads=1,
            baseline_logins=4,
        ),
        # MEM-006: Digital inactivity (0 logins)
        DigitalActivityRecord(
            activity_id="DIG-601",
            member_id="MEM-006",
            month="2026-10",
            login_count=0,
            document_downloads=0,
            baseline_logins=6,
        ),
    ]

    return {
        "members.json": [m.model_dump() for m in members],
        "accounts.json": [a.model_dump() for a in accounts],
        "contributions.json": [c.model_dump() for c in contributions],
        "interactions.json": [i.model_dump() for i in interactions],
        "digital_activity.json": [d.model_dump() for d in digital_activity],
        "retention_cases.json": build_retention_records(),
    }


def generate_synthetic_dataset(output_dir: Optional[Path] = None) -> Path:
    """Generate and write synthetic superannuation JSON files to output directory."""
    target_dir = output_dir or DEFAULT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    dataset = build_synthetic_dataset()
    for filename, records in dataset.items():
        file_path = target_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    return target_dir


if __name__ == "__main__":
    out = generate_synthetic_dataset()
    print(f"Synthetic superannuation dataset successfully generated at: {out}")
