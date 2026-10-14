"""MCP protocol adapter for the synthetic superannuation data gateway."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from mcp.server import MCPServer
from mcp.server.elicitation import ElicitationResult
from mcp.server.mcpserver.resolve import Elicit, Resolve
from mcp.server.mcpserver.tools.base import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from typing_extensions import Annotated

from ai_governance_harness.governance import (
    GovernanceDeniedError,
    LifecyclePoint,
    get_governance_engine,
)
from ai_governance_harness.guardrails.advice_filter import tool_response_policy_data
from ai_governance_harness.mcp_server import tools as gateway_tools
from ai_governance_harness.mcp_server.tool_contracts import build_tool_metadata
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

APPROVAL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)


class OutreachCaseApproval(BaseModel):
    """Primitive form returned by an MCP elicitation-capable client."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    approved: StrictBool = Field(
        description=(
            "Select true to approve preparing a read-only synthetic member "
            "outreach case. No external contact will occur."
        )
    )


mcp = MCPServer(
    name="ai-governance-harness",
    description=(
        "Read-only synthetic superannuation governance tools with optional "
        "form-based human approval."
    ),
    instructions=(
        "Use these tools only for synthetic in-fund data. Raw tool results are factual "
        "and are not financial advice. The prepare_member_outreach_case tool requires "
        "MCP form elicitation and never performs external contact."
    ),
)


def _call_gateway(tool_name: str, operation: Callable[[], ResultT]) -> ResultT:
    started_at = time.perf_counter()
    outcome = "success"
    error_category: str | None = None
    with tracer.start_as_current_span(f"mcp.tool.{tool_name}") as span:
        span.set_attribute("mcp.tool.name", tool_name)
        span.set_attribute("gen_ai.tool.name", tool_name)
        try:
            result = dict(operation())
            result.setdefault(
                "provenance",
                {
                    "source": "internal_superannuation_core",
                    "scope": "synthetic_in_fund_data",
                    "synthetic": True,
                },
            )
            get_governance_engine().require_allowed(
                LifecyclePoint.POST_TOOL,
                tool_name,
                policy_data=tool_response_policy_data(result),
                source="mcp",
            )
        except GovernanceDeniedError as exc:
            outcome = "denied"
            error_category = "governance_denied"
            raise ToolError("Governance denied the tool response.") from exc
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

    return result


def _check_outreach_eligibility(member_id: str) -> None:
    try:
        gateway_tools.require_member_outreach_eligible(member_id)
    except GovernanceDeniedError as exc:
        emit_audit_event(
            "mcp.retention.eligibility",
            outcome="denied",
            tool_name="prepare_member_outreach_case",
        )
        review = gateway_tools.get_default_gateway().retention_review(member_id)
        raise ToolError(review.staff_message()) from exc
    except gateway_tools.MemberNotFoundError as exc:
        raise ToolError("Requested member was not found.") from exc


def _resolve_outreach_approval(member_id: str) -> Elicit[OutreachCaseApproval]:
    _check_outreach_eligibility(member_id)
    return Elicit(
        message=(
            f"Approve preparation of a read-only synthetic outreach case for {member_id}. "
            "The result may include synthetic disengagement signals, but no "
            "message, notification, or other external action will be executed."
        ),
        schema=OutreachCaseApproval,
    )


@mcp.tool(
    annotations=READ_ONLY_ANNOTATIONS,
    title="Get member profile",
    description=(
        "Retrieve factual synthetic member profile and account information when "
        "the user asks to view member details, balance, phase, risk profile, "
        "communication preference, or investment allocation. Do not use this "
        "tool to prepare or open a retention outreach case; use "
        "prepare_member_outreach_case instead."
    ),
    meta=build_tool_metadata(
        intent="member_profile",
        browser_chat_enabled=True,
    ),
)
def get_member_profile(member_id: MemberId) -> dict[str, Any]:
    """Return a synthetic member's internal superannuation profile.

    Args:
        member_id: Synthetic identifier in the form `MEM-001`.
    """
    return _call_gateway(
        "get_member_profile",
        lambda: gateway_tools.get_member_profile(member_id),
    )


@mcp.tool(
    annotations=READ_ONLY_ANNOTATIONS,
    title="Get member disengagement signals",
    description=(
        "Retrieve factual synthetic disengagement and churn signals for one "
        "member. Use this for signal analysis only; it does not prepare an "
        "outreach case or contact the member."
    ),
    meta=build_tool_metadata(
        intent="member_disengagement_signals",
        browser_chat_enabled=False,
    ),
)
def get_member_disengagement_signals(member_id: MemberId) -> dict[str, Any]:
    """Return factual disengagement and churn signals for a synthetic member.

    Args:
        member_id: Synthetic identifier in the form `MEM-001`.
    """
    return _call_gateway(
        "get_member_disengagement_signals",
        lambda: gateway_tools.get_member_disengagement_signals(member_id),
    )


@mcp.tool(
    annotations=READ_ONLY_ANNOTATIONS,
    title="Get cohort churn analytics",
    description=(
        "Retrieve aggregate synthetic churn analytics across member cohorts. "
        "Use this for cohort-level analysis, not individual member profiles or "
        "retention outreach cases."
    ),
    meta=build_tool_metadata(
        intent="cohort_churn_analytics",
        browser_chat_enabled=False,
    ),
)
def get_cohort_churn_analytics() -> dict[str, Any]:
    """Return aggregate synthetic cohort churn analytics."""
    return _call_gateway(
        "get_cohort_churn_analytics",
        gateway_tools.get_cohort_churn_analytics,
    )


@mcp.tool(
    annotations=READ_ONLY_ANNOTATIONS,
    title="Get FUM outflow summary",
    description=(
        "Retrieve an aggregate synthetic funds-under-management outflow-risk "
        "summary. Use this for portfolio-level outflow analysis, not individual "
        "member profiles or retention outreach cases."
    ),
    meta=build_tool_metadata(
        intent="fum_outflow_summary",
        browser_chat_enabled=False,
    ),
)
def get_fum_outflow_summary() -> dict[str, Any]:
    """Return aggregate synthetic funds-under-management outflow risk."""
    return _call_gateway(
        "get_fum_outflow_summary",
        gateway_tools.get_fum_outflow_summary,
    )


@mcp.tool(
    annotations=APPROVAL_ANNOTATIONS,
    title="Prepare member retention outreach case",
    description=(
        "Use this tool when the user asks to prepare, open, create, or start a "
        "retention outreach case for a synthetic member. It checks eligibility "
        "and requires explicit human approval before preparing a read-only "
        "result. Do not substitute a profile response for an outreach-case "
        "request. It never persists a case or contacts the member."
    ),
    meta=build_tool_metadata(
        intent="retention_outreach_case",
        browser_chat_enabled=True,
        requires_approval=True,
    ),
)
def prepare_member_outreach_case(
    member_id: MemberId,
    approval: Annotated[
        ElicitationResult[OutreachCaseApproval],
        Resolve(_resolve_outreach_approval),
    ],
) -> dict[str, Any]:
    """Prepare an eligible synthetic outreach case after MCP form approval.

    Existing cases and specialist restrictions are checked before approval and
    rechecked before preparation. Referrals are staff-facing instructions only.
    This tool never persists a case, sends a message or performs external contact.

    Args:
        member_id: Synthetic identifier in the form `MEM-001`.
    """
    _check_outreach_eligibility(member_id)
    if approval.action == "decline":
        emit_audit_event(
            "mcp.elicitation",
            outcome="declined",
            tool_name="prepare_member_outreach_case",
        )
        raise ToolError("Approval was declined. No operation was executed.")
    if approval.action == "cancel":
        emit_audit_event(
            "mcp.elicitation",
            outcome="cancelled",
            tool_name="prepare_member_outreach_case",
        )
        raise ToolError("Approval was cancelled. No operation was executed.")
    if not approval.data.approved:
        emit_audit_event(
            "mcp.elicitation",
            outcome="not_approved",
            tool_name="prepare_member_outreach_case",
        )
        raise ToolError("Explicit approval is required. No operation was executed.")

    emit_audit_event(
        "mcp.elicitation",
        outcome="approved",
        tool_name="prepare_member_outreach_case",
    )

    def build_case() -> dict[str, Any]:
        signals = gateway_tools.get_member_disengagement_signals(member_id)
        result = {
            "member_id": member_id,
            "approval": {
                "status": "approved",
                "mechanism": "mcp_form_elicitation",
            },
            "external_action_executed": False,
            "case_persisted": False,
            "disengagement_signals": signals,
        }
        return result

    return _call_gateway("prepare_member_outreach_case", build_case)
