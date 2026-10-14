"""Typed runtime configuration for the MCP server."""

from __future__ import annotations

import os
from typing import Literal, Self

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ai_governance_harness.guardrails.sovereignty import (
    SovereigntyGuardrail,
    SovereigntyViolationError,
)
from ai_governance_harness.identity.config import require_loopback_url
from ai_governance_harness.mock_identity_guard import require_mock_identity_allowed

load_dotenv()

Transport = Literal["stdio", "streamable-http"]
Environment = Literal["local", "development", "staging", "production", "test"]


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Expected a boolean value, received '{value}'.")


class ServerSettings(BaseModel):
    """Validated settings for local and hosted MCP transports."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transport: Transport = "stdio"
    host: str = "127.0.0.1"
    port: int = Field(default=8001, ge=1, le=65535)
    mcp_path: str = "/mcp"
    environment: Environment = "local"
    region: str | None = None
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1",
        "http://localhost",
    )
    hosted: bool = False
    json_response: bool = False
    auth_tenant_id: str | None = None
    auth_audience: str | None = None
    auth_required_scope: str | None = None
    principal_source: Literal["easy_auth", "jwt"] | None = None
    jwt_issuer: str | None = None
    jwt_jwks_url: str | None = None
    interactive_agent_id: str | None = None
    reporting_agent_id: str | None = None
    resource_url: str | None = None
    max_request_body_size: int = Field(default=1_048_576, ge=1, le=4_194_304)
    rate_limit_capacity: int = Field(default=60, ge=1, le=10_000)
    rate_limit_refill_per_second: float = Field(default=1.0, gt=0, le=1_000)
    max_replicas: int = Field(default=3, ge=1, le=300)
    deployment_revision: str = "local"
    supported_protocol_versions: tuple[str, ...] = (
        "2025-11-25",
        "2025-06-18",
    )

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        """Reject empty host bindings."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("MCP host must not be empty.")
        return normalized

    @field_validator("mcp_path")
    @classmethod
    def validate_mcp_path(cls, value: str) -> str:
        """Require one absolute URL path without traversal."""
        normalized = value.strip()
        if not normalized.startswith("/") or normalized.startswith("//"):
            raise ValueError("MCP path must start with one '/'.")
        if ".." in normalized or "\x00" in normalized:
            raise ValueError("MCP path must not contain traversal or null bytes.")
        return normalized.rstrip("/") or "/"

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Require explicit HTTP origins without wildcard access."""
        origins = tuple(origin.strip().rstrip("/") for origin in value if origin.strip())
        if not origins:
            raise ValueError("At least one allowed origin is required.")
        if "*" in origins:
            raise ValueError("Wildcard origins are not permitted.")
        return origins

    @model_validator(mode="after")
    def validate_hosted_requirements(self) -> Self:
        """Fail closed when hosted configuration lacks sovereignty controls."""
        if not self.hosted:
            return self

        if self.transport != "streamable-http":
            raise ValueError("Hosted MCP mode requires the streamable-http transport.")
        if not self.region:
            raise ValueError("Hosted MCP mode requires AZURE_AI_PROJECT_REGION or AZURE_REGION.")
        try:
            SovereigntyGuardrail().validate_region(self.region)
        except SovereigntyViolationError as exc:
            raise ValueError(str(exc)) from exc
        if not all(
            (
                self.auth_tenant_id,
                self.auth_audience,
                self.auth_required_scope,
                self.resource_url,
            )
        ):
            raise ValueError(
                "Hosted MCP mode requires tenant, audience, scope, and resource URL settings."
            )
        return self

    @model_validator(mode="after")
    def validate_identity_source(self) -> Self:
        """Require an authenticated source for HTTP without affecting stdio."""
        if self.transport == "stdio":
            return self
        source = self.principal_source or ("easy_auth" if self.hosted else "jwt")
        object.__setattr__(self, "principal_source", source)
        if not all((
            self.auth_tenant_id, self.auth_audience, self.auth_required_scope,
            self.interactive_agent_id, self.reporting_agent_id,
        )):
            raise ValueError("HTTP MCP requires tenant, audience, scope and both agent IDs.")
        if self.interactive_agent_id == self.reporting_agent_id:
            raise ValueError("Interactive and reporting agent IDs must differ.")
        if source == "easy_auth":
            if not self.hosted:
                raise ValueError("Easy Auth requires a trusted hosted boundary.")
        else:
            if self.hosted or self.environment not in {"local", "development", "test"}:
                raise ValueError("Mock JWT trust is restricted to local environments.")
            require_mock_identity_allowed("mcp-jwt", bind_host=self.host)
            if not self.jwt_issuer or not self.jwt_jwks_url:
                raise ValueError("JWT trust requires issuer and JWKS URLs.")
            require_loopback_url(self.jwt_issuer)
            require_loopback_url(self.jwt_jwks_url)
        return self

    @classmethod
    def from_environment(cls) -> Self:
        """Load settings from environment variables."""
        origins_value = os.getenv("MCP_ALLOWED_ORIGINS")
        origins = (
            tuple(origins_value.split(","))
            if origins_value
            else cls.model_fields["allowed_origins"].default
        )
        return cls(
            transport=os.getenv("MCP_TRANSPORT", "stdio"),
            host=os.getenv("MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("MCP_PORT", "8001")),
            mcp_path=os.getenv("MCP_PATH", "/mcp"),
            environment=os.getenv("MCP_ENVIRONMENT", "local"),
            region=os.getenv("AZURE_AI_PROJECT_REGION") or os.getenv("AZURE_REGION"),
            allowed_origins=origins,
            hosted=_parse_bool(os.getenv("MCP_HOSTED"), default=False),
            json_response=_parse_bool(os.getenv("MCP_JSON_RESPONSE"), default=False),
            auth_tenant_id=os.getenv("MCP_AUTH_TENANT_ID") or os.getenv("AZURE_TENANT_ID"),
            auth_audience=os.getenv("MCP_AUTH_AUDIENCE"),
            auth_required_scope=os.getenv("MCP_AUTH_REQUIRED_SCOPE"),
            principal_source=os.getenv("MCP_PRINCIPAL_SOURCE") or None,
            jwt_issuer=os.getenv("MCP_JWT_ISSUER") or None,
            jwt_jwks_url=os.getenv("MCP_JWT_JWKS_URL") or None,
            interactive_agent_id=os.getenv("AGENT_ID_INTERACTIVE_ID") or None,
            reporting_agent_id=os.getenv("AGENT_ID_REPORTING_ID") or None,
            resource_url=os.getenv("MCP_RESOURCE_URL"),
            max_request_body_size=int(
                os.getenv("MCP_MAX_REQUEST_BODY_SIZE", "1048576")
            ),
            rate_limit_capacity=int(os.getenv("MCP_RATE_LIMIT_CAPACITY", "60")),
            rate_limit_refill_per_second=float(
                os.getenv("MCP_RATE_LIMIT_REFILL_PER_SECOND", "1.0")
            ),
            max_replicas=int(os.getenv("MCP_MAX_REPLICAS", "3")),
            deployment_revision=os.getenv("CONTAINER_APP_REVISION", "local"),
        )
