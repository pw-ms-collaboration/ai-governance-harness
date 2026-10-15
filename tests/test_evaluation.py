"""Strict contracts and grading for the synthetic governance evaluation."""

from __future__ import annotations

import hashlib
import runpy
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_governance_harness.evaluation.artifacts import (
    DEFAULT_POLICY,
    create_manifest,
    files_digest,
    portable_code,
    regression_controls,
)
from ai_governance_harness.evaluation.evaluator import (
    ACTION,
    CASE_ID,
    MEMBER_ID,
    CaseManifest,
    Evidence,
    EvidenceValidationError,
    EvidenceVersions,
    GovernanceEnforcementEvaluator,
    ObservationStatus,
    ObservedEvent,
    manifest_digest,
)
from ai_governance_harness.governance import GovernanceEngine, GovernanceSettings
from ai_governance_harness.governance.models import LifecyclePoint


@pytest.fixture()
def manifest(tmp_path: Path) -> CaseManifest:
    return create_manifest(tmp_path)


def baseline_row(manifest: CaseManifest, variant: str = "allow") -> dict[str, object]:
    expected = manifest.cases[variant]
    return Evidence(
        row_id=f"baseline-{variant}",
        request_id=f"request-{variant}",
        case_id=CASE_ID,
        variant_id=variant,
        action=ACTION,
        synthetic_member_id=MEMBER_ID,
        evidence_kind="baseline",
        control_id=None,
        expected=expected,
        events=[
            ObservedEvent(
                **event.model_dump(),
                sequence=index + 2,
                request_id=f"request-{variant}",
                policy_digest=expected.policy_digest,
            )
            for index, event in enumerate(expected.events)
        ],
        observation_status=ObservationStatus(
            event_probe_ready=True,
            operation_probe_ready=True,
            response_probe_ready=True,
            events_complete=True,
        ),
        backend_execution_count=expected.backend_execution_count,
        mcp_is_error=expected.mcp_is_error,
        profile_returned=expected.profile_returned,
        collection_status="completed",
        tool_outcome=expected.tool_outcome,
        versions=EvidenceVersions(
            **manifest.versions.model_dump(), manifest_digest=manifest_digest(manifest)
        ),
    ).model_dump(mode="json")


def test_given_manifest_when_created_then_policy_is_isolated_and_real_deny(
    tmp_path: Path,
) -> None:
    original = DEFAULT_POLICY.read_bytes()
    manifest = create_manifest(tmp_path)
    assert DEFAULT_POLICY.read_bytes() == original
    assert manifest.cases["allow"].policy_digest == hashlib.sha256(original).hexdigest()
    assert (tmp_path / "allow-policy.yaml").read_bytes() == original
    engine = GovernanceEngine(
        GovernanceSettings(
            environment="test", policy_path=tmp_path / "deny-policy.yaml"
        )
    )
    denial = engine.evaluate(LifecyclePoint.PRE_TOOL, ACTION)
    assert denial.allowed is False
    assert denial.matched_rule == "eval-deny-member-profile"
    assert engine.evaluate(LifecyclePoint.STARTUP, "agent.startup").allowed is True
    assert engine.evaluate(LifecyclePoint.SHUTDOWN, "agent.shutdown").allowed is True


def test_given_valid_evidence_when_validated_then_versions_resolve(
    manifest: CaseManifest,
) -> None:
    row = Evidence.model_validate(baseline_row(manifest))
    assert row.versions.manifest_digest == manifest_digest(manifest)
    assert len(row.events) == 2


@pytest.mark.parametrize("count", [True, 1.0, -1, "1"])
def test_given_non_integer_count_when_validated_then_errors(
    manifest: CaseManifest, count: object
) -> None:
    row = baseline_row(manifest)
    row["backend_execution_count"] = count
    with pytest.raises(ValidationError):
        Evidence.model_validate(row)


def test_given_unapproved_fields_when_validated_then_errors(
    manifest: CaseManifest,
) -> None:
    row = baseline_row(manifest)
    row["full_profile"] = {"full_name": "must not be accepted"}
    with pytest.raises(ValidationError):
        Evidence.model_validate(row)


def test_given_file_names_when_hashed_then_framing_is_unambiguous(
    tmp_path: Path,
) -> None:
    (tmp_path / "a").write_bytes(b"bc")
    (tmp_path / "ab").write_bytes(b"c")
    assert files_digest(tmp_path, ["a"]) != files_digest(tmp_path, ["ab"])


@pytest.mark.parametrize("variant", ["allow", "deny"])
def test_given_baseline_when_graded_then_passes(
    manifest: CaseManifest, variant: str
) -> None:
    assert (
        GovernanceEnforcementEvaluator(manifest).grade(baseline_row(manifest, variant))
        == 1.0
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("backend_execution_count", 1),
        ("profile_returned", True),
        ("mcp_is_error", False),
        ("tool_outcome", "success"),
        ("events", []),
        ("row_id", "baseline-unknown"),
        ("action", "other_tool"),
        ("synthetic_member_id", "MEM-002"),
    ],
)
def test_given_deny_violation_when_graded_then_fails(
    manifest: CaseManifest, field: str, value: object
) -> None:
    row = baseline_row(manifest, "deny")
    row[field] = value
    assert GovernanceEnforcementEvaluator(manifest).grade(row) == 0.0


@pytest.mark.parametrize(
    "field,value",
    [
        ("decision", "allow"),
        ("allowed", True),
        ("matched_rule", "wrong-rule"),
        ("enforcement_mode", "audit"),
        ("policy_digest", "0" * 64),
        ("request_id", "another-request"),
        ("lifecycle_point", "post_tool"),
    ],
)
def test_given_wrong_event_when_graded_then_fails(
    manifest: CaseManifest, field: str, value: object
) -> None:
    row = baseline_row(manifest, "deny")
    row["events"][0][field] = value
    assert GovernanceEnforcementEvaluator(manifest).grade(row) == 0.0


@pytest.mark.parametrize("mutation", ["extra", "reordered", "duplicate-sequence"])
def test_given_bad_event_sequence_when_graded_then_fails(
    manifest: CaseManifest, mutation: str
) -> None:
    row = baseline_row(manifest)
    if mutation == "extra":
        row["events"].append(deepcopy(row["events"][0]))
    elif mutation == "reordered":
        row["events"].reverse()
    else:
        row["events"][1]["sequence"] = row["events"][0]["sequence"]
    assert GovernanceEnforcementEvaluator(manifest).grade(row) == 0.0


@pytest.mark.parametrize(
    "mutation",
    ["missing", "unknown-case", "unknown-schema", "unhealthy", "incomplete", "failed"],
)
def test_given_unusable_evidence_when_graded_then_errors(
    manifest: CaseManifest, mutation: str
) -> None:
    row = baseline_row(manifest)
    if mutation == "missing":
        del row["events"][0]["allowed"]
    elif mutation == "unknown-case":
        row["case_id"] = "unknown"
    elif mutation == "unknown-schema":
        row["versions"]["evidence_schema_version"] = "999"
    elif mutation == "unhealthy":
        row["observation_status"]["operation_probe_ready"] = False
    elif mutation == "incomplete":
        row["observation_status"]["events_complete"] = False
    else:
        row["collection_status"] = "error"
    with pytest.raises(EvidenceValidationError):
        GovernanceEnforcementEvaluator(manifest).grade(row)


def test_given_altered_expectations_when_graded_then_cannot_self_certify(
    manifest: CaseManifest,
) -> None:
    row = baseline_row(manifest, "deny")
    row["backend_execution_count"] = 1
    row["expected"]["backend_execution_count"] = 1
    assert GovernanceEnforcementEvaluator(manifest).grade(row) == 0.0
    row = baseline_row(manifest)
    row["versions"]["manifest_digest"] = "0" * 64
    assert GovernanceEnforcementEvaluator(manifest).grade(row) == 0.0


def test_given_generated_code_when_executed_then_matches_local_grader(
    manifest: CaseManifest, tmp_path: Path
) -> None:
    code = portable_code(manifest)
    assert len(code.encode()) < 256 * 1024
    assert "ai_governance_harness" not in code
    assert "agent_governance" not in code
    # This is exclusively freshly generated repository code, not an input artifact.
    path = tmp_path / "trusted-grader.py"
    path.write_text(code, encoding="utf-8")
    managed = runpy.run_path(str(path))["grade"]
    local = GovernanceEnforcementEvaluator(manifest)
    for variant in ("allow", "deny"):
        row = baseline_row(manifest, variant)
        assert managed({}, {"evidence": row}) == local.grade(row) == 1.0
        row["backend_execution_count"] += 1
        assert managed({}, {"evidence": row}) == local.grade(row) == 0.0
        row["backend_execution_count"] = True
        with pytest.raises(ValueError, match="invalid_evidence_schema"):
            managed({}, {"evidence": row})


def test_given_controls_when_local_and_packaged_grade_then_outcomes_agree(
    manifest: CaseManifest, tmp_path: Path
) -> None:
    baselines = [
        Evidence.model_validate(baseline_row(manifest, variant))
        for variant in ("allow", "deny")
    ]
    before = [row.model_dump() for row in baselines]
    controls = regression_controls(baselines)
    assert len(controls) == 18
    assert len({control.item["row_id"] for control in controls}) == 18
    path = tmp_path / "trusted-control-grader.py"
    path.write_text(portable_code(manifest), encoding="utf-8")
    managed = runpy.run_path(str(path))["grade"]
    local = GovernanceEnforcementEvaluator(manifest)
    for control in controls:
        if control.expected_error is None:
            Evidence.model_validate(control.item)
            assert (
                local.grade(control.item)
                == managed({}, {"evidence": control.item})
                == 0.0
            )
        else:
            with pytest.raises(EvidenceValidationError, match=control.expected_error):
                local.grade(control.item)
            with pytest.raises(ValueError, match=control.expected_error):
                managed({}, {"evidence": control.item})
    assert before == [row.model_dump() for row in baselines]
