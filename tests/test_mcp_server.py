"""Protocol-level tests for the MCP server adapter."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from mcp import Client

from ai_governance_harness.mcp_server import tools as gateway_tools
from ai_governance_harness.mcp_server.server import mcp


@pytest.fixture()
def anyio_backend() -> str:
    """Use the asyncio backend supported by the server runtime."""
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_gateway() -> Iterator[None]:
    """Restore the default gateway around protocol tests."""
    gateway_tools.initialize_gateway()
    yield
    gateway_tools.initialize_gateway()


@pytest.mark.anyio
async def test_given_server_when_listing_tools_then_exposes_exact_read_only_surface() -> None:
    # Act
    async with Client(mcp) as client:
        result = await client.list_tools()

    # Assert
    assert {tool.name for tool in result.tools} == {
        "get_member_profile",
        "get_member_disengagement_signals",
        "get_cohort_churn_analytics",
        "get_fum_outflow_summary",
    }
    assert all(tool.annotations and tool.annotations.read_only_hint for tool in result.tools)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_key"),
    [
        ("get_member_profile", {"member_id": "MEM-001"}, "member_id"),
        (
            "get_member_disengagement_signals",
            {"member_id": "MEM-002"},
            "churn_risk_score",
        ),
        ("get_cohort_churn_analytics", {}, "risk_distribution"),
        ("get_fum_outflow_summary", {}, "total_fund_fum_aud"),
    ],
)
async def test_given_valid_arguments_when_calling_tool_then_returns_provenance(
    tool_name: str,
    arguments: dict[str, str],
    expected_key: str,
) -> None:
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    # Assert
    assert result.is_error is False
    assert result.structured_content is not None
    assert expected_key in result.structured_content
    assert result.structured_content["provenance"]["synthetic"] is True


@pytest.mark.anyio
async def test_given_unknown_member_when_calling_tool_then_returns_sanitized_error() -> None:
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_member_profile",
            {"member_id": "MEM-999"},
        )

    # Assert
    assert result.is_error is True
    assert result.content[0].text.endswith("Requested member was not found.")


@pytest.mark.anyio
@pytest.mark.parametrize("member_id", ["../../etc/passwd", "MEM-1", ""])
async def test_given_invalid_member_id_when_calling_tool_then_rejects_argument(
    member_id: str,
) -> None:
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_member_profile",
            {"member_id": member_id},
        )

    # Assert
    assert result.is_error is True


@pytest.mark.anyio
async def test_given_unexpected_gateway_error_when_calling_tool_then_hides_details(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    def fail() -> dict[str, object]:
        raise RuntimeError("sensitive implementation detail")

    monkeypatch.setattr(gateway_tools, "get_fum_outflow_summary", fail)

    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("get_fum_outflow_summary", {})

    # Assert
    assert result.is_error is True
    assert result.content[0].text.endswith("The tool could not complete the request.")
    assert "sensitive implementation detail" not in result.content[0].text
    assert "sensitive implementation detail" not in caplog.text
