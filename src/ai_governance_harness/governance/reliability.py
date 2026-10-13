"""Toolkit-backed reliability boundaries for remote operations."""

from __future__ import annotations

import warnings
from collections.abc import Awaitable, Callable
from typing import TypeVar

import anyio

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from agent_sre.cascade import CircuitBreaker, CircuitBreakerConfig

from ai_governance_harness.governance.config import GovernanceSettings

ResultT = TypeVar("ResultT")


class ReliabilityGuard:
    """Apply timeout and circuit-breaker behavior to async operations."""

    def __init__(self, settings: GovernanceSettings, boundary: str) -> None:
        self._settings = settings
        self._breaker = CircuitBreaker(
            agent_id=f"{settings.agent_id}:{boundary}",
            config=CircuitBreakerConfig(
                failure_threshold=settings.circuit_failure_threshold,
                recovery_timeout_seconds=settings.circuit_recovery_seconds,
            ),
        )

    @property
    def state(self) -> str:
        """Return the current circuit state."""
        return self._breaker.get_state().value.lower()

    async def call(self, operation: Callable[[], Awaitable[ResultT]]) -> ResultT:
        """Run one async operation within its total timeout and circuit."""
        with anyio.fail_after(self._settings.operation_timeout_seconds):
            return await self._breaker.call(operation)
