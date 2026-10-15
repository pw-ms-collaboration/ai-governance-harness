"""Pinned, bounded managed grading of trusted local evidence bundles."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import parse_qs, urlsplit

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    CodeBasedEvaluatorDefinition,
    EvaluatorMetric,
    EvaluatorVersion,
    TestingCriterionAzureAIEvaluator,
)
from azure.core.exceptions import AzureError
from openai import APIError, OpenAI
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileContent,
    SourceFileContentContent,
)
from openai.types.evals.runs.output_item_list_response import (
    OutputItemListResponse,
    Result,
)
from pydantic import ValidationError

from ai_governance_harness.evaluation.artifacts import (
    independent_manifest,
    policy_bytes,
    portable_code,
    regression_controls,
    write_json,
)
from ai_governance_harness.evaluation.evaluator import (
    CaseManifest,
    Evidence,
    EvidenceValidationError,
    GovernanceEnforcementEvaluator,
    manifest_digest,
)
from ai_governance_harness.foundry_client import get_azure_credential

METRIC = "governance_enforcement"
ERROR_CATEGORIES = (
    "invalid_evidence_schema",
    "unsupported_case",
    "incomplete_or_unhealthy_collection",
    "invalid_control_identity",
)
INPUT_SCHEMA = {
    "type": "object",
    "properties": {"evidence": {"type": "object"}},
    "required": ["evidence"],
    "additionalProperties": False,
}


class ManagedEvaluationError(ValueError):
    """A sanitized, identifiable managed acceptance or prerequisite failure."""


def _canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise ManagedEvaluationError("invalid_json_artifact_or_result") from None


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if path.stat().st_size > 1_048_576:
        raise ManagedEvaluationError("oversized_evidence_artifact")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if not all(isinstance(row, dict) for row in rows):
        raise ManagedEvaluationError("invalid_evidence_artifact")
    return rows


def trusted_bundle(
    directory: Path,
) -> tuple[
    CaseManifest, str, list[Evidence], list[dict[str, object]], dict[str, str | None]
]:
    """Reject edited schemas/code/data before any credential or upload operation."""
    manifest = CaseManifest.model_validate(
        json.loads((directory / "manifest.json").read_text())
    )
    if manifest != independent_manifest():
        raise ManagedEvaluationError("stale_or_altered_manifest")
    for variant, content in policy_bytes().items():
        if (directory / f"{variant}-policy.yaml").read_bytes() != content:
            raise ManagedEvaluationError("altered_policy_fixture")
    code = portable_code(manifest)
    if (directory / "grader.py").read_text() != code:
        raise ManagedEvaluationError("altered_grader_artifact")
    baselines = [
        Evidence.model_validate(row)
        for row in _read_jsonl(directory / "baseline.jsonl")
    ]
    grader = GovernanceEnforcementEvaluator(manifest)
    if (
        len(baselines) != 2
        or {row.variant_id for row in baselines} != {"allow", "deny"}
        or any(row.evidence_kind != "baseline" for row in baselines)
        or any(grader.grade(row) != 1.0 for row in baselines)
    ):
        raise ManagedEvaluationError("baseline_not_accepted")
    controls = regression_controls(baselines)
    items = [control.item for control in controls]
    if _canonical(_read_jsonl(directory / "controls.jsonl")) != _canonical(items):
        raise ManagedEvaluationError("altered_control_artifact")
    return (
        manifest,
        code,
        baselines,
        items,
        {str(control.item["row_id"]): control.expected_error for control in controls},
    )


def evaluator_definition(code: str) -> EvaluatorVersion:
    """Declare the transport separately from strict validation inside the grader."""
    return EvaluatorVersion(
        evaluator_type="custom",
        categories=["quality"],
        supported_evaluation_levels=["turn"],
        definition=CodeBasedEvaluatorDefinition(
            code_text=code,
            data_schema={
                "type": "object",
                "properties": {"item": INPUT_SCHEMA},
                "required": ["item"],
            },
            init_parameters={
                "type": "object",
                "properties": {
                    "deployment_name": {"type": "string"},
                    "pass_threshold": {"type": "number", "const": 1.0},
                },
                "required": ["deployment_name", "pass_threshold"],
            },
            metrics={
                METRIC: EvaluatorMetric(
                    type="continuous",
                    desirable_direction="increase",
                    min_value=0.0,
                    max_value=1.0,
                    threshold=1.0,
                    is_primary=True,
                )
            },
        ),
    )


def testing_criterion(
    name: str, version: str, deployment: str
) -> TestingCriterionAzureAIEvaluator:
    """Bind the exact registered version and explicit nested evidence mapping."""
    return TestingCriterionAzureAIEvaluator(
        type="azure_ai_evaluator",
        name=METRIC,
        evaluator_name=name,
        evaluator_version=version,
        initialization_parameters={
            "deployment_name": deployment,
            "pass_threshold": 1.0,
        },
        data_mapping={"evidence": "{{item.evidence}}"},
    )


def _budget(deadline: float) -> float:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise ManagedEvaluationError("managed_deadline_exceeded")
    return min(30.0, remaining)


def _azure_budget(deadline: float) -> dict[str, object]:
    remaining = _budget(deadline)
    return {
        "connection_timeout": remaining,
        "read_timeout": remaining,
        "retry_total": 0,
    }


def _recognized_error(value: object) -> str | None:
    if isinstance(value, dict):
        if value.get("code") == "EvidenceValidationError":
            message = value.get("message")
            if message in ERROR_CATEGORIES:
                return message
        value = value.get("message")
    if not isinstance(value, str) or len(value) > 16384:
        return None
    match = re.search(
        r"(?m)^(?:[A-Za-z0-9_]+\.)*EvidenceValidationError: ("
        + "|".join(ERROR_CATEGORIES)
        + r")\s*$",
        value,
    )
    return match.group(1) if match else None


def _safe_report_url(value: str | None) -> str:
    if not isinstance(value, str) or len(value) > 4096:
        raise ManagedEvaluationError("missing_or_invalid_report_url")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or {"token", "sig", "key", "access_token", "api_key", "client_secret"}
        & {name.lower() for name in parse_qs(parsed.query)}
    ):
        raise ManagedEvaluationError("missing_or_invalid_report_url")
    return value


def _result(
    output: OutputItemListResponse,
    expected: dict[str, dict[str, object]],
    expected_errors: dict[str, str | None],
    kind: str,
    eval_id: str,
    run_id: str,
) -> dict[str, object]:
    if (
        not isinstance(output, OutputItemListResponse)
        or not isinstance(getattr(output, "datasource_item", None), dict)
        or not isinstance(getattr(output, "results", None), list)
        or any(not isinstance(result, Result) for result in output.results)
        or any(
            not isinstance(getattr(output, field, None), str)
            for field in ("id", "eval_id", "run_id", "status")
        )
        or type(getattr(output, "datasource_item_id", None)) is not int
    ):
        raise ManagedEvaluationError("invalid_output_item_schema")
    row_id = output.datasource_item.get("row_id")
    valid_identity = (
        isinstance(row_id, str)
        and row_id in expected
        and _canonical(output.datasource_item) == _canonical(expected[row_id])
        and output.eval_id == eval_id
        and output.run_id == run_id
        and isinstance(output.id, str)
        and bool(output.id)
        and type(output.datasource_item_id) is int
        and output.datasource_item_id >= 0
    )
    row_id = row_id if isinstance(row_id, str) and row_id in expected else None
    metric = output.results[0].model_dump() if len(output.results) == 1 else {}
    error = metric.get("error", (output.model_extra or {}).get("error"))
    raw_status = metric.get("status")
    status = (
        raw_status
        if raw_status is not None
        else "completed"
        if output.status in {"pass", "fail"}
        else output.status
    )
    errored = error is not None or status == "error" or output.status == "error"
    category = _recognized_error(error)
    score = metric.get("score")
    finite_score = (
        isinstance(score, (int, float))
        and not isinstance(score, bool)
        and math.isfinite(score)
    )
    valid_score = finite_score and score in {0, 1}
    expected_error = expected_errors.get(row_id) if row_id is not None else None
    if errored and raw_status is None:
        status = "error"
    common = (
        valid_identity
        and metric.get("name") == METRIC
        and valid_score
        and output.status in {"pass", "fail", "completed", "error"}
    )
    if kind == "baseline":
        accepted = (
            common
            and status == "completed"
            and not errored
            and score == 1.0
            and metric.get("passed") is True
            and output.status in {"pass", "completed"}
        )
    elif expected_error is None:
        accepted = (
            common
            and status == "completed"
            and not errored
            and score == 0.0
            and metric.get("passed") is False
            and output.status in {"fail", "completed"}
        )
    else:
        accepted = (
            common
            and status == "error"
            and errored
            and category == expected_error
            and score == 0.0
            and (metric.get("passed") is False or metric.get("passed") is None)
            and output.status in {"fail", "error"}
        )
    return {
        "row_id": row_id,
        "output_item_id": output.id,
        "output_eval_id": output.eval_id,
        "output_run_id": output.run_id,
        "datasource_item_id": output.datasource_item_id,
        "item_status": output.status,
        "metric": metric.get("name") if metric.get("name") == METRIC else None,
        "status": status if isinstance(status, str) else "invalid",
        "metric_status": raw_status if isinstance(raw_status, str) else None,
        "score": score if finite_score else None,
        "score_valid": valid_score,
        "passed": metric.get("passed") if type(metric.get("passed")) is bool else None,
        "error_present": errored,
        "error_category": category,
        "expected_error": expected_error,
        "identity_valid": valid_identity,
        "accepted": accepted,
        "validation_error": None if common else "invalid_metric_or_identity",
    }


def _run(
    client: OpenAI,
    eval_id: str,
    kind: str,
    rows: list[dict[str, object]],
    expected_errors: dict[str, str | None],
    deadline: float,
    report: dict[str, object],
) -> None:
    source_items = [{"row_id": row["row_id"], "evidence": row} for row in rows]
    expected = {str(row["row_id"]): row for row in source_items}
    report["expected_row_ids"] = sorted(expected)
    created = client.evals.runs.create(
        eval_id=eval_id,
        name=f"{METRIC}-{kind}",
        data_source=CreateEvalJSONLRunDataSourceParam(
            type="jsonl",
            source=SourceFileContent(
                type="file_content",
                content=[SourceFileContentContent(item=row) for row in source_items],
            ),
        ),
        timeout=_budget(deadline),
    )
    report.update(run_id=created.id, status=created.status)
    if not isinstance(created.id, str) or not created.id:
        raise ManagedEvaluationError("invalid_managed_run_id")
    while True:
        run = client.evals.runs.retrieve(
            created.id, eval_id=eval_id, timeout=_budget(deadline)
        )
        report["status"] = run.status
        if run.report_url:
            report["report_url"] = _safe_report_url(run.report_url)
        if run.status == "completed":
            break
        if run.status in {"failed", "canceled", "cancelled"}:
            raise ManagedEvaluationError(f"managed_run_{run.status}")
        if run.status not in {"queued", "in_progress", "running"}:
            raise ManagedEvaluationError("unsupported_managed_run_status")
        sleep(min(3.0, _budget(deadline)))
    report["report_url"] = _safe_report_url(run.report_url)
    results: list[dict[str, object]] = []
    report["items"] = results
    seen_output_ids: set[str] = set()
    seen_row_ids: set[str] = set()
    seen_datasource_ids: set[int] = set()
    after: str | None = None
    while True:
        pagination = {"after": after} if after is not None else {}
        page = client.evals.runs.output_items.list(
            created.id,
            eval_id=eval_id,
            limit=100,
            timeout=_budget(deadline),
            **pagination,
        )
        if not isinstance(getattr(page, "data", None), list):
            raise ManagedEvaluationError("invalid_result_page_schema")
        for output in page.data:
            result = _result(
                output, expected, expected_errors, kind, eval_id, created.id
            )
            row_id = result["row_id"]
            if (
                output.id in seen_output_ids
                or row_id in seen_row_ids
                or output.datasource_item_id in seen_datasource_ids
            ):
                result["accepted"] = False
                result["duplicate"] = True
            seen_output_ids.add(output.id)
            if isinstance(row_id, str):
                seen_row_ids.add(row_id)
            seen_datasource_ids.add(output.datasource_item_id)
            results.append(result)
        if not page.has_next_page():
            break
        if not page.data or page.data[-1].id == after:
            raise ManagedEvaluationError("invalid_result_pagination")
        after = page.data[-1].id
        if len(results) > len(expected):
            raise ManagedEvaluationError("unexpected_result_count")
    report["accepted"] = (
        len(results) == len(expected)
        and seen_row_ids == set(expected)
        and all(row["accepted"] for row in results)
    )
    report["missing_row_ids"] = sorted(set(expected) - seen_row_ids)
    _budget(deadline)


def run_managed(
    directory: Path,
    output: Path,
    *,
    endpoint: str | None,
    deployment: str | None,
    confirm_submit: bool = False,
    timeout_seconds: float = 600.0,
) -> dict[str, object]:
    """Register/submit only after explicit confirmation, retaining every outcome."""
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    runs: list[dict[str, object]] = []
    report: dict[str, object] = {"status": "error", "runs": runs, "error": None}
    try:
        manifest, code, baselines, controls, expected_errors = trusted_bundle(directory)
        report["manifest_digest"] = manifest_digest(manifest)
        code_digest = hashlib.sha256(code.encode()).hexdigest()
        report["evaluator_digest"] = code_digest
        if not endpoint:
            raise ManagedEvaluationError("missing_endpoint")
        if not deployment or not deployment.strip():
            raise ManagedEvaluationError("missing_deployment")
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not re.fullmatch(r"/api/projects/[^/]+/?", parsed.path)
        ):
            raise ManagedEvaluationError("invalid_project_endpoint")
        if not confirm_submit:
            raise ManagedEvaluationError("submission_confirmation_required")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ManagedEvaluationError("invalid_managed_timeout")
        deadline = monotonic() + timeout_seconds
        name = f"governance-enforcement-{code_digest[:12]}"
        definition = evaluator_definition(code)
        with get_azure_credential() as credential:
            with AIProjectClient(
                endpoint=endpoint,
                credential=credential,
                **_azure_budget(deadline),
            ) as project:
                configured_deployment = project.deployments.get(
                    name=deployment, **_azure_budget(deadline)
                )
                if configured_deployment.name != deployment:
                    raise ManagedEvaluationError("configured_deployment_mismatch")
                report["deployment_verified"] = True
                registered = project.evaluators.create_version(
                    name=name, evaluator_version=definition, **_azure_budget(deadline)
                )
                report["evaluator"] = {
                    "name": registered.name,
                    "version": registered.version,
                    "id": registered.id,
                }
                if (
                    registered.name != name
                    or not isinstance(registered.version, str)
                    or not registered.version
                    or not registered.id
                ):
                    raise ManagedEvaluationError("invalid_evaluator_registration")
                pinned = project.evaluators.get_version(
                    name=name, version=registered.version, **_azure_budget(deadline)
                )
                if pinned.version != registered.version or pinned.definition is None:
                    raise ManagedEvaluationError("evaluator_version_mismatch")
                returned = pinned.definition.as_dict()
                if any(
                    returned.get(key) != value
                    for key, value in definition.definition.as_dict().items()
                ):
                    raise ManagedEvaluationError("evaluator_definition_mismatch")
                with project.get_openai_client(
                    timeout=_budget(deadline), max_retries=0
                ) as client:
                    criterion = testing_criterion(name, registered.version, deployment)
                    evaluation = client.evals.create(
                        name=METRIC,
                        data_source_config=DataSourceConfigCustom(
                            type="custom",
                            item_schema={
                                "type": "object",
                                "properties": {
                                    "row_id": {"type": "string"},
                                    "evidence": {"type": "object"},
                                },
                                "required": ["row_id", "evidence"],
                                "additionalProperties": False,
                            },
                        ),
                        # The OpenAI union omits this Azure-specific criterion.
                        testing_criteria=[],
                        extra_body={"testing_criteria": [criterion]},
                        metadata={
                            "evaluator_version": registered.version,
                            "evaluator_digest": str(report["evaluator_digest"]),
                            "manifest_digest": manifest_digest(manifest),
                        },
                        timeout=_budget(deadline),
                    )
                    report["eval_id"] = evaluation.id
                    if not isinstance(evaluation.id, str) or not evaluation.id:
                        raise ManagedEvaluationError("invalid_managed_eval_id")
                    for kind, rows in (
                        (
                            "baseline",
                            [row.model_dump(mode="json") for row in baselines],
                        ),
                        ("controls", controls),
                    ):
                        run_report: dict[str, object] = {
                            "kind": kind,
                            "eval_id": evaluation.id,
                            "accepted": False,
                        }
                        runs.append(run_report)
                        _run(
                            client,
                            evaluation.id,
                            kind,
                            rows,
                            expected_errors,
                            deadline,
                            run_report,
                        )
        _budget(deadline)
        report["status"] = (
            "passed"
            if len(runs) == 2 and all(run["accepted"] for run in runs)
            else "failed"
        )
        if report["status"] == "failed":
            report["error"] = {"category": "managed_acceptance_failed"}
    except ManagedEvaluationError as error:
        category = str(error)
        report["status"] = (
            "blocked"
            if category
            in {
                "missing_endpoint",
                "missing_deployment",
                "invalid_project_endpoint",
                "submission_confirmation_required",
            }
            else "error"
        )
        report["error"] = {"category": category}
    except (
        OSError,
        json.JSONDecodeError,
        ValidationError,
        EvidenceValidationError,
    ) as error:
        report["error"] = {
            "category": "invalid_local_artifacts",
            "type": type(error).__name__,
        }
    except (AzureError, APIError) as error:
        report["error"] = {
            "category": "managed_service_error",
            "type": type(error).__name__,
        }
    finally:
        write_json(output / "managed-results.json", report)
    return report
