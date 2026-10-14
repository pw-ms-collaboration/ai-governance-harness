"""Tests for optional Azure export and bounded governance instruments."""

from __future__ import annotations

import json
import logging

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from ai_governance_harness.chat import __main__ as chat_main
from ai_governance_harness.governance import engine, telemetry as governance_telemetry
from ai_governance_harness.governance.config import GovernanceSettings
from ai_governance_harness.governance.models import LifecyclePoint
from ai_governance_harness.mcp_server import telemetry
from ai_governance_harness.mcp_server.config import ServerSettings


def test_given_no_connection_when_configuring_then_export_stays_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)

    def unexpected_export(**kwargs: object) -> None:
        pytest.fail("Azure export must remain disabled without a connection string.")

    monkeypatch.setattr(telemetry, "configure_azure_monitor", unexpected_export)

    telemetry.configure_azure_export(service_name="chat", environment="test")


@pytest.mark.parametrize(
    ("service_name", "manual_only"),
    [
        ("ai-governance-harness-mcp", False),
        ("ai-governance-harness-chat", True),
    ],
)
def test_given_connection_when_configuring_then_roles_and_privacy_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
    service_name: str,
    manual_only: bool,
) -> None:
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "test-connection")
    calls: list[str] = []

    def configure(
        *,
        connection_string: str,
        resource: Resource,
        logger_name: str,
        instrumentation_options: dict[str, dict[str, bool]],
        **options: object,
    ) -> None:
        assert connection_string == "test-connection"
        assert logger_name == service_name
        assert resource.attributes["service.name"] == service_name
        assert resource.attributes["cloud.region"] == "australiaeast"
        if manual_only:
            assert options["disable_logging"] is True
            assert options["enable_live_metrics"] is False
            assert instrumentation_options
            assert all(
                value == {"enabled": False}
                for value in instrumentation_options.values()
            )
        else:
            assert instrumentation_options == {}
            assert "disable_logging" not in options
        calls.append(logger_name)

    monkeypatch.setattr(telemetry, "configure_azure_monitor", configure)

    telemetry.configure_azure_export(
        service_name=service_name,
        environment="test",
        region="australiaeast",
        manual_only=manual_only,
    )

    assert calls == [service_name]


def test_given_export_failure_when_configuring_then_error_is_not_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "test-connection")

    def fail(**kwargs: object) -> None:
        raise ValueError("Invalid telemetry configuration.")

    monkeypatch.setattr(telemetry, "configure_azure_monitor", fail)

    with pytest.raises(ValueError, match="Invalid telemetry configuration"):
        telemetry.configure_azure_export(service_name="chat", environment="test")


@pytest.mark.usefixtures("mock_chat_environment")
def test_given_chat_startup_when_running_then_export_precedes_app_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "test-model")
    calls: list[str] = []

    def configure(**kwargs: object) -> None:
        assert kwargs["service_name"] == "ai-governance-harness-chat"
        assert kwargs["manual_only"] is True
        calls.append("export")

    def build(settings: object) -> object:
        calls.append("app")
        return object()

    monkeypatch.setattr(chat_main, "configure_azure_export", configure)
    monkeypatch.setattr(chat_main, "build_chat_app", build)
    monkeypatch.setattr(chat_main.uvicorn, "run", lambda *args, **kwargs: None)

    assert chat_main.main() == 0
    assert calls == ["export", "app"]


@pytest.mark.usefixtures("mcp_caller")
def test_given_sensitive_inputs_when_evaluating_then_export_is_metadata_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = InMemoryMetricReader()
    metrics_provider = MeterProvider(metric_readers=[reader])
    meter = metrics_provider.get_meter("governance-test")
    spans = InMemorySpanExporter()
    trace_provider = TracerProvider()
    trace_provider.add_span_processor(SimpleSpanProcessor(spans))
    monkeypatch.setattr(engine, "tracer", trace_provider.get_tracer("governance-test"))
    monkeypatch.setattr(
        governance_telemetry, "decision_counter",
        meter.create_counter("governance.policy.decision.count"),
    )
    monkeypatch.setattr(
        governance_telemetry, "evaluation_duration",
        meter.create_histogram("governance.policy.evaluation.duration"),
    )
    governance = engine.GovernanceEngine(GovernanceSettings(environment="test"))

    try:
        for action in ("get_member_profile", "demo.prohibited_action"):
            governance.evaluate(
                LifecyclePoint.PRE_TOOL,
                action,
                source="chat",
                policy_data={"prompt": "private@example.com", "member_id": "MEM-001"},
            )

        data = reader.get_metrics_data()
        assert data is not None
        metrics = [
            metric
            for resource in data.resource_metrics
            for scope in resource.scope_metrics
            for metric in scope.metrics
        ]
        assert {metric.name for metric in metrics} == {
            "governance.policy.decision.count",
            "governance.policy.evaluation.duration",
        }
        attributes = [
            dict(point.attributes)
            for metric in metrics
            for point in metric.data.data_points
        ]
        assert {item["governance.decision"] for item in attributes} == {"allow", "deny"}
        assert all(item["governance.source"] == "chat" for item in attributes)
        assert all(item["governance.rule.name"] for item in attributes)
        assert all(item["governance.policy.name"] for item in attributes)
        finished_spans = spans.get_finished_spans()
        assert len(finished_spans) == 2
        serialized = json.dumps(
            attributes + [dict(span.attributes) for span in finished_spans]
        )
        assert "private@example.com" not in serialized
        assert "MEM-001" not in serialized
        assert "prompt" not in serialized
    finally:
        metrics_provider.shutdown()
        trace_provider.shutdown()


def test_given_mcp_settings_when_configuring_then_existing_role_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        telemetry, "configure_azure_export", lambda **kwargs: calls.append(kwargs)
    )
    root = telemetry.logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(root, "level", root.level)

    telemetry.configure_telemetry(ServerSettings(environment="test"))

    assert calls == [{
        "service_name": "ai-governance-harness-mcp",
        "environment": "test",
        "region": None,
        "manual_only": True,
    }]


def test_given_bu_denial_when_exporting_then_spans_metrics_and_logs_have_origin(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    reader = InMemoryMetricReader()
    metrics_provider = MeterProvider(metric_readers=[reader])
    meter = metrics_provider.get_meter("provenance-test")
    spans = InMemorySpanExporter()
    trace_provider = TracerProvider()
    trace_provider.add_span_processor(SimpleSpanProcessor(spans))
    monkeypatch.setattr(engine, "tracer", trace_provider.get_tracer("provenance-test"))
    monkeypatch.setattr(governance_telemetry, "decision_counter",
                        meter.create_counter("governance.policy.decision.count"))
    monkeypatch.setattr(governance_telemetry, "evaluation_duration",
                        meter.create_histogram("governance.policy.evaluation.duration"))
    governance = engine.GovernanceEngine(GovernanceSettings(environment="test"))

    try:
        governance.evaluate(
            LifecyclePoint.INPUT, "chat.input", source="chat",
            policy_data={"classification_status": "classified",
                         "request_intent": "financial_recommendation",
                         "advice_subject": "identified_member",
                         "product_scope": "superannuation_option",
                         "confidence": "high",
                         "prompt": "private@example.com"},
        )
        governance.evaluate(LifecyclePoint.PRE_TOOL, "shell.execute", source="chat")
        governance.record_external_denial(
            LifecyclePoint.POST_MODEL, "foundry.chat",
            policy_name="azure-ai-foundry", matched_rule="deny-identified-member-financial-recommendation",
            source="chat",
        )

        finished = spans.get_finished_spans()
        assert finished[0].attributes["governance.policy.id"] == "BU-SUPER-001"
        assert finished[0].attributes["governance.policy.layer"] == "business-unit"
        assert finished[0].attributes["governance.policy.version"] == "1.0"
        assert finished[0].attributes["governance.policy.source"] == (
            "superannuation-ba-policy-source.yaml"
        )
        assert "governance.policy.id" not in finished[1].attributes
        data = reader.get_metrics_data()
        assert data is not None
        attributes = [
            dict(point.attributes)
            for resource in data.resource_metrics
            for scope in resource.scope_metrics
            for metric in scope.metrics
            for point in metric.data.data_points
        ]
        tagged = [item for item in attributes if "governance.policy.id" in item]
        assert len(tagged) == 2
        assert all(item["governance.policy.id"] == "BU-SUPER-001" for item in tagged)
        assert all("governance.policy.source" not in item
                   and "governance.policy.version" not in item for item in attributes)
        formatter = telemetry.PrivacySafeJsonFormatter("test", "revision")
        logs = [json.loads(formatter.format(record)) for record in caplog.records
                if record.message == "governance.policy.decision"]
        assert logs[0]["attributes"]["policy_id"] == "BU-SUPER-001"
        assert logs[0]["attributes"]["policy_source"] == (
            "superannuation-ba-policy-source.yaml"
        )
        assert "policy_id" not in logs[1]["attributes"]
        assert "private@example.com" not in json.dumps(logs + attributes)
    finally:
        metrics_provider.shutdown()
        trace_provider.shutdown()
