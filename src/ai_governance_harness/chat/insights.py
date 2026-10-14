"""Read bounded, metadata-only Application Insights history for local operators."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import ssl
import time
from datetime import UTC, datetime
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

import anyio
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import AzureCliCredential
from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)
ROLES = ("ai-governance-harness-chat", "ai-governance-harness-mcp")
EVENTS = ("mcp.startup", "mcp.readiness", "mcp.tool.call", "governance.policy.decision")
SPAN_NAMES = (
    "evaluate.governance.policy", "http.server.request",
    "mcp.tool.get_member_profile", "mcp.tool.get_member_disengagement_signals",
    "mcp.tool.get_cohort_churn_analytics", "mcp.tool.get_fum_outflow_summary",
    "mcp.tool.prepare_member_outreach_case",
)
# GenAI and MCP semantic-convention span names embed a model or tool name.
GENAI_SPAN_PATTERN = (
    r"^(?:chat|execute_tool|invoke_agent|tools/call|MCP send tools/call) [A-Za-z0-9._-]{1,64}$"
)
# Rule and policy names come from bounded policy configuration.
RULE_PATTERN = r"^[A-Za-z0-9._-]{1,64}$"
TOKEN_METRIC_NAMES = (
    "gen_ai.client.inference.usage.input_tokens",
    "gen_ai.client.inference.usage.output_tokens",
)
METRIC_NAMES = (
    "governance.policy.decision.count", "governance.policy.evaluation.duration",
    "mcp.tool.call.count", "gen_ai.client.inference.usage.input_tokens",
    "gen_ai.client.inference.usage.output_tokens",
)

# Hourly 24h windows add up to ~150 decision buckets and ~50 usage buckets.
MAX_ROWS = 600


def is_known_span(name: str) -> bool:
    """Accept fixed application spans and bounded GenAI semconv span names."""
    return name in SPAN_NAMES or re.fullmatch(GENAI_SPAN_PATTERN, name) is not None


class InsightsUnavailableError(RuntimeError):
    """A sanitized failure suitable for the local UI."""


class HistoryRow(BaseModel):
    """Only allow known metadata fields from a fixed Azure query."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["metric", "span", "log", "rule", "usage"]
    service: Literal["ai-governance-harness-chat", "ai-governance-harness-mcp"]
    name: str = Field(max_length=100)
    timestamp: datetime | None = None
    duration_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    outcome: str = Field(default="", max_length=24, pattern=r"^[a-z_]*$")
    operation_id: str = Field(default="", pattern=r"^(?:[a-fA-F0-9]{32})?$")
    span_id: str = Field(default="", pattern=r"^(?:[a-fA-F0-9]{16}|[a-fA-F0-9]{32})?$")
    parent_id: str = Field(default="", pattern=r"^(?:[a-fA-F0-9]{16}|[a-fA-F0-9]{32})?$")
    total: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    samples: int | None = Field(default=None, ge=0)
    stage: str = Field(default="", max_length=24, pattern=r"^[a-z_]*$")
    policy: str = Field(default="", max_length=64, pattern=r"^[A-Za-z0-9._-]*$")
    rule: str = Field(default="", max_length=64, pattern=r"^[A-Za-z0-9._-]*$")
    model: str = Field(default="", max_length=64, pattern=r"^[A-Za-z0-9._-]*$")
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)


def history_query(hours: int) -> str:
    """Build one fixed query with a validated time window and no caller KQL."""
    if hours not in (1, 4, 24):
        raise ValueError("History range must be 1, 4, or 24 hours.")
    roles = json.dumps(ROLES)
    names = json.dumps(SPAN_NAMES)
    metric_names = json.dumps(METRIC_NAMES)
    token_names = json.dumps(TOKEN_METRIC_NAMES)
    events = json.dumps(EVENTS)
    bucket = {1: "5m", 4: "15m", 24: "1h"}[hours]
    return f"""
let metrics = customMetrics
| where timestamp > ago({hours}h) and cloud_RoleName in (dynamic({roles}))
| where name in (dynamic({metric_names}))
| extend outcome=tostring(customDimensions["governance.decision"])
| extend outcome=iff(outcome in ("allow", "deny", "require_approval"), outcome, "")
| extend bucket=iff(name == "governance.policy.decision.count", bin(timestamp, {bucket}), datetime(null))
| summarize total=sum(valueSum), samples=sum(valueCount) by service=cloud_RoleName, name, outcome, timestamp=bucket
| project ['kind']="metric", service, name, outcome, total, samples, timestamp;
let rules = customMetrics
| where timestamp > ago({hours}h) and cloud_RoleName in (dynamic({roles}))
| where name == "governance.policy.decision.count"
| extend rule=tostring(customDimensions["governance.rule.name"]), policy=tostring(customDimensions["governance.policy.name"])
| extend stage=tostring(customDimensions["governance.lifecycle.point"]), outcome=tostring(customDimensions["governance.decision"])
| where rule matches regex @"{RULE_PATTERN}" and outcome in ("allow", "deny", "require_approval")
| extend policy=iff(policy matches regex @"{RULE_PATTERN}", policy, ""), stage=iff(stage matches regex @"^[a-z_]{{1,24}}$", stage, "")
| summarize total=sum(valueSum), timestamp=max(timestamp) by service=cloud_RoleName, name=rule, policy, stage, outcome
| top 40 by total desc
| project ['kind']="rule", service, name, policy, stage, outcome, total, timestamp;
let usage = customMetrics
| where timestamp > ago({hours}h) and cloud_RoleName in (dynamic({roles}))
| where name in (dynamic({token_names}))
| extend model=tostring(customDimensions["gen_ai.response.model"])
| extend model=iff(model == "", tostring(customDimensions["gen_ai.request.model"]), model)
| extend model=iff(model matches regex @"{RULE_PATTERN}", model, "")
| summarize total=sum(valueSum), samples=sum(valueCount) by service=cloud_RoleName, name, model, timestamp=bin(timestamp, {bucket})
| project ['kind']="usage", service, name, model, total, samples, timestamp;
let candidate_spans = union requests, dependencies
| where timestamp > ago({hours}h) and cloud_RoleName in (dynamic({roles}))
| where name in (dynamic({names})) or name matches regex @"{GENAI_SPAN_PATTERN}";
// HTTP probes are frequent, so cap them separately to keep governance and GenAI spans visible.
let spans = union
(candidate_spans | where name != "http.server.request" | top 100 by timestamp desc),
(candidate_spans | where name == "http.server.request" | top 25 by timestamp desc)
| extend decision=tostring(customDimensions["governance.decision"])
| extend rule=tostring(customDimensions["governance.rule.name"]), stage=tostring(customDimensions["governance.lifecycle.point"])
| extend rule=iff(rule matches regex @"{RULE_PATTERN}", rule, ""), stage=iff(stage matches regex @"^[a-z_]{{1,24}}$", stage, "")
| extend model=tostring(customDimensions["gen_ai.response.model"])
| extend model=iff(model matches regex @"{RULE_PATTERN}", model, "")
| extend input_tokens=toint(customDimensions["gen_ai.usage.input_tokens"]), output_tokens=toint(customDimensions["gen_ai.usage.output_tokens"])
| extend cached_tokens=toint(customDimensions["gen_ai.usage.cache_read.input_tokens"]), reasoning_tokens=toint(customDimensions["gen_ai.usage.reasoning.output_tokens"])
| project ['kind']="span", service=cloud_RoleName, name, timestamp, rule, stage, model,
input_tokens, output_tokens, cached_tokens, reasoning_tokens,
duration_ms=todouble(duration), outcome=case(name == "evaluate.governance.policy" and decision in ("allow", "deny", "require_approval"), decision, success == true, "success", success == false, "failure", "unknown"),
operation_id=operation_Id, span_id=id, parent_id=operation_ParentId;
let logs = traces
| where timestamp > ago({hours}h) and cloud_RoleName in (dynamic({roles}))
| extend event=tostring(customDimensions["event_name"])
| extend event=iff(event in (dynamic({events})), event, iff(message in (dynamic({events})), message, ""))
| where event != ""
| top 50 by timestamp desc
| project ['kind']="log", service=cloud_RoleName, name=event, timestamp,
outcome=case(severityLevel >= 3, "error", severityLevel == 2, "warning", "info"),
operation_id=operation_Id;
union metrics, rules, usage, spans, logs
"""


def read_history(app_id: UUID, hours: int) -> list[HistoryRow]:
    """Query Azure using local CLI identity, verified TLS, and bounded results."""
    try:
        context = ssl.create_default_context(cafile=os.getenv("REQUESTS_CA_BUNDLE") or None)
        with AzureCliCredential(process_timeout=10) as credential:
            token = credential.get_token("https://api.applicationinsights.io/.default")
            request = Request(
                f"https://api.applicationinsights.io/v1/apps/{app_id}/query",
                data=json.dumps({"query": history_query(hours)}).encode(),
                headers={
                    "Authorization": f"Bearer {token.token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(request, context=context, timeout=15) as response:
                payload = response.read(1_048_577)
        if len(payload) > 1_048_576:
            raise InsightsUnavailableError("Azure history exceeded the safe response limit.")
        document = json.loads(payload)
        if not isinstance(document, dict) or document.get("error") or document.get("partialError"):
            raise InsightsUnavailableError("Azure returned incomplete history. Retry later.")
        tables = document.get("tables")
        if not isinstance(tables, list) or len(tables) != 1:
            raise InsightsUnavailableError("Azure returned an unexpected history response.")
        table = tables[0]
        columns = [column["name"] for column in table["columns"]]
        if len(columns) != len(set(columns)) or not set(columns) <= HistoryRow.model_fields.keys():
            raise InsightsUnavailableError("Azure returned unexpected history fields.")
        if len(table["rows"]) > MAX_ROWS:
            raise InsightsUnavailableError("Azure returned too many history rows.")
        result = []
        for cells in table["rows"]:
            if len(cells) != len(columns):
                raise InsightsUnavailableError("Azure returned invalid history rows.")
            row = HistoryRow.model_validate({
                key: value for key, value in zip(columns, cells) if value is not None
            })
            if row.kind == "span":
                known = is_known_span(row.name)
            elif row.kind == "usage":
                known = row.name in TOKEN_METRIC_NAMES
            elif row.kind == "rule":
                known = re.fullmatch(RULE_PATTERN, row.name) is not None
            else:
                known = row.name in (METRIC_NAMES if row.kind == "metric" else EVENTS)
            if not known:
                raise InsightsUnavailableError("Azure returned unexpected history names.")
            result.append(row)
        return result
    except ClientAuthenticationError as exc:
        raise InsightsUnavailableError("Azure sign-in failed. Run az login with telemetry read access.") from exc
    except HTTPError as exc:
        message = (
            "Azure denied history access. Check Application Insights read permissions."
            if exc.code in (401, 403)
            else "Azure history query failed. Check the application ID and retry later."
        )
        raise InsightsUnavailableError(message) from exc
    except (URLError, TimeoutError, ssl.SSLError) as exc:
        raise InsightsUnavailableError("Azure could not be reached. Check network and approved CA configuration.") from exc
    except OSError as exc:
        raise InsightsUnavailableError("Azure history network or CA configuration is unavailable.") from exc
    except (ValueError, KeyError, TypeError, ValidationError) as exc:
        raise InsightsUnavailableError("Azure returned invalid history metadata.") from exc


class InsightsHistory:
    """Cache up to three fixed windows for 60 seconds; never cache failures."""

    def __init__(self, app_id: UUID | None) -> None:
        self._app_id = app_id
        self._cache: dict[int, tuple[float, dict[str, object]]] = {}
        self._lock = asyncio.Lock()

    async def snapshot(self, hours: int) -> dict[str, object]:
        """Return sanitized history with explicit fetch time and cache status."""
        if self._app_id is None:
            raise InsightsUnavailableError("Set APPLICATIONINSIGHTS_APP_ID and restart to enable Azure history.")
        history_query(hours)
        async with self._lock:
            cached = self._cache.get(hours)
            if cached and time.monotonic() - cached[0] < 60:
                return {**cached[1], "cached": True}
            try:
                rows = await anyio.to_thread.run_sync(read_history, self._app_id, hours)
            except InsightsUnavailableError:
                logger.warning("Application Insights history query failed.")
                raise
            snapshot: dict[str, object] = {
                "hours": hours,
                "fetched_at": datetime.now(UTC).isoformat(),
                "cached": False,
                "rows": [row.model_dump(mode="json") for row in rows],
            }
            self._cache[hours] = (time.monotonic(), snapshot)
            return snapshot
