"""Bounded privacy-safe governance events for local observability."""

from __future__ import annotations

import re
import threading
from collections import Counter, deque
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_governance_harness.governance.models import GovernanceDecision, PolicyProvenance

MAX_RETAINED_EVENTS = 200
_SAFE_ACTION = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")

EventSource = Literal["chat", "gateway", "mcp", "demo", "system"]


class GovernanceEvent(BaseModel):
    """One sanitized decision event suitable for a local demo panel."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int = Field(ge=1)
    occurred_at: datetime
    source: EventSource
    lifecycle_point: str = Field(max_length=32)
    action: str = Field(max_length=80, pattern=_SAFE_ACTION.pattern)
    decision: str = Field(max_length=32)
    allowed: bool
    policy_name: str | None = Field(default=None, max_length=128)
    matched_rule: str | None = Field(default=None, max_length=128)
    provenance: PolicyProvenance | None = None
    policy_digest: str = Field(min_length=8, max_length=64)
    enforcement_mode: str = Field(max_length=16)
    evaluation_ms: float = Field(ge=0)


class GovernanceEventStore:
    """Keep a bounded process-local event window with aggregate counts."""

    def __init__(self, max_events: int = MAX_RETAINED_EVENTS) -> None:
        self._events: deque[GovernanceEvent] = deque(maxlen=max_events)
        self._max_events = max_events
        self._sequence = 0
        self._total_counts: Counter[str] = Counter()
        self._lock = threading.Lock()

    def record(
        self,
        decision: GovernanceDecision,
        *,
        action: str,
        source: EventSource,
    ) -> GovernanceEvent:
        """Record only bounded fields that cannot carry request content."""
        safe_action = action if _SAFE_ACTION.fullmatch(action) else "unrecognized-action"
        with self._lock:
            self._sequence += 1
            event = GovernanceEvent(
                sequence=self._sequence,
                occurred_at=datetime.now(UTC),
                source=source,
                lifecycle_point=decision.lifecycle_point.value,
                action=safe_action,
                decision=decision.action,
                allowed=decision.allowed,
                policy_name=decision.policy_name,
                matched_rule=decision.matched_rule,
                provenance=decision.provenance,
                policy_digest=decision.policy_digest,
                enforcement_mode=decision.enforcement_mode,
                evaluation_ms=round(decision.evaluation_ms, 3),
            )
            self._events.append(event)
            self._total_counts[decision.action] += 1
            return event

    def snapshot(self, *, limit: int = 50) -> dict[str, object]:
        """Return aggregate totals and the newest retained events."""
        bounded_limit = min(max(limit, 1), self._max_events)
        with self._lock:
            recent = list(self._events)[-bounded_limit:]
            counts = dict(self._total_counts)
            retained = len(self._events)
            total = sum(self._total_counts.values())
        return {
            "total": total,
            "counts": {
                "allow": counts.get("allow", 0),
                "deny": counts.get("deny", 0),
                "require_approval": counts.get("require_approval", 0),
                "warn": counts.get("warn", 0),
                "log": counts.get("log", 0),
                "transform": counts.get("transform", 0),
                "escalate": counts.get("escalate", 0),
            },
            "retained": retained,
            "retained_limit": self._max_events,
            "recent_events": [
                event.model_dump(mode="json") for event in reversed(recent)
            ],
        }

    def clear(self) -> None:
        """Reset process-local state for isolated tests."""
        with self._lock:
            self._events.clear()
            self._total_counts.clear()
            self._sequence = 0


governance_events = GovernanceEventStore()
