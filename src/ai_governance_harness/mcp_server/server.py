"""MCP protocol adapter for the synthetic superannuation data gateway."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from mcp.server import MCPServer
from mcp.server.mcpserver.tools.base import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field
from typing_extensions import Annotated

from ai_governance_harness.mcp_server import tools as gateway_tools
from ai_governance_harness.mcp_server.telemetry import (
    emit_audit_event,
    tool_call_counter,
    tool_duration,
    tracer,
)

logger = logging.getLogger(__name__)

ResultT = TypeVar("ResultT", bound=dict[str, Any])
MemberId = Annotated[str, Field(pattern=r"^MEM-\d{3}$", min_length=7, max_length=7)]

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

mcp = MCPServer(
    name="ai-governance-harness",
    description="Read-only synthetic superannuation governance tools.",
    instructions=(
        "Use these tools only for synthetic in-fund data. Raw tool results are factual "
        "and are not financial advice."
    ),
)


def _call_gateway(tool_name: str, operation: Callable[[], ResultT]) -> ResultT:
    started_at = time.perf_counter()
    outcome = "success"
    error_category: str | None = None
    with tracer.start_as_current_span(f"mcp.tool.{tool_name}") as span:
        span.set_attribute("mcp.tool.name", tool_name)
        try:
            result = dict(operation())
        except gateway_tools.MemberNotFoundError as exc:
            outcome = "not_found"
            error_category = "member_not_found"
            raise ToolError("Requested member was not found.") from exc
        except Exception as exc:
            outcome = "error"
            error_category = "gateway_failure"
            logger.error(
                "MCP gateway operation failed",
                extra={
                    "tool_name": tool_name,
                    "error_category": error_category,
                },
            )
            raise ToolError("The tool could not complete the request.") from exc
        finally:
            elapsed = time.perf_counter() - started_at
            attributes = {"mcp.tool.name": tool_name, "outcome": outcome}
            tool_call_counter.add(1, attributes)
            tool_duration.record(elapsed, attributes)
            emit_audit_event(
                "mcp.tool.call",
                outcome=outcome,
                tool_name=tool_name,
                error_category=error_category,
                latency_ms=elapsed * 1000,
            )

    result.setdefault(
        "provenance",
        {
            "source": "internal_superannuation_core",
            "scope": "synthetic_in_fund_data",
            "synthetic": True,
        },
    )
    return result


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_member_profile(member_id: MemberId) -> dict[str, Any]:
    """Return a synthetic member's internal superannuation profile.

    Args:
        member_id: Synthetic identifier in the form `MEM-001`.
    """
    return _call_gateway(
        "get_member_profile",
        lambda: gateway_tools.get_member_profile(member_id),
    )


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_member_disengagement_signals(member_id: MemberId) -> dict[str, Any]:
    """Return factual disengagement and churn signals for a synthetic member.

    Args:
        member_id: Synthetic identifier in the form `MEM-001`.
    """
    return _call_gateway(
        "get_member_disengagement_signals",
        lambda: gateway_tools.get_member_disengagement_signals(member_id),
    )


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_cohort_churn_analytics() -> dict[str, Any]:
    """Return aggregate synthetic cohort churn analytics."""
    return _call_gateway(
        "get_cohort_churn_analytics",
        gateway_tools.get_cohort_churn_analytics,
    )


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_fum_outflow_summary() -> dict[str, Any]:
    """Return aggregate synthetic funds-under-management outflow risk."""
    return _call_gateway(
        "get_fum_outflow_summary",
        gateway_tools.get_fum_outflow_summary,
    )
