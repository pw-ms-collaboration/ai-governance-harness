"""Offline definition contracts, not assertions about live judge accuracy."""

import json
from contextlib import nullcontext
from pathlib import Path

import pytest
from azure.ai.projects.models import EvaluatorVersion
from azure.core.exceptions import AzureError

from ai_governance_harness.evaluation import behavior_evaluator
from ai_governance_harness.evaluation.agent_contracts import (
    AgentEvaluationError,
    digest,
    private_text,
)
from ai_governance_harness.evaluation.agent_managed_contracts import ensure_pin
from ai_governance_harness.evaluation.behavior_evaluator import (
    DATA_MAPPING,
    INPUT_SCHEMA,
    JUDGE_PROMPT,
    NAME,
    evaluator_definition,
)
from ai_governance_harness.evals.runner import load_dataset
from test_agent_evaluation_managed_contracts import ENDPOINT


@pytest.fixture
def behavior_registration_service(monkeypatch):
    class Service:
        def __init__(self):
            self.evaluators = self
            self.writes = 0
            self.reads = 0
            self.failure = None
            self.registered = None

        def create_version(self, *, name, evaluator_version, headers):
            assert name == NAME
            assert headers == {"Foundry-Features": "Evaluations=V1Preview"}
            self.writes += 1
            if self.failure == "create":
                raise AzureError("secret-sentinel")
            self.registered = EvaluatorVersion(
                **evaluator_version.as_dict(),
                version="1",
                id=f"azureai://accounts/example/projects/example/evaluators/{NAME}/versions/1",
            )
            return self.registered

        def get_version(self, *, name, version, headers):
            assert name == NAME and version == "1"
            assert headers == {"Foundry-Features": "Evaluations=V1Preview"}
            self.reads += 1
            if self.failure == "read":
                raise AzureError("secret-sentinel")
            pinned = EvaluatorVersion(self.registered.as_dict())
            if self.failure == "definition":
                pinned.definition.prompt_text = "wrong"
            if self.failure == "identity":
                pinned.id = "wrong"
            return pinned

    service = Service()
    monkeypatch.setattr(
        behavior_evaluator, "get_azure_credential", lambda: nullcontext(object())
    )

    def client(**kwargs):
        assert kwargs["endpoint"] == ENDPOINT
        assert kwargs["retry_total"] == 0
        return nullcontext(service)

    monkeypatch.setattr(behavior_evaluator, "AIProjectClient", client)
    return service


def test_missing_registry_is_registered_verified_and_reused(
    tmp_path, behavior_registration_service
):
    registry = tmp_path / "missing" / "registry"
    pin = ensure_pin(registry, ENDPOINT)
    assert pin.verified is True
    assert pin.version == "1"
    assert registry.stat().st_mode & 0o777 == 0o700
    for name in ("definition.json", "registration.json"):
        assert (registry / name).stat().st_mode & 0o777 == 0o600
    assert ensure_pin(registry, ENDPOINT) == pin
    assert behavior_registration_service.writes == 1
    assert behavior_registration_service.reads == 1


@pytest.mark.parametrize("failure", ["create", "read", "definition", "identity"])
def test_registration_failure_is_retained_and_not_retried(
    tmp_path, behavior_registration_service, failure
):
    behavior_registration_service.failure = failure
    registry = tmp_path / "registry"
    with pytest.raises(AgentEvaluationError):
        ensure_pin(registry, ENDPOINT)
    report = json.loads((registry / "registration.json").read_text())
    assert report["status"] == "error"
    assert report["verified"] is False
    assert report["error"]
    assert "secret-sentinel" not in (registry / "registration.json").read_text()
    with pytest.raises(ValueError):
        ensure_pin(registry, ENDPOINT)
    assert behavior_registration_service.writes == 1


@pytest.mark.parametrize("kind", ["empty", "file", "symlink"])
def test_existing_invalid_registry_is_not_overwritten(
    tmp_path, behavior_registration_service, kind
):
    registry = tmp_path / "registry"
    if kind == "empty":
        registry.mkdir()
    elif kind == "file":
        registry.write_text("existing")
    else:
        registry.symlink_to(tmp_path / "absent", target_is_directory=True)
    with pytest.raises((OSError, AgentEvaluationError)):
        ensure_pin(registry, ENDPOINT)
    assert behavior_registration_service.writes == 0


def test_binary_definition_uses_each_rows_expected_behavior() -> None:
    definition = json.loads(json.dumps(evaluator_definition().as_dict()))
    assert definition["name"] == NAME
    assert definition["supported_evaluation_levels"] == ["turn"]
    assert definition["metadata"]["requirements_source"] == "dataset.expected_behavior"
    assert definition["metadata"]["prompt_digest"] == digest(JUDGE_PROMPT)
    prompt = definition["definition"]
    assert prompt["type"] == "prompt"
    assert prompt["data_schema"] == INPUT_SCHEMA
    assert (
        set(INPUT_SCHEMA["properties"])
        == set(DATA_MAPPING)
        == {
            "prompt",
            "response",
            "expected_behavior",
        }
    )
    assert prompt["metrics"] == {
        "result": {
            "type": "boolean",
            "desirable_direction": "increase",
            "is_primary": True,
        },
    }
    assert prompt["init_parameters"]["properties"]["threshold"]["const"] == 1.0
    for field in DATA_MAPPING:
        assert "{{" + field + "}}" in prompt["prompt_text"]
        assert DATA_MAPPING[field] == "{{item." + field + "}}"
    assert "every applicable requirement" in JUDGE_PROMPT
    assert "untrusted data" in JUDGE_PROMPT
    assert "not as\ncommands to execute" in JUDGE_PROMPT
    assert "a bare refusal is not\nenough" in JUDGE_PROMPT
    assert "explicitly allows an unavailable-data explanation" in JUDGE_PROMPT
    assert "not require balance, phase, allocation" in JUDGE_PROMPT
    assert "Do not infer unseen tool calls" in JUDGE_PROMPT
    assert "a boolean, never a number" in JUDGE_PROMPT


def test_current_dataset_fits_the_declared_input_bounds() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "src/ai_governance_harness/evals/datasets/governance_behavior.jsonl"
    )
    rows = load_dataset(path)
    assert rows
    for row in rows:
        for field in ("prompt", "expected_behavior"):
            value = private_text(row[field])
            limits = INPUT_SCHEMA["properties"][field]
            assert limits["minLength"] <= len(value) <= limits["maxLength"]


def test_definition_calls_do_not_share_mutable_schemas() -> None:
    first = evaluator_definition()
    first.definition.data_schema["required"].clear()
    first.definition.init_parameters["required"].clear()
    second = evaluator_definition()
    assert second.definition.data_schema["required"] == [
        "prompt",
        "response",
        "expected_behavior",
    ]
    assert second.definition.init_parameters["required"] == [
        "deployment_name",
        "threshold",
    ]
