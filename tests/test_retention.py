"""Business eligibility, clearance and fail-closed retention tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_governance_harness.governance import (
    GovernanceDeniedError, GovernanceEngine, GovernanceSettings, LifecyclePoint,
)
from ai_governance_harness.governance.retention import RetentionRecord
from ai_governance_harness.mcp_server import tools
from ai_governance_harness.synthetic_data.generator import (
    build_retention_records, generate_synthetic_dataset,
)


def _record(**overrides: object) -> RetentionRecord:
    return RetentionRecord.model_validate({
        "member_id": "MEM-001",
        "account_status": "active",
        "new_signals_status": "satisfied",
        "contact_policy_status": "satisfied",
        "cooling_off_status": "satisfied",
        "cases": [],
        **overrides,
    })


@pytest.mark.parametrize(
    ("kind", "status", "clearance", "expected"),
    [
        ("routine_retention", "open", "routine_cleared", "duplicate_open"),
        ("routine_retention", "closed", "routine_cleared", "routine_permitted"),
        ("routine_retention", "closed", "review_required", "review_required"),
        ("routine_retention", "closed", "unknown", "review_required"),
        ("specialist", "open", "routine_cleared", "specialist_required"),
        ("specialist", "closed", "routine_cleared", "routine_permitted"),
        ("specialist", "closed", "review_required", "specialist_required"),
        ("specialist", "closed", "unknown", "specialist_required"),
    ],
)
def test_given_case_status_when_reviewing_then_requires_explicit_clearance(
    kind: str, status: str, clearance: str, expected: str,
) -> None:
    # Arrange
    record = _record(cases=[{
        "case_id": "CASE-001", "kind": kind, "status": status,
        "closure_outcome": clearance, "specialist_team": "hardship",
    }])

    # Act
    review = record.review()

    # Assert
    assert review.status == expected
    assert review.policy_data() == {"retention_handling_status": expected}


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("account_status", "closed", "account_exited"),
        ("account_status", "exit_completed", "account_exited"),
        ("account_status", "unknown", "unknown"),
        ("contact_policy_status", "restricted", "review_required"),
        ("contact_policy_status", "unknown", "unknown"),
        ("cooling_off_status", "restricted", "review_required"),
        ("cooling_off_status", "unknown", "unknown"),
        ("new_signals_status", "not_satisfied", "review_required"),
        ("new_signals_status", "unknown", "unknown"),
    ],
)
def test_given_unconfirmed_eligibility_when_reviewing_then_blocks(
    field: str, value: str, expected: str,
) -> None:
    # Act
    review = _record(**{field: value}).review()

    # Assert
    assert review.status == expected


@pytest.mark.parametrize(
    "status",
    ["routine_permitted", "duplicate_open", "specialist_required",
     "account_exited", "review_required", "unknown", None, "invalid"],
)
def test_given_retention_status_when_policy_runs_then_only_permitted_allows(
    status: str | None,
) -> None:
    # Arrange
    engine = GovernanceEngine(GovernanceSettings(environment="test"))
    data = {"retention_handling_status": status} if status else {}

    # Act
    decision = engine.evaluate(
        LifecyclePoint.PRE_TOOL, "prepare_member_outreach_case", policy_data=data,
    )

    # Assert
    assert decision.allowed is (status == "routine_permitted")


def test_given_multiple_cases_when_reviewing_then_specialist_overrides_duplicate() -> None:
    # Arrange
    record = _record(cases=[
        {"case_id": "CASE-001", "kind": "routine_retention", "status": "open"},
        {"case_id": "CASE-002", "kind": "specialist", "status": "open",
         "specialist_team": "bereavement"},
    ])

    # Act
    review = record.review()

    # Assert
    assert review.status == "specialist_required"
    assert review.specialist_team == "bereavement"
    assert "No specialist case was created" in review.staff_message()


def test_given_missing_case_file_when_gateway_checks_then_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    generate_synthetic_dataset(tmp_path)
    (tmp_path / "retention_cases.json").unlink()
    gateway = tools.SuperannuationDataGateway(tmp_path)
    monkeypatch.setattr(tools, "get_default_gateway", lambda: gateway)

    # Act & Assert
    with pytest.raises(GovernanceDeniedError):
        tools.require_member_outreach_eligible("MEM-001")
    assert gateway.get_member_profile("MEM-001")["retention_review"]["status"] == "unknown"


def test_given_invalid_case_data_when_loading_then_rejects(
    tmp_path: Path,
) -> None:
    # Arrange
    generate_synthetic_dataset(tmp_path)
    (tmp_path / "retention_cases.json").write_text(
        json.dumps([{"member_id": "MEM-001", "cases": [{"status": "invalid"}]}]),
        encoding="utf-8",
    )

    # Act & Assert
    with pytest.raises(ValidationError):
        tools.SuperannuationDataGateway(tmp_path)


def test_given_missing_case_inventory_when_validating_then_rejects() -> None:
    # Act & Assert
    with pytest.raises(ValidationError):
        RetentionRecord.model_validate({
            "member_id": "MEM-001",
            "account_status": "active",
            "new_signals_status": "satisfied",
            "contact_policy_status": "satisfied",
            "cooling_off_status": "satisfied",
        })


def test_given_missing_member_eligibility_when_checking_then_denies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    gateway = tools.SuperannuationDataGateway()
    gateway._retention_records.pop("MEM-001")
    monkeypatch.setattr(tools, "get_default_gateway", lambda: gateway)

    # Act & Assert
    with pytest.raises(GovernanceDeniedError):
        tools.require_member_outreach_eligible("MEM-001")


def test_given_packaged_fixture_when_regenerating_then_preserves_case_personas() -> None:
    # Arrange
    records = json.loads((tools.DATA_DIR / "retention_cases.json").read_text(encoding="utf-8"))

    # Assert
    assert [
        RetentionRecord.model_validate(item).model_dump(mode="json") for item in records
    ] == build_retention_records()
