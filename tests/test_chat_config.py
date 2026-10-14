"""Tests for chat service configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.identity.constants import INTERACTIVE_ID

pytestmark = pytest.mark.usefixtures("mock_chat_environment")


def test_given_environment_when_loading_then_parses_service_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "model-name")
    monkeypatch.setenv("CHAT_USE_PROMPT_AGENT", "true")
    monkeypatch.setenv("FOUNDRY_AGENT_NAME", "member-wealth-insights-agent")
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:9000/mcp")
    monkeypatch.setenv("CHAT_PORT", "8081")
    monkeypatch.setenv("CHAT_CLASSIFIER_MAX_OUTPUT_TOKENS", "320")

    # Act
    settings = ChatSettings.from_environment()

    # Assert
    assert settings.model_deployment == "model-name"
    assert settings.agent_name == "member-wealth-insights-agent"
    assert settings.mcp_url == "http://127.0.0.1:9000/mcp"
    assert settings.port == 8081
    assert settings.classifier_max_output_tokens == 320


def test_given_prompt_agent_name_when_prompt_agent_mode_is_disabled_then_uses_local_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "model-name")
    monkeypatch.setenv("CHAT_USE_PROMPT_AGENT", "false")
    monkeypatch.setenv("FOUNDRY_AGENT_NAME", "member-wealth-insights-agent")

    # Act
    settings = ChatSettings.from_environment()

    # Assert
    assert settings.agent_name is None


def test_given_prompt_agent_mode_without_agent_name_when_loading_then_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "model-name")
    monkeypatch.setenv("CHAT_USE_PROMPT_AGENT", "true")
    monkeypatch.delenv("FOUNDRY_AGENT_NAME", raising=False)

    # Act & Assert
    with pytest.raises(ValueError, match="FOUNDRY_AGENT_NAME is required"):
        ChatSettings.from_environment()


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


@pytest.mark.parametrize(
    ("url", "audience"),
    [
        ("https://gateway.example/snapshot", None),
        (None, "api://mcp-server"),
        ("http://gateway.example/snapshot", "api://mcp-server"),
        ("https://gateway.example/snapshot?token=secret", "api://mcp-server"),
    ],
)
def test_given_unsafe_snapshot_settings_when_constructing_then_rejects_config(
    url: str | None, audience: str | None,
) -> None:
    with pytest.raises(ValidationError):
        ChatSettings(
            model_deployment="model",
            mcp_snapshot_url=url,
            mcp_snapshot_audience=audience,
        )
