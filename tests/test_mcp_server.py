"""Protocol-level tests for the MCP server adapter."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from mcp import Client, types

from ai_governance_harness.mcp_server import tools as gateway_tools
from ai_governance_harness.mcp_server.server import mcp


@pytest.fixture()
def anyio_backend() -> str:
    """Use the asyncio backend supported by the server runtime."""
    return "asyncio"


def _exception_messages(error: BaseException) -> list[str]:
    if isinstance(error, BaseExceptionGroup):
        return [
            message
            for nested in error.exceptions
            for message in _exception_messages(nested)
        ]
    return [str(error)]


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
        "prepare_member_outreach_case",
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


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool_name", "gateway_name", "arguments"),
    [
        ("get_member_profile", "get_member_profile", {"member_id": "MEM-001"}),
        (
            "get_member_disengagement_signals",
            "get_member_disengagement_signals",
            {"member_id": "MEM-001"},
        ),
        ("get_cohort_churn_analytics", "get_cohort_churn_analytics", {}),
        ("get_fum_outflow_summary", "get_fum_outflow_summary", {}),
        (
            "prepare_member_outreach_case",
            "get_member_disengagement_signals",
            {"member_id": "MEM-001"},
        ),
    ],
)
@pytest.mark.parametrize(
    ("text", "expected_error"),
    [
        ("You should switch your super to Growth. PRIVATE_MARKER", True),
        ("Your current investment option is Growth.", False),
        ("Consider obtaining personal financial advice before making a decision.", False),
    ],
)
async def test_given_tool_response_when_releasing_then_checks_advice_boundary(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tool_name: str,
    gateway_name: str,
    arguments: dict[str, str],
    text: str,
    expected_error: bool,
) -> None:
    # Arrange
    def response(*args: object) -> dict[str, object]:
        return {"nested": [{"text": text}]}

    async def approve(_context, _params):
        return types.ElicitResult(action="accept", content={"approved": True})

    monkeypatch.setattr(gateway_tools, gateway_name, response)

    # Act
    async with Client(mcp, elicitation_callback=approve) as client:
        result = await client.call_tool(tool_name, arguments)

    # Assert
    assert result.is_error is expected_error
    assert "PRIVATE_MARKER" not in caplog.text
    if expected_error:
        assert result.content[0].text.endswith("Governance denied the tool response.")
        assert "PRIVATE_MARKER" not in result.model_dump_json()
    else:
        assert text in result.model_dump_json()


@pytest.mark.anyio
async def test_given_approval_when_preparing_outreach_case_then_returns_case() -> None:
    # Arrange
    async def approve(_context, params):
        assert params.mode == "form"
        assert "approved" in params.requested_schema["properties"]
        return types.ElicitResult(
            action="accept",
            content={"approved": True},
        )

    # Act
    async with Client(mcp, elicitation_callback=approve) as client:
        result = await client.call_tool(
            "prepare_member_outreach_case",
            {"member_id": "MEM-002"},
        )

    # Assert
    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["approval"] == {
        "status": "approved",
        "mechanism": "mcp_form_elicitation",
    }
    assert result.structured_content["external_action_executed"] is False
    assert (
        result.structured_content["disengagement_signals"]["member_id"]
        == "MEM-002"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("action", "expected_message"),
    [
        ("decline", "Approval was declined. No operation was executed."),
        ("cancel", "Approval was cancelled. No operation was executed."),
    ],
)
async def test_given_non_acceptance_when_preparing_case_then_fails_closed(
    action: str,
    expected_message: str,
) -> None:
    # Arrange
    async def do_not_approve(_context, _params):
        return types.ElicitResult(action=action)

    # Act
    async with Client(mcp, elicitation_callback=do_not_approve) as client:
        result = await client.call_tool(
            "prepare_member_outreach_case",
            {"member_id": "MEM-002"},
        )

    # Assert
    assert result.is_error is True
    assert result.content[0].text.endswith(expected_message)


@pytest.mark.anyio
async def test_given_negative_form_response_when_preparing_case_then_fails_closed() -> None:
    # Arrange
    async def reject(_context, _params):
        return types.ElicitResult(
            action="accept",
            content={"approved": False},
        )

    # Act
    async with Client(mcp, elicitation_callback=reject) as client:
        result = await client.call_tool(
            "prepare_member_outreach_case",
            {"member_id": "MEM-002"},
        )

    # Assert
    assert result.is_error is True
    assert result.content[0].text.endswith(
        "Explicit approval is required. No operation was executed."
    )


@pytest.mark.anyio
async def test_given_invalid_form_response_when_preparing_case_then_fails_closed() -> None:
    # Arrange
    async def return_invalid_content(_context, _params):
        return types.ElicitResult(
            action="accept",
            content={"approved": "yes"},
        )

    # Act
    async with Client(mcp, elicitation_callback=return_invalid_content) as client:
        result = await client.call_tool(
            "prepare_member_outreach_case",
            {"member_id": "MEM-002"},
        )

    # Assert
    assert result.is_error is True
    assert "does not match the requested schema" in result.content[0].text


@pytest.mark.anyio
async def test_given_client_without_elicitation_when_preparing_case_then_fails_closed() -> None:
    # Act
    with pytest.raises(BaseExceptionGroup) as exc_info:
        async with Client(mcp) as client:
            await client.call_tool(
                "prepare_member_outreach_case",
                {"member_id": "MEM-002"},
            )

    # Assert
    assert any(
        "did not declare the form elicitation capability" in message
        for message in _exception_messages(exc_info.value)
    )
