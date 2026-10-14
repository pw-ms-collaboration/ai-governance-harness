"""Tests for schema-constrained semantic advice classification."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ai_governance_harness.guardrails.advice_classifier import (
    AdviceClassificationFailure,
    AdviceRequestClassification,
    FoundryAdviceRequestClassifier,
    classification_failure_policy_data,
)


class _Completions:
    def __init__(self, completion: object) -> None:
        self.completion = completion
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.completion


class _FailingCompletions:
    def create(self, **_kwargs):
        error = RuntimeError("provider rejected request")
        error.body = {
            "error": {
                "innererror": {
                    "code": "ResponsibleAIPolicyViolation",
                }
            }
        }
        raise error


def _client(
    content: str | None,
    *,
    finish_reason: str = "stop",
) -> tuple[object, _Completions]:
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(content=content),
            )
        ]
    )
    completions = _Completions(completion)
    return SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    ), completions


@pytest.mark.anyio
async def test_classifier_returns_closed_policy_facts() -> None:
    payload = {
        "classification_status": "classified",
        "request_intent": "financial_recommendation",
        "advice_subject": "identified_member",
        "financial_action": "invest",
        "product_scope": "external_security",
        "confidence": "high",
    }
    client, completions = _client(json.dumps(payload))
    classifier = FoundryAdviceRequestClassifier(
        model="test-model",
        max_output_tokens=400,
    )

    result = await classifier.classify(
        client,
        current_user_text="Should they invest in Microsoft stock?",
        previous_user_text="I cannot open a case for member MEM-003.",
    )

    assert isinstance(result, AdviceRequestClassification)
    assert result.to_policy_data() == payload
    call = completions.calls[0]
    assert call["store"] is False
    assert call["reasoning_effort"] == "minimal"
    assert call["verbosity"] == "low"
    assert call["max_completion_tokens"] == 400
    assert "tools" not in call
    response_format = call["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False


@pytest.mark.anyio
@pytest.mark.parametrize("content", [None, "", "{}", '{"unexpected": true}'])
async def test_classifier_rejects_invalid_responses(content: str | None) -> None:
    client, _ = _client(content)
    classifier = FoundryAdviceRequestClassifier(
        model="test-model",
        max_output_tokens=400,
    )

    with pytest.raises(AdviceClassificationFailure) as error:
        await classifier.classify(
            client,
            current_user_text="Show me MEM-001.",
            previous_user_text=None,
        )

    assert error.value.reason == "invalid_response"


@pytest.mark.anyio
async def test_classifier_reports_provider_filter_stop() -> None:
    client, _ = _client(None, finish_reason="content_filter")
    classifier = FoundryAdviceRequestClassifier(
        model="test-model",
        max_output_tokens=400,
    )

    with pytest.raises(AdviceClassificationFailure) as error:
        await classifier.classify(
            client,
            current_user_text="Show me MEM-001.",
            previous_user_text=None,
        )

    assert error.value.reason == "filtered"


@pytest.mark.anyio
async def test_classifier_maps_provider_filter_http_error() -> None:
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=_FailingCompletions())
    )
    classifier = FoundryAdviceRequestClassifier(
        model="test-model",
        max_output_tokens=400,
    )

    with pytest.raises(AdviceClassificationFailure) as error:
        await classifier.classify(
            client,
            current_user_text="Show me MEM-001.",
            previous_user_text=None,
        )

    assert error.value.reason == "filtered"


def test_failure_policy_data_is_bounded_and_fail_closed() -> None:
    assert classification_failure_policy_data("timeout") == {
        "classification_status": "unavailable",
        "request_intent": "unknown",
        "advice_subject": "unknown",
        "financial_action": "unknown",
        "product_scope": "unknown",
        "confidence": "low",
    }
