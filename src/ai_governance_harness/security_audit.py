"""Run dependency auditing with a bounded, expiring VEX exception."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, date, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = PROJECT_ROOT / "security" / "vex" / "audit-policy.yaml"


class AuditPolicyError(RuntimeError):
    """Raised when a vulnerability exception is invalid or stale."""


def _load_mapping(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise AuditPolicyError(f"{path} must contain a YAML object.")
    return document


def _parse_expiry(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise AuditPolicyError("expires_at must be an ISO date.") from error
    raise AuditPolicyError("expires_at must be an ISO date.")


def _string_list(policy: dict[str, Any], key: str) -> list[str]:
    value = policy.get(key)
    if not isinstance(value, list) or not value:
        raise AuditPolicyError(f"{key} must be a non-empty list.")
    if not all(isinstance(item, str) and item for item in value):
        raise AuditPolicyError(f"{key} entries must be non-empty strings.")
    return value


def _validate_versions(policy: dict[str, Any]) -> None:
    expected = policy.get("expected_packages")
    if not isinstance(expected, dict) or not expected:
        raise AuditPolicyError("expected_packages must be a non-empty object.")
    for package, expected_version in expected.items():
        if not isinstance(package, str) or not isinstance(expected_version, str):
            raise AuditPolicyError(
                "expected_packages entries must map strings to strings."
            )
        installed_version = metadata.version(package)
        if installed_version != expected_version:
            raise AuditPolicyError(
                f"{package} changed from reviewed version "
                f"{expected_version} to {installed_version}."
            )


def _distribution_python_files(distribution_name: str) -> list[Path]:
    distribution = metadata.distribution(distribution_name)
    paths: list[Path] = []
    for relative_path in distribution.files or []:
        if relative_path.suffix != ".py":
            continue
        path = Path(distribution.locate_file(relative_path)).resolve()
        if path.is_file():
            paths.append(path)
    return paths


def _validate_reachability(policy: dict[str, Any]) -> None:
    symbols = _string_list(policy, "forbidden_symbols")
    files = list((PROJECT_ROOT / "src").rglob("*.py"))
    for distribution in _string_list(policy, "scan_distributions"):
        files.extend(_distribution_python_files(distribution))

    matches: list[str] = []
    for path in sorted(set(files)):
        content = path.read_text(encoding="utf-8", errors="replace")
        for symbol in symbols:
            if symbol in content:
                matches.append(f"{path}: {symbol}")
    if matches:
        details = "\n".join(matches[:20])
        raise AuditPolicyError(
            "A reviewed vulnerable API became reachable:\n" + details
        )


def _validate_vex(policy: dict[str, Any]) -> None:
    relative_path = policy.get("vex_document")
    if not isinstance(relative_path, str) or not relative_path:
        raise AuditPolicyError("vex_document must be a repository-relative path.")
    vex_path = (PROJECT_ROOT / relative_path).resolve()
    if PROJECT_ROOT not in vex_path.parents or not vex_path.is_file():
        raise AuditPolicyError("vex_document must resolve to an existing file.")
    document = json.loads(vex_path.read_text(encoding="utf-8"))
    statements = document.get("statements")
    if not isinstance(statements, list):
        raise AuditPolicyError("The VEX document must contain statements.")

    expected_ids = set(_string_list(policy, "ignored_vulnerabilities"))
    approved_ids = {
        statement.get("vulnerability", {}).get("name")
        for statement in statements
        if isinstance(statement, dict)
        and statement.get("status") == "not_affected"
        and statement.get("justification")
        == "vulnerable_code_not_in_execute_path"
        and isinstance(statement.get("vulnerability"), dict)
    }
    if approved_ids != expected_ids:
        raise AuditPolicyError(
            "VEX statements do not exactly match ignored vulnerabilities."
        )


def validate_policy(
    policy_path: Path = POLICY_PATH,
    *,
    today: date | None = None,
) -> list[str]:
    """Validate the scoped exception and return approved advisory IDs."""
    policy = _load_mapping(policy_path)
    if policy.get("schema") != "ai-governance-audit-policy/v1":
        raise AuditPolicyError("Unsupported audit policy schema.")
    expiry = _parse_expiry(policy.get("expires_at"))
    current_date = today or datetime.now(UTC).date()
    if current_date > expiry:
        raise AuditPolicyError(
            f"The vulnerability exception expired on {expiry.isoformat()}."
        )
    _validate_versions(policy)
    _validate_reachability(policy)
    _validate_vex(policy)
    return _string_list(policy, "ignored_vulnerabilities")


def run_audit(vulnerability_ids: list[str]) -> int:
    """Run pip-audit while ignoring only prevalidated advisory IDs."""
    command = [sys.executable, "-m", "pip_audit"]
    for vulnerability_id in vulnerability_ids:
        command.extend(["--ignore-vuln", vulnerability_id])
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    """Validate the exception and audit the installed environment."""
    try:
        vulnerability_ids = validate_policy()
    except (AuditPolicyError, metadata.PackageNotFoundError, OSError) as error:
        print(f"Dependency audit policy failed: {error}", file=sys.stderr)
        return EXIT_ERROR
    print(
        "Validated temporary VEX exception for "
        + ", ".join(vulnerability_ids)
        + ".",
        file=sys.stderr,
    )
    return run_audit(vulnerability_ids)


if __name__ == "__main__":
    sys.exit(main())
