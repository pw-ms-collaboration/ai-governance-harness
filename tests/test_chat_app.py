"""Tests for the browser chat API and static UI."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from starlette.testclient import TestClient

from ai_governance_harness.chat.app import STATIC_DIR, build_chat_app
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.chat.service import ChatRequest, ChatResponse
from ai_governance_harness.chat.service import ChatServiceError


class _FakeChatService:
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def complete(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(message="Grounded response", tools_used=["get_member_profile"])

    async def governance_snapshot(self) -> dict[str, object]:
        return {
            "schema": "ai-governance-observability/v1",
            "status": "partial",
            "services": [
                {"name": "chat", "status": "ready"},
                {"name": "mcp", "status": "unavailable"},
            ],
        }


class _FailingChatService(_FakeChatService):
    def __init__(self, error: ChatServiceError) -> None:
        super().__init__()
        self._error = error

    async def complete(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        raise self._error


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
        "policy_notice": None,
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


def test_given_governance_denial_when_posting_then_returns_policy_error() -> None:
    # Arrange
    service = _FailingChatService(
        ChatServiceError(
            "Governance policy denied the requested operation.",
            code="governance_denied",
            status_code=403,
            details={
                "lifecycle_point": "post_tool",
                "matched_rule": "deny-personal-advice-tool-response",
            },
        )
    )
    client = TestClient(build_chat_app(_settings(), service))

    # Act
    response = client.post(
        "/api/chat",
        headers={"X-Correlation-ID": "policy-test"},
        json={"messages": [{"role": "user", "content": "Recommend an investment"}]},
    )

    # Assert
    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "governance_denied",
            "message": "Governance policy denied the requested operation.",
            "correlation_id": "policy-test",
            "details": {
                "lifecycle_point": "post_tool",
                "matched_rule": "deny-personal-advice-tool-response",
            },
        }
    }


def test_given_foundry_filter_when_posting_then_returns_stop_details() -> None:
    # Arrange
    service = _FailingChatService(
        ChatServiceError(
            "Azure AI Foundry blocked the model response under a configured "
            "content filter.",
            code="model_content_filtered",
            status_code=422,
            details={
                "finish_reason": "content_filter",
                "content_filter_category": (
                    "personally_identifiable_information"
                ),
                "content_filter_severity": "medium",
            },
        )
    )
    client = TestClient(build_chat_app(_settings(), service))

    # Act
    response = client.post(
        "/api/chat",
        headers={"X-Correlation-ID": "filter-test"},
        json={"messages": [{"role": "user", "content": "Show MEM-001"}]},
    )

    # Assert
    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "model_content_filtered",
        "message": (
            "Azure AI Foundry blocked the model response under a configured "
            "content filter."
        ),
        "correlation_id": "filter-test",
        "details": {
            "finish_reason": "content_filter",
            "content_filter_category": "personally_identifiable_information",
            "content_filter_severity": "medium",
        },
    }


def test_given_personal_advice_request_when_posting_then_policy_denies_input() -> None:
    # Arrange
    service = _FailingChatService(
        ChatServiceError(
            "Governance policy denied the requested operation.",
            code="governance_denied",
            status_code=403,
            details={
                "action": "chat.input",
                "matched_rule": (
                    "deny-identified-member-financial-recommendation"
                ),
            },
        )
    )
    client = TestClient(build_chat_app(_settings(), service))

    # Act
    response = client.post(
        "/api/chat",
        headers={"X-Correlation-ID": "advice-request-test"},
        json={
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Given this customer's account balance, give me some "
                        "financial recommendations on how to grow their balance"
                    ),
                }
            ]
        },
    )

    # Assert
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "governance_denied"
    assert (
        response.json()["error"]["details"]["matched_rule"]
        == "deny-identified-member-financial-recommendation"
    )
    assert response.json()["error"]["correlation_id"] == "advice-request-test"


def test_given_upstream_failure_when_posting_then_returns_distinct_error() -> None:
    # Arrange
    service = _FailingChatService(
        ChatServiceError(
            "An upstream chat dependency could not complete the request.",
            code="upstream_failure",
        )
    )
    client = TestClient(build_chat_app(_settings(), service))

    # Act
    response = client.post(
        "/api/chat",
        headers={"X-Correlation-ID": "upstream-test"},
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    # Assert
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_failure"
    assert response.json()["error"]["correlation_id"] == "upstream-test"


def test_given_ui_request_when_loading_then_includes_security_headers() -> None:
    # Arrange
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))

    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
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
    assert any(
        tag == "aside" and attrs.get("aria-labelledby") == "governance-title"
        for tag, attrs in tags
    )
    assert sum(tag == "details" for tag, _ in tags) >= 5
    assert sum(tag == "caption" for tag, _ in tags) >= 2
    assert any(
        tag == "button" and attrs.get("id") == "refresh-governance"
        for tag, attrs in tags
    )
    assert any(
        tag == "button" and attrs.get("id") == "pause-governance"
        for tag, attrs in tags
    )
    assert any(
        tag == "p" and attrs.get("id") == "circuit-health-summary"
        for tag, attrs in tags
    )
    assert any(
        tag == "ul"
        and attrs.get("id") == "circuit-statuses"
        and attrs.get("aria-label") == "Dependency health"
        for tag, attrs in tags
    )
    assert Path(STATIC_DIR / "app.js").is_file()


def test_governance_snapshot_returns_sanitized_service_view() -> None:
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))

    response = client.get("/api/governance/snapshot")

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    assert response.json()["services"][1]["status"] == "unavailable"
