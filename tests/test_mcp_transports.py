"""End-to-end tests for MCP stdio and local HTTP transports."""

from __future__ import annotations

import os
import json
import socket
import subprocess
import sys
import tempfile
import time

import anyio
import httpx2
import pytest
from mcp import Client, StdioServerParameters, types
from mcp.client.streamable_http import streamable_http_client
from ai_governance_harness.identity.config import IdentitySettings
from ai_governance_harness.identity.constants import TENANT_ID, MCP_API_ID, INTERACTIVE_ID, REPORTING_ID

EXPECTED_TOOLS = {
    "get_member_profile",
    "get_member_disengagement_signals",
    "get_cohort_churn_analytics",
    "get_fum_outflow_summary",
    "prepare_member_outreach_case",
}


@pytest.fixture()
def anyio_backend() -> str:
    """Use the asyncio backend supported by the server runtime."""
    return "asyncio"


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return int(server_socket.getsockname()[1])


def _wait_for_port(
    port: int,
    process: subprocess.Popen[str],
    output,
) -> None:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output.seek(0)
            raise AssertionError(
                f"MCP HTTP process exited during startup: {output.read()}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    output.seek(0)
    raise AssertionError(f"MCP HTTP startup timed out: {output.read()}")


async def _approve_elicitation(_context, params):
    assert params.mode == "form"
    return types.ElicitResult(
        action="accept",
        content={"approved": True},
    )


@pytest.mark.anyio
@pytest.mark.parametrize("persona", [None, "retention_specialist"])
async def test_given_stdio_process_when_client_connects_then_protocol_is_usable(persona) -> None:
    # Arrange
    env = os.environ.copy()
    env["MCP_TRANSPORT"] = "stdio"
    env["APPLICATIONINSIGHTS_CONNECTION_STRING"] = ""
    env["MOCK_IDENTITY_ENABLED"] = "true"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["GOVERNANCE_ENVIRONMENT"] = "test"
    env["MCP_ENVIRONMENT"] = "test"
    env["MCP_HOSTED"] = "false"
    if persona is None:
        env.pop("MOCK_IDENTITY_LOCAL_PERSONA", None)
    else:
        env["MOCK_IDENTITY_LOCAL_PERSONA"] = persona
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ai_governance_harness.mcp_server"],
        env=env,
    )

    # Act
    async with Client(
        parameters,
        mode="legacy",
        elicitation_callback=_approve_elicitation,
    ) as client:
        listed = await client.list_tools()
        approved = await client.call_tool(
            "prepare_member_outreach_case",
            {"member_id": "MEM-002"},
        )

    # Assert
    assert {tool.name for tool in listed.tools} == EXPECTED_TOOLS
    assert approved.is_error == (persona is None)
    if persona is not None:
        assert approved.structured_content is not None
        assert approved.structured_content["approval"]["status"] == "approved"


@pytest.mark.anyio
async def test_given_http_process_when_client_connects_then_protocol_is_usable() -> None:
    # Arrange
    port = _available_port()
    identity_port = _available_port()
    identity_settings = IdentitySettings(port=identity_port)
    env = os.environ.copy()
    env.update(
        {
            "MCP_TRANSPORT": "streamable-http",
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(port),
            "MCP_PATH": "/mcp",
            "MCP_HOSTED": "false",
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "",
            "MOCK_IDENTITY_ENABLED": "true",
            "MOCK_IDENTITY_PORT": str(identity_port),
            "MOCK_IDENTITY_HOST": "127.0.0.1",
            "MCP_ENVIRONMENT": "test",
            "GOVERNANCE_ENVIRONMENT": "test",
            "MCP_PRINCIPAL_SOURCE": "jwt",
            "MCP_JWT_ISSUER": identity_settings.issuer,
            "MCP_JWT_JWKS_URL": identity_settings.jwks_url,
            "MCP_AUTH_TENANT_ID": TENANT_ID,
            "MCP_AUTH_AUDIENCE": MCP_API_ID,
            "MCP_AUTH_REQUIRED_SCOPE": "Tools.Read",
            "AGENT_ID_INTERACTIVE_ID": INTERACTIVE_ID,
            "AGENT_ID_REPORTING_ID": REPORTING_ID,
            "AGENT_ID_SIDECAR_URL": identity_settings.base_url,
            "MCP_SERVER_URL": f"http://127.0.0.1:{port}/mcp",
        }
    )
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
        identity_process = subprocess.Popen(
            [sys.executable, "-m", "ai_governance_harness.identity"],
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
        )
        process = None
        try:
            _wait_for_port(identity_port, identity_process, output)
            process = subprocess.Popen(
                [sys.executable, "-m", "ai_governance_harness.mcp_server"],
                env=env, stdout=output, stderr=subprocess.STDOUT, text=True,
            )
            _wait_for_port(port, process, output)

            # Act
            with anyio.fail_after(45):
                async with httpx2.AsyncClient(trust_env=False) as http:
                    ready = await http.get(f"http://127.0.0.1:{port}/health/ready")
                    assert ready.json()["identity"]["jwks"] == "loaded"
                    assert (await http.post(f"http://127.0.0.1:{port}/mcp", json={})).status_code == 401
                    for persona in ("analyst", "retention_specialist"):
                        signin = await http.post(f"{identity_settings.base_url}/mock/signin", json={"persona": persona})
                        exchange = await http.get(
                            f"{identity_settings.base_url}/AuthorizationHeader/mcp",
                            params={"AgentIdentity": INTERACTIVE_ID},
                            headers={"Authorization": "Bearer " + signin.json()["access_token"]},
                        )
                        async with httpx2.AsyncClient(
                            trust_env=False, headers={"Authorization": exchange.json()["authorizationHeader"]},
                        ) as authenticated:
                            async with Client(
                                streamable_http_client(f"http://127.0.0.1:{port}/mcp", http_client=authenticated),
                                elicitation_callback=_approve_elicitation,
                            ) as client:
                                aggregate = await client.call_tool("get_cohort_churn_analytics", {})
                                assert not aggregate.is_error
                                profile = await client.call_tool("get_member_profile", {"member_id": "MEM-001"})
                                assert profile.is_error == (persona == "analyst")
                                if persona == "retention_specialist":
                                    approved = await client.call_tool("prepare_member_outreach_case", {"member_id": "MEM-002"})
                                    assert not approved.is_error
                                    assert approved.structured_content["approval"]["status"] == "approved"
            report = subprocess.run(
                [sys.executable, "-m", "ai_governance_harness.report", "--json"],
                env=env, capture_output=True, text=True, timeout=60,
            )
            assert report.returncode == 0, report.stderr
            summary = json.loads(report.stdout)
            assert [item["outcome"] for item in summary["tools"]] == ["allowed", "allowed", "denied"]
            assert "Bearer" not in report.stdout and REPORTING_ID not in report.stdout
        finally:
            for child in (process, identity_process):
                if child is not None and child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=10)
