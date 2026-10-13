"""Tests for the scoped dependency vulnerability exception."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from ai_governance_harness import security_audit


def _write_policy(tmp_path: Path, *, expires_at: str) -> Path:
    vex_path = tmp_path / "exception.openvex.json"
    vex_path.write_text(
        json.dumps(
            {
                "statements": [
                    {
                        "vulnerability": {"name": "PYSEC-TEST-1"},
                        "status": "not_affected",
                        "justification": "vulnerable_code_not_in_execute_path",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    policy_path = tmp_path / "audit-policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "schema": "ai-governance-audit-policy/v1",
                "vex_document": str(vex_path.relative_to(tmp_path)),
                "expires_at": expires_at,
                "expected_packages": {"pytest": pytest.__version__},
                "ignored_vulnerabilities": ["PYSEC-TEST-1"],
                "scan_distributions": ["pytest"],
                "forbidden_symbols": ["not-a-real-python-symbol-8294"],
            }
        ),
        encoding="utf-8",
    )
    return policy_path


def test_given_current_exception_when_validating_then_returns_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    policy_path = _write_policy(tmp_path, expires_at="2026-11-13")
    monkeypatch.setattr(security_audit, "PROJECT_ROOT", tmp_path)

    # Act
    result = security_audit.validate_policy(
        policy_path,
        today=date(2026, 10, 14),
    )

    # Assert
    assert result == ["PYSEC-TEST-1"]


def test_given_expired_exception_when_validating_then_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    policy_path = _write_policy(tmp_path, expires_at="2026-10-13")
    monkeypatch.setattr(security_audit, "PROJECT_ROOT", tmp_path)

    # Act and Assert
    with pytest.raises(
        security_audit.AuditPolicyError,
        match="expired",
    ):
        security_audit.validate_policy(
            policy_path,
            today=date(2026, 10, 14),
        )


def test_given_version_drift_when_validating_then_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    policy_path = _write_policy(tmp_path, expires_at="2026-11-13")
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    policy["expected_packages"]["pytest"] = "0.0.0"
    policy_path.write_text(yaml.safe_dump(policy), encoding="utf-8")
    monkeypatch.setattr(security_audit, "PROJECT_ROOT", tmp_path)

    # Act and Assert
    with pytest.raises(
        security_audit.AuditPolicyError,
        match="changed from reviewed version",
    ):
        security_audit.validate_policy(
            policy_path,
            today=date(2026, 10, 14),
        )
