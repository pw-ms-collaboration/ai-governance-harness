"""Staff Operator Command-Line Interface.

Provides internal superannuation consultants and analysts with commands to inspect
member profiles, diagnose churn risks, prepare compliant interaction briefings,
and analyze cohort FUM outflows.
"""

import argparse
import json
import sys
from typing import Optional

from ai_governance_harness.agent import MemberWealthInsightsAgent
from ai_governance_harness.mcp_server import MemberNotFoundError


def format_header(title: str) -> str:
    """Format section banner for terminal output."""
    border = "=" * 70
    return f"\n{border}\n  {title}\n{border}\n"


def run_cli(args: Optional[list] = None) -> int:
    """Main CLI entrypoint parser and dispatcher."""
    parser = argparse.ArgumentParser(
        prog="ai-governance-harness",
        description="Member Whole-of-Wealth Insights & Interaction Advisory Agent CLI",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Connect to live Azure AI Foundry (requires credentials in .env).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output raw structured JSON instead of formatted text.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Operational commands")

    # Command: profile
    p_parser = subparsers.add_parser("profile", help="Inspect unified member superannuation profile")
    p_parser.add_argument("member_id", help="Member identifier (e.g. MEM-001, MEM-002, MEM-003)")

    # Command: churn
    c_parser = subparsers.add_parser("churn", help="Diagnose member churn risk factors and disengagement")
    c_parser.add_argument("member_id", help="Member identifier (e.g. MEM-001, MEM-002, MEM-003)")

    # Command: prep
    prep_parser = subparsers.add_parser("prep", help="Generate consultant interaction briefing notes")
    prep_parser.add_argument("member_id", help="Member identifier (e.g. MEM-001, MEM-002, MEM-003)")

    # Command: fum-outflows
    subparsers.add_parser("fum-outflows", help="Analyze cohort-level Funds Under Management (FUM) at risk")

    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 1

    use_mock = not parsed_args.live
    agent = MemberWealthInsightsAgent(use_mock_backend=use_mock)

    try:
        if parsed_args.command == "profile":
            result = agent.inspect_member_profile(parsed_args.member_id)
            if parsed_args.json_output:
                print(json.dumps(result, indent=2))
            else:
                print(format_header("MEMBER WHOLE-OF-WEALTH INSIGHTS - PROFILE INSPECTION"))
                print(result["formatted_summary"])
                print(f"[Latency: {result['latency_seconds']:.3f}s]")

        elif parsed_args.command == "churn":
            result = agent.diagnose_member_churn(parsed_args.member_id)
            if parsed_args.json_output:
                print(json.dumps(result, indent=2))
            else:
                print(format_header("MEMBER ATTRITION & CHURN DIAGNOSTICS"))
                print(result["formatted_report"])
                print(f"[Latency: {result['latency_seconds']:.3f}s]")

        elif parsed_args.command == "prep":
            result = agent.prepare_staff_interaction_briefing(parsed_args.member_id)
            if parsed_args.json_output:
                print(json.dumps(result, indent=2))
            else:
                print(format_header("STAFF INTERACTION BRIEFING & TALKING POINTS"))
                print(result["briefing_text"])
                print(f"[Latency: {result['latency_seconds']:.3f}s]")

        elif parsed_args.command == "fum-outflows":
            result = agent.analyze_cohort_fum_outflows()
            if parsed_args.json_output:
                print(json.dumps(result, indent=2))
            else:
                print(format_header("COHORT FUNDS UNDER MANAGEMENT (FUM) OUTFLOW SIZING"))
                print(result["formatted_summary"])
                print(f"[Latency: {result['latency_seconds']:.3f}s]")

        return 0

    except MemberNotFoundError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2
    except Exception as err:
        print(f"Unexpected error: {err}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(run_cli())
