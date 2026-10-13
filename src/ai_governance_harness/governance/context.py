"""Request-scoped, privacy-minimized governance identity context."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Literal

from pydantic import BaseModel, ConfigDict, Field


class GovernanceContext(BaseModel):
    """Bounded context supplied to governance decisions."""

    model_config = ConfigDict(frozen=True)

    workload_id: str = Field(default="ai-governance-harness", max_length=128)
    environment: str = Field(default="local", max_length=32)
    correlation_id: str | None = Field(default=None, max_length=128)
    principal_hash: str | None = Field(default=None, min_length=64, max_length=64)
    authentication_outcome: Literal[
        "local", "authenticated", "unauthenticated", "rejected"
    ] = "local"

    def to_policy_context(self) -> dict[str, str]:
        """Return only bounded, non-PII fields for policy evaluation."""
        values = {
            "workload_id": self.workload_id,
            "environment": self.environment,
            "authentication_outcome": self.authentication_outcome,
        }
        if self.correlation_id:
            values["correlation_id"] = self.correlation_id
        if self.principal_hash:
            values["principal_hash"] = self.principal_hash
        return values


_context: ContextVar[GovernanceContext] = ContextVar(
    "governance_context",
    default=GovernanceContext(),
)


def get_governance_context() -> GovernanceContext:
    """Return the current request governance context."""
    return _context.get()


def set_governance_context(
    context: GovernanceContext,
) -> Token[GovernanceContext]:
    """Replace the current request governance context."""
    return _context.set(context)


def reset_governance_context(token: Token[GovernanceContext]) -> None:
    """Restore the context that preceded a bounded request."""
    _context.reset(token)


@contextmanager
def governance_context(context: GovernanceContext) -> Iterator[None]:
    """Set governance context for one bounded operation."""
    token = _context.set(context)
    try:
        yield
    finally:
        _context.reset(token)
