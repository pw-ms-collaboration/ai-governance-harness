"""Minimal, versioned artifacts for the two synthetic evaluation cases."""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from importlib.metadata import version
from pathlib import Path

from pydantic import BaseModel

from ai_governance_harness.evaluation.evaluator import (
    ACTION,
    DENY_RULE,
    BuildVersions,
    CaseExpectation,
    CaseManifest,
    ExpectedEvent,
    Evidence,
    StrictModel,
)

PACKAGE_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = PACKAGE_DIRECTORY / "governance" / "policies" / "default.yaml"
DATA_DIRECTORY = PACKAGE_DIRECTORY / "data" / "synthetic"
FIXTURE_NAMES = (
    "accounts.json",
    "contributions.json",
    "digital_activity.json",
    "interactions.json",
    "members.json",
)


def files_digest(directory: Path, names: list[str] | tuple[str, ...]) -> str:
    """Hash file names and bytes with unambiguous length framing."""
    digest = hashlib.sha256()
    if not names:
        raise ValueError("Cannot version an empty application or fixture file set.")
    for name in sorted(names):
        label = name.encode()
        content = (directory / name).read_bytes()
        digest.update(len(label).to_bytes(8, "big"))
        digest.update(label)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def build_versions() -> BuildVersions:
    """Identify source bytes and synthetic fixtures, including uncommitted code."""
    repository = PACKAGE_DIRECTORY.parent.parent
    if (repository / ".git").exists():
        revision = subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            text=True,
            timeout=5,
        ).strip()
    else:
        revision = f"package:{version('ai-governance-harness')}"
    source_names = [
        path.relative_to(PACKAGE_DIRECTORY).as_posix()
        for path in PACKAGE_DIRECTORY.rglob("*.py")
    ]
    return BuildVersions(
        application_revision=revision,
        application_digest=files_digest(PACKAGE_DIRECTORY, source_names),
        fixture_digest=files_digest(DATA_DIRECTORY, FIXTURE_NAMES),
        toolkit_version=version("agent-governance-toolkit"),
    )


def write_json(path: Path, value: BaseModel | dict[str, object]) -> None:
    """Create a private artifact without overwriting a retained result."""
    data = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    with path.open("x", encoding="utf-8") as output:
        path.chmod(0o600)
        json.dump(data, output, sort_keys=True, indent=2, allow_nan=False)
        output.write("\n")


def policy_bytes() -> dict[str, bytes]:
    """Return trusted policy fixture bytes without consuming observed evidence."""
    allow_bytes = DEFAULT_POLICY.read_bytes()
    deny_bytes = (
        allow_bytes
        + (
            f"\n  - name: {DENY_RULE}\n"
            "    stage: pre_tool\n"
            f"    condition: \"action.type == '{ACTION}'\"\n"
            "    action: deny\n"
        ).encode()
    )
    return {"allow": allow_bytes, "deny": deny_bytes}


def independent_manifest() -> CaseManifest:
    """Build the approved oracle from current source and trusted policy bytes."""
    policies = policy_bytes()

    def event(point: str, decision: str, rule: str) -> ExpectedEvent:
        return ExpectedEvent(
            source="gateway",
            lifecycle_point=point,
            action=ACTION,
            decision=decision,
            allowed=decision == "allow",
            matched_rule=rule,
            enforcement_mode="enforce",
            boundary="local",
            staff_role="retention_specialist",
        )

    return CaseManifest(
        versions=build_versions(),
        cases={
            "allow": CaseExpectation(
                policy_digest=hashlib.sha256(policies["allow"]).hexdigest(),
                events=[
                    event("pre_tool", "allow", "allow-local-retention-tools"),
                    event("post_tool", "allow", "allow-member-profile-result"),
                ],
                backend_execution_count=1,
                mcp_is_error=False,
                profile_returned=True,
                tool_outcome="success",
            ),
            "deny": CaseExpectation(
                policy_digest=hashlib.sha256(policies["deny"]).hexdigest(),
                events=[event("pre_tool", "deny", DENY_RULE)],
                backend_execution_count=0,
                mcp_is_error=True,
                profile_returned=False,
                tool_outcome="policy_denied",
            ),
        },
    )


def create_manifest(directory: Path) -> CaseManifest:
    """Create private isolated policies and an independently authored manifest."""
    manifest = independent_manifest()
    for variant, content in policy_bytes().items():
        path = directory / f"{variant}-policy.yaml"
        with path.open("xb") as output:
            path.chmod(0o600)
            output.write(content)
    write_json(directory / "manifest.json", manifest)
    return manifest


def portable_code(manifest: CaseManifest) -> str:
    """Package trusted grading source and JSON data, never input Python code."""
    source = (Path(__file__).parent / "evaluator.py").read_text(encoding="utf-8")
    payload = json.dumps(manifest.model_dump(mode="json"), sort_keys=True)
    code = source + (
        f"\n_BUNDLED_MANIFEST = CaseManifest.model_validate(json.loads({payload!r}))\n"
        "_GRADER = GovernanceEnforcementEvaluator(_BUNDLED_MANIFEST)\n\n"
        "def grade(sample: dict, item: dict) -> float:\n"
        '    """Grade the mapped evidence item without invoking a model."""\n'
        "    if not isinstance(item, dict) or 'evidence' not in item:\n"
        "        raise EvidenceValidationError('invalid_evidence_schema')\n"
        "    return _GRADER.grade(item['evidence'])\n"
    )
    if len(code.encode()) >= 256 * 1024:
        raise ValueError("Portable evaluator exceeds the managed code size limit.")
    return code


class RegressionControl(StrictModel):
    """Independently declared expected outcome for one known evidence mutation."""

    control_id: str
    expected_error: str | None
    item: dict[str, object]


def regression_controls(baselines: list[Evidence]) -> list[RegressionControl]:
    """Mutate copies only; never overwrite baseline observations or expectations."""
    by_variant = {row.variant_id: row for row in baselines}
    if len(baselines) != 2 or set(by_variant) != {"allow", "deny"}:
        raise ValueError("Controls require exactly the two baseline variants.")
    controls: list[RegressionControl] = []
    for name in (
        "wrong-decision",
        "wrong-allowed",
        "deny-backend-executed",
        "deny-profile-returned",
        "wrong-policy-digest",
        "wrong-deny-rule",
        "disabled-enforcement",
        "missing-event",
        "extra-event",
        "reordered-events",
        "altered-expectations",
        "missing-field",
        "boolean-count",
        "unknown-schema",
        "unknown-case",
        "unhealthy-operation-probe",
        "incomplete-events",
        "failed-collection",
    ):
        variant = "allow" if name == "reordered-events" else "deny"
        item = deepcopy(by_variant[variant].model_dump(mode="json"))
        item.update(row_id=f"control-{name}", evidence_kind="control", control_id=name)
        expected_error = None
        if name == "wrong-decision":
            item["events"][0]["decision"] = "allow"
        elif name == "wrong-allowed":
            item["events"][0]["allowed"] = True
        elif name == "deny-backend-executed":
            item["backend_execution_count"] = 1
        elif name == "deny-profile-returned":
            item["profile_returned"] = True
        elif name == "wrong-policy-digest":
            item["events"][0]["policy_digest"] = "0" * 64
        elif name == "wrong-deny-rule":
            item["events"][0]["matched_rule"] = "wrong-rule"
        elif name == "disabled-enforcement":
            item["events"][0]["enforcement_mode"] = "disabled"
        elif name == "missing-event":
            item["events"] = []
        elif name == "extra-event":
            item["events"].append(deepcopy(item["events"][0]))
        elif name == "reordered-events":
            item["events"].reverse()
        elif name == "altered-expectations":
            item["backend_execution_count"] = 1
            item["expected"]["backend_execution_count"] = 1
        elif name == "missing-field":
            del item["events"][0]["allowed"]
            expected_error = "invalid_evidence_schema"
        elif name == "boolean-count":
            item["backend_execution_count"] = True
            expected_error = "invalid_evidence_schema"
        elif name == "unknown-schema":
            item["versions"]["evidence_schema_version"] = "999"
            expected_error = "invalid_evidence_schema"
        elif name == "unknown-case":
            item["case_id"] = "unsupported"
            expected_error = "unsupported_case"
        elif name == "unhealthy-operation-probe":
            item["observation_status"]["operation_probe_ready"] = False
            expected_error = "incomplete_or_unhealthy_collection"
        elif name == "incomplete-events":
            item["observation_status"]["events_complete"] = False
            expected_error = "incomplete_or_unhealthy_collection"
        elif name == "failed-collection":
            item["collection_status"] = "error"
            expected_error = "incomplete_or_unhealthy_collection"
        controls.append(
            RegressionControl(control_id=name, expected_error=expected_error, item=item)
        )
    return controls


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Create private JSONL containing only approved evidence contracts."""
    with path.open("x", encoding="utf-8") as output:
        path.chmod(0o600)
        for row in rows:
            output.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
