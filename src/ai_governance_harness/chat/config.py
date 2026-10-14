"""Typed configuration for the browser chat service."""

from __future__ import annotations

import os
from typing import Self
from urllib.parse import urlparse
from uuid import UUID

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

load_dotenv()


class ChatSettings(BaseModel):
    """Validated settings for the local and hosted chat service."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1, le=65535)
    mcp_url: str = "http://127.0.0.1:8001/mcp"
    mcp_snapshot_url: str | None = None
    mcp_snapshot_audience: str | None = None
    model_deployment: str
    agent_name: str | None = None
    application_insights_app_id: UUID | None = None
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    )
    max_messages: int = Field(default=20, ge=1, le=50)
    max_message_length: int = Field(default=4_000, ge=100, le=20_000)
    max_tool_rounds: int = Field(default=4, ge=1, le=8)
    max_output_tokens: int = Field(default=1_200, ge=100, le=4_000)
    classifier_max_output_tokens: int = Field(default=400, ge=100, le=800)
    max_request_body_size: int = Field(default=65_536, ge=1_024, le=1_048_576)
    # Foundry reports token usage, not cost; these list prices drive estimates only.
    token_price_currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    token_price_input_per_million: float = Field(default=1.25, ge=0, le=1_000)
    token_price_cached_input_per_million: float = Field(default=0.125, ge=0, le=1_000)
    token_price_output_per_million: float = Field(default=10.0, ge=0, le=1_000)

    @field_validator("host", "model_deployment")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        """Reject empty host and model values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty.")
        return normalized

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, value: str | None) -> str | None:
        """Normalize an optional Foundry Prompt Agent name."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("FOUNDRY_AGENT_NAME must not be empty when configured.")
        return normalized

    @field_validator("mcp_url")
    @classmethod
    def validate_mcp_url(cls, value: str) -> str:
        """Require an HTTP MCP endpoint without credentials or query strings."""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("MCP_SERVER_URL must be an absolute HTTP(S) URL.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("MCP_SERVER_URL must not contain credentials, query, or fragment.")
        return value.rstrip("/")

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize explicit browser origins and reject wildcards."""
        origins = tuple(origin.strip().rstrip("/") for origin in value if origin.strip())
        if not origins or "*" in origins:
            raise ValueError("CHAT_ALLOWED_ORIGINS must contain explicit origins.")
        return origins

    @model_validator(mode="after")
    def validate_snapshot_access(self) -> Self:
        """Require a fixed HTTPS endpoint for authenticated snapshots."""
        if bool(self.mcp_snapshot_url) != bool(self.mcp_snapshot_audience):
            raise ValueError("MCP snapshot URL and audience must be configured together.")
        if self.mcp_snapshot_url:
            self.validate_mcp_url(self.mcp_snapshot_url)
            if urlparse(self.mcp_snapshot_url).scheme != "https":
                raise ValueError("Authenticated MCP snapshots require HTTPS.")
            if not self.mcp_snapshot_audience or not self.mcp_snapshot_audience.strip():
                raise ValueError("MCP snapshot audience must not be empty.")
        return self

    @classmethod
    def from_environment(cls) -> Self:
        """Load chat settings from environment variables."""
        use_prompt_agent = os.getenv("CHAT_USE_PROMPT_AGENT", "false").strip().lower()
        if use_prompt_agent not in {"true", "false"}:
            raise ValueError("CHAT_USE_PROMPT_AGENT must be 'true' or 'false'.")
        agent_name = os.getenv("FOUNDRY_AGENT_NAME") if use_prompt_agent == "true" else None
        if use_prompt_agent == "true" and not agent_name:
            raise ValueError("FOUNDRY_AGENT_NAME is required when Prompt Agent mode is enabled.")
        origins_value = os.getenv("CHAT_ALLOWED_ORIGINS")
        origins = (
            tuple(origins_value.split(","))
            if origins_value
            else cls.model_fields["allowed_origins"].default
        )
        app_id = os.getenv("APPLICATIONINSIGHTS_APP_ID", "").strip()
        return cls(
            host=os.getenv("CHAT_HOST", "127.0.0.1"),
            port=int(os.getenv("CHAT_PORT", "8080")),
            mcp_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp"),
            mcp_snapshot_url=os.getenv("MCP_GOVERNANCE_SNAPSHOT_URL"),
            mcp_snapshot_audience=os.getenv("MCP_GOVERNANCE_SNAPSHOT_AUDIENCE"),
            model_deployment=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", ""),
            agent_name=agent_name,
            application_insights_app_id=UUID(app_id) if app_id else None,
            allowed_origins=origins,
            max_messages=int(os.getenv("CHAT_MAX_MESSAGES", "20")),
            max_message_length=int(os.getenv("CHAT_MAX_MESSAGE_LENGTH", "4000")),
            max_tool_rounds=int(os.getenv("CHAT_MAX_TOOL_ROUNDS", "4")),
            max_output_tokens=int(os.getenv("CHAT_MAX_OUTPUT_TOKENS", "1200")),
            classifier_max_output_tokens=int(
                os.getenv("CHAT_CLASSIFIER_MAX_OUTPUT_TOKENS", "400")
            ),
            max_request_body_size=int(
                os.getenv("CHAT_MAX_REQUEST_BODY_SIZE", "65536")
            ),
            token_price_currency=os.getenv("GENAI_PRICE_CURRENCY", "USD"),
            token_price_input_per_million=float(
                os.getenv("GENAI_PRICE_INPUT_PER_1M", "1.25")
            ),
            token_price_cached_input_per_million=float(
                os.getenv("GENAI_PRICE_CACHED_INPUT_PER_1M", "0.125")
            ),
            token_price_output_per_million=float(
                os.getenv("GENAI_PRICE_OUTPUT_PER_1M", "10.0")
            ),
        )
