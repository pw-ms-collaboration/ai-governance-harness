"""Guarded local identity service settings."""

import os
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from ai_governance_harness.identity.constants import TENANT_ID
from ai_governance_harness.mock_identity_guard import is_loopback


def require_loopback_url(value: str) -> str:
    """Reject nonlocal endpoints, user information, query strings and fragments."""
    try:
        url = urlsplit(value)
        valid = (
            url.scheme == "http"
            and url.hostname
            and is_loopback(url.hostname)
            and not url.username
            and not url.password
            and not url.query
            and not url.fragment
            and url.port != 0
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Mock identity requires a loopback HTTP URL.")
    return value.rstrip("/")


class IdentitySettings(BaseModel):
    """Loopback issuer configuration with fixed synthetic identifiers."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    host: str = "127.0.0.1"
    port: int = Field(default=8002, ge=1, le=65535)

    @property
    def base_url(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}"

    @property
    def issuer(self) -> str:
        return f"{self.base_url}/{TENANT_ID}/v2.0"

    @property
    def jwks_url(self) -> str:
        return f"{self.base_url}/{TENANT_ID}/discovery/v2.0/keys"

    @classmethod
    def from_environment(cls) -> "IdentitySettings":
        """Load the local bind host and port."""
        return cls(
            host=os.getenv("MOCK_IDENTITY_HOST", "127.0.0.1"),
            port=int(os.getenv("MOCK_IDENTITY_PORT", "8002")),
        )
