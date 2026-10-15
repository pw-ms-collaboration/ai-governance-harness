"""Offline definition contracts, not assertions about live judge accuracy."""

import json
from pathlib import Path

from ai_governance_harness.evaluation.agent_contracts import digest, private_text
from ai_governance_harness.evaluation.behavior_evaluator import (
    DATA_MAPPING,
    INPUT_SCHEMA,
    JUDGE_PROMPT,
    NAME,
    evaluator_definition,
)
from ai_governance_harness.evals.runner import load_dataset


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
