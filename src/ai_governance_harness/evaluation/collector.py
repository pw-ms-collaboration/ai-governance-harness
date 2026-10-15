"""Collect real, isolated stdio enforcement evidence without saving profiles."""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Literal
from uuid import uuid4

import anyio
from mcp import Client, StdioServerParameters, types
from mcp.client.client import CallToolResult
from mcp.client.stdio import get_default_environment
from mcp.shared.exceptions import MCPError
from pydantic import ValidationError

from ai_governance_harness.evaluation.artifacts import (
    build_versions,
    create_manifest,
    portable_code,
    regression_controls,
    write_json,
    write_jsonl,
)
from ai_governance_harness.evaluation.evaluator import (
    ACTION,
    CASE_ID,
    DENY_RULE,
    MEMBER_ID,
    CaseManifest,
    Evidence,
    EvidenceValidationError,
    EvidenceVersions,
    ObservationStatus,
    GovernanceEnforcementEvaluator,
    manifest_digest,
)
from ai_governance_harness.evaluation.worker import WorkerReport

TRANSPORT_ERRORS = (
    OSError,
    EOFError,
    TimeoutError,
    MCPError,
    ValidationError,
    anyio.EndOfStream,
    anyio.BrokenResourceError,
    anyio.ClosedResourceError,
)


def isolated_environment(directory: Path, policy: Path) -> dict[str, str]:
    """Override SDK defaults and prevent dotenv, Azure, or telemetry inheritance."""
    env = {key: "" for key in get_default_environment()}
    env.update(
        {
            "HOME": str(directory),
            "USERPROFILE": str(directory),
            "USER": "evaluation",
            "LOGNAME": "evaluation",
            "PATH": os.defpath,
            "SHELL": "/bin/false",
            "TERM": "dumb",
            "LANG": "C.UTF-8",
            "PYTHON_DOTENV_DISABLED": "true",
            "PYTHONUNBUFFERED": "1",
            "MCP_TRANSPORT": "stdio",
            "MCP_HOSTED": "false",
            "MCP_ENVIRONMENT": "local",
            "MOCK_IDENTITY_ENABLED": "true",
            "MOCK_IDENTITY_LOCAL_PERSONA": "retention_specialist",
            "GOVERNANCE_ENVIRONMENT": "local",
            "GOVERNANCE_ENABLED": "true",
            "GOVERNANCE_POLICY_PATH": str(policy),
            "GOVERNANCE_SANDBOX_PROVIDER": "none",
        }
    )
    return env


def response_probe(result: CallToolResult) -> tuple[bool, bool]:
    """Inspect every representation; unknown content cannot certify absence."""
    structured = result.structured_content
    healthy = structured is None or isinstance(structured, dict)
    returned_data = bool(structured)
    safe_errors = {
        "The tool could not complete the request.",
        f"Error calling tool '{ACTION}': The tool could not complete the request.",
        f"Error executing tool {ACTION}: The tool could not complete the request.",
        "Governance denied the tool response.",
        f"Error calling tool '{ACTION}': Governance denied the tool response.",
        f"Error executing tool {ACTION}: Governance denied the tool response.",
    }
    for block in result.content:
        if not isinstance(block, types.TextContent):
            healthy = False
            continue
        try:
            decoded = json.loads(block.text)
        except json.JSONDecodeError:
            if not result.is_error or block.text not in safe_errors:
                healthy = False
        else:
            healthy &= isinstance(decoded, dict)
            returned_data |= bool(decoded)
    return healthy, returned_data


def _known_transport_group(group: BaseExceptionGroup) -> bool:
    return all(
        _known_transport_group(error)
        if isinstance(error, BaseExceptionGroup)
        else isinstance(error, TRANSPORT_ERRORS)
        for error in group.exceptions
    )


async def collect_case(
    manifest: CaseManifest,
    variant: Literal["allow", "deny"],
    directory: Path,
    *,
    timeout_seconds: float = 30.0,
) -> tuple[Evidence, dict[str, object]]:
    """Run exactly one tool call and require a healthy, normally exited worker."""
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("Collection timeout must be finite and positive.")
    directory = directory.resolve()
    request_id = uuid4().hex
    report_path = directory / f"{variant}-worker.json"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "ai_governance_harness.evaluation.worker",
            "--report",
            str(report_path),
            "--request-id",
            request_id,
        ],
        env=isolated_environment(directory, directory / f"{variant}-policy.yaml"),
    )
    stage = "startup"
    failure: str | None = None
    response_ready = False
    mcp_is_error: bool | None = None
    profile_returned: bool | None = None
    try:
        with anyio.fail_after(timeout_seconds):
            async with Client(
                parameters, mode="legacy", read_timeout_seconds=timeout_seconds
            ) as client:
                stage = "request"
                result = await client.call_tool(ACTION, {"member_id": MEMBER_ID})
                mcp_is_error = result.is_error
                response_ready, profile_returned = response_probe(result)
                stage = "shutdown"
    except TRANSPORT_ERRORS as error:
        failure = "timeout" if isinstance(error, TimeoutError) else "protocol_error"
    except ExceptionGroup as errors:
        if not _known_transport_group(errors):
            raise
        failure = "protocol_error"

    report: WorkerReport | None = None
    try:
        report = WorkerReport.model_validate(json.loads(report_path.read_text()))
    except (OSError, json.JSONDecodeError, ValidationError):
        failure = failure or "missing_or_invalid_worker_report"
    capture = report.capture if report is not None else None
    if report is not None and report.child_exit_code != 0:
        failure = failure or "abnormal_worker_exit"
    if capture is not None and capture.request_id != request_id:
        failure = failure or "worker_request_mismatch"
    status = ObservationStatus(
        event_probe_ready=capture.event_probe_ready if capture else False,
        operation_probe_ready=capture.operation_probe_ready if capture else False,
        response_probe_ready=response_ready,
        events_complete=(
            capture.events_complete if capture and failure is None else False
        ),
    )
    if not all(status.model_dump().values()):
        failure = failure or "unhealthy_or_incomplete_observation"
    events = capture.events if capture else []
    explicit_denial = any(
        event.lifecycle_point == "pre_tool"
        and event.decision == "deny"
        and not event.allowed
        and event.matched_rule == DENY_RULE
        for event in events
    )
    outcome = (
        "error"
        if failure is not None or mcp_is_error is None
        else "success"
        if not mcp_is_error
        else "policy_denied"
        if explicit_denial
        else "error"
    )
    row = Evidence(
        row_id=f"baseline-{variant}",
        request_id=request_id,
        case_id=CASE_ID,
        variant_id=variant,
        action=ACTION,
        synthetic_member_id=MEMBER_ID,
        evidence_kind="baseline",
        control_id=None,
        expected=manifest.cases[variant],
        events=events,
        observation_status=status,
        backend_execution_count=capture.backend_execution_count if capture else 0,
        mcp_is_error=mcp_is_error,
        profile_returned=profile_returned,
        collection_status="error" if failure is not None else "completed",
        tool_outcome=outcome,
        versions=EvidenceVersions(
            **(capture.versions if capture else build_versions()).model_dump(),
            manifest_digest=manifest_digest(manifest),
        ),
    )
    return row, {
        "row_id": row.row_id,
        "request_id": request_id,
        "stage": stage,
        "error": failure,
        "child_exit_code": report.child_exit_code if report else None,
    }


async def run_local(
    directory: Path, *, timeout_seconds: float = 30.0
) -> dict[str, object]:
    """Collect both baselines, then prove the intended regression outcomes."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    manifest = create_manifest(directory)
    grader = GovernanceEnforcementEvaluator(manifest)
    baselines: list[Evidence] = []
    baseline_results: list[dict[str, object]] = []
    for variant in ("allow", "deny"):
        row, diagnostics = await collect_case(
            manifest, variant, directory, timeout_seconds=timeout_seconds
        )
        baselines.append(row)
        score = None
        error = None
        try:
            score = grader.grade(row)
        except EvidenceValidationError as invalid:
            error = str(invalid)
        baseline_results.append(
            {
                **diagnostics,
                "score": score,
                "grader_error": error,
                "accepted": score == 1.0 and error is None,
            }
        )
    write_jsonl(
        directory / "baseline.jsonl",
        [row.model_dump(mode="json") for row in baselines],
    )
    baseline_passed = all(result["accepted"] for result in baseline_results)
    controls = regression_controls(baselines) if baseline_passed else []
    control_results: list[dict[str, object]] = []
    for control in controls:
        score = None
        error = None
        try:
            score = grader.grade(control.item)
        except EvidenceValidationError as invalid:
            error = str(invalid)
        control_results.append(
            {
                "row_id": control.item["row_id"],
                "control_id": control.control_id,
                "score": score,
                "error": error,
                "expected_error": control.expected_error,
                "accepted": (
                    error == control.expected_error
                    and (score == 0.0 if error is None else score is None)
                ),
            }
        )
    write_jsonl(directory / "controls.jsonl", [control.item for control in controls])
    code_path = directory / "grader.py"
    with code_path.open("x", encoding="utf-8") as output:
        code_path.chmod(0o600)
        output.write(portable_code(manifest))
    result = {
        "status": (
            "passed"
            if baseline_passed
            and len(controls) == 18
            and all(item["accepted"] for item in control_results)
            else "failed"
        ),
        "manifest_digest": manifest_digest(manifest),
        "baselines": baseline_results,
        "controls": control_results,
    }
    write_json(directory / "local-results.json", result)
    return result
