"""Tests for the browser chat API and static UI."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import pytest

from starlette.testclient import TestClient

from ai_governance_harness.chat.app import STATIC_DIR, build_chat_app
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.chat.service import (
    ChatContentFilteredError,
    ChatRequest,
    ChatResponse,
    ChatServiceError,
)
from ai_governance_harness.identity.constants import INTERACTIVE_ID
from ai_governance_harness.identity.sidecar import SidecarClient

pytestmark = pytest.mark.usefixtures("mock_chat_environment")


@pytest.fixture(autouse=True)
def authenticated_sidecar(monkeypatch, caller_identity):
    async def validate(self, headers):
        return caller_identity
    monkeypatch.setattr(SidecarClient, "validate", validate)


class _FakeChatService:
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def complete(self, request: ChatRequest, caller) -> ChatResponse:
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

    async def complete(self, request: ChatRequest, caller) -> ChatResponse:
        self.requests.append(request)
        raise self._error


class _FilteredChatService(_FakeChatService):
    async def complete(self, request: ChatRequest, caller) -> ChatResponse:
        raise ChatContentFilteredError()


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


class _AncestorParser(HTMLParser):
    """Record each element with its active ancestors."""

    _VOID = frozenset({"br", "hr", "img", "input", "link", "meta"})

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, dict[str, str | None]]] = []
        self.elements: list[
            tuple[
                str,
                dict[str, str | None],
                tuple[tuple[str, dict[str, str | None]], ...],
            ]
        ] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        self.elements.append((tag, values, tuple(self.stack)))
        if tag not in self._VOID:
            self.stack.append((tag, values))

    def handle_endtag(self, tag: str) -> None:
        if tag not in self._VOID and self.stack:
            self.stack.pop()


def _settings() -> ChatSettings:
    return ChatSettings(model_deployment="test-model", sidecar_url="http://127.0.0.1:8002", interactive_agent_id=INTERACTIVE_ID)


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


def test_content_filtered_response_returns_explicit_denial_without_an_answer() -> None:
    client = TestClient(build_chat_app(_settings(), _FilteredChatService()))

    response = client.post(
        "/api/chat",
        headers={"X-Correlation-ID": "filtered-response-test"},
        json={"messages": [{"role": "user", "content": "Profile MEM-001"}]},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "model_content_filtered",
            "message": (
                "Azure AI Foundry blocked the model response under a configured "
                "content filter."
            ),
            "correlation_id": "filtered-response-test",
        },
    }
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_other_chat_service_errors_keep_sanitized_502() -> None:
    service = _FailingChatService(
        ChatServiceError(
            "An upstream chat dependency could not complete the request.",
            code="upstream_failure",
        )
    )
    client = TestClient(build_chat_app(_settings(), service))

    response = client.post(
        "/api/chat",
        headers={"X-Correlation-ID": "service-error-test"},
        json={"messages": [{"role": "user", "content": "Profile MEM-001"}]},
    )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "upstream_failure",
            "message": "An upstream chat dependency could not complete the request.",
            "correlation_id": "service-error-test",
        },
    }


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
    assert "BU-SUPER-001" not in response.text


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
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    parser = _StructureParser()
    parser.feed(html)
    tags = parser.tags
    ancestor_parser = _AncestorParser()
    ancestor_parser.feed(html)

    # Assert
    assert any(tag == "html" and attrs.get("lang") == "en" for tag, attrs in tags)
    assert sum(tag == "title" and not attrs.get("id") for tag, attrs in tags) == 1
    assert sum(tag == "link" and attrs.get("rel") == "stylesheet" for tag, attrs in tags) == 1
    assert any(tag == "script" and attrs.get("type") == "module" for tag, attrs in tags)
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
    assert any(
        tag == "button" and attrs.get("id") == "run-evaluation"
        for tag, attrs in tags
    )
    assert any(
        tag == "p" and attrs.get("id") == "evaluation-status"
        and attrs.get("aria-live") == "polite"
        for tag, attrs in tags
    )
    assert any(
        tag == "p" and attrs.get("id") == "evaluation-error"
        and attrs.get("role") == "alert"
        for tag, attrs in tags
    )
    assert Path(STATIC_DIR / "app.js").is_file()
    assert any(tag == "label" and attrs.get("for") == "mock-persona" for tag, attrs in tags)
    assert any(attrs.get("id") == "identity-status" and attrs.get("aria-live") == "polite" for _, attrs in tags)
    options = {attrs.get("value") for tag, attrs in tags if tag == "option"}
    assert {"", "analyst", "retention_specialist", "compliance_reviewer", "administrator"} <= options
    assert any(
        tag == "section" and attrs.get("aria-label") == "Identity"
        for tag, attrs in tags
    )
    assert any(tag == "details" and attrs.get("class") == "role-comparison" for tag, attrs in tags)
    assert any(tag == "details" and attrs.get("class") == "runtime-summary" for tag, attrs in tags)
    assert any(
        attrs.get("class") == "governance-header" and "hidden" in attrs for _, attrs in tags
    )
    assert 'id="identity-mode"' not in html
    filter_ids = {attrs.get("id") for _, attrs in tags if "data-policy-filter" in attrs}
    assert filter_ids == {"rule-filter-stage"}
    prompt_buttons = [
        ancestors
        for tag, attrs, ancestors in ancestor_parser.elements
        if tag == "button" and attrs.get("class") == "example"
    ]
    assert len(prompt_buttons) == 3
    assert all(
        any(tag == "form" and attrs.get("id") == "chat-form" for tag, attrs in ancestors)
        for ancestors in prompt_buttons
    )
    assert all(
        not any(
            attrs.get("class") == "access-panel"
            for tag, attrs in ancestors
        )
        for ancestors in prompt_buttons
    )
    for expected_text in (
        "Selected-role access",
        "Preview only. Actual access requires successful sign-in and runtime policy evaluation.",
        "Try a prompt",
        "Analyst <span>OBO</span>",
        "Retention Specialist <span>OBO</span>",
        "Compliance Reviewer / Administrator <span>OBO</span>",
        "Reporting agent <span>App-only</span>",
        "Requires eligibility and explicit approval; browser approval supported",
    ):
        assert expected_text in html
    assert "step-number" not in html
    assert "Sign in (mock)" not in html
    assert any(attrs.get("id") == "send-button" and "disabled" in attrs for _, attrs in tags)


def test_given_identity_ui_when_inspecting_then_no_storage_or_cross_origin():
    script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    for forbidden in ("localStorage", "sessionStorage", "indexedDB", "document.cookie", ":8002", "http://", "https://"):
        assert forbidden not in script
    for expected_access in (
        'aggregate: ["Allow", "allowed"]',
        'member: ["Deny", "denied"]',
        'outreach: ["Eligibility + approval", "conditional"]',
    ):
        assert expected_access in script
    assert "signInButton.disabled = isBusy || Boolean(accessToken);" in script
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))
    assert client.get("/").headers["Content-Security-Policy"] == (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )


def test_given_guarded_mock_when_building_snapshot_then_mode_is_truthful(monkeypatch):
    from ai_governance_harness.governance import GovernanceEngine, GovernanceSettings
    from ai_governance_harness.governance.snapshot import build_governance_snapshot
    engine = GovernanceEngine(GovernanceSettings(environment="test"))
    assert build_governance_snapshot(engine, source="chat")["identity"]["mode"] == "mock"
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "false")
    assert build_governance_snapshot(engine, source="chat")["identity"]["mode"] == "none"


def test_governance_snapshot_returns_sanitized_service_view() -> None:
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))

    response = client.get("/api/governance/snapshot")

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    assert response.json()["services"][1]["status"] == "unavailable"


class _PanelParser(HTMLParser):
    """Record which tab panel contains each element ID."""

    _VOID = frozenset({"br", "hr", "img", "input", "link", "meta"})

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str | None] = []
        self.panel_of: dict[str, str | None] = {}
        self.tabs: list[dict[str, str | None]] = []
        self.panels: dict[str, dict[str, str | None]] = {}

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        if values.get("role") == "tab":
            self.tabs.append(values)
        if values.get("role") == "tabpanel" and values.get("id"):
            self.panels[values["id"]] = values
        current = values["id"] if values.get("role") == "tabpanel" else (
            self.stack[-1] if self.stack else None
        )
        if values.get("id"):
            self.panel_of[values["id"]] = current
        if tag not in self._VOID:
            self.stack.append(current)

    def handle_endtag(self, tag: str) -> None:
        if tag not in self._VOID and self.stack:
            self.stack.pop()


def test_given_ui_when_loaded_then_chat_observability_and_eval_are_separate_tabs() -> None:
    # Arrange
    parser = _PanelParser()

    # Act
    parser.feed((STATIC_DIR / "index.html").read_text(encoding="utf-8"))

    # Assert
    assert [tab["id"] for tab in parser.tabs] == [
        "tab-chat", "tab-observability", "tab-eval",
    ]
    assert [tab["aria-controls"] for tab in parser.tabs] == [
        "panel-chat",
        "panel-observability",
        "panel-eval",
    ]
    assert parser.tabs[0]["aria-selected"] == "true"
    assert "hidden" not in parser.panels["panel-chat"]
    assert "hidden" in parser.panels["panel-observability"]
    assert "hidden" in parser.panels["panel-eval"]
    for tab in parser.tabs:
        assert parser.panels[tab["aria-controls"]]["aria-labelledby"] == tab["id"]
        if tab["id"] != "tab-chat":
            assert tab["aria-selected"] == "false"
            assert tab["tabindex"] == "-1"
    assert parser.panel_of["chat-input"] == "panel-chat"
    assert parser.panel_of["governance-title"] == "panel-observability"
    assert parser.panel_of["insights-title"] == "panel-observability"
    for element_id in (
        "evaluation-title", "run-evaluation", "evaluation-status",
        "evaluation-error", "evaluation-results", "evaluation-summary",
        "evaluation-artifact", "evaluation-baselines", "evaluation-controls",
    ):
        assert parser.panel_of[element_id] == "panel-eval"


def test_evaluation_controls_are_not_duplicated_when_moved_to_eval_tab() -> None:
    parser = _StructureParser()
    parser.feed((STATIC_DIR / "index.html").read_text(encoding="utf-8"))
    ids = [attrs["id"] for _, attrs in parser.tags if attrs.get("id")]
    assert len(ids) == len(set(ids))


def test_given_tab_script_when_requested_then_served_as_javascript() -> None:
    # Arrange
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))

    # Act
    response = client.get("/static/tabs.js")

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert "innerHTML" not in response.text


def test_given_flow_script_when_requested_then_served_without_html_injection() -> None:
    # Arrange
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))

    # Act
    response = client.get("/static/flow.js")

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert "innerHTML" not in response.text
    assert "/api/governance/snapshot" in response.text
    assert "setOutcomeFilter" in response.text
    assert "activeOutcome" in response.text


def test_given_observability_tab_when_loaded_then_request_flow_shows_every_outcome() -> None:
    # Arrange
    client = TestClient(build_chat_app(_settings(), _FakeChatService()))

    # Act
    html = client.get("/").text

    # Assert
    observability = html.split('id="panel-observability"', 1)[1]
    assert 'aria-labelledby="flow-title"' in observability
    for outcome in ("allow", "deny", "approval", "other"):
        assert f'id="flow-count-{outcome}"' in observability
        assert f'id="flow-out-{outcome}"' in observability
        assert (
            f'id="flow-node-{outcome}" class="flow-node flow-outcome flow-{outcome}" '
            'role="button" tabindex="0"'
        ) in observability
    assert 'id="flow-ticker"' in observability
    assert 'id="flow-filter-clear"' in observability
    assert 'aria-live="polite"' in observability
    assert "/static/flow.js" in html


def test_given_approval_prompt_when_rendered_then_buttons_send_backend_replies() -> None:
    # Arrange
    from ai_governance_harness.chat.service import (
        _APPROVE_RESPONSES,
        _DECLINE_RESPONSES,
        _OUTREACH_APPROVAL_HEADING,
    )

    # Act
    script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    # Assert
    assert f'const APPROVAL_HEADING = "{_OUTREACH_APPROVAL_HEADING}";' in script
    assert '["Approve", "approve"]' in script
    assert '["Decline", "danger-secondary"]' in script
    assert "approve" in _APPROVE_RESPONSES
    assert "decline" in _DECLINE_RESPONSES
    assert "innerHTML" not in script
