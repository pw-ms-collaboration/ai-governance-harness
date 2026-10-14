"""Typed governance lifecycle and decision models."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LifecyclePoint(StrEnum):
    """Supported agent lifecycle policy intervention points."""

    STARTUP = "agent_startup"
    INPUT = "input"
    PRE_MODEL = "pre_model"
    POST_MODEL = "post_model"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    OUTPUT = "output"
    SHUTDOWN = "agent_shutdown"


class PolicyProvenance(BaseModel):
    """Repository-approved identifiers, never request content or source paths."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    layer: Literal["enterprise", "business-unit"]
    policy_id: str = Field(
        min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"
    )
    policy_version: str = Field(
        min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"
    )
    source: str = Field(
        max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.ya?ml$"
    )


class GovernanceDecision(BaseModel):
    """Normalized decision returned by the repository governance boundary."""

    model_config = ConfigDict(frozen=True)

    allowed: bool
    action: Literal[
        "allow",
        "deny",
        "warn",
        "require_approval",
        "log",
        "transform",
        "escalate",
    ]
    lifecycle_point: LifecyclePoint
    policy_name: str | None = None
    matched_rule: str | None = None
    provenance: PolicyProvenance | None = None
    reason: str | None = None
    evaluation_ms: float = 0.0
    policy_digest: str
    enforcement_mode: Literal["enforce", "disabled"]
