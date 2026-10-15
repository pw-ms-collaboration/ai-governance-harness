"""OpenTelemetry instruments for bounded governance decisions."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from opentelemetry import metrics, trace

from ai_governance_harness.governance.events import EventSource
from ai_governance_harness.governance.models import (
    GovernanceDecision,
    LifecyclePoint,
    PolicyProvenance,
)

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


guardrail_counter = _meter.create_counter(
    "governance.guardrail.evaluation.count",
    unit="1",
    description="Count of guardrail checks by guardrail, lifecycle point and outcome.",
)

GuardrailName = Literal[
    "advice_request_classifier",
    "foundry_content_filter",
    "tool_allowlist",
    "outreach_eligibility",
    "personal_advice_scan",
    "whole_of_wealth_scope",
    "personal_advice_output_filter",
    "scope_refusal",
]
GuardrailOutcome = Literal["passed", "triggered", "error"]
_BOUNDED_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_BOUNDED_ACTION = re.compile(r"^[a-z][a-z0-9_.]{0,63}$")


def bounded_action(action: str) -> str:
    """Return a telemetry-safe action label; unexpected text is never exported."""
    return action if _BOUNDED_ACTION.fullmatch(action) else "invalid"


class GuardrailCheck:
    """Record one guardrail outcome; a check left unset is recorded as passed."""

    def __init__(self, span: trace.Span) -> None:
        self._span = span
        self.outcome: GuardrailOutcome = "passed"
        self.reason = "none"

    def passed(self) -> None:
        self.outcome, self.reason = "passed", "none"

    def triggered(self, reason: str) -> None:
        self.outcome, self.reason = "triggered", _bounded_code(reason)

    def error(self, reason: str) -> None:
        self.outcome, self.reason = "error", _bounded_code(reason)


def _bounded_code(reason: str) -> str:
    return reason if _BOUNDED_CODE.fullmatch(reason) else "other"


@contextmanager
def guardrail_span(
    name: GuardrailName,
    lifecycle_point: LifecyclePoint,
) -> Iterator[GuardrailCheck]:
    """Trace one guardrail check as ``apply_guardrail {name}`` with a bounded outcome.

    OpenTelemetry GenAI conventions define no vendor-neutral guardrail span, so the
    attributes use the harness ``governance.guardrail.*`` namespace. Only closed
    vocabularies are recorded: never user, model or tool content.
    """
    with tracer.start_as_current_span(
        f"apply_guardrail {name}",
        attributes={
            "governance.guardrail.name": name,
            "governance.lifecycle.point": lifecycle_point.value,
        },
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        check = GuardrailCheck(span)
        try:
            yield check
        except BaseException as exc:
            if check.outcome == "passed":
                check.error(_exception_code(exc))
            raise
        finally:
            if check.outcome == "error":
                span.set_status(trace.Status(trace.StatusCode.ERROR))
            span.set_attributes({
                "governance.guardrail.outcome": check.outcome,
                "governance.guardrail.reason": check.reason,
            })
            guardrail_counter.add(1, {
                "governance.guardrail.name": name,
                "governance.lifecycle.point": lifecycle_point.value,
                "governance.guardrail.outcome": check.outcome,
                "governance.guardrail.reason": check.reason,
            })


def _exception_code(exc: BaseException) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()


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
        # Rule and policy names come from bounded policy configuration, not user input.
        "governance.rule.name": decision.matched_rule or "unmatched",
        "governance.policy.name": decision.policy_name or "unknown",
    }
    if decision.provenance:
        attributes.update({
            "governance.policy.layer": decision.provenance.layer,
            "governance.policy.id": decision.provenance.policy_id,
        })
    decision_counter.add(1, attributes)
    evaluation_duration.record(decision.evaluation_ms / 1000, attributes)
