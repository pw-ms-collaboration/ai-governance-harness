"""Sandboxed Model Context Protocol (MCP) data access tools for superannuation data.

Enforces read-only isolation over synthetic superannuation records, never accepting
or exposing filesystem paths, and ensuring compliance with in-fund data scope invariants.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"


class MemberNotFoundError(ValueError):
    """Raised when a requested member_id is not found in the synthetic dataset."""
    pass


class SuperannuationDataGateway:
    """In-memory data gateway accessing synthetic superannuation records."""

    def __init__(self, data_directory: Optional[Path] = None):
        self._dir = data_directory or DATA_DIR
        self._members: Dict[str, dict] = {}
        self._accounts: Dict[str, dict] = {}
        self._contributions: List[dict] = []
        self._interactions: List[dict] = []
        self._digital_activity: List[dict] = []
        self._load_data()

    def _load_data(self) -> None:
        """Load synthetic records into memory."""
        members_file = self._dir / "members.json"
        accounts_file = self._dir / "accounts.json"
        contributions_file = self._dir / "contributions.json"
        interactions_file = self._dir / "interactions.json"
        digital_file = self._dir / "digital_activity.json"

        if not members_file.exists():
            raise FileNotFoundError(
                f"Synthetic data not found in {self._dir}. Please run generator first."
            )

        with open(members_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                self._members[item["member_id"]] = item

        with open(accounts_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                self._accounts[item["member_id"]] = item

        with open(contributions_file, "r", encoding="utf-8") as f:
            self._contributions = json.load(f)

        with open(interactions_file, "r", encoding="utf-8") as f:
            self._interactions = json.load(f)

        with open(digital_file, "r", encoding="utf-8") as f:
            self._digital_activity = json.load(f)

    def get_member_profile(self, member_id: str) -> Dict[str, Any]:
        """Retrieve unified internal superannuation profile for a member.

        Includes member details, account balances, investment options, and baseline
        contribution parameters. Invariant: only internal fund data is returned.
        """
        member = self._members.get(member_id)
        if not member:
            raise MemberNotFoundError(f"Member '{member_id}' not found.")

        account = self._accounts.get(member_id, {})
        member_contributions = [
            c for c in self._contributions if c["member_id"] == member_id
        ]
        recent_contributions = sorted(
            member_contributions, key=lambda x: x["date"], reverse=True
        )[:3]

        return {
            "member_id": member["member_id"],
            "full_name": member["full_name"],
            "age": member["age"],
            "tenure_years": member["tenure_years"],
            "risk_profile": member["risk_profile"],
            "communication_preference": member.get("communication_pref", "email"),
            "account": {
                "account_id": account.get("account_id"),
                "balance": account.get("balance", 0.0),
                "phase": account.get("phase", "Accumulation"),
                "option_allocation": account.get("option_allocation", {}),
            },
            "recent_contributions": recent_contributions,
            "has_closure_inquiry": member.get("has_closure_inquiry", False),
            "data_source": "internal_superannuation_core",
            "provenance_notice": "Data strictly restricted to in-fund superannuation holdings. External assets not verified.",
        }

    def get_member_disengagement_signals(self, member_id: str) -> Dict[str, Any]:
        """Analyze contribution drops, digital inactivity, and closure inquiries for a member."""
        member = self._members.get(member_id)
        if not member:
            raise MemberNotFoundError(f"Member '{member_id}' not found.")

        # 1. Contribution Trend Analysis
        member_contributions = [
            c for c in self._contributions if c["member_id"] == member_id
        ]
        contribution_drop_detected = False
        contribution_change_pct = 0.0
        baseline_contribution = 0.0
        latest_contribution = 0.0

        if member_contributions:
            sorted_c = sorted(member_contributions, key=lambda x: x["date"], reverse=True)
            latest = sorted_c[0]
            latest_contribution = latest["amount"]
            baseline_contribution = latest["usual_monthly_baseline"]
            if baseline_contribution > 0:
                diff = latest_contribution - baseline_contribution
                contribution_change_pct = round((diff / baseline_contribution) * 100, 1)
                if contribution_change_pct <= -25.0:
                    contribution_drop_detected = True

        # 2. Digital Activity Analysis
        member_activity = [
            a for a in self._digital_activity if a["member_id"] == member_id
        ]
        digital_drop_detected = False
        login_deficit_pct = 0.0
        recent_logins = 0
        baseline_logins = 0

        if member_activity:
            sorted_a = sorted(member_activity, key=lambda x: x["month"], reverse=True)
            latest_a = sorted_a[0]
            recent_logins = latest_a["login_count"]
            baseline_logins = latest_a["baseline_logins"]
            if baseline_logins > 0:
                deficit = baseline_logins - recent_logins
                login_deficit_pct = round((deficit / baseline_logins) * 100, 1)
                if recent_logins <= 1 or login_deficit_pct >= 50.0:
                    digital_drop_detected = True

        # 3. Closure Inquiry Flag (Autonomous trigger)
        member_interactions = [
            i for i in self._interactions if i["member_id"] == member_id
        ]
        has_closure_inquiry = member.get("has_closure_inquiry", False) or any(
            i.get("closure_inquiry_flag", False) for i in member_interactions
        )
        closure_interactions = [
            i for i in member_interactions if i.get("closure_inquiry_flag", False)
        ]

        # 4. Churn Risk Score & Severity Categorization
        risk_score = 0.0
        risk_factors: List[str] = []

        if has_closure_inquiry:
            risk_score += 0.85
            risk_factors.append("Explicit closure/transfer inquiry recorded on file")

        if contribution_drop_detected:
            if abs(contribution_change_pct) >= 50.0:
                risk_score += 0.50
            else:
                risk_score += 0.35
            risk_factors.append(
                f"Contribution drop: {abs(contribution_change_pct)}% below baseline (${latest_contribution} vs ${baseline_contribution})"
            )

        if digital_drop_detected:
            if recent_logins <= 1 or login_deficit_pct >= 50.0:
                risk_score += 0.30
            else:
                risk_score += 0.20
            risk_factors.append(
                f"Digital disengagement: {recent_logins} logins this month vs {baseline_logins} baseline"
            )

        risk_score = min(round(risk_score, 2), 1.0)
        risk_level = "High" if risk_score >= 0.7 else ("Medium" if risk_score >= 0.35 else "Low")

        return {
            "member_id": member_id,
            "churn_risk_score": risk_score,
            "risk_level": risk_level,
            "immediate_outreach_required": has_closure_inquiry,
            "risk_factors": risk_factors,
            "contribution_analysis": {
                "drop_detected": contribution_drop_detected,
                "latest_amount": latest_contribution,
                "baseline_amount": baseline_contribution,
                "change_percent": contribution_change_pct,
            },
            "digital_engagement": {
                "drop_detected": digital_drop_detected,
                "recent_monthly_logins": recent_logins,
                "baseline_logins": baseline_logins,
                "login_deficit_percent": login_deficit_pct,
            },
            "closure_inquiry_details": {
                "has_closure_inquiry": has_closure_inquiry,
                "recorded_interactions": closure_interactions,
            },
        }

    def get_cohort_churn_analytics(self, cohort_filter: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate attrition factors and lookback attribution across the cohort."""
        total_members = len(self._members)
        high_risk_members: List[str] = []
        medium_risk_members: List[str] = []
        low_risk_members: List[str] = []
        closure_inquiry_members: List[str] = []
        contribution_drop_members: List[str] = []
        digital_inactive_members: List[str] = []

        for m_id in self._members.keys():
            signals = self.get_member_disengagement_signals(m_id)
            if signals["immediate_outreach_required"]:
                closure_inquiry_members.append(m_id)
            if signals["contribution_analysis"]["drop_detected"]:
                contribution_drop_members.append(m_id)
            if signals["digital_engagement"]["drop_detected"]:
                digital_inactive_members.append(m_id)

            if signals["risk_level"] == "High":
                high_risk_members.append(m_id)
            elif signals["risk_level"] == "Medium":
                medium_risk_members.append(m_id)
            else:
                low_risk_members.append(m_id)

        # Primary drivers attribution
        drivers_breakdown = {
            "closure_or_transfer_inquiry": len(closure_inquiry_members),
            "contribution_reduction_over_25pct": len(contribution_drop_members),
            "digital_portal_inactivity": len(digital_inactive_members),
        }

        return {
            "total_cohort_members": total_members,
            "risk_distribution": {
                "high_risk_count": len(high_risk_members),
                "medium_risk_count": len(medium_risk_members),
                "low_risk_count": len(low_risk_members),
            },
            "immediate_outreach_cohort": closure_inquiry_members,
            "high_risk_members": high_risk_members,
            "primary_attrition_drivers": drivers_breakdown,
            "lookback_window": "90_days",
        }

    def get_fum_outflow_summary(self) -> Dict[str, Any]:
        """Calculate aggregate Funds Under Management (FUM) at risk and cohort breakdown."""
        total_fum = sum(acc.get("balance", 0.0) for acc in self._accounts.values())
        high_risk_fum = 0.0
        closure_inquiry_fum = 0.0
        risk_by_phase: Dict[str, float] = {}

        for m_id, acc in self._accounts.items():
            signals = self.get_member_disengagement_signals(m_id)
            bal = acc.get("balance", 0.0)
            phase = acc.get("phase", "Accumulation")

            if signals["risk_level"] == "High":
                high_risk_fum += bal
                risk_by_phase[phase] = risk_by_phase.get(phase, 0.0) + bal

            if signals["immediate_outreach_required"]:
                closure_inquiry_fum += bal

        at_risk_pct = round((high_risk_fum / total_fum) * 100, 2) if total_fum > 0 else 0.0

        return {
            "total_fund_fum_aud": round(total_fum, 2),
            "high_risk_fum_aud": round(high_risk_fum, 2),
            "closure_inquiry_fum_aud": round(closure_inquiry_fum, 2),
            "fum_at_risk_percentage": at_risk_pct,
            "at_risk_fum_by_phase": {k: round(v, 2) for k, v in risk_by_phase.items()},
            "currency": "AUD",
            "calculation_method": "Internal superannuation account balance sum of High-Risk / Closure-Inquiry members.",
        }


# Global singleton gateway
_default_gateway = SuperannuationDataGateway()


def get_member_profile(member_id: str) -> Dict[str, Any]:
    """MCP Tool: Return internal superannuation profile for member_id."""
    return _default_gateway.get_member_profile(member_id)


def get_member_disengagement_signals(member_id: str) -> Dict[str, Any]:
    """MCP Tool: Return disengagement and churn diagnostic signals for member_id."""
    return _default_gateway.get_member_disengagement_signals(member_id)


def get_cohort_churn_analytics(cohort_filter: Optional[str] = None) -> Dict[str, Any]:
    """MCP Tool: Return cohort-wide churn attrition factors and lookback attribution."""
    return _default_gateway.get_cohort_churn_analytics(cohort_filter)


def get_fum_outflow_summary() -> Dict[str, Any]:
    """MCP Tool: Return aggregate FUM at risk and phase distribution."""
    return _default_gateway.get_fum_outflow_summary()


# Tool definitions for Azure AI Foundry / OpenAI Function Calling
MCP_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_member_profile",
            "description": "Retrieve unified internal superannuation profile (balance, options, baseline contributions).",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_id": {
                        "type": "string",
                        "description": "The unique member identifier, e.g. MEM-001, MEM-002, MEM-003.",
                    }
                },
                "required": ["member_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_member_disengagement_signals",
            "description": "Analyze contribution drops, digital portal activity drops, and closure inquiries for a member.",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_id": {
                        "type": "string",
                        "description": "The unique member identifier, e.g. MEM-001, MEM-002, MEM-003.",
                    }
                },
                "required": ["member_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cohort_churn_analytics",
            "description": "Aggregate cohort churn drivers, risk distributions, and lookback attribution factors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cohort_filter": {
                        "type": "string",
                        "description": "Optional filter for cohort analysis.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fum_outflow_summary",
            "description": "Calculate total Funds Under Management (FUM) at risk in AUD and phase distribution.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]
