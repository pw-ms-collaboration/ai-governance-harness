"""Read-only cloud results, privacy, pagination, and browser API contracts."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from openai import APIConnectionError
import httpx2
from starlette.testclient import TestClient

from ai_governance_harness.chat import foundry_evaluations as foundry
from ai_governance_harness.chat.app import build_chat_app
from ai_governance_harness.chat.config import ChatSettings


def test_output_preserves_zero_score_and_distinguishes_errors() -> None:
    row = foundry.output_item(
        {
            "id": "item-1",
            "status": "fail",
            "datasource_item": {
                "id": "adv-001",
                "prompt": "Test",
                "response": "Declined",
                "expected_behavior": "Decline",
                "category": "personal_advice",
            },
            "results": [
                {
                    "name": "behavior",
                    "score": 0,
                    "passed": False,
                    "reason": "Missing referral",
                },
                {"name": "broken", "score": 1, "passed": True, "status": "skipped"},
                {"name": "missing", "passed": True},
            ],
        }
    )
    assert row["case_id"] == "adv-001"
    assert row["metrics"][0]["score"] == 0
    assert row["metrics"][0]["passed"] is False
    assert row["metrics"][0]["reason"] == "Missing referral"
    assert row["metrics"][1]["passed"] is None
    assert row["metrics"][2]["status"] == "error"


def test_sensitive_content_and_report_urls_are_withheld() -> None:
    assert "withheld" in foundry.safe_text("API_KEY=supersecret")
    assert "withheld" in foundry.safe_text("person@example.com")
    assert foundry.report_link("https://ai.azure.com/report") is not None
    assert foundry.report_link("https://ai.azure.com/report?sig=secret") is None
    assert foundry.report_link("https://attacker.example/report") is None
    assert foundry.report_link("javascript:alert(1)") is None


def test_item_errors_cannot_be_displayed_as_passing_scores() -> None:
    row = foundry.output_item(
        {
            "id": "item-1",
            "status": "error",
            "sample": {"error": {"message": "Judge request failed"}},
            "results": [{"name": "behavior", "score": 1, "passed": True}],
        }
    )
    metric = row["metrics"][0]
    assert metric["score"] is None and metric["passed"] is None
    assert metric["status"] == "error"
    assert metric["error"] == "Judge request failed"


def test_model_target_response_is_read_from_public_assistant_output() -> None:
    row = foundry.output_item(
        {
            "id": "item-1",
            "datasource_item": {"prompt": "Test"},
            "sample": {
                "output": [
                    {"role": "tool", "content": "Private tool payload"},
                    {"role": "assistant", "content": "General information only."},
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": "Speak with an adviser."},
                        ],
                    },
                ]
            },
        }
    )
    assert row["response"] == "General information only.\nSpeak with an adviser."
    assert "Private tool payload" not in row["response"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            '{"annotations":[],"text":"Public answer","type":"output_text","logprobs":[]}',
            "Public answer",
        ),
        (
            '{"answer":"Keep this JSON response"}',
            '{"answer":"Keep this JSON response"}',
        ),
        ("{Incomplete JSON", "{Incomplete JSON"),
        (
            '{"type":"output_text","text":"person@example.com"}',
            "[Content withheld by the evaluation privacy guard]",
        ),
    ],
)
def test_serialized_public_text_envelopes_are_unwrapped(content, expected) -> None:
    assert (
        foundry.sample_response({"output": [{"role": "assistant", "content": content}]})
        == expected
    )


def test_cloud_reader_lists_pages_and_closes_clients(monkeypatch) -> None:
    calls = []
    row = SimpleNamespace(model_dump=lambda **_: {"id": "eval-1", "name": "Behavior"})
    page = SimpleNamespace(data=[row], has_next_page=lambda: True)
    client = SimpleNamespace(
        evals=SimpleNamespace(
            list=lambda **kwargs: calls.append(kwargs) or page,
        )
    )
    project = SimpleNamespace(get_openai_client=lambda **_: nullcontext(client))
    monkeypatch.setenv(
        "AZURE_AI_PROJECT_ENDPOINT",
        "https://example.services.ai.azure.com/api/projects/example",
    )
    monkeypatch.setattr(foundry, "get_azure_credential", lambda: nullcontext(object()))
    monkeypatch.setattr(foundry, "AIProjectClient", lambda **_: nullcontext(project))
    payload = foundry.read_foundry(None, None, "eval-previous")
    assert payload["source"] == "foundry"
    assert payload["next"] == "eval-1"
    assert calls[0]["after"] == "eval-previous"
    assert calls[0]["limit"] == 20
    assert calls[0]["extra_headers"] == foundry.FOUNDRY_HEADERS


@pytest.mark.parametrize(
    "path",
    [
        "/api/foundry/evaluations",
        "/api/foundry/evaluations/eval-1/runs",
        "/api/foundry/evaluations/eval-1/runs/run-1?after=item-1",
    ],
)
def test_browser_routes_only_read_and_do_not_fall_back_to_local(
    monkeypatch, path
) -> None:
    calls = []
    monkeypatch.setattr(
        foundry,
        "read_foundry",
        lambda *args: (
            calls.append(args)
            or {
                "items": [],
                "next": None,
                "source": "foundry",
            }
        ),
    )
    app = build_chat_app(ChatSettings(model_deployment="test"), service=object())
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["source"] == "foundry"
        assert response.headers["Cache-Control"] == "no-store"
        assert len(calls) == 1
        assert client.post(path).status_code == 405
        assert len(calls) == 1


def test_invalid_cursor_and_host_never_call_cloud(monkeypatch) -> None:
    monkeypatch.setattr(
        foundry, "read_foundry", lambda *_: pytest.fail("Must not call cloud")
    )
    with TestClient(
        build_chat_app(ChatSettings(model_deployment="test"), service=object())
    ) as client:
        assert (
            client.get("/api/foundry/evaluations?after=invalid/token").status_code
            == 400
        )
    with TestClient(
        build_chat_app(
            ChatSettings(model_deployment="test", host="0.0.0.0"), service=object()
        )
    ) as client:
        assert client.get("/api/foundry/evaluations").status_code == 403


def test_cloud_failure_is_explicit_and_sanitized(monkeypatch) -> None:
    def broken(*_):
        raise APIConnectionError(
            message="secret-sentinel",
            request=httpx2.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(foundry, "read_foundry", broken)
    with TestClient(
        build_chat_app(ChatSettings(model_deployment="test"), service=object())
    ) as client:
        response = client.get("/api/foundry/evaluations")
        assert response.status_code == 502
        assert "secret-sentinel" not in response.text
        assert "items" not in response.json()


def test_ui_shows_run_summary_without_case_detail_controls() -> None:
    with TestClient(
        build_chat_app(ChatSettings(model_deployment="test"), service=object())
    ) as client:
        html = client.get("/").text
        assert 'id="foundry-runs"' in html
        assert '<th scope="col">Pass rate</th>' in html
        assert 'id="foundry-details"' not in html
        assert 'id="foundry-items"' not in html
        assert 'id="foundry-case-filter"' not in html
        assert 'id="foundry-run"' in html
        assert 'aria-labelledby="evaluation-title" hidden inert' in html
