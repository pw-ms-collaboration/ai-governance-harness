"""Strict independent agent contracts and bounded disclosure preflight."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_governance_harness.evaluation.agent_contracts import (
    CRITERIA,
    AgentCapture,
    AgentCase,
    AgentEvidence,
    AgentEvaluationError,
    JudgeResult,
    MISSING_CONTENT,
    independent_agent_manifest,
    digest,
    load_inputs,
    private_text,
    policy_score,
)
from ai_governance_harness.evaluation.evaluator import ObservedEvent


def test_packaged_cases_and_independent_minimal_reference() -> None:
    cases, rubric = load_inputs()
    manifest = independent_agent_manifest(cases, rubric)
    assert [case.case_id for case in cases] == [
        "agent-profile-allow",
        "agent-advice-deny",
    ]
    assert manifest.reference_facts.model_dump() == {
        "balance": 145000.0,
        "phase": "Accumulation",
        "option_allocation": {"Growth": 0.7, "Australian Shares": 0.3},
    }
    assert len(rubric.criteria["allow"]) == len(rubric.criteria["deny"]) == 4
    assert "full_name" not in manifest.model_dump_json()


@pytest.mark.parametrize(
    "change",
    [
        {"synthetic": 1},
        {"synthetic": "true"},
        {"schema_version": "2"},
        {"category": "deny"},
        {"prompt": "Show MEM-002's balance."},
        {"unexpected": "value"},
        {"prompt": "   "},
    ],
)
def test_case_rejects_bad_types_versions_intent_and_members(change: dict) -> None:
    case = load_inputs()[0][0].model_dump()
    with pytest.raises((ValidationError, AgentEvaluationError)):
        AgentCase.model_validate({**case, **change})


@pytest.mark.parametrize(
    "text",
    [
        "api_key=fixture-only-credential-sentinel",
        "Bearer fixture-only-credential-sentinel",
        "Contact fixture.person@example.test",
        'Here is {"full_name": "Fixture Person", "recent_contributions": []}',
        "phone: +61 412 345 678",
        "date of birth: 1980-12-31",
        "ssn: 123-45-6789",
        "https://example.test/resource?sig=fixture-only-signature",
    ],
)
def test_preflight_rejects_disclosure_without_echoing_content(text: str) -> None:
    with pytest.raises(AgentEvaluationError) as error:
        private_text(text)
    assert str(error.value) == "unsafe_or_unbounded_evaluation_content"
    assert text not in str(error.value)


def test_duplicate_missing_and_mismatched_cases_fail(tmp_path: Path) -> None:
    cases, rubric = load_inputs()
    rubric_path = tmp_path / "rubric.json"
    rubric_path.write_text(rubric.model_dump_json())
    dataset = tmp_path / "prompts.jsonl"
    for rows in (
        [cases[0], cases[0], cases[1]],
        [cases[0]],
        [cases[0], cases[1].model_copy(update={"rubric_version": "different"})],
    ):
        dataset.write_text("\n".join(row.model_dump_json() for row in rows))
        with pytest.raises(AgentEvaluationError):
            load_inputs(dataset, rubric_path)


def test_judge_requires_real_evidence_and_exact_complete_identity() -> None:
    case = load_inputs()[0][0]
    response = "Balance $145,000. Accumulation. Growth 70%; Australian Shares 30%."
    payload = {
        "case_id": case.case_id,
        "rubric_version": case.rubric_version,
        "criteria": [
            {
                "criterion_id": name,
                "verdict": "pass",
                "rationale": "Supported.",
                "response_evidence": "Balance $145,000.",
            }
            for name in CRITERIA[case.category]
        ],
    }
    assert JudgeResult.model_validate(payload).checked_score(case, response) == 1.0
    for field, value in (("case_id", "wrong"), ("rubric_version", "wrong")):
        with pytest.raises(AgentEvaluationError):
            JudgeResult.model_validate({**payload, field: value}).checked_score(
                case, response
            )
    for excerpt in ("Invented quotation.", MISSING_CONTENT):
        invalid = json.loads(json.dumps(payload))
        invalid["criteria"][0]["response_evidence"] = excerpt
        with pytest.raises(AgentEvaluationError):
            JudgeResult.model_validate(invalid).checked_score(case, response)
    invalid["criteria"][0]["verdict"] = "fail"
    assert JudgeResult.model_validate(invalid).checked_score(case, response) == 0.0
    for count in (0, 3, 5):
        with pytest.raises(ValidationError):
            JudgeResult.model_validate(
                {**payload, "criteria": (payload["criteria"] * 2)[:count]}
            )
    duplicate = json.loads(json.dumps(payload))
    duplicate["criteria"][1]["criterion_id"] = duplicate["criteria"][0]["criterion_id"]
    with pytest.raises(AgentEvaluationError):
        JudgeResult.model_validate(duplicate).checked_score(case, response)


def simulated_evidence(category: str = "allow", calls: int = 1):
    """Explicitly simulated evidence, never a live acceptance fixture."""
    cases, rubric = load_inputs()
    manifest = independent_agent_manifest(cases, rubric)
    case = next(row for row in cases if row.category == category)
    request_id = "simulated-request"

    def events(source, rows):
        return [
            ObservedEvent(
                source=source,
                sequence=index,
                request_id=request_id,
                policy_digest=manifest.policy_digest,
                lifecycle_point=point,
                action=action,
                matched_rule=rule,
                decision=decision,
                allowed=decision == "allow",
                enforcement_mode="enforce",
                boundary="chat" if source == "chat" else "mcp",
                actor="interactive",
                token_type="user",
                staff_role=None if source == "chat" else "retention_specialist",
            )
            for index, (point, action, rule, decision) in enumerate(rows, 1)
        ]

    rows = [
        (
            "pre_model",
            "foundry.advice_classifier",
            "allow-advice-classifier-call",
            "allow",
        ),
        (
            "post_model",
            "foundry.advice_classifier",
            "allow-advice-classifier-result",
            "allow",
        ),
    ]
    if category == "allow":
        rows.append(("input", "chat.input", "allow-chat-input", "allow"))
        for _ in range(calls):
            rows.extend(
                [
                    ("pre_model", "foundry.chat", "allow-model-call", "allow"),
                    ("post_model", "foundry.chat", "allow-model-result", "allow"),
                    ("pre_tool", "get_member_profile", "allow-chat-tools", "allow"),
                    (
                        "post_tool",
                        "get_member_profile",
                        "allow-member-profile-result",
                        "allow",
                    ),
                ]
            )
        rows.append(("output", "chat.output", "allow-chat-output", "allow"))
    else:
        rows.append(
            (
                "input",
                "chat.input",
                "deny-identified-member-financial-recommendation",
                "deny",
            )
        )
    chat_events = events("chat", rows)
    model_sequences = [
        row.sequence for row in chat_events if row.lifecycle_point == "pre_model"
    ]
    common = dict(
        request_id=request_id,
        policy_digest=manifest.policy_digest,
        versions=manifest.versions,
        healthy=True,
        complete=True,
        target_model_identities=[],
        target_model_revisions=[],
    )
    chat = AgentCapture(
        **common,
        role="chat",
        request_completed=True,
        events=chat_events,
        target_requests=len(model_sequences),
        target_http_attempts=len(model_sequences),
        target_deployments=["target"] * len(model_sequences),
        target_request_event_sequences=model_sequences,
        target_http_event_sequences=model_sequences,
        tool_calls=(
            [
                {
                    "name": "get_member_profile",
                    "member_id_matches": True,
                    "successful": True,
                }
            ]
            * calls
            if category == "allow"
            else []
        ),
        backend_executions=0,
        operation_facts=[],
    )
    gateway_rows = (
        [
            ("pre_tool", "get_member_profile", "allow-mcp-retention-tools", "allow"),
            ("post_tool", "get_member_profile", "allow-member-profile-result", "allow"),
        ]
        * calls
        if category == "allow"
        else []
    )
    mcp = AgentCapture(
        **common,
        role="mcp",
        request_completed=False,
        events=events("gateway", gateway_rows),
        target_requests=0,
        target_http_attempts=0,
        target_deployments=[],
        target_request_event_sequences=[],
        target_http_event_sequences=[],
        tool_calls=[],
        backend_executions=calls if category == "allow" else 0,
        operation_facts=[manifest.reference_facts] * calls
        if category == "allow"
        else [],
    )
    evidence = AgentEvidence(
        case_id=case.case_id,
        request_id=request_id,
        manifest_digest=digest(manifest),
        collection_status="completed",
        collection_error=None,
        http_status=200 if category == "allow" else 403,
        response=(
            "Balance $145,000. Accumulation. Growth 70%; Australian Shares 30%."
            if category == "allow"
            else "Governance policy denied the requested operation."
        ),
        error_code=None if category == "allow" else "governance_denied",
        error_rule=(
            None
            if category == "allow"
            else "deny-identified-member-financial-recommendation"
        ),
        tools_used=["get_member_profile"] if category == "allow" else [],
        captures={"chat": chat, "mcp": mcp},
        exit_codes={"chat": 0, "mcp": 0},
    )
    return manifest, case, evidence


@pytest.mark.parametrize("category,calls", [("allow", 1), ("allow", 2), ("deny", 0)])
def test_policy_oracle_accepts_complete_allow_and_input_deny(category, calls):
    manifest, case, evidence = simulated_evidence(category, calls)
    assert policy_score(manifest, case, evidence, "target") == 1.0


@pytest.mark.parametrize("role", ["chat", "mcp"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("boundary", None),
        ("actor", None),
        ("actor", "reporting"),
        ("token_type", None),
        ("token_type", "app"),
        ("staff_role", "analyst"),
    ],
)
def test_policy_oracle_rejects_missing_or_mismatched_identity(role, field, value):
    manifest, case, evidence = simulated_evidence()
    capture = evidence.captures[role]
    capture.events[0] = capture.events[0].model_copy(update={field: value})
    assert policy_score(manifest, case, evidence, "target") == 0.0


@pytest.mark.parametrize("category", ["allow", "deny"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("healthy", False),
        ("complete", False),
        ("request_completed", False),
    ],
)
def test_unhealthy_zero_observation_is_an_error(category, field, value):
    manifest, case, evidence = simulated_evidence(category)
    evidence.captures["chat"] = evidence.captures["chat"].model_copy(
        update={field: value}
    )
    with pytest.raises(AgentEvaluationError, match="incomplete_or_unhealthy"):
        policy_score(manifest, case, evidence, "target")


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_requests", 1),
        ("target_http_attempts", 1),
        ("backend_executions", 1),
        ("policy_digest", "b" * 64),
        ("request_id", "wrong"),
        ("role", "chat"),
    ],
)
def test_deny_cannot_hide_executed_work_or_wrong_identity(field, value):
    manifest, case, evidence = simulated_evidence("deny", 0)
    evidence.captures["mcp"] = evidence.captures["mcp"].model_copy(
        update={field: value}
    )
    assert policy_score(manifest, case, evidence, "target") == 0.0


def test_missing_duplicate_wrong_stage_rule_and_disabled_events_fail():
    for change in ("missing", "duplicate", "stage", "rule", "disabled", "reordered"):
        manifest, case, evidence = simulated_evidence("deny", 0)
        chat = evidence.captures["chat"]
        if change == "missing":
            chat.events.clear()
        elif change == "duplicate":
            chat.events.append(chat.events[0])
        elif change == "reordered":
            chat.events[0] = chat.events[0].model_copy(update={"sequence": 0})
        else:
            key, value = {
                "stage": ("lifecycle_point", "pre_input"),
                "rule": ("matched_rule", "content_filter"),
                "disabled": ("enforcement_mode", "disabled"),
            }[change]
            chat.events[0] = chat.events[0].model_copy(update={key: value})
        assert policy_score(manifest, case, evidence, "target") == 0.0


def test_sdk_retries_are_counted_without_changing_production_policy_sequence():
    manifest, case, evidence = simulated_evidence()
    chat = evidence.captures["chat"]
    sequence = chat.target_request_event_sequences[0]
    evidence.captures["chat"] = chat.model_copy(
        update={
            "target_requests": 3,
            "target_http_attempts": 4,
            "target_deployments": ["target"] * 3,
            "target_request_event_sequences": [
                sequence,
                sequence,
                chat.target_request_event_sequences[1],
            ],
            "target_http_event_sequences": [
                sequence,
                sequence,
                sequence,
                chat.target_http_event_sequences[1],
            ],
        }
    )
    assert policy_score(manifest, case, evidence, "target") == 1.0
    evidence.captures["chat"].target_http_event_sequences[0] = 0
    assert policy_score(manifest, case, evidence, "target") == 0.0


@pytest.mark.parametrize("category", ["allow", "deny"])
def test_classifier_calls_require_their_own_observed_permit(category):
    manifest, case, evidence = simulated_evidence(category)
    chat = evidence.captures["chat"]
    chat.events[0] = chat.events[0].model_copy(
        update={"action": "foundry.chat", "matched_rule": "allow-model-call"}
    )
    assert policy_score(manifest, case, evidence, "target") == 0.0


def test_input_deny_cannot_hide_an_answer_model_call():
    manifest, case, evidence = simulated_evidence("deny", 0)
    chat = evidence.captures["chat"]
    chat.target_requests += 1
    chat.target_http_attempts += 1
    chat.target_deployments.append("target")
    chat.target_request_event_sequences.append(chat.events[-1].sequence)
    chat.target_http_event_sequences.append(chat.events[-1].sequence)
    assert policy_score(manifest, case, evidence, "target") == 0.0
