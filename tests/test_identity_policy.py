"""Identity policy matrix, unsafe-input and local guard contracts."""

import itertools
import json
import re

import pytest
import yaml
from pydantic import ValidationError

from ai_governance_harness.governance import (
    GovernanceContext,
    GovernanceDeniedError,
    GovernanceEngine,
    GovernanceSettings,
    LifecyclePoint,
    governance_context,
)
from ai_governance_harness.governance.config import DEFAULT_POLICY_PATH
from ai_governance_harness.governance.events import governance_events
from ai_governance_harness.mock_identity_guard import (
    MockIdentityGuardError,
    require_mock_identity_allowed,
    resolve_local_persona,
)
from ai_governance_harness.mcp_server.tools import SuperannuationDataGateway

TOOLS = (
    "get_cohort_churn_analytics",
    "get_fum_outflow_summary",
    "get_member_profile",
    "get_member_disengagement_signals",
    "prepare_member_outreach_case",
)
ROLES = (
    "analyst",
    "retention_specialist",
    "compliance_reviewer",
    "administrator",
    "none",
    None,
)


def test_given_all_identity_combinations_when_evaluating_then_exact_matrix() -> None:
    engine = GovernanceEngine(GovernanceSettings(environment="test"))
    for boundary, actor, token_type, role, tool in itertools.product(
        ("chat", "mcp", "local", None),
        ("interactive", "reporting", None),
        ("user", "app", None),
        ROLES,
        TOOLS,
    ):
        aggregate = tool in TOOLS[:2]
        staff_allowed = role == "retention_specialist" or (
            role == "analyst" and (
                aggregate or tool == "get_member_disengagement_signals"
            )
        )
        expected = (
            (boundary == "chat" and actor == "interactive")
            or (boundary == "local" and staff_allowed)
            or (
                boundary == "mcp"
                and actor == "interactive"
                and token_type == "user"
                and staff_allowed
            )
            or (
                boundary == "mcp"
                and actor == "reporting"
                and token_type == "app"
                and aggregate
            )
        )
        context = GovernanceContext(
            boundary=boundary,
            actor=actor,
            token_type=token_type,
            staff_role=role,
        )
        result = engine.evaluate(
            LifecyclePoint.PRE_TOOL, tool, context=context,
            policy_data={"retention_handling_status": "routine_permitted"},
        )
        assert result.allowed == expected, (context, tool, result)
        if not expected:
            assert result.matched_rule is not None
            assert result.matched_rule.startswith("deny-"), (context, tool, result)
            assert result.provenance is not None
            assert result.provenance.layer == "identity"
            assert result.provenance.policy_id == "IDENTITY-001"
        if tool == "prepare_member_outreach_case":
            for status in (None, "unknown", "specialist_required", "duplicate_open"):
                assert not engine.evaluate(
                    LifecyclePoint.PRE_TOOL, tool, context=context,
                    policy_data={"retention_handling_status": status},
                ).allowed


def test_given_bad_policy_snapshots_when_evaluating_each_allow_rule_then_deny() -> None:
    engine = GovernanceEngine(GovernanceSettings(environment="test"))
    rules = yaml.safe_load(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))["rules"]
    for rule in rules:
        if rule["stage"] != "pre_tool" or rule["action"] != "allow":
            continue
        values = dict(re.findall(r"governance\.(\w+) == '([^']+)'", rule["condition"]))
        tool = re.search(r"action.type (?:in \[|== )'([^']+)'", rule["condition"])[1]
        for field in values:
            for bad in (
                [],
                {},
                42,
                None,
                "unknown",
                values[field].upper(),
                f" {values[field]} ",
            ):
                snapshot = {**values, field: bad}

                class BadSnapshot(GovernanceContext):
                    def to_policy_context(self):
                        return snapshot

                assert not engine.evaluate(
                    LifecyclePoint.PRE_TOOL,
                    tool,
                    context=BadSnapshot(),
                    policy_data={"retention_handling_status": "routine_permitted"},
                ).allowed, (rule["name"], field, bad)
            snapshot = {key: value for key, value in values.items() if key != field}
            assert not engine.evaluate(
                LifecyclePoint.PRE_TOOL,
                tool,
                context=BadSnapshot(),
                policy_data={"retention_handling_status": "routine_permitted"},
            ).allowed


@pytest.mark.parametrize("field", ["boundary", "actor", "token_type", "staff_role"])
def test_given_unknown_enum_when_constructing_context_then_reject(field: str) -> None:
    with pytest.raises(ValidationError):
        GovernanceContext(**{field: "untrusted"})
    assert field not in GovernanceContext().to_policy_context()


@pytest.mark.parametrize(
    "context",
    [
        GovernanceContext(boundary="local", staff_role="analyst"),
        GovernanceContext(
            boundary="mcp", actor="interactive", token_type="user", staff_role="analyst"
        ),
        GovernanceContext(boundary="mcp", actor="reporting", token_type="app"),
    ],
)
def test_given_caller_when_using_gateway_then_enforces_profile_and_signals_permissions(
    context,
):
    gateway = SuperannuationDataGateway()
    with governance_context(context):
        assert gateway.get_cohort_churn_analytics()
        assert gateway.get_fum_outflow_summary()
        if context.staff_role == "analyst":
            signals = gateway.get_member_disengagement_signals("MEM-001")
            assert signals["member_id"] == "MEM-001"
            assert "full_name" not in signals
            assert "account" not in signals
        else:
            with pytest.raises(GovernanceDeniedError):
                gateway.get_member_disengagement_signals("MEM-001")
        with pytest.raises(GovernanceDeniedError) as error:
            gateway.get_member_profile("MEM-001")
        assert error.value.decision is not None
        expected_rule = (
            "deny-analyst-member-tools" if context.staff_role == "analyst"
            else "deny-reporting-member-tools"
        )
        assert error.value.decision.matched_rule == expected_rule
        assert error.value.decision.provenance is not None
        assert error.value.decision.provenance.layer == "identity"


@pytest.fixture
def guarded_environment(monkeypatch):
    for name in (
        "MOCK_IDENTITY_ENABLED",
        "MOCK_IDENTITY_LOCAL_PERSONA",
        "MCP_HOSTED",
        "MCP_ENVIRONMENT",
        "GOVERNANCE_ENVIRONMENT",
        "CONTAINER_APP_NAME",
        "CONTAINER_APP_REVISION",
        "CONTAINER_APP_HOSTNAME",
        "WEBSITE_INSTANCE_ID",
        "WEBSITE_SITE_NAME",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "true")
    return monkeypatch


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MOCK_IDENTITY_ENABLED", "false"),
        ("MOCK_IDENTITY_ENABLED", "sensitive-invalid-value"),
        ("MCP_HOSTED", "true"),
        ("MCP_ENVIRONMENT", "staging"),
        ("MCP_ENVIRONMENT", "production"),
        ("GOVERNANCE_ENVIRONMENT", "staging"),
        ("GOVERNANCE_ENVIRONMENT", "production"),
        ("CONTAINER_APP_NAME", ""),
        ("CONTAINER_APP_REVISION", "revision"),
    ],
)
def test_given_unsafe_environment_when_guarding_then_refuse(
    guarded_environment, name, value
):
    guarded_environment.setenv("GOVERNANCE_ENVIRONMENT", "local")
    guarded_environment.setenv(name, value)
    with pytest.raises(MockIdentityGuardError) as error:
        require_mock_identity_allowed("test", bind_host="127.0.0.1")
    assert name in str(error.value)
    assert "sensitive-invalid-value" not in str(error.value)


def test_given_local_persona_when_resolving_then_guard_and_fail_closed(
    guarded_environment,
):
    assert resolve_local_persona() is None
    require_mock_identity_allowed("test", bind_host="::1")
    with pytest.raises(MockIdentityGuardError):
        require_mock_identity_allowed("test", bind_host="0.0.0.0")
    guarded_environment.setenv("MOCK_IDENTITY_LOCAL_PERSONA", "unknown")
    with pytest.raises(MockIdentityGuardError):
        resolve_local_persona()
    guarded_environment.setenv("MOCK_IDENTITY_LOCAL_PERSONA", "analyst")
    assert resolve_local_persona() == "analyst"
    guarded_environment.delenv("MOCK_IDENTITY_ENABLED")
    with pytest.raises(MockIdentityGuardError):
        resolve_local_persona()


def test_given_explicit_context_when_recording_then_only_identity_enums() -> None:
    engine = GovernanceEngine(GovernanceSettings(environment="test"))
    context = GovernanceContext(
        boundary="mcp",
        actor="reporting",
        token_type="app",
        staff_role="none",
        principal_hash="f" * 64,
    )
    governance_events.clear()
    engine.evaluate(LifecyclePoint.PRE_TOOL, TOOLS[0], context=context)
    event = governance_events.snapshot()["recent_events"][0]
    assert {
        key: event[key] for key in context.identity_attributes()
    } == context.identity_attributes()
    assert "f" * 64 not in json.dumps(event)
