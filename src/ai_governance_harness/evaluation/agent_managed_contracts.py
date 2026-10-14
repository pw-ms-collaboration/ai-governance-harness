"""Private contracts for the reviewed dataset and one pinned behavior evaluator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator, model_validator

from ai_governance_harness.evaluation.agent_contracts import (
    AgentEvaluationError,
    digest,
    private_text,
)
from ai_governance_harness.evaluation.agent_runner import (
    AgentConfiguration,
    CollectionOutcome,
)
from ai_governance_harness.evaluation.artifacts import DEFAULT_POLICY, build_versions
from ai_governance_harness.evaluation.behavior_evaluator import (
    DATA_MAPPING,
    INSTRUCTION_VERSION,
    JUDGE_PROMPT,
    NAME,
    evaluator_definition,
)
from ai_governance_harness.evaluation.evaluator import (
    SHA256,
    BuildVersions,
    StrictModel,
)
from ai_governance_harness.evals.runner import DEFAULT_DATASET

METRIC = "governance_behavior_match"


def content_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def private_content(value: object) -> None:
    if isinstance(value, str):
        private_text(value)
    elif isinstance(value, dict):
        for key, child in value.items():
            private_text(key)
            private_content(child)
    elif isinstance(value, list):
        for child in value:
            private_content(child)


def read_private_json(path: Path) -> dict:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise AgentEvaluationError("symlink_managed_artifact")
    if path.stat().st_size > 4_194_304:
        raise AgentEvaluationError("oversized_managed_artifact")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError):
        raise AgentEvaluationError("invalid_managed_artifact") from None
    if not isinstance(value, dict):
        raise AgentEvaluationError("invalid_managed_artifact")
    private_content(value)
    return value


class BehaviorCase(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    category: str = Field(pattern=r"^[a-z][a-z_]{0,79}$")
    prompt: str = Field(min_length=1, max_length=4000)
    expected_behavior: str = Field(min_length=1, max_length=2000)

    @field_validator("prompt", "expected_behavior")
    @classmethod
    def safe_text(cls, value: str) -> str:
        return private_text(value)

    @property
    def case_id(self) -> str:
        return self.id


def load_cases(path: Path = DEFAULT_DATASET) -> list[BehaviorCase]:
    def read(selected: Path) -> list[BehaviorCase]:
        if selected.is_symlink() or selected.stat().st_size > 1_048_576:
            raise AgentEvaluationError("invalid_dataset_file")
        try:
            return [
                BehaviorCase.model_validate_json(line)
                for line in selected.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except UnicodeError:
            raise AgentEvaluationError("invalid_dataset_encoding") from None

    approved = {case.id: case for case in read(DEFAULT_DATASET)}
    cases = read(path)
    if (
        not cases
        or len({case.id for case in cases}) != len(cases)
        or any(approved.get(case.id) != case for case in cases)
    ):
        raise AgentEvaluationError("unreviewed_or_duplicate_dataset_cases")
    return cases


class BehaviorManifest(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    cases: list[BehaviorCase] = Field(min_length=1, max_length=128)
    versions: BuildVersions
    policy_digest: str = Field(pattern=SHA256)


def independent_manifest(cases: list[BehaviorCase]) -> BehaviorManifest:
    return BehaviorManifest(
        cases=cases,
        versions=build_versions(),
        policy_digest=hashlib.sha256(DEFAULT_POLICY.read_bytes()).hexdigest(),
    )


class EvaluatorPin(StrictModel):
    schema_version: Literal["1.0.0"]
    name: Literal["governance-behavior-match"]
    version: str = Field(pattern=r"^[1-9][0-9]{0,19}$")
    id: str = Field(min_length=1, max_length=2048)
    project_endpoint: str
    instruction_version: Literal["1.0.0"]
    prompt_digest: str = Field(pattern=SHA256)
    status: Literal["registered"]
    verified: Literal[True]
    error: None
    data_mapping: dict[str, str]

    @field_validator("verified", mode="before")
    @classmethod
    def require_verified(cls, value: object) -> object:
        if value is not True:
            raise AgentEvaluationError("unverified_evaluator")
        return value

    @model_validator(mode="after")
    def valid_pin(self) -> EvaluatorPin:
        if (
            self.data_mapping != DATA_MAPPING
            or self.prompt_digest != digest(JUDGE_PROMPT)
            or self.instruction_version != INSTRUCTION_VERSION
            or not self.id.endswith(f"/evaluators/{NAME}/versions/{self.version}")
        ):
            raise AgentEvaluationError("invalid_evaluator_pin")
        private_content(self.model_dump(mode="json"))
        return self


def load_pin(directory: Path, endpoint: str) -> EvaluatorPin:
    pin = EvaluatorPin.model_validate(
        read_private_json(directory / "registration.json")
    )
    if (
        pin.project_endpoint.rstrip("/") != endpoint.rstrip("/")
        or read_private_json(directory / "definition.json")
        != evaluator_definition().as_dict()
    ):
        raise AgentEvaluationError("evaluator_bundle_mismatch")
    return pin


class ManagedRecord(BehaviorCase):
    response: str = Field(min_length=1, max_length=32000)

    @field_validator("response")
    @classmethod
    def safe_response(cls, value: str) -> str:
        return private_text(value)


class ManagedResponse(StrictModel):
    status: Literal["not_run", "completed", "error", "skipped"] = "not_run"
    score: Literal[0.0, 1.0] | None = None
    label: Literal["pass", "fail"] | None = None
    passed: bool | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    error: str | None = None
    provider_error_code: str | None = Field(default=None, max_length=128)
    output_id: str | None = Field(default=None, max_length=256)

    @field_validator("score", mode="before")
    @classmethod
    def require_numeric_binary(cls, value: object) -> object:
        if value is not None and (
            type(value) not in (float, int) or value not in (0, 1)
        ):
            raise AgentEvaluationError("invalid_managed_score")
        return value

    @model_validator(mode="after")
    def consistent(self) -> ManagedResponse:
        if self.status == "completed":
            if (
                self.score is None
                or self.passed is not (self.score == 1.0)
                or (
                    self.label is not None and (self.label == "pass") is not self.passed
                )
                or not self.reason
                or self.error is not None
                or self.provider_error_code is not None
            ):
                raise AgentEvaluationError("inconsistent_managed_response")
        elif (
            self.score is not None or self.label is not None or self.passed is not None
        ):
            raise AgentEvaluationError("inconsistent_managed_error")
        if self.status in {"error", "skipped"} and not self.error:
            raise AgentEvaluationError("missing_managed_error")
        private_content(self.model_dump(mode="json"))
        return self


class ManagedOutcome(StrictModel):
    case: BehaviorCase
    collection: CollectionOutcome
    record: ManagedRecord | None = None
    response: ManagedResponse = Field(default_factory=ManagedResponse)

    @computed_field
    @property
    def accepted(self) -> bool:
        return (
            self.collection.enforcement_accepted
            and self.response.status == "completed"
            and self.response.error is None
            and self.response.score == 1.0
        )


class ManagedAgentResults(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    response_backend: Literal["foundry"] = "foundry"
    run_id: str
    execution_kind: Literal["live", "simulated"]
    status: Literal["passed", "failed", "error", "cancelled"] = "failed"
    error: str | None = "run_incomplete"
    configuration: AgentConfiguration
    manifest: BehaviorManifest
    evaluator: EvaluatorPin
    eval_id: str | None = None
    foundry_run_id: str | None = None
    foundry_status: str = "not_run"
    input_digest: str | None = Field(default=None, pattern=SHA256)
    rows: list[ManagedOutcome]

    def inputs(self) -> dict:
        return {
            "run_id": self.run_id,
            "execution_kind": self.execution_kind,
            "configuration": self.configuration.model_dump(mode="json"),
            "manifest": self.manifest.model_dump(mode="json"),
            "evaluator": self.evaluator.model_dump(mode="json"),
            "rows": [
                row.model_dump(
                    mode="json", exclude={"response"}, exclude_computed_fields=True
                )
                for row in self.rows
            ],
        }

    def finish(self) -> None:
        passed = (
            self.foundry_status == "completed"
            and len(self.rows) == len(self.manifest.cases)
            and all(row.accepted for row in self.rows)
        )
        self.status = "passed" if passed else "failed"
        self.error = None if passed else "managed_acceptance_failed"
