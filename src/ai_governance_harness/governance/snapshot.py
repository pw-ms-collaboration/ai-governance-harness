"""Build sanitized governance snapshots for local operator surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ai_governance_harness.governance.engine import GovernanceEngine
from ai_governance_harness.governance.events import (
    GovernanceEvent,
    governance_events,
)
from ai_governance_harness.governance.sandbox import SandboxGuard

_EVIDENCE_PATH = Path(__file__).resolve().parent / "evidence" / "owasp-agentic.yaml"


def _load_yaml_object(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"Expected a YAML object in {path.name}.")
    return document


def _policy_summary(engine: GovernanceEngine) -> dict[str, Any]:
    document = _load_yaml_object(engine.settings.policy_path)
    rules = document.get("rules", [])
    safe_rules = []
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            safe_rules.append(
                {
                    "name": str(rule.get("name", ""))[:128],
                    "stage": str(rule.get("stage", ""))[:32],
                    "action": str(rule.get("action", ""))[:32],
                    "condition": str(rule.get("condition", ""))[:256],
                    "provenance": (
                        provenance.model_dump()
                        if (provenance := engine.rule_provenance(rule.get("name")))
                        else None
                    ),
                }
            )
    return {
        "name": str(document.get("name", ""))[:128],
        "version": str(document.get("version", ""))[:32],
        "agent": str(document.get("agent", ""))[:128],
        "default_action": str(document.get("default_action", ""))[:32],
        "digest": engine.policy_digest,
        "rules": safe_rules,
    }


def _evidence_summary() -> dict[str, Any]:
    document = _load_yaml_object(_EVIDENCE_PATH)
    controls = document.get("controls", [])
    safe_controls = []
    status_counts: dict[str, int] = {}
    if isinstance(controls, list):
        for control in controls:
            if not isinstance(control, dict):
                continue
            status = str(control.get("status", "gap"))[:32]
            status_counts[status] = status_counts.get(status, 0) + 1
            evidence = control.get("evidence", [])
            safe_controls.append(
                {
                    "id": str(control.get("id", ""))[:16],
                    "title": str(control.get("title", ""))[:128],
                    "status": status,
                    "evidence": [
                        str(item)[:160]
                        for item in evidence
                        if isinstance(item, str)
                    ][:8],
                    "limitation": (
                        str(control.get("limitation", ""))[:256] or None
                    ),
                }
            )
    return {
        "framework": str(document.get("framework", ""))[:128],
        "assessment": str(document.get("assessment", ""))[:128],
        "status_counts": status_counts,
        "controls": safe_controls,
        "certification": False,
    }


def build_governance_snapshot(
    engine: GovernanceEngine,
    *,
    source: str,
    circuits: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return a privacy-safe, bounded process snapshot."""
    sandbox = SandboxGuard(engine.settings)
    return {
        "schema": "ai-governance-observability/v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source": source,
        "status": "ready" if engine.ready and sandbox.ready else "not_ready",
        "events": governance_events.snapshot(),
        "policy": _policy_summary(engine),
        "runtime": {
            "enforcement": (
                "enabled" if engine.settings.enabled else "disabled_for_test"
            ),
            "environment": engine.settings.environment,
            "circuits": circuits or {},
            "sandbox": {
                "provider": sandbox.provider_kind,
                "status": (
                    "not_required_for_read_only"
                    if sandbox.provider_kind == "none"
                    else ("ready" if sandbox.ready else "not_ready")
                ),
            },
        },
        "evidence": _evidence_summary(),
        "privacy": {
            "retention": "process-memory-only",
            "raw_prompts": False,
            "raw_arguments": False,
            "raw_results": False,
            "member_data": False,
            "raw_identity_claims": False,
        },
    }


def merge_governance_snapshots(
    chat_snapshot: dict[str, Any],
    mcp_snapshot: dict[str, Any] | None,
    *,
    mcp_error: str | None = None,
) -> dict[str, Any]:
    """Merge known bounded fields from two process snapshots."""
    merged = dict(chat_snapshot)
    local_event_data = chat_snapshot.get("events", {})
    local_events = _validated_events(local_event_data)
    remote_events: list[GovernanceEvent] = []
    remote_event_data: dict[str, Any] = {}
    mcp_status = "unavailable"

    if (
        isinstance(mcp_snapshot, dict)
        and mcp_snapshot.get("schema") == "ai-governance-observability/v1"
    ):
        remote_event_data = _event_data(mcp_snapshot)
        remote_events = _validated_events(remote_event_data)
        mcp_status = str(mcp_snapshot.get("status", "unknown"))[:32]

    all_events = sorted(
        [*local_events, *remote_events],
        key=lambda event: event.occurred_at,
        reverse=True,
    )[:100]
    local_counts = _counts(local_event_data)
    remote_counts = _counts(remote_event_data)
    count_keys = set(local_counts) | set(remote_counts)
    counts = {
        key: local_counts.get(key, 0) + remote_counts.get(key, 0)
        for key in sorted(count_keys)
    }
    merged["events"] = {
        "total": _safe_int(local_event_data.get("total"))
        + _safe_int(remote_event_data.get("total")),
        "counts": counts,
        "retained": len(local_events) + len(remote_events),
        "retained_limit": 400,
        "recent_events": [
            event.model_dump(mode="json") for event in all_events
        ],
    }
    merged["services"] = [
        {
            "name": "chat",
            "status": str(chat_snapshot.get("status", "unknown"))[:32],
        },
        {
            "name": "mcp",
            "status": mcp_status,
            "detail": mcp_error[:160] if mcp_error else None,
        },
    ]
    merged["status"] = (
        "ready"
        if all(service["status"] == "ready" for service in merged["services"])
        else "partial"
    )
    return merged


def _event_data(snapshot: dict[str, Any]) -> dict[str, Any]:
    value = snapshot.get("events")
    return value if isinstance(value, dict) else {}


def _validated_events(event_data: object) -> list[GovernanceEvent]:
    if not isinstance(event_data, dict):
        return []
    events = event_data.get("recent_events", [])
    if not isinstance(events, list):
        return []
    validated: list[GovernanceEvent] = []
    for event in events[:200]:
        try:
            validated.append(GovernanceEvent.model_validate(event))
        except (TypeError, ValueError):
            continue
    return validated


def _safe_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return min(max(value, 0), 1_000_000_000)


def _counts(event_data: object) -> dict[str, int]:
    if not isinstance(event_data, dict):
        return {}
    values = event_data.get("counts", {})
    if not isinstance(values, dict):
        return {}
    allowed = {
        "allow",
        "deny",
        "require_approval",
        "warn",
        "log",
        "transform",
        "escalate",
    }
    return {
        key: _safe_int(value)
        for key, value in values.items()
        if key in allowed
    }
