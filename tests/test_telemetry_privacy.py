"""Privacy tests proving injected markers stay out of logs, spans, and evidence."""

from __future__ import annotations

import json
import logging

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from ai_governance_harness.governance import (
    GovernanceEngine,
    GovernanceSettings,
    LifecyclePoint,
)
from ai_governance_harness.governance import engine as governance_engine
from ai_governance_harness.governance.config import DEFAULT_POLICY_PATH
from ai_governance_harness.governance.events import governance_events
from ai_governance_harness.mcp_server.telemetry import PrivacySafeJsonFormatter

SYNTHETIC_MARKER = "SYNTHETIC-MARKER-7f3a9c"


def _settings() -> GovernanceSettings:
    return GovernanceSettings(environment="test", policy_path=DEFAULT_POLICY_PATH)


@pytest.fixture(autouse=True)
def _clear_governance_events() -> None:
    governance_events.clear()


@pytest.fixture()
def span_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(
        governance_engine,
        "tracer",
        provider.get_tracer("test-governance"),
    )
    return exporter


def test_governance_evidence_omits_injected_markers(
    caplog: pytest.LogCaptureFixture,
    span_exporter: InMemorySpanExporter,
) -> None:
    # Arrange
    caplog.set_level(logging.INFO)
    engine = GovernanceEngine(_settings())
    formatter = PrivacySafeJsonFormatter("test", "revision")

    # Act
    decision = engine.evaluate(
        LifecyclePoint.PRE_TOOL,
        f"get_member_profile {SYNTHETIC_MARKER}",
        policy_data={"prompt": SYNTHETIC_MARKER},
        source="chat",
    )

    # Assert
    spans = span_exporter.get_finished_spans()
    assert spans, "expected a governance span to be recorded"
    evidence = [
        caplog.text,
        json.dumps(governance_events.snapshot()),
        decision.reason or "",
        *(str(value) for span in spans for value in (span.attributes or {}).values()),
        *(formatter.format(record) for record in caplog.records),
    ]
    assert all(SYNTHETIC_MARKER not in item for item in evidence)
