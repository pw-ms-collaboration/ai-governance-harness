"""End-to-end tests for MCP stdio and local HTTP transports."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import pytest
from mcp import Client, StdioServerParameters

EXPECTED_TOOLS = {
    "get_member_profile",
    "get_member_disengagement_signals",
    "get_cohort_churn_analytics",
    "get_fum_outflow_summary",
}


@pytest.fixture()
def anyio_backend() -> str:
    """Use the asyncio backend supported by the server runtime."""
    return "asyncio"


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return int(server_socket.getsockname()[1])


def _wait_for_port(port: int, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            _, stderr = process.communicate()
            raise AssertionError(f"MCP HTTP process exited during startup: {stderr}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise AssertionError("MCP HTTP process did not open its configured port.")


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
    async with Client(parameters) as client:
        result = await client.list_tools()

    # Assert
    assert {tool.name for tool in result.tools} == EXPECTED_TOOLS


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
    process = subprocess.Popen(
        [sys.executable, "-m", "ai_governance_harness.mcp_server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_for_port(port, process)

        # Act
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            result = await client.call_tool(
                "get_member_profile",
                {"member_id": "MEM-001"},
            )

        # Assert
        assert result.is_error is False
        assert result.structured_content is not None
        assert result.structured_content["member_id"] == "MEM-001"
    finally:
        process.terminate()
        process.wait(timeout=10)
