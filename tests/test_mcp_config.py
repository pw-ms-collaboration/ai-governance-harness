"""Tests for MCP runtime configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_governance_harness.mcp_server.config import ServerSettings


def test_given_no_environment_when_loading_settings_then_uses_local_stdio_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    for key in (
        "MCP_TRANSPORT",
        "MCP_HOST",
        "MCP_PORT",
        "MCP_PATH",
        "MCP_ENVIRONMENT",
        "MCP_ALLOWED_ORIGINS",
        "MCP_HOSTED",
        "MCP_JSON_RESPONSE",
        "AZURE_AI_PROJECT_REGION",
        "AZURE_REGION",
    ):
        monkeypatch.delenv(key, raising=False)

    # Act
    settings = ServerSettings.from_environment()

    # Assert
    assert settings.transport == "stdio"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8001
    assert settings.mcp_path == "/mcp"
    assert settings.hosted is False


def test_given_hosted_mode_without_region_when_loading_then_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("MCP_HOSTED", "true")
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.delenv("AZURE_AI_PROJECT_REGION", raising=False)
    monkeypatch.delenv("AZURE_REGION", raising=False)

    # Act & Assert
    with pytest.raises(ValidationError, match="requires AZURE_AI_PROJECT_REGION"):
        ServerSettings.from_environment()


def test_given_disallowed_hosted_region_when_loading_then_rejects_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("MCP_HOSTED", "true")
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("AZURE_AI_PROJECT_REGION", "eastus")

    # Act & Assert
    with pytest.raises(ValidationError, match="Sovereignty Violation"):
        ServerSettings.from_environment()


def test_given_valid_http_environment_when_loading_then_parses_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_PORT", "8080")
    monkeypatch.setenv("MCP_PATH", "/governance/mcp/")
    monkeypatch.setenv(
        "MCP_ALLOWED_ORIGINS",
        "https://one.example, https://two.example/",
    )

    # Act
    settings = ServerSettings.from_environment()

    # Assert
    assert settings.host == "0.0.0.0"
    assert settings.port == 8080
    assert settings.mcp_path == "/governance/mcp"
    assert settings.allowed_origins == (
        "https://one.example",
        "https://two.example",
    )


@pytest.mark.parametrize("path", ["mcp", "//mcp", "/../mcp", "/mcp\x00"])
def test_given_unsafe_path_when_constructing_settings_then_rejects_path(path: str) -> None:
    # Act & Assert
    with pytest.raises(ValidationError, match="MCP path"):
        ServerSettings(mcp_path=path)
