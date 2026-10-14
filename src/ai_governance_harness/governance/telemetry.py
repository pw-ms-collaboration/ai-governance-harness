"""OpenTelemetry instruments for bounded governance decisions."""

from __future__ import annotations

from opentelemetry import metrics, trace

from ai_governance_harness.governance.events import EventSource
from ai_governance_harness.governance.models import GovernanceDecision, PolicyProvenance

_meter = metrics.get_meter("ai-governance-harness-governance", "0.1.0")
tracer = trace.get_tracer("ai-governance-harness-governance", "0.1.0")

decision_counter = _meter.create_counter(
    "governance.policy.decision.count",
    unit="1",
    description="Count of bounded runtime governance decisions.",
)
evaluation_duration = _meter.create_histogram(
    "governance.policy.evaluation.duration",
    unit="s",
    description="Runtime governance policy evaluation duration.",
)


def provenance_attributes(provenance: PolicyProvenance | None) -> dict[str, str]:
    """Return validated policy identifiers for spans, excluding policy content."""
    if provenance is None:
        return {}
    return {
        "governance.policy.layer": provenance.layer,
        "governance.policy.id": provenance.policy_id,
        "governance.policy.version": provenance.policy_version,
        "governance.policy.source": provenance.source,
    }


def record_decision_metrics(
    decision: GovernanceDecision,
    *,
    source: EventSource,
) -> None:
    """Record low-cardinality decision metrics without policy inputs."""
    attributes = {
        "governance.lifecycle.point": decision.lifecycle_point.value,
        "governance.decision": decision.action,
        "governance.source": source,
        "governance.enforcement.mode": decision.enforcement_mode,
    }
    if decision.provenance:
        attributes.update({
            "governance.policy.layer": decision.provenance.layer,
            "governance.policy.id": decision.provenance.policy_id,
        })
    decision_counter.add(1, attributes)
    evaluation_duration.record(decision.evaluation_ms / 1000, attributes)
