"""Synthetic data generator for Australian Superannuation member records.

Produces synthetic profiles conforming to SEC-2026-SUPER-001 (data minimisation)
and PRD-2026-SUPER-001 (diverse behavioral cohorts).
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import List

from ai_governance_harness.models.member import (
    ContributionRecord,
    DigitalActivityRecord,
    InteractionRecord,
    MemberProfile,
)


def generate_synthetic_members() -> List[MemberProfile]:
    """Generate 10 representative synthetic member profiles covering all analytical test cohorts."""
    members: List[MemberProfile] = []

    # 1. MEM-101: Stable accumulator (Low risk)
    members.append(
        MemberProfile(
            member_id="MEM-101",
            first_name="Alex",
            last_name="Taylor",
            age=34,
            tenure_years=5.2,
            current_balance=85400.0,
            investment_options=["Balanced", "High Growth"],
            insurance_opt_in=True,
            contributions=[
                ContributionRecord(date=date(2026, m, 15), employer_contribution=1050.0, voluntary_contribution=200.0)
                for m in range(1, 10)
            ],
            digital_activity=[
                DigitalActivityRecord(month=f"2026-0{m}", portal_logins=4, app_sessions=8, document_downloads=1)
                for m in range(1, 10)
            ],
            interactions=[
                InteractionRecord(
                    timestamp=datetime(2026, 4, 10, 11, 30),
                    channel="phone",
                    topic="general_inquiry",
                    closure_inquiry=False,
                    notes_summary="Inquired about investment option switching timelines; consultant provided factual info.",
                )
            ],
        )
    )

    # 2. MEM-102: Significant contribution drop (> 30% reduction, Medium/High risk)
    members.append(
        MemberProfile(
            member_id="MEM-102",
            first_name="Jordan",
            last_name="Smith",
            age=42,
            tenure_years=7.8,
            current_balance=164000.0,
            investment_options=["Growth"],
            insurance_opt_in=True,
            contributions=[
                # High historical (Jan-Jun: $1,400) -> sharp decline (Jul-Sep: $600)
                *(ContributionRecord(date=date(2026, m, 15), employer_contribution=1100.0, voluntary_contribution=300.0) for m in range(1, 7)),
                *(ContributionRecord(date=date(2026, m, 15), employer_contribution=600.0, voluntary_contribution=0.0) for m in range(7, 10)),
            ],
            digital_activity=[
                DigitalActivityRecord(month=f"2026-0{m}", portal_logins=3, app_sessions=5, document_downloads=0)
                for m in range(1, 10)
            ],
            interactions=[],
        )
    )

    # 3. MEM-103: Digital disengagement (App sessions & logins dropped to 0, Medium risk)
    members.append(
        MemberProfile(
            member_id="MEM-103",
            first_name="Casey",
            last_name="Wong",
            age=29,
            tenure_years=3.1,
            current_balance=42800.0,
            investment_options=["Sustainable International"],
            insurance_opt_in=False,
            contributions=[
                ContributionRecord(date=date(2026, m, 15), employer_contribution=750.0, voluntary_contribution=50.0)
                for m in range(1, 10)
            ],
            digital_activity=[
                # Jan-May active, Jun-Sep 0 activity
                *(DigitalActivityRecord(month=f"2026-0{m}", portal_logins=5, app_sessions=10, document_downloads=2) for m in range(1, 6)),
                *(DigitalActivityRecord(month=f"2026-0{m}", portal_logins=0, app_sessions=0, document_downloads=0) for m in range(6, 10)),
            ],
            interactions=[],
        )
    )

    # 4. MEM-104: Closure inquiry alone (Immediate staff outreach opportunity per FR-004 / AC-004)
    members.append(
        MemberProfile(
            member_id="MEM-104",
            first_name="Morgan",
            last_name="Davies",
            age=51,
            tenure_years=11.4,
            current_balance=318500.0,
            investment_options=["Balanced", "Australian Shares"],
            insurance_opt_in=True,
            contributions=[
                ContributionRecord(date=date(2026, m, 15), employer_contribution=1600.0, voluntary_contribution=400.0)
                for m in range(1, 10)
            ],
            digital_activity=[
                DigitalActivityRecord(month=f"2026-0{m}", portal_logins=2, app_sessions=4, document_downloads=1)
                for m in range(1, 10)
            ],
            interactions=[
                InteractionRecord(
                    timestamp=datetime(2026, 9, 28, 14, 15),
                    channel="phone",
                    topic="closure_inquiry",
                    closure_inquiry=True,
                    notes_summary="Member called asking about rollover transfer process to an external SMSF and requested exit statement.",
                )
            ],
        )
    )

    # 5. MEM-105: Compound risk (Contribution stop + digital drop + closure inquiry)
    members.append(
        MemberProfile(
            member_id="MEM-105",
            first_name="Riley",
            last_name="O'Connor",
            age=47,
            tenure_years=8.0,
            current_balance=245000.0,
            investment_options=["Growth"],
            insurance_opt_in=True,
            contributions=[
                *(ContributionRecord(date=date(2026, m, 15), employer_contribution=1300.0, voluntary_contribution=250.0) for m in range(1, 6)),
                *(ContributionRecord(date=date(2026, m, 15), employer_contribution=0.0, voluntary_contribution=0.0) for m in range(6, 10)),
            ],
            digital_activity=[
                *(DigitalActivityRecord(month=f"2026-0{m}", portal_logins=4, app_sessions=6, document_downloads=1) for m in range(1, 6)),
                *(DigitalActivityRecord(month=f"2026-0{m}", portal_logins=0, app_sessions=0, document_downloads=0) for m in range(6, 10)),
            ],
            interactions=[
                InteractionRecord(
                    timestamp=datetime(2026, 9, 15, 9, 45),
                    channel="secure_portal_message",
                    topic="rollover_inquiry",
                    closure_inquiry=True,
                    notes_summary="Inquired about consolidating into a retail fund via SuperMatch.",
                )
            ],
        )
    )

    # 6. MEM-106: Young accumulator (Low risk)
    members.append(
        MemberProfile(
            member_id="MEM-106",
            first_name="Sam",
            last_name="Patel",
            age=24,
            tenure_years=1.8,
            current_balance=16200.0,
            investment_options=["High Growth"],
            insurance_opt_in=False,
            contributions=[
                ContributionRecord(date=date(2026, m, 15), employer_contribution=550.0, voluntary_contribution=0.0)
                for m in range(1, 10)
            ],
            digital_activity=[
                DigitalActivityRecord(month=f"2026-0{m}", portal_logins=1, app_sessions=14, document_downloads=0)
                for m in range(1, 10)
            ],
            interactions=[],
        )
    )

    # 7. MEM-107: Pre-retiree transition (High balance, fee sensitivity inquiry)
    members.append(
        MemberProfile(
            member_id="MEM-107",
            first_name="Robin",
            last_name="Campbell",
            age=61,
            tenure_years=16.5,
            current_balance=785000.0,
            investment_options=["Conservative Balanced", "Cash"],
            insurance_opt_in=True,
            contributions=[
                ContributionRecord(date=date(2026, m, 15), employer_contribution=1850.0, voluntary_contribution=1000.0)
                for m in range(1, 10)
            ],
            digital_activity=[
                DigitalActivityRecord(month=f"2026-0{m}", portal_logins=6, app_sessions=2, document_downloads=4)
                for m in range(1, 10)
            ],
            interactions=[
                InteractionRecord(
                    timestamp=datetime(2026, 8, 20, 16, 0),
                    channel="phone",
                    topic="fee_inquiry",
                    closure_inquiry=False,
                    notes_summary="Member reviewed PDS and asked about administration fee caps approaching retirement.",
                )
            ],
        )
    )

    # 8. MEM-108: High FUM at risk (Balance $940k, closure inquiry, high outflow impact)
    members.append(
        MemberProfile(
            member_id="MEM-108",
            first_name="Avery",
            last_name="Chen",
            age=56,
            tenure_years=14.0,
            current_balance=940000.0,
            investment_options=["Growth", "Australian Shares"],
            insurance_opt_in=True,
            contributions=[
                *(ContributionRecord(date=date(2026, m, 15), employer_contribution=2200.0, voluntary_contribution=1500.0) for m in range(1, 7)),
                *(ContributionRecord(date=date(2026, m, 15), employer_contribution=2200.0, voluntary_contribution=0.0) for m in range(7, 10)),
            ],
            digital_activity=[
                DigitalActivityRecord(month=f"2026-0{m}", portal_logins=2, app_sessions=3, document_downloads=2)
                for m in range(1, 10)
            ],
            interactions=[
                InteractionRecord(
                    timestamp=datetime(2026, 10, 2, 10, 15),
                    channel="email",
                    topic="account_closure",
                    closure_inquiry=True,
                    notes_summary="Requested direct rollover benefit payment forms for self-managed super fund transfer.",
                )
            ],
        )
    )

    # 9. MEM-109: Stagnant/dormant member (Zero contributions, low activity)
    members.append(
        MemberProfile(
            member_id="MEM-109",
            first_name="Taylor",
            last_name="Wilson",
            age=39,
            tenure_years=6.0,
            current_balance=38900.0,
            investment_options=["Balanced"],
            insurance_opt_in=True,
            contributions=[
                ContributionRecord(date=date(2026, m, 15), employer_contribution=0.0, voluntary_contribution=0.0)
                for m in range(1, 10)
            ],
            digital_activity=[
                DigitalActivityRecord(month=f"2026-0{m}", portal_logins=0, app_sessions=0, document_downloads=0)
                for m in range(1, 10)
            ],
            interactions=[],
        )
    )

    # 10. MEM-110: Highly engaged accumulator (Low risk)
    members.append(
        MemberProfile(
            member_id="MEM-110",
            first_name="Quinn",
            last_name="Martin",
            age=38,
            tenure_years=4.5,
            current_balance=112000.0,
            investment_options=["Balanced"],
            insurance_opt_in=True,
            contributions=[
                ContributionRecord(date=date(2026, m, 15), employer_contribution=1250.0, voluntary_contribution=350.0)
                for m in range(1, 10)
            ],
            digital_activity=[
                DigitalActivityRecord(month=f"2026-0{m}", portal_logins=7, app_sessions=12, document_downloads=3)
                for m in range(1, 10)
            ],
            interactions=[
                InteractionRecord(
                    timestamp=datetime(2026, 7, 12, 13, 0),
                    channel="secure_portal_message",
                    topic="insurance_update",
                    closure_inquiry=False,
                    notes_summary="Updated beneficiary binding nomination and confirmed insurance cover details.",
                )
            ],
        )
    )

    return members


def save_synthetic_members(filepath: Path) -> None:
    """Save the synthetic member profiles to JSON format."""
    members = generate_synthetic_members()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([m.model_dump(mode="json") for m in members], f, indent=2)


if __name__ == "__main__":
    out_path = Path(__file__).parent / "synthetic_members.json"
    save_synthetic_members(out_path)
    print(f"Generated synthetic members at {out_path}")
