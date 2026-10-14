"""Toolkit-backed reliability boundaries for remote operations."""

from __future__ import annotations

import warnings
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import TypeVar

import anyio

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from agent_sre.cascade import CircuitBreaker, CircuitBreakerConfig

from ai_governance_harness.governance.config import GovernanceSettings

ResultT = TypeVar("ResultT")
_ignore_failure: ContextVar[bool] = ContextVar("ignore_circuit_failure", default=False)


class _SelectiveCircuitBreaker(CircuitBreaker):
    """Retain toolkit admission semantics while excluding caller-auth failures."""

    def record_failure(self) -> None:
        if not _ignore_failure.get():
            super().record_failure()


class ReliabilityGuard:
    """Apply timeout and circuit-breaker behavior to async operations."""

    def __init__(self, settings: GovernanceSettings, boundary: str) -> None:
        self._settings = settings
        self._breaker = _SelectiveCircuitBreaker(
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

    async def call(
        self, operation: Callable[[], Awaitable[ResultT]], *,
        ignore_error: Callable[[Exception], bool] | None = None,
    ) -> ResultT:
        """Run one async operation within its total timeout and circuit."""
        token = _ignore_failure.set(False)

        async def guarded() -> ResultT:
            try:
                return await operation()
            except Exception as error:
                if ignore_error is not None and ignore_error(error):
                    _ignore_failure.set(True)
                raise

        try:
            with anyio.fail_after(self._settings.operation_timeout_seconds):
                return await self._breaker.call(guarded)
        finally:
            _ignore_failure.reset(token)
