"""Privacy-safe telemetry for MCP requests and tool calls."""

from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics, trace
from opentelemetry.sdk.resources import Resource

from ai_governance_harness.mcp_server.config import ServerSettings

SERVICE_NAME = "ai-governance-harness-mcp"
SERVICE_VERSION = "0.1.0"

correlation_id_context: ContextVar[str | None] = ContextVar(
    "mcp_correlation_id",
    default=None,
)

tracer = trace.get_tracer(SERVICE_NAME, SERVICE_VERSION)
meter = metrics.get_meter(SERVICE_NAME, SERVICE_VERSION)
tool_call_counter = meter.create_counter(
    "mcp.tool.call.count",
    unit="1",
    description="Count of MCP tool calls.",
)
tool_duration = meter.create_histogram(
    "mcp.tool.call.duration",
    unit="s",
    description="MCP tool call duration.",
)
http_request_counter = meter.create_counter(
    "mcp.http.request.count",
    unit="1",
    description="Count of MCP HTTP requests.",
)
http_request_duration = meter.create_histogram(
    "http.server.request.duration",
    unit="s",
    description="Inbound HTTP request duration.",
)

_ALLOWED_EVENT_ATTRIBUTES = {
    "authentication_outcome",
    "correlation_id",
    "decision_rule",
    "deployment_revision",
    "enforcement_mode",
    "error_category",
    "event_name",
    "governance_decision",
    "governance_point",
    "latency_ms",
    "outcome",
    "policy_digest",
    "policy_name",
    "tool_name",
}


class PrivacySafeJsonFormatter(logging.Formatter):
    """Render structured logs with an explicit low-cardinality allowlist."""

    def __init__(self, environment: str, revision: str) -> None:
        super().__init__()
        self._environment = environment
        self._revision = revision

    def format(self, record: logging.LogRecord) -> str:
        attributes = {
            key: getattr(record, key)
            for key in _ALLOWED_EVENT_ATTRIBUTES
            if hasattr(record, key)
        }
        attributes.setdefault("deployment_revision", self._revision)
        correlation_id = correlation_id_context.get()
        if correlation_id:
            attributes.setdefault("correlation_id", correlation_id)

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity_text": record.levelname,
            "severity_number": record.levelno,
            "body": record.getMessage(),
            "attributes": attributes,
            "resource": {
                "service.name": SERVICE_NAME,
                "service.version": SERVICE_VERSION,
                "deployment.environment": self._environment,
            },
        }
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if span_context.is_valid:
            payload["trace_id"] = f"{span_context.trace_id:032x}"
            payload["span_id"] = f"{span_context.span_id:016x}"
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_azure_export(
    *,
    service_name: str,
    environment: str,
    region: str | None = None,
    manual_only: bool = False,
) -> None:
    """Export existing instruments when an Insights connection is configured.

    Manual-only export avoids automatically instrumenting model and HTTP clients
    in the chat process. It exports explicit spans and metrics, not root logs.
    """
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string:
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": SERVICE_VERSION,
                "deployment.environment": environment,
                "cloud.region": region or "local",
            }
        )
        configure_azure_monitor(
            connection_string=connection_string,
            resource=resource,
            logger_name=service_name,
            instrumentation_options=(
                {
                    name: {"enabled": False}
                    for name in (
                        "azure_sdk", "django", "fastapi", "flask", "httpx",
                        "httpx2", "psycopg2", "requests", "urllib", "urllib3",
                    )
                }
                if manual_only
                else {}
            ),
            **(
                {"disable_logging": True, "enable_live_metrics": False}
                if manual_only
                else {}
            ),
        )


def configure_telemetry(settings: ServerSettings) -> None:
    """Configure structured logs and optional Azure Monitor export."""
    configure_azure_export(
        service_name=SERVICE_NAME,
        environment=settings.environment,
        region=settings.region,
    )

    handler = logging.StreamHandler()
    if settings.transport == "streamable-http":
        handler.setFormatter(
            PrivacySafeJsonFormatter(
                settings.environment,
                settings.deployment_revision,
            )
        )
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def emit_audit_event(
    event_name: str,
    *,
    outcome: str,
    settings: ServerSettings | None = None,
    tool_name: str | None = None,
    error_category: str | None = None,
    latency_ms: float | None = None,
    authentication_outcome: str | None = None,
) -> None:
    """Emit one allowlisted audit event without request or response payloads."""
    attributes: dict[str, Any] = {
        "event_name": event_name,
        "outcome": outcome,
    }
    if settings:
        attributes["deployment_revision"] = settings.deployment_revision
    if tool_name:
        attributes["tool_name"] = tool_name
    if error_category:
        attributes["error_category"] = error_category
    if latency_ms is not None:
        attributes["latency_ms"] = round(latency_ms, 2)
    if authentication_outcome:
        attributes["authentication_outcome"] = authentication_outcome

    logging.getLogger(SERVICE_NAME).info(event_name, extra=attributes)
