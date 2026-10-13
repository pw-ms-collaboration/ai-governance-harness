"""Typed configuration for the browser chat service."""

from __future__ import annotations

import os
from typing import Self
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

load_dotenv()


class ChatSettings(BaseModel):
    """Validated settings for the local and hosted chat service."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1, le=65535)
    mcp_url: str = "http://127.0.0.1:8001/mcp"
    model_deployment: str
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    )
    max_messages: int = Field(default=20, ge=1, le=50)
    max_message_length: int = Field(default=4_000, ge=100, le=20_000)
    max_tool_rounds: int = Field(default=4, ge=1, le=8)
    max_output_tokens: int = Field(default=1_200, ge=100, le=4_000)
    max_request_body_size: int = Field(default=65_536, ge=1_024, le=1_048_576)

    @field_validator("host", "model_deployment")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        """Reject empty host and model values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty.")
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

    @classmethod
    def from_environment(cls) -> Self:
        """Load chat settings from environment variables."""
        origins_value = os.getenv("CHAT_ALLOWED_ORIGINS")
        origins = (
            tuple(origins_value.split(","))
            if origins_value
            else cls.model_fields["allowed_origins"].default
        )
        return cls(
            host=os.getenv("CHAT_HOST", "127.0.0.1"),
            port=int(os.getenv("CHAT_PORT", "8080")),
            mcp_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp"),
            model_deployment=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", ""),
            allowed_origins=origins,
            max_messages=int(os.getenv("CHAT_MAX_MESSAGES", "20")),
            max_message_length=int(os.getenv("CHAT_MAX_MESSAGE_LENGTH", "4000")),
            max_tool_rounds=int(os.getenv("CHAT_MAX_TOOL_ROUNDS", "4")),
            max_output_tokens=int(os.getenv("CHAT_MAX_OUTPUT_TOKENS", "1200")),
            max_request_body_size=int(
                os.getenv("CHAT_MAX_REQUEST_BODY_SIZE", "65536")
            ),
        )
