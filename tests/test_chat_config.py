"""Tests for chat service configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_governance_harness.chat.config import ChatSettings


def test_given_environment_when_loading_then_parses_service_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "model-name")
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:9000/mcp")
    monkeypatch.setenv("CHAT_PORT", "8081")
    monkeypatch.setenv("CHAT_CLASSIFIER_MAX_OUTPUT_TOKENS", "320")

    # Act
    settings = ChatSettings.from_environment()

    # Assert
    assert settings.model_deployment == "model-name"
    assert settings.mcp_url == "http://127.0.0.1:9000/mcp"
    assert settings.port == 8081
    assert settings.classifier_max_output_tokens == 320


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/mcp",
        "http://user:password@localhost:8000/mcp",
        "http://localhost:8000/mcp?token=secret",
    ],
)
def test_given_unsafe_mcp_url_when_constructing_then_rejects_url(url: str) -> None:
    # Act & Assert
    with pytest.raises(ValidationError, match="MCP_SERVER_URL"):
        ChatSettings(model_deployment="model", mcp_url=url)
