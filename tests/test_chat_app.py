"""Tests for the browser chat API and static UI."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from starlette.testclient import TestClient

from ai_governance_harness.chat.app import STATIC_DIR, build_chat_app
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.chat.service import ChatRequest, ChatResponse


class _FakeChatService:
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def complete(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(message="Grounded response", tools_used=["get_member_profile"])


class _StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.tags.append((tag, dict(attrs)))


def _settings() -> ChatSettings:
    return ChatSettings(model_deployment="test-model")


def test_given_valid_chat_request_when_posting_then_returns_response() -> None:
    # Arrange
    service = _FakeChatService()
    client = TestClient(build_chat_app(_settings(), service))

    # Act
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Profile MEM-001"}]},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": "Grounded response",
        "tools_used": ["get_member_profile"],
    }
    assert service.requests[0].messages[0].content == "Profile MEM-001"


def test_given_invalid_chat_request_when_posting_then_rejects_before_service() -> None:
    # Arrange
    service = _FakeChatService()
    client = TestClient(build_chat_app(_settings(), service))

    # Act
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "assistant", "content": "Not a user turn"}]},
    )

    # Assert
    assert response.status_code == 400
    assert service.requests == []


def test_given_disallowed_origin_when_posting_then_returns_403() -> None:
    # Arrange
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))

    # Act
    response = client.post(
        "/api/chat",
        headers={"Origin": "https://attacker.example"},
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    # Assert
    assert response.status_code == 403


def test_given_ui_request_when_loading_then_includes_security_headers() -> None:
    # Arrange
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))

    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_static_ui_has_required_accessible_structure() -> None:
    # Arrange
    parser = _StructureParser()
    parser.feed((STATIC_DIR / "index.html").read_text(encoding="utf-8"))
    tags = parser.tags

    # Assert
    assert any(tag == "html" and attrs.get("lang") == "en" for tag, attrs in tags)
    assert any(tag == "main" for tag, _ in tags)
    assert any(
        tag == "label" and attrs.get("for") == "chat-input"
        for tag, attrs in tags
    )
    assert any(
        tag == "p" and attrs.get("role") == "status"
        for tag, attrs in tags
    )
    assert any(
        tag == "p" and attrs.get("role") == "alert"
        for tag, attrs in tags
    )
    assert Path(STATIC_DIR / "app.js").is_file()
