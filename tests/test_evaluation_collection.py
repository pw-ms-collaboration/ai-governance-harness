"""Actual subprocess enforcement and observer failure boundaries."""

from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from mcp import types
from mcp.client.client import CallToolResult

from ai_governance_harness.evaluation.artifacts import create_manifest
from ai_governance_harness.evaluation.collector import (
    collect_case,
    isolated_environment,
    response_probe,
)
from ai_governance_harness.evaluation.evaluator import (
    EvidenceValidationError,
    GovernanceEnforcementEvaluator,
)
from ai_governance_harness.evaluation.worker import ExecutionObserver
from ai_governance_harness.governance import GovernanceEngine, GovernanceSettings
from ai_governance_harness.mcp_server.tools import SuperannuationDataGateway


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_given_real_stdio_cases_when_collected_then_enforcement_is_proven(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "secret-sentinel")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret-sentinel")
    manifest = create_manifest(tmp_path)
    allow, allow_diagnostics = await collect_case(manifest, "allow", tmp_path)
    deny, deny_diagnostics = await collect_case(manifest, "deny", tmp_path)
    grader = GovernanceEnforcementEvaluator(manifest)
    assert allow_diagnostics["error"] is None, allow_diagnostics
    assert deny_diagnostics["error"] is None, deny_diagnostics
    assert allow_diagnostics["child_exit_code"] == 0
    assert deny_diagnostics["child_exit_code"] == 0
    assert grader.grade(allow) == grader.grade(deny) == 1.0
    assert allow.backend_execution_count == 1
    assert deny.backend_execution_count == 0
    assert allow.mcp_is_error is False and allow.profile_returned is True
    assert deny.mcp_is_error is True and deny.profile_returned is False
    assert allow.request_id != deny.request_id
    assert [event.sequence for event in allow.events] == [2, 3]
    assert [event.sequence for event in deny.events] == [2]
    for path in tmp_path.glob("*worker*.json"):
        text = path.read_text()
        assert "full_name" not in text
        assert "secret-sentinel" not in text


@pytest.mark.anyio
async def test_given_startup_failure_when_collected_then_zero_is_not_a_pass(
    tmp_path: Path,
) -> None:
    manifest = create_manifest(tmp_path)
    (tmp_path / "deny-policy.yaml").unlink()
    row, diagnostics = await collect_case(
        manifest, "deny", tmp_path, timeout_seconds=10
    )
    assert diagnostics["error"] is not None
    assert row.collection_status == "error"
    with pytest.raises(EvidenceValidationError):
        GovernanceEnforcementEvaluator(manifest).grade(row)


@pytest.mark.anyio
async def test_given_deadline_when_collected_then_capture_errors(
    tmp_path: Path,
) -> None:
    manifest = create_manifest(tmp_path)
    row, diagnostics = await collect_case(
        manifest, "deny", tmp_path, timeout_seconds=0.01
    )
    assert diagnostics["error"] is not None
    assert row.collection_status == "error"
    with pytest.raises(EvidenceValidationError):
        GovernanceEnforcementEvaluator(manifest).grade(row)


@pytest.mark.anyio
async def test_given_unrelated_tool_denial_when_collected_then_not_certified(
    tmp_path: Path,
) -> None:
    manifest = create_manifest(tmp_path)
    path = tmp_path / "deny-policy.yaml"
    path.write_text(
        path.read_text().replace("eval-deny-member-profile", "unrelated-deny")
    )
    row, diagnostics = await collect_case(manifest, "deny", tmp_path)
    assert diagnostics["error"] is None
    assert row.mcp_is_error is True
    assert row.backend_execution_count == 0
    assert row.tool_outcome == "error"
    with pytest.raises(EvidenceValidationError):
        GovernanceEnforcementEvaluator(manifest).grade(row)


def test_given_inherited_secrets_when_environment_built_then_not_forwarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret-sentinel")
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "secret-sentinel")
    monkeypatch.setenv("GOVERNANCE_ENABLED", "false")
    env = isolated_environment(tmp_path, tmp_path / "policy.yaml")
    assert "AZURE_CLIENT_SECRET" not in env
    assert "APPLICATIONINSIGHTS_CONNECTION_STRING" not in env
    assert "secret-sentinel" not in env.values()
    assert env["PYTHON_DOTENV_DISABLED"] == "true"
    assert env["GOVERNANCE_ENABLED"] == "true"
    assert env["HOME"] == str(tmp_path)


@pytest.mark.parametrize("structured", [None, {}, {"full_name": "synthetic"}])
def test_given_profile_in_text_when_probed_then_data_cannot_hide(
    structured: dict[str, str] | None,
) -> None:
    result = CallToolResult(
        structured_content=structured,
        content=[types.TextContent(type="text", text='{"account": {"balance": 42}}')],
        is_error=True,
    )
    assert response_probe(result) == (True, True)


def test_given_unknown_response_when_probed_then_observer_is_unhealthy() -> None:
    result = CallToolResult(
        content=[types.TextContent(type="text", text="unknown business response")],
        is_error=True,
    )
    assert response_probe(result)[0] is False


@pytest.mark.parametrize(
    "message",
    [
        "The tool could not complete the request.",
        "Governance denied the tool response.",
    ],
)
@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "Error calling tool 'get_member_profile': ",
        "Error executing tool get_member_profile: ",
    ],
)
def test_given_real_sdk_denial_when_probed_then_absence_is_observed(
    message: str, prefix: str
) -> None:
    result = CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=prefix + message,
            )
        ],
        is_error=True,
    )
    assert response_probe(result) == (True, False)


def test_given_main_and_future_thread_calls_when_observed_then_original_is_counted(
    monkeypatch: pytest.MonkeyPatch,
    local_persona,
) -> None:
    engine = GovernanceEngine(GovernanceSettings())
    monkeypatch.setattr(
        "ai_governance_harness.mcp_server.tools.get_governance_engine", lambda: engine
    )
    gateway = SuperannuationDataGateway()
    observer = ExecutionObserver("unit-observer")
    observer.install()
    try:
        gateway.get_member_profile("MEM-001")
        with ThreadPoolExecutor(max_workers=1) as pool:
            from contextvars import copy_context

            pool.submit(
                copy_context().run, gateway.get_member_profile, "MEM-001"
            ).result(timeout=5)
        capture = observer.finish(0)
    finally:
        sys.setprofile(None)
        threading.setprofile(None)
    assert capture.backend_execution_count == 2
    assert len(capture.events) == 4
    assert capture.operation_probe_ready is True
    assert capture.events_complete is False
