"""Execution classification and Agent Sandbox readiness controls."""

from __future__ import annotations

import warnings
from enum import StrEnum

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from agent_sandbox import SandboxProvider

from ai_governance_harness.governance.config import GovernanceSettings


class ExecutionClass(StrEnum):
    """Capability classes that determine sandbox requirements."""

    READ_ONLY_DATA = "read_only_data"
    CODE = "code"
    SHELL = "shell"
    FILESYSTEM_WRITE = "filesystem_write"
    UNRESTRICTED_NETWORK = "unrestricted_network"


class SandboxUnavailableError(RuntimeError):
    """Raised when executable capability lacks an approved sandbox."""


class SandboxGuard:
    """Require an explicit provider for executable capability classes."""

    def __init__(
        self,
        settings: GovernanceSettings,
        provider: SandboxProvider | None = None,
    ) -> None:
        self._settings = settings
        self._provider = provider

    @property
    def provider_kind(self) -> str:
        """Return the configured provider kind without provider details."""
        return self._settings.sandbox_provider

    @property
    def ready(self) -> bool:
        """Return whether the configured execution provider is available."""
        if self._settings.sandbox_provider == "none":
            return True
        return self._provider is not None

    def require_ready(self, execution_class: ExecutionClass) -> None:
        """Deny executable classes when no approved provider is active."""
        if execution_class == ExecutionClass.READ_ONLY_DATA:
            return
        if self._settings.sandbox_provider == "none" or self._provider is None:
            raise SandboxUnavailableError(
                "Executable capability requires an approved sandbox provider."
            )
