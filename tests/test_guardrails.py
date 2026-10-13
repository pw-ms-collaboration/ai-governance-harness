"""Unit tests for compliance guardrails (ASIC RG 244 and APRA CPS 234)."""

import pytest
from ai_governance_harness.guardrails import (
    SovereigntyGuardrail,
    SovereigntyViolationError,
    AdviceClassificationGuardrail,
    DisclosureAttacher,
    PersonalAdviceViolationError,
)
from ai_governance_harness.guardrails.advice_filter import tool_response_policy_data


def test_sovereignty_guardrail_approved_regions():
    """Verify that australiaeast and australiasoutheast pass sovereignty check."""
    guard = SovereigntyGuardrail()
    assert guard.validate_region("australiaeast") is True
    assert guard.validate_region("australiasoutheast") is True
    assert guard.validate_region("Australia East") is True


def test_sovereignty_guardrail_blocks_foreign_regions():
    """Verify that foreign Azure regions fail closed with SovereigntyViolationError."""
    guard = SovereigntyGuardrail()
    with pytest.raises(SovereigntyViolationError):
        guard.validate_region("eastus")

    with pytest.raises(SovereigntyViolationError):
        guard.validate_region("westeurope")


def test_sovereignty_guardrail_inspects_endpoints():
    """Verify endpoint hostname inspection for sovereignty compliance."""
    guard = SovereigntyGuardrail()
    assert guard.validate_endpoint("https://my-foundry.australiaeast.models.ai.azure.com") is True

    with pytest.raises(SovereigntyViolationError):
        guard.validate_endpoint("https://my-foundry.eastus.models.ai.azure.com")


def test_advice_classification_detects_prohibited_advice():
    """Verify that directive personal financial product advice is detected."""
    guard = AdviceClassificationGuardrail()

    prohibited_samples = [
        "Based on your profile, you should switch your balance to Growth.",
        "We recommend rolling over your superannuation into our fund.",
        "I recommend that you switch investment options.",
        "The best option for you is our Australian Shares option.",
        "You should allocate your super to High Growth.",
    ]

    for sample in prohibited_samples:
        violations = guard.scan_for_personal_advice(sample)
        assert len(violations) > 0, f"Failed to detect advice violation in: {sample}"


def test_advice_classification_allows_factual_information():
    """Verify that factual information without directive recommendations passes."""
    guard = AdviceClassificationGuardrail()

    factual_samples = [
        "Your current balance is $145,000 invested across Growth and Australian Shares.",
        "The fund offers Conservative, Balanced, Growth, and High Growth options.",
        "Members may submit an investment switch request online through the portal.",
    ]

    for sample in factual_samples:
        violations = guard.scan_for_personal_advice(sample)
        assert len(violations) == 0, f"False positive advice violation in: {sample}"


def test_advice_classification_enforces_fallback_or_exception():
    """Verify advice enforcement triggers factual fallback or raises error."""
    guard = AdviceClassificationGuardrail()
    bad_text = "You should switch your super to our Cash option immediately."

    # Test fallback mode
    safe_text, violated = guard.enforce_advice_boundaries(bad_text, allow_fallback=True)
    assert violated is True
    assert "prohibited by ASIC RG 244" in safe_text

    # Test strict exception mode
    with pytest.raises(PersonalAdviceViolationError):
        guard.enforce_advice_boundaries(bad_text, allow_fallback=False)


def test_disclosure_attacher_appends_statutory_notices():
    """Verify that General Advice Warning and In-Fund Data Scope notices are appended."""
    text = "Member Alex Morgan has a balance of $145,000."
    disclosed = DisclosureAttacher.attach_disclosures(text)

    assert "GENERAL ADVICE WARNING (ASIC RG 244)" in disclosed
    assert "IN-FUND DATA SCOPE & PROVENANCE NOTICE" in disclosed


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"balance": 145_000, "active": True}, "passed"),
        (
            {"guidance": ["Consider obtaining personal financial advice."]},
            "passed",
        ),
        (
            {"nested": [{"text": "You should switch your balance to Growth."}]},
            "personal_advice_detected",
        ),
        (
            {"You should close your account": None},
            "personal_advice_detected",
        ),
        (
            {"nested": ["You\nshould\nswitch your balance to Growth."]},
            "personal_advice_detected",
        ),
    ],
)
def test_given_structured_response_when_scanning_then_returns_only_metadata(
    payload: object,
    expected_status: str,
) -> None:
    # Act
    result = tool_response_policy_data(payload)

    # Assert
    assert result == {
        "result_type": type(payload).__name__,
        "advice_scan_status": expected_status,
    }


def test_given_unsupported_response_when_scanning_then_rejects_unscanned_data() -> None:
    # Act & Assert
    with pytest.raises(TypeError, match="JSON-compatible response"):
        tool_response_policy_data({"unscannable": object()})
