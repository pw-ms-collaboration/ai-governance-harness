"""Tests for the mandatory Agent Governance Toolkit boundary."""

from __future__ import annotations

import json
import logging
import statistics
import time
from pathlib import Path

import pytest
import yaml

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
from ai_governance_harness.governance.models import GovernanceDecision, PolicyProvenance
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
from ai_governance_harness.governance.telemetry import provenance_attributes
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


@pytest.mark.parametrize(
    ("point", "action", "data", "rule"),
    [
        (LifecyclePoint.INPUT, "chat.input",
         {"classification_status": "classified", "request_intent": "financial_recommendation",
          "advice_subject": "identified_member", "product_scope": "superannuation_option",
          "confidence": "high"},
         "deny-identified-member-financial-recommendation"),
        (LifecyclePoint.POST_TOOL, "get_member_profile",
         {"advice_scan_status": "personal_advice_detected"},
         "deny-personal-advice-tool-response"),
        (LifecyclePoint.INPUT, "chat.input",
         {"classification_status": "classified", "request_intent": "factual_information",
          "confidence": "high"}, "allow-chat-input"),
    ],
)
def test_given_tagged_rule_when_evaluating_then_attributes_event_and_snapshot(
    point: LifecyclePoint, action: str, data: dict[str, str], rule: str,
) -> None:
    engine = GovernanceEngine(_settings())

    decision = engine.evaluate(point, action, policy_data=data, source="chat")
    snapshot = build_governance_snapshot(engine, source="chat")
    merged = merge_governance_snapshots(snapshot, snapshot)

    expected = {
        "layer": "business-unit", "policy_id": "BU-SUPER-001",
        "policy_version": "1.0", "source": "superannuation-ba-policy-source.yaml",
    }
    assert decision.matched_rule == rule
    assert decision.provenance is not None
    assert decision.provenance.model_dump() == expected
    assert all(event["provenance"] == expected
               for event in merged["events"]["recent_events"])
    assert next(item for item in snapshot["policy"]["rules"]
                if item["name"] == rule)["provenance"] == expected


@pytest.mark.parametrize(
    ("action", "point", "data"),
    [
        ("chat.input", LifecyclePoint.INPUT, {"request_intent": "unknown"}),
        ("shell.execute", LifecyclePoint.PRE_TOOL, {}),
    ],
)
def test_given_unattributed_rule_when_evaluating_then_does_not_infer_bu_origin(
    action: str, point: LifecyclePoint, data: dict[str, object],
) -> None:
    engine = GovernanceEngine(_settings())
    data["provenance"] = {"policy_id": "caller-supplied"}

    decision = engine.evaluate(point, action, policy_data=data)

    assert decision.provenance is None
    assert governance_events.snapshot()["recent_events"][0]["provenance"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("layer", "regulatory"),
        ("policy_id", "private@example.com"),
        ("policy_id", "a" * 65),
        ("policy_version", 1.0),
        ("policy_version", "a" * 33),
        ("source", "a" * 124 + ".yaml"),
        ("source", "../private.yaml"),
        ("source", "C:\\private.yaml"),
        ("prompt", "sensitive"),
    ],
)
def test_given_invalid_provenance_when_loading_then_rejects_configuration(
    tmp_path: Path, field: str, value: object,
) -> None:
    document = yaml.safe_load(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    document["rules"][0]["provenance"][field] = value
    policy_path = tmp_path / "invalid.yaml"
    policy_path.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ValueError):
        GovernanceEngine(_settings(policy_path=policy_path))


def test_given_duplicate_tagged_rule_when_loading_then_rejects_ambiguous_origin(
    tmp_path: Path,
) -> None:
    document = yaml.safe_load(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    document["rules"].append(dict(document["rules"][0]))
    policy_path = tmp_path / "duplicate.yaml"
    policy_path.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ValueError, match="unique policy rule names"):
        GovernanceEngine(_settings(policy_path=policy_path))


def test_given_invalid_remote_provenance_when_merging_then_drops_event() -> None:
    engine = GovernanceEngine(_settings())
    engine.evaluate(
        LifecyclePoint.INPUT, "chat.input",
        policy_data={"classification_status": "classified",
                     "request_intent": "financial_recommendation",
                     "advice_subject": "identified_member", "confidence": "high"},
    )
    snapshot = build_governance_snapshot(engine, source="chat")
    remote = json.loads(json.dumps(snapshot))
    remote["events"]["recent_events"][0]["provenance"]["source"] = "../private.yaml"

    merged = merge_governance_snapshots(snapshot, remote)

    assert len(merged["events"]["recent_events"]) == 1
    assert "../private.yaml" not in json.dumps(merged)


@pytest.mark.parametrize("source_name", [
    "superannuation-ba-policy-source.yaml",
    "identity-policy-source.yaml",
])
def test_given_policy_source_when_loading_then_all_mappings_match_active_provenance(
    source_name: str,
) -> None:
    source_path = DEFAULT_POLICY_PATH.with_name(source_name)
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    engine = GovernanceEngine(_settings())
    expected = PolicyProvenance(
        layer=source["policy_layer"], policy_id=source["policy_id"],
        policy_version=source["version"], source=source_path.name,
    )

    for name in [item["rule"] for item in source["rule_mappings"]] + source.get("supporting_rules", []):
        assert engine.rule_provenance(name) == expected


@pytest.mark.parametrize("layer", ["identity", "regulation", "enterprise", "business-unit"])
def test_given_supported_origin_when_evaluating_then_preserves_attribution(
    tmp_path: Path, layer: str,
) -> None:
    document = yaml.safe_load(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    expected = {
        "layer": layer, "policy_id": "TEST-001", "policy_version": "1.0",
        "source": "test-policy-source.yaml",
    }
    document["rules"][0]["provenance"] = expected
    policy_path = tmp_path / "tagged.yaml"
    policy_path.write_text(yaml.safe_dump(document), encoding="utf-8")
    engine = GovernanceEngine(_settings(policy_path=policy_path))

    decision = engine.evaluate(
        LifecyclePoint.PRE_TOOL, "prepare_member_outreach_case",
        context=GovernanceContext(
            boundary="mcp", actor="interactive", token_type="user",
            staff_role="retention_specialist",
        ),
        policy_data={"retention_handling_status": "specialist_required"},
    )

    assert decision.allowed is False
    assert decision.matched_rule == "deny-outreach-requiring-specialist-handling"
    assert decision.provenance is not None
    assert decision.provenance.model_dump() == expected
    assert governance_events.snapshot()["recent_events"][0]["provenance"] == expected
    assert provenance_attributes(decision.provenance) == {
        "governance.policy.layer": layer,
        "governance.policy.id": "TEST-001",
        "governance.policy.version": "1.0",
        "governance.policy.source": "test-policy-source.yaml",
    }


def test_given_default_policy_when_inspecting_then_regulatory_mappings_are_not_invented() -> None:
    engine = GovernanceEngine(_settings())
    snapshot = build_governance_snapshot(engine, source="chat")

    assert all(
        rule["provenance"] is None or rule["provenance"]["layer"] != "regulation"
        for rule in snapshot["policy"]["rules"]
    )


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
    assert decision.provenance is None
    assert snapshot["recent_events"][0]["provenance"] is None


@pytest.mark.usefixtures("chat_caller")
def test_given_human_approval_gate_when_recording_then_counts_require_approval() -> None:
    # Arrange
    engine = GovernanceEngine(_settings(enabled=True))

    # Act
    decision = engine.record_approval_required(
        "prepare_member_outreach_case",
        source="mcp",
    )
    snapshot = governance_events.snapshot()

    # Assert
    assert decision.allowed is False
    assert decision.action == "require_approval"
    assert decision.lifecycle_point == LifecyclePoint.PRE_TOOL
    assert snapshot["counts"]["require_approval"] == 1
    event = snapshot["recent_events"][0]
    assert event["source"] == "mcp"
    assert event["matched_rule"] == "require-human-approval"
    assert event["policy_name"] == "human-approval-gate"


@pytest.mark.parametrize(
    ("overrides", "expected_allowed", "expected_rule"),
    [
        ({}, True, "allow-chat-input"),
        (
            {
                "request_intent": "financial_recommendation",
                "advice_subject": "identified_member",
                "financial_action": "invest",
                "product_scope": "superannuation_option",
            },
            False,
            "deny-identified-member-financial-recommendation",
        ),
        (
            {
                "request_intent": "financial_recommendation",
                "advice_subject": "general_audience",
                "financial_action": "buy",
                "product_scope": "external_security",
            },
            False,
            "deny-external-security-recommendation",
        ),
        (
            {
                "request_intent": "financial_recommendation",
                "advice_subject": "general_audience",
                "financial_action": "allocate",
                "product_scope": "superannuation_option",
            },
            False,
            "deny-general-financial-recommendation",
        ),
        (
            {"classification_status": "unavailable"},
            False,
            "deny-unclassified-chat-input",
        ),
        (
            {"request_intent": "unknown"},
            False,
            "deny-unknown-chat-intent",
        ),
        (
            {"confidence": "low"},
            False,
            "deny-low-confidence-chat-input",
        ),
    ],
)
def test_given_semantic_advice_facts_when_evaluating_input_then_enforces_policy(
    overrides: dict[str, str],
    expected_allowed: bool,
    expected_rule: str,
) -> None:
    # Arrange
    engine = GovernanceEngine(_settings())
    policy_data = {
        "classification_status": "classified",
        "request_intent": "factual_information",
        "advice_subject": "none",
        "financial_action": "none",
        "product_scope": "none",
        "confidence": "high",
        **overrides,
    }

    # Act
    decision = engine.evaluate(
        LifecyclePoint.INPUT,
        "chat.input",
        policy_data=policy_data,
    )

    # Assert
    assert decision.allowed is expected_allowed
    assert decision.matched_rule == expected_rule


@pytest.mark.parametrize(
    "lifecycle_point",
    [LifecyclePoint.PRE_MODEL, LifecyclePoint.POST_MODEL],
)
def test_classifier_model_lifecycle_is_explicitly_allowed(
    lifecycle_point: LifecyclePoint,
) -> None:
    engine = GovernanceEngine(_settings())

    decision = engine.evaluate(
        lifecycle_point,
        "foundry.advice_classifier",
        policy_data={"classification_status": "classified"},
    )

    assert decision.allowed is True


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


@pytest.mark.parametrize(
    ("action", "policy_data", "expected_rule"),
    [
        ("shell.execute", {"tool_status": "unregistered"}, "deny-unregistered-tool"),
        (
            "prepare_member_outreach_case",
            {"tool_known": True},
            "deny-outreach-without-eligibility-facts",
        ),
        (
            "prepare_member_outreach_case",
            {"retention_handling_status": "not_a_status"},
            "deny-outreach-without-eligibility-facts",
        ),
        (
            "prepare_member_outreach_case",
            {"retention_handling_status": "routine_permitted"},
            "allow-chat-eligible-outreach-case",
        ),
    ],
)
def test_given_pre_tool_facts_when_evaluating_then_named_rule_matches(
    action: str,
    policy_data: dict[str, object],
    expected_rule: str,
) -> None:
    # Arrange
    engine = GovernanceEngine(_settings())
    context = GovernanceContext(boundary="chat", actor="interactive")

    # Act
    decision = engine.evaluate(
        LifecyclePoint.PRE_TOOL, action, policy_data=policy_data, context=context,
    )

    # Assert
    assert decision.matched_rule == expected_rule


def test_given_every_classification_when_evaluating_input_then_a_rule_matches() -> None:
    # Arrange
    from itertools import product

    from ai_governance_harness.guardrails.advice_classifier import (
        AdviceSubject,
        ClassificationConfidence,
        FinancialAction,
        ProductScope,
        RequestIntent,
    )

    engine = GovernanceEngine(_settings())
    unmatched = []

    # Act
    for intent, subject, action, scope, confidence in product(
        RequestIntent, AdviceSubject, FinancialAction, ProductScope,
        ClassificationConfidence,
    ):
        policy_data = {
            "classification_status": "classified",
            "request_intent": intent.value,
            "advice_subject": subject.value,
            "financial_action": action.value,
            "product_scope": scope.value,
            "confidence": confidence.value,
        }
        decision = engine.evaluate(
            LifecyclePoint.INPUT, "chat.input", policy_data=policy_data,
        )
        if decision.matched_rule is None:
            unmatched.append(policy_data)

    # Assert
    assert unmatched == []
