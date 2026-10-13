"""End-to-end tests for MCP stdio and local HTTP transports."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time

import anyio
import pytest
from mcp import Client, StdioServerParameters, types

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
    deadline = time.monotonic() + 15
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
    raise AssertionError("MCP HTTP process did not open its configured port.")


async def _approve_elicitation(_context, params):
    assert params.mode == "form"
    return types.ElicitResult(
        action="accept",
        content={"approved": True},
    )


@pytest.mark.anyio
async def test_given_stdio_process_when_client_connects_then_protocol_is_usable() -> None:
    # Arrange
    env = os.environ.copy()
    env["MCP_TRANSPORT"] = "stdio"
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
    assert approved.is_error is False
    assert approved.structured_content is not None
    assert approved.structured_content["approval"]["status"] == "approved"


@pytest.mark.anyio
async def test_given_http_process_when_client_connects_then_protocol_is_usable() -> None:
    # Arrange
    port = _available_port()
    env = os.environ.copy()
    env.update(
        {
            "MCP_TRANSPORT": "streamable-http",
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(port),
            "MCP_PATH": "/mcp",
            "MCP_HOSTED": "false",
        }
    )
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, "-m", "ai_governance_harness.mcp_server"],
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            _wait_for_port(port, process, output)

            # Act
            with anyio.fail_after(30):
                async with Client(
                    f"http://127.0.0.1:{port}/mcp",
                    elicitation_callback=_approve_elicitation,
                ) as client:
                    profile = await client.call_tool(
                        "get_member_profile",
                        {"member_id": "MEM-001"},
                    )
                    approved = await client.call_tool(
                        "prepare_member_outreach_case",
                        {"member_id": "MEM-002"},
                    )

            # Assert
            assert profile.is_error is False
            assert profile.structured_content is not None
            assert profile.structured_content["member_id"] == "MEM-001"
            assert approved.is_error is False
            assert approved.structured_content is not None
            assert approved.structured_content["approval"]["status"] == "approved"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
