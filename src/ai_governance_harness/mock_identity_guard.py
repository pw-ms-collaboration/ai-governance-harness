"""Shared fail-closed startup guard for local mock identities."""

from __future__ import annotations

import ipaddress
import os
from typing import cast

from ai_governance_harness.governance import StaffRole
from ai_governance_harness.governance.config import _parse_bool


class MockIdentityGuardError(ValueError):
    """Mock identity configuration is unsafe or invalid."""


def is_loopback(host: str) -> bool:
    """Accept only a loopback IP literal or the reserved localhost name."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _boolean(name: str, *, default: bool) -> bool:
    try:
        return _parse_bool(os.getenv(name), default=default)
    except ValueError:
        raise MockIdentityGuardError(f"Invalid {name}.") from None


def require_mock_identity_allowed(
    component: str, *, bind_host: str | None = None
) -> None:
    """Reject mock operation unless explicitly enabled and strictly local."""
    if not _boolean("MOCK_IDENTITY_ENABLED", default=False):
        raise MockIdentityGuardError("MOCK_IDENTITY_ENABLED must be enabled.")
    for name in ("GOVERNANCE_ENVIRONMENT", "MCP_ENVIRONMENT"):
        if name in os.environ and os.environ[name] not in {
            "local",
            "development",
            "test",
        }:
            raise MockIdentityGuardError(f"Mock identity is forbidden by {name}.")
    if _boolean("MCP_HOSTED", default=False):
        raise MockIdentityGuardError("Mock identity is forbidden by MCP_HOSTED.")
    for name in (
        "CONTAINER_APP_NAME",
        "CONTAINER_APP_REVISION",
        "CONTAINER_APP_HOSTNAME",
        "WEBSITE_INSTANCE_ID",
        "WEBSITE_SITE_NAME",
    ):
        if name in os.environ:
            raise MockIdentityGuardError(f"Mock identity is forbidden by {name}.")
    if bind_host is not None and not is_loopback(bind_host):
        raise MockIdentityGuardError("Mock identity requires a loopback bind host.")


def resolve_local_persona() -> StaffRole | None:
    """Resolve an explicitly configured and guarded token-less staff persona."""
    value = os.getenv("MOCK_IDENTITY_LOCAL_PERSONA")
    if value is None:
        return None
    require_mock_identity_allowed("local persona")
    if value not in {
        "analyst",
        "retention_specialist",
        "compliance_reviewer",
        "administrator",
    }:
        raise MockIdentityGuardError("Invalid MOCK_IDENTITY_LOCAL_PERSONA.")
    return cast(StaffRole, value)
