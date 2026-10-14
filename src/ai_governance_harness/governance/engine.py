"""Fail-closed adapter over Agent Governance Toolkit 4.1 policy APIs."""

from __future__ import annotations

import hashlib
import logging
import threading
import warnings
from collections.abc import Mapping
from typing import Any

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from agentmesh.governance import PolicyEngine

from ai_governance_harness.governance.config import GovernanceSettings
from ai_governance_harness.governance.context import (
    GovernanceContext,
    get_governance_context,
)
from ai_governance_harness.governance.events import (
    EventSource,
    governance_events,
)
from ai_governance_harness.governance.models import (
    GovernanceDecision,
    LifecyclePoint,
)
from ai_governance_harness.governance.telemetry import (
    record_decision_metrics,
    tracer,
)

logger = logging.getLogger(__name__)

_TOOLKIT_STAGE_BY_LIFECYCLE = {
    LifecyclePoint.STARTUP: "pre_input",
    LifecyclePoint.INPUT: "pre_input",
    LifecyclePoint.PRE_MODEL: "pre_input",
    LifecyclePoint.POST_MODEL: "post_tool",
    LifecyclePoint.PRE_TOOL: "pre_tool",
    LifecyclePoint.POST_TOOL: "post_tool",
    LifecyclePoint.OUTPUT: "pre_output",
    LifecyclePoint.SHUTDOWN: "pre_output",
}


class GovernanceDeniedError(RuntimeError):
    """Raised when policy prevents an operation from executing."""

    def __init__(
        self,
        message: str,
        *,
        action: str | None = None,
        decision: GovernanceDecision | None = None,
    ) -> None:
        super().__init__(message)
        self.action = action
        self.decision = decision


class GovernanceEngine:
    """Load one policy and normalize toolkit decisions."""

    def __init__(self, settings: GovernanceSettings) -> None:
        self.settings = settings
        self._policy_digest = "disabled"
        self._engine: PolicyEngine | None = None
        if settings.enabled:
            policy_bytes = settings.policy_path.read_bytes()
            self._policy_digest = hashlib.sha256(policy_bytes).hexdigest()
            engine = PolicyEngine(conflict_strategy="deny_overrides")
            policy = engine.load_yaml(policy_bytes.decode("utf-8"))
            engine.load_policy(policy)
            if not engine.list_policies():
                raise ValueError("Governance policy did not load.")
            self._engine = engine

    @property
    def policy_digest(self) -> str:
        """Return the active policy's content digest."""
        return self._policy_digest

    @property
    def ready(self) -> bool:
        """Return whether required governance is ready."""
        return not self.settings.enabled or self._engine is not None

    def evaluate(
        self,
        lifecycle_point: LifecyclePoint,
        action: str,
        *,
        context: GovernanceContext | None = None,
        policy_data: Mapping[str, Any] | None = None,
        source: EventSource = "system",
    ) -> GovernanceDecision:
        """Evaluate one minimum-necessary in-memory policy snapshot."""
        if not self.settings.enabled:
            decision = GovernanceDecision(
                allowed=True,
                action="allow",
                lifecycle_point=lifecycle_point,
                reason="Governance is disabled in the test environment.",
                policy_digest=self.policy_digest,
                enforcement_mode="disabled",
            )
            return self._record_decision(decision, action=action, source=source)

        if self._engine is None:
            decision = self._failure_decision(
                lifecycle_point,
                "Governance policy engine is unavailable.",
            )
            return self._record_decision(decision, action=action, source=source)

        snapshot: dict[str, Any] = {
            "action": {"type": action},
            "governance": (
                context or get_governance_context()
            ).to_policy_context(),
        }
        if policy_data:
            snapshot["data"] = dict(policy_data)

        try:
            with tracer.start_as_current_span(
                "evaluate.governance.policy"
            ) as span:
                span.set_attribute(
                    "governance.lifecycle.point",
                    lifecycle_point.value,
                )
                span.set_attribute("governance.source", source)
                toolkit_decision = self._engine.evaluate(
                    self.settings.agent_id,
                    snapshot,
                    stage=_TOOLKIT_STAGE_BY_LIFECYCLE[lifecycle_point],
                )
                span.set_attribute(
                    "governance.decision",
                    toolkit_decision.action,
                )
        except Exception:
            logger.exception(
                "Governance policy evaluation failed",
                extra={
                    "governance_point": lifecycle_point.value,
                    "governance_decision": "deny",
                    "policy_digest": self.policy_digest,
                    "enforcement_mode": "enforce",
                },
            )
            decision = self._failure_decision(
                lifecycle_point,
                "Governance policy evaluation failed.",
            )
            return self._record_decision(decision, action=action, source=source)

        decision = GovernanceDecision(
            allowed=toolkit_decision.allowed,
            action=toolkit_decision.action,
            lifecycle_point=lifecycle_point,
            policy_name=toolkit_decision.policy_name,
            matched_rule=toolkit_decision.matched_rule,
            reason=toolkit_decision.reason,
            evaluation_ms=toolkit_decision.evaluation_ms or 0.0,
            policy_digest=self.policy_digest,
            enforcement_mode="enforce",
        )
        logger.info(
            "governance.policy.decision",
            extra={
                "governance_point": lifecycle_point.value,
                "governance_decision": decision.action,
                "policy_digest": self.policy_digest,
                "enforcement_mode": "enforce",
                "decision_rule": decision.matched_rule,
                "policy_name": decision.policy_name,
                "latency_ms": round(decision.evaluation_ms, 2),
            },
        )
        return self._record_decision(decision, action=action, source=source)

    def require_allowed(
        self,
        lifecycle_point: LifecyclePoint,
        action: str,
        *,
        context: GovernanceContext | None = None,
        policy_data: Mapping[str, Any] | None = None,
        source: EventSource = "system",
    ) -> GovernanceDecision:
        """Evaluate policy and raise a sanitized error unless it allows execution."""
        decision = self.evaluate(
            lifecycle_point,
            action,
            context=context,
            policy_data=policy_data,
            source=source,
        )
        if not decision.allowed or decision.action == "require_approval":
            raise GovernanceDeniedError(
                f"Governance denied the {lifecycle_point.value} operation.",
                action=action,
                decision=decision,
            )
        return decision

    def record_external_denial(
        self,
        lifecycle_point: LifecyclePoint,
        action: str,
        *,
        policy_name: str,
        matched_rule: str,
        source: EventSource = "system",
    ) -> GovernanceDecision:
        """Record an enforced provider denial independently of local policy."""
        decision = GovernanceDecision(
            allowed=False,
            action="deny",
            lifecycle_point=lifecycle_point,
            policy_name=policy_name,
            matched_rule=matched_rule,
            policy_digest=self.policy_digest,
            enforcement_mode="enforce",
        )
        return self._record_decision(decision, action=action, source=source)

    @staticmethod
    def _record_decision(
        decision: GovernanceDecision,
        *,
        action: str,
        source: EventSource,
    ) -> GovernanceDecision:
        governance_events.record(decision, action=action, source=source)
        record_decision_metrics(decision, source=source)
        return decision

    def _failure_decision(
        self,
        lifecycle_point: LifecyclePoint,
        reason: str,
    ) -> GovernanceDecision:
        return GovernanceDecision(
            allowed=False,
            action="deny",
            lifecycle_point=lifecycle_point,
            reason=reason,
            policy_digest=self.policy_digest,
            enforcement_mode="enforce",
        )


_engine: GovernanceEngine | None = None
_engine_lock = threading.Lock()


def get_governance_engine() -> GovernanceEngine:
    """Return the process governance engine, initializing it once."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = GovernanceEngine(GovernanceSettings.from_environment())
    return _engine


def reset_governance_engine() -> None:
    """Clear the cached engine for configuration-isolated tests."""
    global _engine
    with _engine_lock:
        _engine = None
