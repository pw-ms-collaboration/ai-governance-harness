"""Tests for the behaviour evaluation dataset and payload builders."""

import json
from pathlib import Path

import pytest

from ai_governance_harness.evals.runner import (
    DEFAULT_DATASET,
    REQUIRED_FIELDS,
    build_eval_definition,
    build_run_definition,
    load_dataset,
)

EXPECTED_CATEGORIES = {
    "personal_advice",
    "whole_of_wealth",
    "sensitive_data",
    "prohibited_action",
    "no_fabrication",
    "uncertainty",
    "banking_advice",
    "superannuation_advice",
    "customer_info",
}


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> Path:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def _row(item_id: str = "case-1") -> dict[str, str]:
    return {
        "id": item_id,
        "category": "benign_scope",
        "prompt": "Explain the term.",
        "expected_behavior": "Give a concise definition.",
    }


def test_default_dataset_covers_expected_categories() -> None:
    items = load_dataset(DEFAULT_DATASET)

    assert len(items) >= 10
    assert {item["category"] for item in items} == EXPECTED_CATEGORIES


def test_default_dataset_ids_are_unique() -> None:
    items = load_dataset(DEFAULT_DATASET)

    assert len({item["id"] for item in items}) == len(items)


def test_dataset_skips_only_blank_and_full_line_comments(tmp_path: Path) -> None:
    path = tmp_path / "commented.jsonl"
    row = _row()
    row["prompt"] = "Explain https://example.invalid and // markers."
    path.write_text(
        "\n // disabled scenario\n//"
        + json.dumps(_row("disabled"))
        + "\n"
        + json.dumps(row)
    )
    assert load_dataset(path) == [row]
    path.write_text("// no enabled scenarios\n")
    with pytest.raises(ValueError, match="no evaluation items"):
        load_dataset(path)


def test_load_dataset_rejects_missing_field(tmp_path: Path) -> None:
    row = _row()
    del row["expected_behavior"]
    path = _write_jsonl(tmp_path / "data.jsonl", [row])

    with pytest.raises(ValueError, match="expected_behavior"):
        load_dataset(path)


def test_load_dataset_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = _write_jsonl(tmp_path / "data.jsonl", [_row("dup"), _row("dup")])

    with pytest.raises(ValueError, match="duplicate id: dup"):
        load_dataset(path)


def test_load_dataset_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text("\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no evaluation items"):
        load_dataset(path)


def test_load_dataset_keeps_only_required_fields(tmp_path: Path) -> None:
    row = {**_row(), "notes": "extra"}
    path = _write_jsonl(tmp_path / "data.jsonl", [row])

    items = load_dataset(path)

    assert set(items[0]) == set(REQUIRED_FIELDS)


def test_eval_definition_uses_label_grader_with_judge_model() -> None:
    definition = build_eval_definition("eval", judge_model="gpt-5")

    criterion = definition["testing_criteria"][0]
    assert criterion["type"] == "label_model"
    assert criterion["model"] == "gpt-5"
    assert criterion["passing_labels"] == ["pass"]
    assert set(criterion["labels"]) == {"pass", "fail"}
    assert definition["data_source_config"]["type"] == "custom"


def test_run_definition_sends_every_item_to_target_model() -> None:
    items = load_dataset(DEFAULT_DATASET)

    definition = build_run_definition("run", "gpt-5", items)

    data_source = definition["data_source"]
    assert data_source["type"] == "responses"
    assert data_source["model"] == "gpt-5"
    assert len(data_source["source"]["content"]) == len(items)
    assert data_source["source"]["content"][0]["item"] == items[0]
    user_template = data_source["input_messages"]["template"][-1]
    assert user_template["content"] == "{{item.prompt}}"
