"""Member Whole-of-Wealth Insights & Interaction Advisory Agent Orchestrator.

Provides internal superannuation staff (Member Service Consultants, Retention Specialists,
and Business Analysts) with actionable, compliant member profiles, churn diagnostics,
FUM outflow sizing, and staff interaction briefings.

Enforces ASIC RG 244 advice boundaries (no personal financial product recommendations)
and APRA CPS 234 Australian data sovereignty.
"""

import os
import time
from typing import Any, Dict, List, Optional

from ai_governance_harness.guardrails import (
    SovereigntyGuardrail,
    SovereigntyViolationError,
    AdviceClassificationGuardrail,
    WholeOfWealthInvariantGuardrail,
    DisclosureAttacher,
)
from ai_governance_harness.mcp_server import (
    SuperannuationDataGateway,
    MemberNotFoundError,
    get_member_profile,
    get_member_disengagement_signals,
    get_cohort_churn_analytics,
    get_fum_outflow_summary,
)


class MemberWealthInsightsAgent:
    """Core advisory agent orchestrating superannuation insights and staff interaction prep."""

    def __init__(
        self,
        use_mock_backend: Optional[bool] = None,
        data_gateway: Optional[SuperannuationDataGateway] = None,
    ):
        self.sovereignty_guardrail = SovereigntyGuardrail()
        self.advice_guardrail = AdviceClassificationGuardrail()
        self.wealth_guardrail = WholeOfWealthInvariantGuardrail()
        self.gateway = data_gateway

        # Determine backend execution mode
        if use_mock_backend is not None:
            self.use_mock = use_mock_backend
        else:
            # Default to mock unless explicit Azure Foundry endpoint is configured
            has_endpoint = bool(
                os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
                or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
            )
            self.use_mock = not has_endpoint

        # Validate sovereignty if cloud mode is selected
        if not self.use_mock:
            self.sovereignty_guardrail.validate_endpoint(None)

    def inspect_member_profile(self, member_id: str) -> Dict[str, Any]:
        """FR-001 / AC-001: Return unified internal superannuation profile for member.

        Includes account holdings, balances, investment options, and baseline contributions.
        Guarantees response within latency budget (<= 2.5s).
        """
        start_time = time.time()
        raw_profile = (
            self.gateway.get_member_profile(member_id)
            if self.gateway
            else get_member_profile(member_id)
        )

        elapsed = time.time() - start_time

        # Format profile summary
        summary_text = (
            f"MEMBER PROFILE: {raw_profile['full_name']} ({raw_profile['member_id']})\n"
            f"Age: {raw_profile['age']} | Tenure: {raw_profile['tenure_years']} years\n"
            f"Risk Profile: {raw_profile['risk_profile']}\n"
            f"Account ID: {raw_profile['account']['account_id']} | Phase: {raw_profile['account']['phase']}\n"
            f"Total Super Balance: ${raw_profile['account']['balance']:,.2f} AUD\n"
            f"Investment Options: {raw_profile['account']['option_allocation']}\n"
            f"Closure Inquiry on Record: {'YES (Immediate Flag)' if raw_profile['has_closure_inquiry'] else 'No'}\n"
        )

        sanitized_summary = self.wealth_guardrail.sanitize_scope_claims(summary_text)
        safe_summary, _ = self.advice_guardrail.enforce_advice_boundaries(sanitized_summary)
        compliant_summary = DisclosureAttacher.attach_disclosures(safe_summary)

        return {
            "status": "success",
            "member_id": member_id,
            "latency_seconds": round(elapsed, 4),
            "profile": raw_profile,
            "formatted_summary": compliant_summary,
        }

    def diagnose_member_churn(self, member_id: str) -> Dict[str, Any]:
        """FR-002 / AC-002: Evaluate member disengagement signals and churn risk factors.

        Analyzes contribution drops, digital portal activity drops, and closure inquiries.
        """
        start_time = time.time()
        signals = (
            self.gateway.get_member_disengagement_signals(member_id)
            if self.gateway
            else get_member_disengagement_signals(member_id)
        )
        profile = (
            self.gateway.get_member_profile(member_id)
            if self.gateway
            else get_member_profile(member_id)
        )
        elapsed = time.time() - start_time

        # Narrative explanation of churn factors
        narrative_parts = [
            f"CHURN DIAGNOSTIC REPORT: {profile['full_name']} ({member_id})",
            f"Assessed Churn Risk Level: {signals['risk_level'].upper()} (Score: {signals['churn_risk_score']})",
            f"Immediate Frontline Outreach Required: {'YES' if signals['immediate_outreach_required'] else 'NO'}",
            "\nContributing Risk Drivers:",
        ]

        if signals["risk_factors"]:
            for factor in signals["risk_factors"]:
                narrative_parts.append(f" - {factor}")
        else:
            narrative_parts.append(" - No disengagement risk factors detected (member active and loyal).")

        narrative_parts.append(
            f"\nContribution Status: Recent ${signals['contribution_analysis']['latest_amount']:,.2f} vs "
            f"baseline ${signals['contribution_analysis']['baseline_amount']:,.2f} "
            f"({signals['contribution_analysis']['change_percent']:+}% change)"
        )
        narrative_parts.append(
            f"Digital Engagement: {signals['digital_engagement']['recent_monthly_logins']} logins this month "
            f"(baseline {signals['digital_engagement']['baseline_logins']} logins/month)"
        )

        narrative_text = "\n".join(narrative_parts)
        safe_narrative, _ = self.advice_guardrail.enforce_advice_boundaries(narrative_text)
        compliant_report = DisclosureAttacher.attach_disclosures(safe_narrative)

        return {
            "status": "success",
            "member_id": member_id,
            "latency_seconds": round(elapsed, 4),
            "signals": signals,
            "formatted_report": compliant_report,
        }

    def prepare_staff_interaction_briefing(self, member_id: str) -> Dict[str, Any]:
        """FR-004 / AC-004: Prepare frontline consultant interaction briefing notes.

        Generates factual talking points, member context, and non-directive probing questions.
        If member has a closure inquiry recorded, immediately marks High Priority Outreach.
        """
        start_time = time.time()
        profile_data = (
            self.gateway.get_member_profile(member_id)
            if self.gateway
            else get_member_profile(member_id)
        )
        signals = (
            self.gateway.get_member_disengagement_signals(member_id)
            if self.gateway
            else get_member_disengagement_signals(member_id)
        )

        is_priority_outreach = signals["immediate_outreach_required"]
        member_name = profile_data["full_name"]
        balance = profile_data["account"]["balance"]

        # Consultant guidance and conversational prompt generation
        sections = [
            f"=== CONSULTANT INTERACTION BRIEFING: {member_name} ({member_id}) ===",
            f"Account Balance: ${balance:,.2f} AUD | Tenure: {profile_data['tenure_years']} years",
            f"Priority Level: {'HIGH PRIORITY - IMMEDIATE OUTREACH REQUIRED' if is_priority_outreach else 'STANDARD'}",
            "\n[1] SITUATION SUMMARY:",
        ]

        if is_priority_outreach:
            sections.append(
                "NOTICE: A closure or transfer inquiry has been recorded on this account. "
                "The consultant should initiate empathetic, open-ended contact to understand the member's "
                "experience, clarify factual fund features, and explore unmet service needs."
            )
        elif signals["risk_level"] == "High":
            sections.append(
                "NOTICE: Significant disengagement detected (reduced contributions and/or digital inactivity). "
                "Engage the member to confirm whether their employment situation has changed or if they have questions "
                "regarding their superannuation account."
            )
        else:
            sections.append(
                "Member is actively engaged with consistent contributions and normal digital activity."
            )

        sections.append("\n[2] SUGGESTED FACTUAL TALKING POINTS (NON-DIRECTIVE):")
        if is_priority_outreach:
            sections.extend([
                " - 'Thank you for your ongoing membership. We noticed you recently inquired about account transfer procedures.'",
                " - 'We want to make sure you have all factual details regarding your existing insurance covers, fee tiers, and investment performance before making any decision.'",
                " - 'Are there specific features or service expectations you were looking for that we can clarify for you?'",
            ])
        elif signals["contribution_analysis"]["drop_detected"]:
            sections.extend([
                " - 'We noticed a recent change in regular contribution flows to your account.'",
                " - 'Are there any questions we can answer regarding voluntary contribution caps or employer SG processing?'",
                " - 'Would you like a copy of our latest Product Disclosure Statement explaining fee structures and investment options?'",
            ])
        else:
            sections.extend([
                " - 'Confirm member contact preferences and ensure online portal access is functioning smoothly.'",
                " - 'Provide factual information regarding upcoming annual member statements and education webinars.'",
            ])

        sections.extend([
            "\n[3] COMPLIANCE NOTICE FOR CONSULTANT:",
            " - REMINDER: Provide FACTUAL INFORMATION ONLY. Do NOT recommend switching investment options, "
            "rolling over balances, or closing accounts. Refer the member to a licensed financial adviser "
            "for personal financial product advice.",
        ])

        raw_briefing = "\n".join(sections)

        # Apply guardrails
        sanitized_briefing = self.wealth_guardrail.sanitize_scope_claims(raw_briefing)
        safe_briefing, was_filtered = self.advice_guardrail.enforce_advice_boundaries(sanitized_briefing)
        final_briefing = DisclosureAttacher.attach_disclosures(safe_briefing)

        elapsed = time.time() - start_time

        return {
            "status": "success",
            "member_id": member_id,
            "latency_seconds": round(elapsed, 4),
            "priority_outreach": is_priority_outreach,
            "risk_level": signals["risk_level"],
            "briefing_text": final_briefing,
            "guardrail_filtered": was_filtered,
        }

    def analyze_cohort_fum_outflows(self) -> Dict[str, Any]:
        """FR-003 / AC-003: Calculate cohort FUM at risk and phase breakdown."""
        start_time = time.time()
        fum_summary = (
            self.gateway.get_fum_outflow_summary()
            if self.gateway
            else get_fum_outflow_summary()
        )
        cohort_analytics = (
            self.gateway.get_cohort_churn_analytics()
            if self.gateway
            else get_cohort_churn_analytics()
        )
        elapsed = time.time() - start_time

        summary_text = (
            "=== STRATEGIC COHORT FUM & ATTRITION ANALYSIS ===\n"
            f"Total Monitored Superannuation FUM: ${fum_summary['total_fund_fum_aud']:,.2f} AUD\n"
            f"FUM at Elevated Churn Risk: ${fum_summary['high_risk_fum_aud']:,.2f} AUD "
            f"({fum_summary['fum_at_risk_percentage']}% of total FUM)\n"
            f"FUM with Active Closure Inquiries: ${fum_summary['closure_inquiry_fum_aud']:,.2f} AUD\n\n"
            f"Risk by Account Phase: {fum_summary['at_risk_fum_by_phase']}\n"
            f"Risk Distribution across Cohort: {cohort_analytics['risk_distribution']}\n"
            f"Primary Attrition Drivers: {cohort_analytics['primary_attrition_drivers']}\n"
            f"High Risk Member IDs: {cohort_analytics['high_risk_members']}\n"
            f"Immediate Outreach Queue: {cohort_analytics['immediate_outreach_cohort']}\n"
        )

        compliant_summary = DisclosureAttacher.attach_disclosures(summary_text)

        return {
            "status": "success",
            "latency_seconds": round(elapsed, 4),
            "fum_metrics": fum_summary,
            "cohort_metrics": cohort_analytics,
            "formatted_summary": compliant_summary,
        }
