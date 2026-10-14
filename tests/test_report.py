"""Bounded reporting summaries and sanitized failure exit codes."""

import json

import pytest
from types import SimpleNamespace
from mcp import types

from ai_governance_harness import report
from ai_governance_harness.identity.constants import REPORTING_ID

pytestmark = pytest.mark.usefixtures("mock_chat_environment")


@pytest.fixture
def report_environment(monkeypatch):
    monkeypatch.setenv("AGENT_ID_REPORTING_ID", REPORTING_ID)
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")


def test_given_report_results_when_printing_json_then_bounded_summary(
    report_environment, monkeypatch, capsys
):
    async def results(*args, **kwargs):
        return [
            {"tool": "get_cohort_churn_analytics", "outcome": "allowed"},
            {"tool": "get_fum_outflow_summary", "outcome": "allowed"},
            {"tool": "get_member_profile", "outcome": "denied"},
        ]

    monkeypatch.setattr(report, "run_report", results)
    assert report.main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["outcome"] for row in payload["tools"]] == [
        "allowed",
        "allowed",
        "denied",
    ]
    assert payload["identity"] == "local mock reporting agent"


def test_given_guard_failure_when_reporting_then_exit_two(
    report_environment, monkeypatch
):
    monkeypatch.setenv("GOVERNANCE_ENVIRONMENT", "staging")
    assert report.main([]) == 2


def test_given_dependency_failure_when_reporting_then_sanitized_exit_one(
    report_environment, monkeypatch, capsys
):
    async def fail(*args, **kwargs):
        raise RuntimeError("Bearer private-token-marker")

    monkeypatch.setattr(report, "run_report", fail)
    assert report.main([]) == 1
    assert "private-token-marker" not in capsys.readouterr().err


def test_given_non_policy_tool_error_when_reporting_then_not_a_successful_denial(
    monkeypatch,
):
    import anyio

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def call_tool(self, name, arguments):
            return SimpleNamespace(
                is_error=True,
                content=[
                    types.TextContent(
                        type="text",
                        text="The tool could not complete the request.",
                    )
                ],
            )

    monkeypatch.setattr(report, "Client", Client)

    async def run():
        with pytest.raises(RuntimeError, match="MCP tool execution failed"):
            await report.run_report(
                "http://127.0.0.1:8002",
                REPORTING_ID,
                "http://127.0.0.1:8001/mcp",
                timeout=1,
            )

    anyio.run(run)
