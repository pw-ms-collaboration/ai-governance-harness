"""Tests for bounded Azure history, sanitized failures, caching, and routes."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from uuid import UUID

import pytest
from starlette.testclient import TestClient

from ai_governance_harness.chat import insights
from ai_governance_harness.chat.app import build_chat_app
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.identity.constants import INTERACTIVE_ID

pytestmark = pytest.mark.usefixtures("mock_chat_environment")


def _settings(**overrides):
    return ChatSettings(**{
        "model_deployment": "test",
        "sidecar_url": "http://127.0.0.1:8002",
        "interactive_agent_id": INTERACTIVE_ID,
        **overrides,
    })

APP_ID = UUID("ae56da30-d77c-4183-9c7c-f1bc7e29cf16")


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
def azure_response(monkeypatch: pytest.MonkeyPatch):
    """Supply a deterministic credential and transport with no network calls."""
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    class Credential:
        def __init__(self, **kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def get_token(self, scope: str):
            assert scope == "https://api.applicationinsights.io/.default"

            class Token:
                token = "secret-token-not-for-browser"

            return Token()

    monkeypatch.setattr(insights, "AzureCliCredential", Credential)

    def install(document: object):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def read(self, limit: int) -> bytes:
                return json.dumps(document).encode()[:limit]

        def open_response(request, **kwargs):
            assert request.full_url == f"https://api.applicationinsights.io/v1/apps/{APP_ID}/query"
            assert kwargs["timeout"] == 15
            return Response()

        monkeypatch.setattr(insights, "urlopen", open_response)

    return install


def document(rows: list[list[object]], columns: list[str]) -> dict[str, object]:
    return {"tables": [{"columns": [{"name": name} for name in columns], "rows": rows}]}


def test_given_known_metadata_when_reading_then_payloads_and_tokens_are_absent(
    azure_response,
) -> None:
    azure_response(document([
        ["span", insights.ROLES[0], "evaluate.governance.policy", "deny", 0.12],
    ], ["kind", "service", "name", "outcome", "duration_ms"]))

    rows = insights.read_history(APP_ID, 1)

    assert len(rows) == 1
    assert rows[0].duration_ms == 0.12
    assert "secret-token" not in rows[0].model_dump_json()


@pytest.mark.parametrize("length", [16, 32])
def test_given_azure_parent_id_when_parsing_then_accepts_bounded_hex(length: int) -> None:
    row = insights.HistoryRow(
        kind="span", service=insights.ROLES[0],
        name="evaluate.governance.policy", parent_id="a" * length,
    )

    assert row.parent_id == "a" * length


def test_given_app_id_environment_when_loading_then_parses_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "test")
    monkeypatch.setenv("APPLICATIONINSIGHTS_APP_ID", str(APP_ID))

    assert ChatSettings.from_environment().application_insights_app_id == APP_ID
    monkeypatch.setenv("APPLICATIONINSIGHTS_APP_ID", "not-a-uuid")
    with pytest.raises(ValueError):
        ChatSettings.from_environment()


@pytest.mark.parametrize("unsafe", [
    document([["log", insights.ROLES[0], "private@example.com"]],
             ["kind", "service", "name"]),
    document([["span", insights.ROLES[0], "evaluate.governance.policy", "private@example.com"]],
             ["kind", "service", "name", "operation_id"]),
    document([], ["kind", "message"]),
    document([], ["kind", "kind"]),
    document([["span"]], ["kind", "name"]),
    {"tables": [], "error": {"message": "private@example.com"}},
    {"tables": [], "partialError": {"message": "private@example.com"}},
    document([["log", insights.ROLES[0], "mcp.startup"]] * (insights.MAX_ROWS + 1),
             ["kind", "service", "name"]),
])
def test_given_unsafe_azure_result_when_reading_then_rejects_without_leaking(
    azure_response, unsafe: object,
) -> None:
    azure_response(unsafe)

    with pytest.raises(insights.InsightsUnavailableError) as error:
        insights.read_history(APP_ID, 1)

    assert "private@example.com" not in str(error.value)


@pytest.mark.parametrize("error", [
    HTTPError("https://private.example", 403, "secret", {}, None),
    HTTPError("https://private.example", 429, "secret", {}, None),
    URLError("secret"),
    TimeoutError("secret"),
])
def test_given_transport_failure_when_reading_then_error_is_sanitized(
    monkeypatch: pytest.MonkeyPatch, azure_response, error: Exception,
) -> None:
    azure_response(document([], ["kind", "service", "name"]))

    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(insights, "urlopen", fail)

    with pytest.raises(insights.InsightsUnavailableError) as caught:
        insights.read_history(APP_ID, 1)

    assert "secret" not in str(caught.value)


def test_given_oversized_payload_when_reading_then_rejects(
    azure_response,
) -> None:
    azure_response("x" * 1_048_577)

    with pytest.raises(insights.InsightsUnavailableError, match="safe response limit"):
        insights.read_history(APP_ID, 1)


@pytest.mark.anyio
async def test_given_repeated_window_when_loading_then_cache_is_bounded_and_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    clock = [0.0]
    monkeypatch.setattr(insights.time, "monotonic", lambda: clock[0])

    def read(app_id: UUID, hours: int) -> list[insights.HistoryRow]:
        calls.append(hours)
        return []

    monkeypatch.setattr(insights, "read_history", read)
    history = insights.InsightsHistory(APP_ID)

    assert (await history.snapshot(1))["cached"] is False
    assert (await history.snapshot(1))["cached"] is True
    await history.snapshot(4)
    await history.snapshot(24)
    clock[0] = 61
    assert (await history.snapshot(1))["cached"] is False
    assert calls == [1, 4, 24, 1]
    assert len(history._cache) == 3
    with pytest.raises(ValueError):
        await history.snapshot(48)


@pytest.mark.anyio
async def test_given_failed_query_when_retrying_then_failure_is_not_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def read(app_id: UUID, hours: int) -> list[insights.HistoryRow]:
        calls.append(hours)
        raise insights.InsightsUnavailableError("Azure unavailable.")

    monkeypatch.setattr(insights, "read_history", read)
    history = insights.InsightsHistory(APP_ID)
    for _ in range(2):
        with pytest.raises(insights.InsightsUnavailableError):
            await history.snapshot(1)
    assert calls == [1, 1]


def test_given_unconfigured_history_when_requested_then_visible_error() -> None:
    client = TestClient(build_chat_app(_settings()))

    response = client.get("/api/observability/history")

    assert response.status_code == 503
    assert "APPLICATIONINSIGHTS_APP_ID" in response.json()["error"]


@pytest.mark.parametrize("hours", ["0", "100", "text", "1h; traces", "-1"])
def test_given_invalid_window_when_requested_then_rejects(hours: str) -> None:
    client = TestClient(build_chat_app(_settings()))

    response = client.get("/api/observability/history", params={"hours": hours})

    assert response.status_code == 400


def test_given_nonlocal_binding_when_requested_then_rejects() -> None:
    with pytest.raises(ValueError, match="loopback"):
        _settings(host="0.0.0.0")


def test_given_valid_history_when_requested_then_returns_no_store_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def snapshot(self, hours: int) -> dict[str, object]:
        return {"hours": hours, "rows": [], "cached": False}

    monkeypatch.setattr(insights.InsightsHistory, "snapshot", snapshot)
    client = TestClient(build_chat_app(_settings()))

    response = client.get("/api/observability/history?hours=4")

    assert response.status_code == 200
    assert response.json()["hours"] == 4
    assert response.headers["cache-control"] == "no-store"


def test_given_ui_when_loaded_then_has_history_controls_and_static_script() -> None:
    client = TestClient(build_chat_app(_settings()))

    page = client.get("/")
    script = client.get("/static/insights.js")

    assert 'id="insights-range"' in page.text
    assert 'id="refresh-insights"' in page.text
    assert script.status_code == 200
    assert "textContent" in script.text
    assert "innerHTML" not in script.text
    assert 'id="insights-kpis"' in page.text
    assert 'id="insights-trend-values"' in page.text
    assert 'id="insights-policy-feed"' in page.text


@pytest.mark.parametrize(("hours", "bucket"), [(1, "5m"), (4, "15m"), (24, "1h")])
def test_given_history_window_when_querying_then_time_buckets_are_bounded(
    hours: int, bucket: str,
) -> None:
    query = insights.history_query(hours)

    assert f"bin(timestamp, {bucket})" in query
    assert "timestamp=bucket" in query
    assert 'decision in ("allow", "deny", "require_approval")' in query


def test_given_decision_bucket_when_reading_then_timestamp_and_count_are_preserved(
    azure_response,
) -> None:
    azure_response(document([
        ["metric", insights.ROLES[0], "governance.policy.decision.count",
         "deny", 3, "2026-10-14T02:00:00Z"],
    ], ["kind", "service", "name", "outcome", "total", "timestamp"]))

    row = insights.read_history(APP_ID, 1)[0]

    assert row.total == 3
    assert row.outcome == "deny"
    assert row.timestamp is not None


@pytest.mark.parametrize("name", [
    "chat gpt-4o-mini", "execute_tool get_member_profile",
    "invoke_agent superannuation-governance-assistant", "tools/call get_member_profile",
    "MCP send tools/call get_member_profile",
])
def test_given_genai_span_name_when_reading_then_accepts_bounded_semconv_name(
    azure_response, name: str,
) -> None:
    azure_response(document([["span", insights.ROLES[0], name, "success"]],
                            ["kind", "service", "name", "outcome"]))

    assert insights.read_history(APP_ID, 1)[0].name == name


@pytest.mark.parametrize("name", [
    "chat private@example.com", "chat ", "execute_tool a b", "MCP send initialize",
])
def test_given_unbounded_genai_span_name_when_reading_then_rejects(
    azure_response, name: str,
) -> None:
    azure_response(document([["span", insights.ROLES[0], name]], ["kind", "service", "name"]))

    with pytest.raises(insights.InsightsUnavailableError):
        insights.read_history(APP_ID, 1)


def test_given_token_metrics_when_querying_then_genai_usage_is_included() -> None:
    query = insights.history_query(1)

    assert "gen_ai.client.inference.usage.input_tokens" in query
    assert "gen_ai.client.inference.usage.output_tokens" in query
    assert insights.GENAI_SPAN_PATTERN in query


def test_given_rule_metrics_when_querying_then_rules_are_bounded_and_aggregated() -> None:
    query = insights.history_query(24)

    assert 'customDimensions["governance.rule.name"]' in query
    assert "top 40 by total desc" in query
    assert "union metrics, rules, usage, spans, logs" in query


def test_given_rule_row_when_reading_then_accepts_bounded_rule_name(azure_response) -> None:
    azure_response(document([
        ["rule", insights.ROLES[1], "deny-personal-advice-request", "ai-governance-harness-default",
         "input", "deny", 4, "2026-10-14T02:00:00Z"],
    ], ["kind", "service", "name", "policy", "stage", "outcome", "total", "timestamp"]))

    row = insights.read_history(APP_ID, 1)[0]

    assert (row.name, row.stage, row.outcome, row.total) == (
        "deny-personal-advice-request", "input", "deny", 4,
    )


@pytest.mark.parametrize("name", ["private@example.com", "a b", "x" * 65])
def test_given_unbounded_rule_name_when_reading_then_rejects(azure_response, name: str) -> None:
    azure_response(document([["rule", insights.ROLES[0], name, "deny"]],
                            ["kind", "service", "name", "outcome"]))

    with pytest.raises(insights.InsightsUnavailableError):
        insights.read_history(APP_ID, 1)


def test_given_policy_span_when_querying_then_rule_and_stage_are_bounded() -> None:
    query = insights.history_query(1)

    assert 'customDimensions["governance.lifecycle.point"]' in query
    assert "service=cloud_RoleName, name, timestamp, rule, stage," in query


def test_given_policy_span_with_rule_when_reading_then_rule_is_preserved(azure_response) -> None:
    azure_response(document([
        ["span", insights.ROLES[0], "evaluate.governance.policy", "deny",
         "deny-out-of-scope-request", "output"],
    ], ["kind", "service", "name", "outcome", "rule", "stage"]))

    row = insights.read_history(APP_ID, 1)[0]

    assert (row.rule, row.stage) == ("deny-out-of-scope-request", "output")


def test_given_token_usage_when_querying_then_buckets_by_model_and_reads_span_usage() -> None:
    query = insights.history_query(24)

    assert "let usage = customMetrics" in query
    assert 'customDimensions["gen_ai.response.model"]' in query
    assert 'customDimensions["gen_ai.usage.reasoning.output_tokens"]' in query
    assert "union metrics, rules, usage, spans, logs" in query


def test_given_usage_and_span_tokens_when_reading_then_preserves_token_fields(
    azure_response,
) -> None:
    azure_response(document([
        ["usage", insights.ROLES[0], "gen_ai.client.inference.usage.output_tokens",
         "gpt-5-2025-08-07", 900, 3, None, None, None, None],
        ["span", insights.ROLES[0], "chat gpt-5", "gpt-5-2025-08-07", None, None,
         750, 477, 0, 320],
    ], ["kind", "service", "name", "model", "total", "samples",
        "input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens"]))

    usage, span = insights.read_history(APP_ID, 24)

    assert (usage.kind, usage.model, usage.total, usage.samples) == (
        "usage", "gpt-5-2025-08-07", 900, 3,
    )
    assert (span.input_tokens, span.output_tokens, span.reasoning_tokens) == (750, 477, 320)


@pytest.mark.parametrize("row", [
    ["usage", insights.ROLES[0], "governance.policy.decision.count", "gpt-5"],
    ["usage", insights.ROLES[0], "gen_ai.client.inference.usage.input_tokens", "gpt 5; drop"],
])
def test_given_unexpected_usage_row_when_reading_then_rejects(azure_response, row) -> None:
    azure_response(document([row], ["kind", "service", "name", "model"]))

    with pytest.raises(insights.InsightsUnavailableError):
        insights.read_history(APP_ID, 24)


def test_given_history_when_requested_then_includes_configured_token_pricing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def snapshot(self, hours: int) -> dict[str, object]:
        return {"hours": hours, "rows": [], "cached": False}

    monkeypatch.setattr(insights.InsightsHistory, "snapshot", snapshot)
    settings = _settings(model_deployment="gpt-5", token_price_output_per_million=8.0)
    client = TestClient(build_chat_app(settings))

    pricing = client.get("/api/observability/history?hours=1").json()["pricing"]

    assert pricing == {
        "currency": "USD",
        "input_per_million": 1.25,
        "cached_input_per_million": 0.125,
        "output_per_million": 8.0,
        "model": "gpt-5",
    }


def test_given_ui_when_loaded_then_has_tokenomics_panel() -> None:
    client = TestClient(build_chat_app(_settings()))

    page = client.get("/").text
    script = client.get("/static/insights.js").text

    for element_id in ("token-kpis", "token-trend", "token-split", "token-runs", "token-pricing-note"):
        assert f'id="{element_id}"' in page
    assert "renderTokenomics" in script
