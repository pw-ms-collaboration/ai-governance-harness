"""Tests for the mandatory Agent Governance Toolkit boundary."""

from __future__ import annotations

import json
import logging
import statistics
import time

import pytest

from ai_governance_harness.governance import (
    GovernanceContext,
    GovernanceDeniedError,
    GovernanceEngine,
    GovernanceSettings,
    LifecyclePoint,
)
from ai_governance_harness.governance.config import DEFAULT_POLICY_PATH
from ai_governance_harness.governance.events import (
    GovernanceEventStore,
    governance_events,
)
from ai_governance_harness.governance.models import GovernanceDecision
from ai_governance_harness.governance.reliability import ReliabilityGuard
from ai_governance_harness.governance.sandbox import (
    ExecutionClass,
    SandboxGuard,
    SandboxUnavailableError,
)
from ai_governance_harness.governance.snapshot import (
    build_governance_snapshot,
    merge_governance_snapshots,
)
from ai_governance_harness.mcp_server import tools
from ai_governance_harness.mcp_server.telemetry import PrivacySafeJsonFormatter


def _settings(**overrides: object) -> GovernanceSettings:
    values: dict[str, object] = {
        "environment": "test",
        "policy_path": DEFAULT_POLICY_PATH,
    }
    values.update(overrides)
    return GovernanceSettings(**values)


@pytest.fixture(autouse=True)
def _clear_governance_events() -> None:
    governance_events.clear()


def _decision(action: str = "allow") -> GovernanceDecision:
    return GovernanceDecision(
        allowed=action == "allow",
        action=action,
        lifecycle_point=LifecyclePoint.PRE_TOOL,
        policy_digest="a" * 64,
        enforcement_mode="enforce",
        evaluation_ms=1.25,
    )


@pytest.mark.usefixtures("mcp_caller")
def test_policy_allows_known_tool_and_denies_unknown_action() -> None:
    engine = GovernanceEngine(_settings())

    allowed = engine.evaluate(
        LifecyclePoint.PRE_TOOL,
        "get_member_profile",
    )
    denied = engine.evaluate(LifecyclePoint.PRE_TOOL, "shell.execute")

    assert allowed.allowed is True
    assert allowed.matched_rule == "allow-mcp-retention-tools"
    assert denied.allowed is False
    assert denied.action == "deny"


def test_given_denied_policy_when_requiring_allowed_then_exposes_decision() -> None:
    # Arrange
    engine = GovernanceEngine(_settings())

    # Act
    with pytest.raises(GovernanceDeniedError) as error:
        engine.require_allowed(LifecyclePoint.PRE_TOOL, "shell.execute")

    # Assert
    assert error.value.action == "shell.execute"
    assert error.value.decision is not None
    assert error.value.decision.action == "deny"
    assert error.value.decision.lifecycle_point == LifecyclePoint.PRE_TOOL


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.usefixtures("chat_caller")
def test_given_external_denial_when_recording_then_enforces_and_counts_it(
    enabled: bool,
) -> None:
    # Arrange
    engine = GovernanceEngine(_settings(enabled=enabled))

    # Act
    decision = engine.record_external_denial(
        LifecyclePoint.POST_MODEL,
        "foundry.chat",
        policy_name="azure-ai-foundry",
        matched_rule="content_filter",
        source="chat",
    )
    snapshot = governance_events.snapshot()

    # Assert
    assert decision.allowed is False
    assert decision.enforcement_mode == "enforce"
    assert snapshot["counts"]["deny"] == 1
    assert snapshot["recent_events"][0]["policy_name"] == "azure-ai-foundry"
    assert snapshot["recent_events"][0]["boundary"] == "chat"
    assert snapshot["recent_events"][0]["actor"] == "interactive"


@pytest.mark.parametrize(
    ("status", "expected_allowed"),
    [("passed", True), ("personal_advice_requested", False), ("unknown", False)],
)
def test_given_advice_request_status_when_evaluating_input_then_enforces_policy(
    status: str,
    expected_allowed: bool,
) -> None:
    # Arrange
    engine = GovernanceEngine(_settings())

    # Act
    decision = engine.evaluate(
        LifecyclePoint.INPUT,
        "chat.input",
        policy_data={"advice_request_status": status},
    )

    # Assert
    assert decision.allowed is expected_allowed
    if status == "personal_advice_requested":
        assert decision.matched_rule == "deny-personal-advice-request"


@pytest.mark.parametrize(
    "action",
    [
        "get_member_profile",
        "get_member_disengagement_signals",
        "get_cohort_churn_analytics",
        "get_fum_outflow_summary",
        "prepare_member_outreach_case",
    ],
)
@pytest.mark.parametrize(
    ("status", "expected_allowed"),
    [("passed", True), ("personal_advice_detected", False), ("unknown", False), (None, False)],
)
def test_given_tool_scan_status_when_evaluating_result_then_requires_passed_scan(
    action: str,
    status: str | None,
    expected_allowed: bool,
) -> None:
    # Arrange
    engine = GovernanceEngine(_settings())
    data = {"advice_scan_status": status} if status is not None else {}

    # Act
    decision = engine.evaluate(
        LifecyclePoint.POST_TOOL,
        action,
        policy_data=data,
    )

    # Assert
    assert decision.allowed is expected_allowed
    if status == "personal_advice_detected":
        assert decision.matched_rule == "deny-personal-advice-tool-response"


@pytest.mark.usefixtures("mcp_caller")
def test_given_direct_gateway_advice_when_returning_result_then_policy_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    engine = GovernanceEngine(_settings())
    monkeypatch.setattr(tools, "get_governance_engine", lambda: engine)

    @tools.governed_read_only_tool("get_member_profile")
    def response() -> dict[str, object]:
        return {"nested": [{"text": "You should switch your super to Growth."}]}

    # Act & Assert
    with pytest.raises(GovernanceDeniedError):
        response()


def test_policy_evaluation_failure_denies_without_sensitive_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = GovernanceEngine(_settings())
    assert engine._engine is not None

    def fail_evaluation(*args: object, **kwargs: object) -> None:
        raise RuntimeError("raw prompt: account@example.com")

    monkeypatch.setattr(engine._engine, "evaluate", fail_evaluation)

    decision = engine.evaluate(LifecyclePoint.PRE_TOOL, "get_member_profile")

    assert decision.allowed is False
    assert decision.reason == "Governance policy evaluation failed."
    assert "account@example.com" not in decision.reason


def test_shared_gateway_denial_blocks_direct_legacy_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = tools.SuperannuationDataGateway()

    class _DenyEngine:
        settings = _settings()

        def require_allowed(self, *args: object, **kwargs: object) -> None:
            raise GovernanceDeniedError("denied")

    monkeypatch.setattr(tools, "get_governance_engine", _DenyEngine)

    with pytest.raises(GovernanceDeniedError):
        gateway.get_member_profile("MEM-001")


def test_executable_capability_fails_closed_without_sandbox() -> None:
    guard = SandboxGuard(_settings(sandbox_provider="none"))

    guard.require_ready(ExecutionClass.READ_ONLY_DATA)
    with pytest.raises(SandboxUnavailableError):
        guard.require_ready(ExecutionClass.CODE)


def test_raw_identity_is_not_exposed_to_policy_context() -> None:
    context = GovernanceContext(
        correlation_id="trace-123",
        principal_hash="a" * 64,
        authentication_outcome="authenticated",
    )

    policy_context = context.to_policy_context()

    assert policy_context["principal_hash"] == "a" * 64
    assert "email" not in policy_context
    assert "claims" not in policy_context


def test_structured_telemetry_drops_raw_content() -> None:
    formatter = PrivacySafeJsonFormatter("test", "revision")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="governance.policy.decision",
        args=(),
        exc_info=None,
    )
    record.governance_point = "pre_tool"
    record.governance_decision = "deny"
    record.raw_prompt = "email account@example.com and member MEM-001"

    payload = json.loads(formatter.format(record))

    assert payload["attributes"]["governance_point"] == "pre_tool"
    assert payload["attributes"]["governance_decision"] == "deny"
    assert "raw_prompt" not in payload["attributes"]
    assert "account@example.com" not in json.dumps(payload)


@pytest.mark.anyio
async def test_circuit_opens_after_configured_failure() -> None:
    guard = ReliabilityGuard(
        _settings(circuit_failure_threshold=1),
        "test-boundary",
    )

    async def fail() -> None:
        raise RuntimeError("dependency failed")

    with pytest.raises(RuntimeError):
        await guard.call(fail)

    assert guard.state == "open"
    with pytest.raises(Exception) as exception:
        await guard.call(fail)
    assert type(exception.value).__name__ == "CircuitOpenError"


def test_event_store_bounds_and_sanitizes_records() -> None:
    store = GovernanceEventStore(max_events=2)

    store.record(_decision(), action="safe.tool", source="chat")
    store.record(
        _decision("deny"),
        action="unsafe value account@example.com",
        source="demo",
    )
    store.record(_decision(), action="safe.final", source="mcp")

    snapshot = store.snapshot(limit=50)

    assert snapshot["total"] == 3
    assert snapshot["retained"] == 2
    assert snapshot["counts"]["allow"] == 2
    assert snapshot["counts"]["deny"] == 1
    serialized = json.dumps(snapshot)
    assert "account@example.com" not in serialized
    assert "unrecognized-action" in serialized


def test_snapshot_merge_rejects_malformed_remote_events_and_sensitive_fields() -> None:
    engine = GovernanceEngine(_settings())
    local = build_governance_snapshot(engine, source="chat")
    remote = {
        "schema": "ai-governance-observability/v1",
        "status": "ready",
        "events": {
            "total": 2,
            "counts": {"allow": 1, "made_up": 100},
            "recent_events": [
                {
                    "sequence": 1,
                    "occurred_at": "2026-10-14T00:00:00Z",
                    "source": "mcp",
                    "lifecycle_point": "pre_tool",
                    "action": "get_member_profile",
                    "decision": "allow",
                    "allowed": True,
                    "policy_digest": "b" * 64,
                    "enforcement_mode": "enforce",
                    "evaluation_ms": 1.0,
                },
                {
                    "sequence": 2,
                    "occurred_at": "2026-10-14T00:00:00Z",
                    "source": "mcp",
                    "lifecycle_point": "pre_tool",
                    "action": "raw prompt account@example.com",
                    "decision": "allow",
                    "allowed": True,
                    "policy_digest": "b" * 64,
                    "enforcement_mode": "enforce",
                    "evaluation_ms": 1.0,
                    "raw_prompt": "account@example.com",
                },
            ],
        },
    }

    valid_event = remote["events"]["recent_events"][0]
    remote["events"]["recent_events"].extend([
        {**valid_event, "oid": "private-object-marker"},
        {**valid_event, "azp": "private-agent-marker"},
    ])
    merged = merge_governance_snapshots(local, remote)

    assert merged["status"] == "ready"
    assert len(merged["events"]["recent_events"]) == 1
    serialized = json.dumps(merged)
    assert "account@example.com" not in serialized
    assert "made_up" not in serialized
    assert "private-object-marker" not in serialized
    assert "private-agent-marker" not in serialized


def test_snapshot_reports_remote_unavailability_as_partial() -> None:
    engine = GovernanceEngine(_settings())
    local = build_governance_snapshot(engine, source="chat")

    merged = merge_governance_snapshots(
        local,
        None,
        mcp_error="Connection unavailable.",
    )

    assert merged["status"] == "partial"
    assert merged["services"][1] == {
        "name": "mcp",
        "status": "unavailable",
        "detail": "Connection unavailable.",
    }


def test_policy_evaluation_p95_is_below_100_ms() -> None:
    engine = GovernanceEngine(_settings())
    durations: list[float] = []

    for _ in range(100):
        started_at = time.perf_counter()
        engine.evaluate(LifecyclePoint.PRE_TOOL, "get_member_profile")
        durations.append((time.perf_counter() - started_at) * 1000)

    p95 = statistics.quantiles(durations, n=100)[94]
    assert p95 < 100
