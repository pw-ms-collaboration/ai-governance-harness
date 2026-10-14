"""Demonstrate app-only reporting access through the authenticated MCP boundary."""

from __future__ import annotations

import argparse
import json
import os
import sys

import anyio
import httpx2
from dotenv import load_dotenv
from mcp import Client, types
from mcp.client.streamable_http import streamable_http_client

from ai_governance_harness.governance import GovernanceSettings
from ai_governance_harness.identity.config import require_loopback_url
from ai_governance_harness.identity.sidecar import AgentAuth, SidecarClient
from ai_governance_harness.mock_identity_guard import require_mock_identity_allowed


async def run_report(
    sidecar_url: str, agent_id: str, mcp_url: str, *, timeout: float
) -> list[dict[str, str]]:
    """Call aggregate tools and one member tool without printing data or tokens."""
    sidecar = SidecarClient(sidecar_url, timeout=timeout)
    outcomes = []
    async with (
        httpx2.AsyncClient(
            auth=AgentAuth(sidecar, agent_id),
            trust_env=False,
            follow_redirects=False,
            timeout=timeout,
        ) as http,
        Client(streamable_http_client(mcp_url, http_client=http)) as client,
    ):
        for name, arguments in (
            ("get_cohort_churn_analytics", {}),
            ("get_fum_outflow_summary", {}),
            ("get_member_profile", {"member_id": "MEM-001"}),
        ):
            result = await client.call_tool(name, arguments)
            if result.is_error and not any(
                isinstance(item, types.TextContent)
                and item.text
                == f"Error executing tool {name}: Governance denied the tool response."
                for item in result.content
            ):
                raise RuntimeError("MCP tool execution failed.")
            outcomes.append(
                {"tool": name, "outcome": "denied" if result.is_error else "allowed"}
            )
    return outcomes


def main(argv: list[str] | None = None) -> int:
    """Run the local mock reporting demonstration."""
    parser = argparse.ArgumentParser(
        description="Demonstrate local mock reporting identity."
    )
    parser.add_argument(
        "--json", action="store_true", help="Print only bounded per-tool outcomes."
    )
    args = parser.parse_args(argv)
    load_dotenv()
    try:
        require_mock_identity_allowed("report")
        sidecar_url = require_loopback_url(os.getenv("AGENT_ID_SIDECAR_URL", ""))
        mcp_url = require_loopback_url(os.getenv("MCP_SERVER_URL", ""))
        agent_id = os.getenv("AGENT_ID_REPORTING_ID", "").strip()
        if not agent_id:
            raise ValueError("Missing reporting identity.")
        timeout = GovernanceSettings.from_environment().operation_timeout_seconds
    except ValueError:
        print("Invalid or unsafe mock reporting configuration.", file=sys.stderr)
        return 2
    try:

        async def execute():
            with anyio.fail_after(timeout):
                return await run_report(sidecar_url, agent_id, mcp_url, timeout=timeout)

        outcomes = anyio.run(execute)
    except Exception:
        print("Mock reporting failed: identity or MCP is unavailable.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"identity": "local mock reporting agent", "tools": outcomes}))
    else:
        print("Local mock reporting agent (not Microsoft Entra)")
        for result in outcomes:
            print(f"{result['tool']}: {result['outcome']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
