"""Strict contracts for the single reviewed dataset evaluator."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from ai_governance_harness.evaluation.agent_contracts import (
    AgentEvaluationError,
    digest,
)
from ai_governance_harness.evaluation.agent_managed_contracts import (
    EvaluatorPin,
    ManagedOutcome,
    ManagedResponse,
    load_cases,
    load_pin,
)
from ai_governance_harness.evaluation.agent_runner import CollectionOutcome
from ai_governance_harness.evaluation.artifacts import write_json
from ai_governance_harness.evaluation.behavior_evaluator import (
    DATA_MAPPING,
    JUDGE_PROMPT,
    NAME,
    evaluator_definition,
)

ENDPOINT = "https://example.services.ai.azure.com/api/projects/example"


def registration():
    return {
        "schema_version": "1.0.0",
        "status": "registered",
        "name": NAME,
        "version": "1",
        "id": f"azureai://accounts/example/projects/example/evaluators/{NAME}/versions/1",
        "project_endpoint": ENDPOINT,
        "instruction_version": "1.0.0",
        "prompt_digest": digest(JUDGE_PROMPT),
        "data_mapping": deepcopy(DATA_MAPPING),
        "verified": True,
        "error": None,
    }


def registry_bundle(directory):
    directory.mkdir()
    write_json(directory / "registration.json", registration())
    write_json(directory / "definition.json", evaluator_definition().as_dict())
    return directory


def test_all_reviewed_scenarios_are_preserved(tmp_path):
    cases = load_cases()
    assert len(cases) == 29
    assert len({case.category for case in cases}) == 12
    assert cases[0].id == "adv-001"
    assert "member 1001" in cases[0].prompt
    subset = tmp_path / "subset.jsonl"
    subset.write_text(cases[0].model_dump_json() + "\n")
    assert load_cases(subset) == cases[:1]
    subset.write_text(cases[0].model_dump_json() + "\n" + cases[0].model_dump_json())
    with pytest.raises(AgentEvaluationError, match="duplicate"):
        load_cases(subset)


def test_changed_scenario_is_not_silently_accepted(tmp_path):
    case = load_cases()[0].model_copy(update={"expected_behavior": "Always pass."})
    path = tmp_path / "unreviewed.jsonl"
    path.write_text(case.model_dump_json())
    with pytest.raises(AgentEvaluationError, match="unreviewed"):
        load_cases(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", "latest"),
        ("verified", False),
        ("verified", 1),
        ("prompt_digest", "0" * 64),
        ("data_mapping", {"response": "{{sample.output_text}}"}),
        ("name", "agent-response-answer-clear"),
    ],
)
def test_only_verified_behavior_pin_is_supported(field, value):
    payload = registration()
    payload[field] = value
    with pytest.raises(ValidationError):
        EvaluatorPin.model_validate(payload)


def test_saved_pin_and_definition_are_bound_to_project(tmp_path):
    bundle = registry_bundle(tmp_path / "registry")
    assert load_pin(bundle, ENDPOINT).version == "1"
    with pytest.raises(AgentEvaluationError, match="bundle_mismatch"):
        load_pin(bundle, ENDPOINT + "-different")


@pytest.mark.parametrize("score", [True, "1", 0.5, 2.0, float("nan")])
def test_invalid_binary_results_are_not_passes(score):
    with pytest.raises(ValidationError):
        ManagedResponse(
            status="completed", score=score, passed=True, reason="Meets scope."
        )


def test_reason_and_response_fail_closed():
    with pytest.raises(ValidationError):
        ManagedResponse(
            status="completed",
            score=1.0,
            passed=True,
            reason="password=secret-sentinel",
        )
    with pytest.raises(ValidationError):
        ManagedResponse(status="completed", score=1.0, passed=False, reason="Mismatch.")
    with pytest.raises(ValidationError):
        ManagedResponse(status="completed", score=1.0, passed=True)


@pytest.mark.parametrize(("score", "label"), [(1.0, "pass"), (0.0, "fail")])
def test_binary_labels_are_preserved(score, label):
    response = ManagedResponse(
        status="completed",
        score=score,
        label=label,
        passed=score == 1.0,
        reason="Reviewed behavior verdict.",
    )
    assert ManagedResponse.model_validate_json(response.model_dump_json()) == response


@pytest.mark.parametrize(
    ("status", "score", "label", "passed"),
    [
        ("completed", 1.0, "fail", True),
        ("completed", 0.0, "pass", False),
        ("completed", 1.0, "partial", True),
        ("error", None, "pass", None),
        ("not_run", None, "fail", None),
    ],
)
def test_inconsistent_or_unfinished_labels_are_rejected(status, score, label, passed):
    with pytest.raises(ValidationError):
        ManagedResponse(
            status=status,
            score=score,
            label=label,
            passed=passed,
            reason="Reviewed behavior verdict.",
            error="provider_error" if status == "error" else None,
        )


def test_response_pass_does_not_override_collection_failure():
    row = ManagedOutcome(
        case=load_cases()[0],
        collection=CollectionOutcome(case_id="adv-001", collection_status="error"),
        response=ManagedResponse(
            status="completed", score=1.0, passed=True, reason="Behavior matches."
        ),
    )
    assert row.accepted is False
