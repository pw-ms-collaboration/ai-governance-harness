"""Validated settings for runtime governance controls."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "policies" / "default.yaml"


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Expected a boolean value, received '{value}'.")


class GovernanceSettings(BaseModel):
    """Fail-closed governance configuration shared by chat and MCP."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True
    environment: Literal[
        "local", "development", "staging", "production", "test"
    ] = "local"
    hosted: bool = False
    agent_id: str = "ai-governance-harness"
    policy_path: Path = DEFAULT_POLICY_PATH
    operation_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    circuit_failure_threshold: int = Field(default=3, ge=1, le=100)
    circuit_recovery_seconds: float = Field(default=30.0, gt=0, le=3600)
    sandbox_provider: Literal["none", "docker"] = "none"

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 128:
            raise ValueError("GOVERNANCE_AGENT_ID must contain 1-128 characters.")
        return normalized

    @model_validator(mode="after")
    def validate_enforcement(self) -> Self:
        if not self.enabled and (self.hosted or self.environment not in {"test"}):
            raise ValueError(
                "Governance may be disabled only in the explicit test environment."
            )
        if self.enabled and not self.policy_path.is_file():
            raise ValueError(f"Governance policy was not found: {self.policy_path}")
        return self

    @classmethod
    def from_environment(cls) -> Self:
        """Load governance settings from environment variables."""
        policy_path = os.getenv("GOVERNANCE_POLICY_PATH", "").strip()
        return cls(
            enabled=_parse_bool(os.getenv("GOVERNANCE_ENABLED"), default=True),
            environment=os.getenv(
                "GOVERNANCE_ENVIRONMENT",
                os.getenv("MCP_ENVIRONMENT", "local"),
            ),
            hosted=_parse_bool(os.getenv("MCP_HOSTED"), default=False),
            agent_id=os.getenv(
                "GOVERNANCE_AGENT_ID",
                "ai-governance-harness",
            ),
            policy_path=Path(policy_path) if policy_path else DEFAULT_POLICY_PATH,
            operation_timeout_seconds=float(
                os.getenv("GOVERNANCE_OPERATION_TIMEOUT_SECONDS", "30")
            ),
            circuit_failure_threshold=int(
                os.getenv("GOVERNANCE_CIRCUIT_FAILURE_THRESHOLD", "3")
            ),
            circuit_recovery_seconds=float(
                os.getenv("GOVERNANCE_CIRCUIT_RECOVERY_SECONDS", "30")
            ),
            sandbox_provider=os.getenv("GOVERNANCE_SANDBOX_PROVIDER", "none"),
        )
