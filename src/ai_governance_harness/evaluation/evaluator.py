"""Portable governance evidence contracts and deterministic grading."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

SCHEMA_VERSION = "1.0.0"
EVALUATOR_VERSION = "1.0.0"
CASE_ID = "member-profile-lookup"
ACTION = "get_member_profile"
MEMBER_ID = "MEM-001"
DENY_RULE = "eval-deny-member-profile"
SHA256 = r"^[a-f0-9]{64}$"


class EvidenceValidationError(ValueError):
    """Raised when evidence cannot support a trustworthy grading result."""


class StrictModel(BaseModel):
    """Reject implicit coercion and fields outside the minimal contract."""

    model_config = ConfigDict(extra="forbid", strict=True)


class BuildVersions(StrictModel):
    """Identify the application, fixture, and grading contract."""

    application_revision: str = Field(min_length=1, max_length=128)
    application_digest: str = Field(pattern=SHA256)
    fixture_digest: str = Field(pattern=SHA256)
    toolkit_version: str = Field(min_length=1, max_length=32)
    evidence_schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    evaluator_version: Literal["1.0.0"] = EVALUATOR_VERSION


class EvidenceVersions(BuildVersions):
    """Bind an evidence row to its independent manifest."""

    manifest_digest: str = Field(pattern=SHA256)


class ExpectedEvent(StrictModel):
    """Expected fields independent of runtime-generated sequence numbers."""

    source: str = Field(min_length=1, max_length=32)
    lifecycle_point: str = Field(min_length=1, max_length=32)
    action: str = Field(min_length=1, max_length=80)
    decision: str = Field(min_length=1, max_length=32)
    allowed: bool
    matched_rule: str | None = Field(max_length=128)
    enforcement_mode: str = Field(min_length=1, max_length=16)


class ObservedEvent(ExpectedEvent):
    """A real recorded event attributable to one isolated request."""

    sequence: int = Field(ge=1)
    request_id: str = Field(min_length=1, max_length=128)
    policy_digest: str = Field(pattern=SHA256)


class CaseExpectation(StrictModel):
    """Independent policy, execution, and response oracle for one variant."""

    policy_digest: str = Field(pattern=SHA256)
    events: list[ExpectedEvent]
    backend_execution_count: int = Field(ge=0)
    mcp_is_error: bool
    profile_returned: bool
    tool_outcome: Literal["success", "policy_denied"]


class CaseManifest(StrictModel):
    """Versioned authoritative expectations bundled with the grader."""

    case_id: Literal["member-profile-lookup"] = CASE_ID
    action: Literal["get_member_profile"] = ACTION
    synthetic_member_id: Literal["MEM-001"] = MEMBER_ID
    versions: BuildVersions
    cases: dict[str, CaseExpectation]

    @field_validator("cases")
    @classmethod
    def require_both_variants(
        cls, value: dict[str, CaseExpectation]
    ) -> dict[str, CaseExpectation]:
        if set(value) != {"allow", "deny"}:
            raise ValueError("The manifest requires exactly allow and deny variants.")
        return value


class ObservationStatus(StrictModel):
    """Positive readiness and completeness evidence, not inferred zero counts."""

    event_probe_ready: bool
    operation_probe_ready: bool
    response_probe_ready: bool
    events_complete: bool


class Evidence(StrictModel):
    """Minimal baseline or controlled-regression evidence for one request."""

    row_id: str = Field(min_length=1, max_length=128)
    request_id: str = Field(min_length=1, max_length=128)
    case_id: str = Field(min_length=1, max_length=80)
    variant_id: str = Field(min_length=1, max_length=32)
    action: str = Field(min_length=1, max_length=80)
    synthetic_member_id: str = Field(pattern=r"^MEM-\d{3}$")
    evidence_kind: Literal["baseline", "control"]
    control_id: str | None = Field(max_length=80)
    expected: CaseExpectation
    events: list[ObservedEvent]
    observation_status: ObservationStatus
    backend_execution_count: int = Field(ge=0)
    mcp_is_error: bool | None
    profile_returned: bool | None
    collection_status: Literal["completed", "error"]
    tool_outcome: Literal["success", "policy_denied", "error"]
    versions: EvidenceVersions


def manifest_digest(manifest: CaseManifest) -> str:
    """Hash canonical manifest data without trusting a row's copy of it."""
    encoded = json.dumps(
        manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class GovernanceEnforcementEvaluator:
    """Grade observations against a separate, immutable copy of the oracle."""

    def __init__(self, manifest: CaseManifest) -> None:
        self._manifest = manifest.model_copy(deep=True)
        self._digest = manifest_digest(self._manifest)

    def grade(self, item: Evidence | dict[str, object]) -> float:
        """Return a binary grade, or explicitly reject unusable evidence."""
        try:
            row = Evidence.model_validate(item)
        except ValidationError:
            raise EvidenceValidationError("invalid_evidence_schema") from None
        manifest = self._manifest
        if row.case_id != manifest.case_id or row.variant_id not in manifest.cases:
            raise EvidenceValidationError("unsupported_case")
        if (
            row.collection_status != "completed"
            or row.tool_outcome == "error"
            or not all(row.observation_status.model_dump().values())
            or row.mcp_is_error is None
            or row.profile_returned is None
        ):
            raise EvidenceValidationError("incomplete_or_unhealthy_collection")
        if (row.evidence_kind == "control") != bool(row.control_id):
            raise EvidenceValidationError("invalid_control_identity")

        expected = manifest.cases[row.variant_id]
        identity = (
            f"control-{row.control_id}"
            if row.evidence_kind == "control"
            else f"baseline-{row.variant_id}"
        )
        if (
            row.row_id != identity
            or row.action != manifest.action
            or row.synthetic_member_id != manifest.synthetic_member_id
            or row.expected != expected
            or row.versions.model_dump(exclude={"manifest_digest"})
            != manifest.versions.model_dump()
            or row.versions.manifest_digest != self._digest
            or row.backend_execution_count != expected.backend_execution_count
            or row.mcp_is_error != expected.mcp_is_error
            or row.profile_returned != expected.profile_returned
            or row.tool_outcome != expected.tool_outcome
            or len(row.events) != len(expected.events)
        ):
            return 0.0

        previous_sequence = 0
        for observed, oracle in zip(row.events, expected.events, strict=True):
            if (
                observed.sequence <= previous_sequence
                or observed.request_id != row.request_id
                or observed.policy_digest != expected.policy_digest
                or observed.model_dump(
                    exclude={"sequence", "request_id", "policy_digest"}
                )
                != oracle.model_dump()
            ):
                return 0.0
            previous_sequence = observed.sequence
        return 1.0
