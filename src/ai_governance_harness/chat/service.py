"""Foundry chat orchestration that executes tools only through MCP."""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlsplit, urlunsplit
from typing import Any, Literal, Protocol

import anyio
import httpx
import httpx2
from mcp.client.streamable_http import streamable_http_client
from mcp import Client, types
from openai import APIStatusError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from ai_governance_harness.chat import genai_telemetry
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.foundry_client import get_azure_credential, get_foundry_client
from ai_governance_harness.errors import ChatServiceError
from ai_governance_harness.errors import ChatErrorCode as ChatErrorCode
from ai_governance_harness.identity.sidecar import AgentAuth, CallerIdentity, SidecarClient
from ai_governance_harness.governance import (
    GovernanceDeniedError,
    LifecyclePoint,
    get_governance_engine,
)
from ai_governance_harness.governance.reliability import ReliabilityGuard
from ai_governance_harness.governance.retention import RetentionReview
from ai_governance_harness.governance.snapshot import (
    build_governance_snapshot,
    merge_governance_snapshots,
)
from ai_governance_harness.guardrails.advice_filter import (
    AdviceClassificationGuardrail,
    WholeOfWealthInvariantGuardrail,
    tool_response_policy_data,
)
from ai_governance_harness.guardrails.advice_classifier import (
    AdviceClassificationFailure,
    AdviceRequestClassification,
    FoundryAdviceRequestClassifier,
    classification_failure_policy_data,
)
from ai_governance_harness.mcp_server.tool_contracts import (
    browser_chat_enabled,
)

SYSTEM_INSTRUCTIONS = (
    "You are an internal assistant for business analysts working only with "
    "synthetic in-fund superannuation data. Use the available tools for cohort "
    "risk, FUM summaries and member disengagement signals when requested. "
    "Governance enforces the caller's role; never bypass a denied tool. "
    "Use get_member_profile for factual "
    "member and account-profile requests. Use prepare_member_outreach_case when "
    "the user asks to prepare, open, create, or start a retention outreach case; "
    "that workflow checks eligibility and requires explicit human approval. Do "
    "not substitute a profile response for an outreach-case request. Never "
    "invent tool results. If asked for contact details, use the profile's "
    "communication preference and state that no email address or phone number "
    "is recorded. For unsupported customer information, explain the supported "
    "member, aggregate and retention-outreach capabilities. Do not give personal "
    "financial advice, recommend actions for a member, or claim visibility into "
    "external assets. Keep responses concise."
)

logger = logging.getLogger(__name__)
_SAFE_ERROR_VALUE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_EMPTY_RESPONSE_RECOVERY_INSTRUCTION = (
    "The previous model response was empty. Answer the user's request using the "
    "available conversation and tool results. Return a concise text response."
)
_OUTREACH_APPROVAL_HEADING = "Approval required for "
_APPROVE_RESPONSES = frozenset(
    {"approve", "approved", "yes", "yes approve", "yes, approve"}
)
_DECLINE_RESPONSES = frozenset(
    {"cancel", "decline", "declined", "do not approve", "no"}
)

SCOPE_REFUSAL_PREFIX = "Sorry, I can't assist with this request"
SCOPE_REFUSAL_MESSAGE = (
    "Sorry, I can’t assist with this request. I can provide factual synthetic "
    "member profile information or help prepare an eligible read-only retention "
    "outreach case with explicit approval."
)

PROFILE_FIELDS = (
    "member_id",
    "full_name",
    "tenure_years",
    "risk_profile",
    "communication_preference",
    "account",
    "provenance",
)


def _is_scope_refusal(message: str) -> bool:
    """Detect the fixed out-of-scope refusal, tolerating typographic apostrophes."""
    normalized = message.replace("\u2019", "'").strip()
    return normalized.startswith(SCOPE_REFUSAL_PREFIX)


def _tool_enabled_for_browser_chat(tool: Any) -> bool:
    """Fail closed unless MCP metadata explicitly enables the tool."""
    return browser_chat_enabled(getattr(tool, "meta", None))


def _restrict_tool_payload(tool_name: str, payload: Any) -> Any:
    """Reduce a member profile to permitted fields before the model sees it."""
    if tool_name != "get_member_profile" or not isinstance(payload, dict):
        return payload
    return {key: payload[key] for key in PROFILE_FIELDS if key in payload}


def _governance_error_details(error: GovernanceDeniedError) -> dict[str, str]:
    """Return bounded policy metadata that is safe for a public error response."""
    decision = error.decision
    values = {
        "action": error.action,
        "lifecycle_point": (
            decision.lifecycle_point.value if decision is not None else None
        ),
        "decision": decision.action if decision is not None else None,
        "policy_name": decision.policy_name if decision is not None else None,
        "matched_rule": decision.matched_rule if decision is not None else None,
    }
    return {
        key: value
        for key, value in values.items()
        if value is not None and _SAFE_ERROR_VALUE.fullmatch(value)
    }


def _governance_service_error(error: GovernanceDeniedError) -> ChatServiceError:
    """Convert a policy denial to the public chat-service error contract."""
    return ChatServiceError(
        "Governance policy denied the requested operation.",
        code="governance_denied",
        status_code=403,
        details=_governance_error_details(error),
    )


def _foundry_filter_service_error(
    error: BaseException,
) -> ChatServiceError | None:
    """Normalize Azure content-filter HTTP errors without exposing content."""
    body = getattr(error, "body", None)
    if not isinstance(body, dict):
        return None
    payload = body.get("error", body)
    if not isinstance(payload, dict):
        return None

    details: dict[str, str] = {}
    code = payload.get("code")
    if isinstance(code, str) and _SAFE_ERROR_VALUE.fullmatch(code):
        details["foundry_error_code"] = code
    parameter = payload.get("param")
    if isinstance(parameter, str) and _SAFE_ERROR_VALUE.fullmatch(parameter):
        details["content_filter_stage"] = parameter

    inner = payload.get("innererror", payload.get("inner_error"))
    if isinstance(inner, dict):
        inner_code = inner.get("code")
        if (
            isinstance(inner_code, str)
            and _SAFE_ERROR_VALUE.fullmatch(inner_code)
        ):
            details["foundry_inner_error_code"] = inner_code
        filter_results = inner.get(
            "content_filter_result",
            inner.get("content_filter_results"),
        )
        if isinstance(filter_results, dict):
            for category, result in filter_results.items():
                if not isinstance(result, dict):
                    continue
                if not (result.get("filtered") or result.get("detected")):
                    continue
                details["content_filter_category"] = str(category)
                severity = result.get("severity")
                if severity is not None:
                    details["content_filter_severity"] = str(severity)
                break

    recognized_codes = {
        details.get("foundry_error_code", "").lower(),
        details.get("foundry_inner_error_code", "").lower(),
    }
    if (
        "content_filter" not in recognized_codes
        and "responsibleaipolicyviolation" not in recognized_codes
        and "content_filter_category" not in details
    ):
        return None
    return ChatServiceError(
        "Azure AI Foundry blocked the model request or response under a "
        "configured content filter.",
        code="model_content_filtered",
        status_code=422,
        details=details,
    )


def _mcp_capability_service_error(
    error: BaseException,
) -> ChatServiceError | None:
    """Normalize the known MCP form-elicitation capability failure."""
    message = str(error)
    if (
        "did not declare the form elicitation capability" not in message
        or "_resolve_outreach_approval" not in message
    ):
        return None
    return ChatServiceError(
        "Preparing an outreach case requires interactive approval, but browser "
        "chat does not support MCP form elicitation.",
        code="client_capability_required",
        status_code=409,
        details={
            "required_capability": "form_elicitation",
            "tool": "prepare_member_outreach_case",
            "resolution": "use_elicitation_capable_mcp_client",
        },
    )


def _known_service_error(error: BaseException) -> ChatServiceError | None:
    """Find a known service error wrapped by an asynchronous task group."""
    if isinstance(error, ChatServiceError):
        return error
    if isinstance(error, GovernanceDeniedError):
        return _governance_service_error(error)
    foundry_filter_error = _foundry_filter_service_error(error)
    if foundry_filter_error is not None:
        return foundry_filter_error
    mcp_capability_error = _mcp_capability_service_error(error)
    if mcp_capability_error is not None:
        return mcp_capability_error
    if isinstance(error, BaseExceptionGroup):
        for nested_error in error.exceptions:
            known_error = _known_service_error(nested_error)
            if known_error is not None:
                return known_error
    return None


def _is_empty_model_content(content: str | None) -> bool:
    """Detect blank text and JSON values that contain no user-facing answer."""
    if content is None or not content.strip():
        return True
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return False
    return parsed is None or parsed == "" or parsed == {} or parsed == []


def _empty_model_response_details(
    completion: Any,
    choice: Any,
) -> dict[str, str]:
    """Return non-content diagnostics for an empty model response."""
    details: dict[str, str] = {}
    finish_reason = getattr(choice, "finish_reason", None)
    if finish_reason is not None:
        details["finish_reason"] = str(finish_reason)

    usage = getattr(completion, "usage", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    if completion_tokens is not None:
        details["completion_tokens"] = str(completion_tokens)

    token_details = getattr(usage, "completion_tokens_details", None)
    reasoning_tokens = getattr(token_details, "reasoning_tokens", None)
    if reasoning_tokens is not None:
        details["reasoning_tokens"] = str(reasoning_tokens)

    filter_results = getattr(choice, "content_filter_results", None)
    if filter_results is None:
        model_extra = getattr(choice, "model_extra", None) or {}
        filter_results = model_extra.get("content_filter_results")
    if hasattr(filter_results, "model_dump"):
        filter_results = filter_results.model_dump()
    if isinstance(filter_results, dict):
        for category, result in filter_results.items():
            if hasattr(result, "model_dump"):
                result = result.model_dump()
            if not isinstance(result, dict) or not result.get("filtered"):
                continue
            details["content_filter_category"] = str(category)
            severity = result.get("severity")
            if severity is not None:
                details["content_filter_severity"] = str(severity)
            break
    return details


def _model_stop_error(
    completion: Any,
    choice: Any,
    *,
    recovery_attempted: bool,
) -> ChatServiceError | None:
    """Convert explicit Foundry stop conditions into stable public errors."""
    details = _empty_model_response_details(completion, choice)
    finish_reason = details.get("finish_reason")
    if finish_reason == "content_filter":
        return ChatServiceError(
            "Azure AI Foundry blocked the model response under a configured "
            "content filter.",
            code="model_content_filtered",
            status_code=422,
            details=details,
        )
    if finish_reason == "length" and recovery_attempted:
        return ChatServiceError(
            "The model reached its configured output limit before returning "
            "an answer.",
            code="model_output_limit",
            details=details,
        )


def _foundry_guardrail_code(error: APIStatusError) -> str | None:
    """Recognize explicit policy-denial codes without inspecting error messages."""
    codes = [error.code]
    if isinstance(error.body, dict):
        details = error.body.get("error", error.body)
        if isinstance(details, dict):
            codes.append(details.get("code"))
            inner_error = details.get("innererror")
            if isinstance(inner_error, dict):
                codes.append(inner_error.get("code"))
    for code in codes:
        if isinstance(code, str) and code.lower() in {
            "content_filter",
            "content_policy_violation",
            "responsibleaipolicyviolation",
        }:
            return "content_filter"
    return None


def _identity_failure(error: Exception) -> bool:
    known = _known_service_error(error)
    return known is not None and known.code in {"authentication_required", "identity_unavailable"}


def _advice_classifier_context(
    messages: list[ChatMessage],
) -> tuple[str, str | None, str | None]:
    """Return bounded user context and the intervening assistant turn."""
    user_messages = [
        message.content for message in messages if message.role == "user"
    ]
    previous = user_messages[-2] if len(user_messages) > 1 else None
    current_index = max(
        index for index, message in enumerate(messages) if message.role == "user"
    )
    previous_assistant = (
        messages[current_index - 1].content
        if current_index > 0 and messages[current_index - 1].role == "assistant"
        else None
    )
    return user_messages[-1], previous, previous_assistant


def _classification_stop_reason(policy_data: dict[str, str]) -> str | None:
    """Return the bounded reason for a fail-closed classification stop."""
    status = policy_data["classification_status"]
    if status != "classified":
        return status
    if policy_data["request_intent"] == "unknown":
        return "unknown_intent"
    if policy_data["confidence"] == "low":
        return "low_confidence"
    return None


class ChatMessage(BaseModel):
    """One bounded user or assistant message."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4_000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        """Strip whitespace and reject effectively empty messages."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message content must not be empty.")
        return normalized


class ChatRequest(BaseModel):
    """Bounded conversation submitted by the browser."""

    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=20)

    @field_validator("messages")
    @classmethod
    def require_latest_user_message(
        cls,
        value: list[ChatMessage],
    ) -> list[ChatMessage]:
        """Require the submitted conversation to end with a user turn."""
        if value[-1].role != "user":
            raise ValueError("The conversation must end with a user message.")
        return value


def _active_advice_request_text(messages: list[ChatMessage]) -> str:
    """Include prior user intent when the latest turn only supplies a member ID."""
    latest = messages[-1]
    if (
        latest.role != "user"
        or len(latest.content) > 80
        or re.search(r"\bMEM-\d{3}\b", latest.content, re.IGNORECASE) is None
    ):
        return latest.content

    previous_user = next(
        (message for message in reversed(messages[:-1]) if message.role == "user"),
        None,
    )
    if previous_user is None:
        return latest.content
    return f"{previous_user.content}\n{latest.content}"


class PolicyNotice(BaseModel):
    """Governance outcome shown beside a refused request. Contains no prompt content."""

    model_config = ConfigDict(extra="forbid")

    decision: str
    policy_name: str | None = None
    rule: str | None = None


def _outreach_approval_prompt(member_id: str) -> str:
    """Return the bounded browser-chat approval question."""
    return (
        f"{_OUTREACH_APPROVAL_HEADING}{member_id}\n\n"
        "This member is eligible for a read-only synthetic retention outreach "
        "case. The case may include disengagement signals, but it will not send "
        "a message, notify the member, persist a case, or perform external "
        "contact.\n\nReply **Approve** to prepare the case or **Decline** to stop."
    )


def _pending_outreach_approval(
    messages: list[ChatMessage],
) -> tuple[str, bool | None] | None:
    """Read an explicit response to the immediately preceding approval prompt."""
    if len(messages) < 2 or messages[-2].role != "assistant":
        return None
    previous = messages[-2].content
    if not previous.startswith(_OUTREACH_APPROVAL_HEADING):
        return None
    member_match = re.match(
        rf"^{re.escape(_OUTREACH_APPROVAL_HEADING)}(MEM-\d{{3}})\b",
        previous,
    )
    if member_match is None:
        return None

    response = re.sub(r"\s+", " ", messages[-1].content.strip().lower())
    if response in _APPROVE_RESPONSES:
        decision: bool | None = True
    elif response in _DECLINE_RESPONSES:
        decision = False
    else:
        decision = None
    return member_match.group(1), decision


def _requested_outreach_member(messages: list[ChatMessage]) -> str | None:
    """Return the member named in an explicit outreach-case request."""
    latest = messages[-1].content
    normalized = latest.lower()
    if (
        "outreach" not in normalized
        or "case" not in normalized
        or not any(
            action in normalized
            for action in ("prepare", "open", "create", "start")
        )
    ):
        return None
    member_match = re.search(r"\bMEM-\d{3}\b", latest, re.IGNORECASE)
    return member_match.group(0).upper() if member_match is not None else None


class ChatResponse(BaseModel):
    """Sanitized response returned to the browser."""

    message: str
    tools_used: list[str]
    policy_notice: PolicyNotice | None = None


class _MemberAccountResult(BaseModel):
    """Validated account fields used by deterministic profile rendering."""

    model_config = ConfigDict(extra="ignore")

    account_id: str = Field(pattern=r"^ACC-\d{3}$")
    balance: float = Field(ge=0)
    phase: str = Field(min_length=1, max_length=64)
    option_allocation: dict[str, float]


class _MemberProfileResult(BaseModel):
    """Validated profile fields used by deterministic profile rendering."""

    model_config = ConfigDict(extra="ignore")

    member_id: str = Field(pattern=r"^MEM-\d{3}$")
    full_name: str = Field(min_length=1, max_length=100)
    tenure_years: float = Field(ge=0)
    risk_profile: str = Field(min_length=1, max_length=64)
    communication_preference: str = Field(min_length=1, max_length=32)
    account: _MemberAccountResult


def _format_member_profile(payload: Any) -> str:
    """Render a validated synthetic profile without another model call."""
    try:
        profile = _MemberProfileResult.model_validate(payload)
    except ValidationError:
        raise ChatServiceError(
            "The tool returned an invalid member profile.",
            code="unsafe_tool_result",
        ) from None

    allocation = ", ".join(
        f"{option}: {share:.0%}"
        for option, share in profile.account.option_allocation.items()
    )
    if not allocation:
        allocation = "Not recorded"
    return "\n".join(
        [
            (
                f"The synthetic profile for {profile.member_id} was retrieved "
                "from internal fund records."
            ),
            "",
            f"- Name: {profile.full_name}",
            f"- Fund tenure: {profile.tenure_years:g} years",
            f"- Risk profile: {profile.risk_profile}",
            (
                "- Communication preference: "
                f"{profile.communication_preference}"
            ),
            f"- Account: {profile.account.account_id}",
            f"- Balance: ${profile.account.balance:,.2f}",
            f"- Phase: {profile.account.phase}",
            f"- Investment allocation: {allocation}",
            "- Contact details: No email address or phone number is recorded.",
        ]
    )


class _CompletionClient(Protocol):
    chat: Any
    responses: Any

    def close(self) -> None: ...


class _AdviceRequestClassifier(Protocol):
    async def classify(
        self,
        model_client: _CompletionClient,
        *,
        current_user_text: str,
        previous_user_text: str | None,
        previous_assistant_text: str | None = None,
    ) -> AdviceRequestClassification: ...


class ChatService:
    """Run a bounded Foundry tool-calling loop against an MCP endpoint."""

    def __init__(
        self,
        settings: ChatSettings,
        advice_classifier: _AdviceRequestClassifier | None = None,
    ) -> None:
        self._settings = settings
        self._advice_classifier = (
            advice_classifier
            or FoundryAdviceRequestClassifier(
                model=settings.model_deployment,
                max_output_tokens=settings.classifier_max_output_tokens,
            )
        )
        self._advice_guardrail = AdviceClassificationGuardrail()
        self._wealth_guardrail = WholeOfWealthInvariantGuardrail()
        self._governance = get_governance_engine()
        self._foundry_reliability = ReliabilityGuard(
            self._governance.settings,
            "foundry",
        )
        self._classifier_reliability = ReliabilityGuard(
            self._governance.settings,
            "foundry-advice-classifier",
        )
        self._mcp_reliability = ReliabilityGuard(
            self._governance.settings,
            "mcp",
        )
        self._dashboard_reliability = ReliabilityGuard(
            self._governance.settings,
            "mcp-observability",
        )

    async def governance_snapshot(self) -> dict[str, Any]:
        """Merge sanitized chat and MCP process governance state."""
        local_snapshot = build_governance_snapshot(
            self._governance,
            source="chat",
            circuits={
                "foundry": self._foundry_reliability.state,
                "foundry_advice_classifier": (
                    self._classifier_reliability.state
                ),
                "mcp": self._mcp_reliability.state,
                "mcp_observability": self._dashboard_reliability.state,
            },
        )

        async def fetch_mcp_snapshot() -> dict[str, Any]:
            return await anyio.to_thread.run_sync(self._read_mcp_snapshot)

        try:
            mcp_snapshot = await self._dashboard_reliability.call(
                fetch_mcp_snapshot,
            )
        except Exception:
            return merge_governance_snapshots(
                local_snapshot,
                None,
                mcp_error="MCP governance snapshot is unavailable.",
            )
        return merge_governance_snapshots(local_snapshot, mcp_snapshot)

    def _read_mcp_snapshot(self) -> dict[str, Any]:
        parsed = urlsplit(self._settings.mcp_url)
        snapshot_url = self._settings.mcp_snapshot_url or urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                "/governance/snapshot",
                "",
                "",
            )
        )
        headers = {"Accept": "application/json"}
        if self._settings.mcp_snapshot_audience:
            with get_azure_credential() as credential:
                token = credential.get_token(
                    f"{self._settings.mcp_snapshot_audience.rstrip('/')}/.default"
                )
            headers["Authorization"] = f"Bearer {token.token}"
        payload = bytearray()
        with httpx.stream(
            "GET",
            snapshot_url,
            headers=headers,
            follow_redirects=False,
            timeout=self._governance.settings.operation_timeout_seconds,
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                payload.extend(chunk)
                if len(payload) > 262_144:
                    raise ValueError("MCP governance snapshot exceeded the safe limit.")
        document = json.loads(payload)
        if not isinstance(document, dict):
            raise ValueError("MCP governance snapshot must be an object.")
        return document

    async def complete(
        self,
        request: ChatRequest,
        caller: CallerIdentity | None = None,
    ) -> ChatResponse:
        """Complete one chat turn without persisting conversation content."""
        with genai_telemetry.invoke_agent_span(model=self._settings.model_deployment):
            return await self._complete(request, caller)

    async def _complete(self, request: ChatRequest, caller: CallerIdentity | None) -> ChatResponse:
        if len(request.messages) > self._settings.max_messages:
            raise ChatServiceError(
                "The conversation is too long.",
                code="invalid_request",
                status_code=400,
            )
        if any(
            len(message.content) > self._settings.max_message_length
            for message in request.messages
        ):
            raise ChatServiceError(
                "A message exceeds the configured length.",
                code="invalid_request",
                status_code=400,
            )
        project_client = None
        model_client: _CompletionClient | None = None
        tools_used: list[str] = []
        pending_approval = _pending_outreach_approval(request.messages)
        requested_outreach_member = _requested_outreach_member(request.messages)
        try:
            project_client = get_foundry_client()
            model_client = project_client.get_openai_client()
            current_user_text, previous_user_text, previous_assistant_text = (
                _advice_classifier_context(request.messages)
            )
            self._governance.require_allowed(
                LifecyclePoint.PRE_MODEL,
                "foundry.advice_classifier",
                policy_data={
                    "context_user_turn_count": (
                        2 if previous_user_text is not None else 1
                    )
                },
                source="chat",
            )
            classification_failure_reason: str | None = None
            try:
                async def classify_request() -> AdviceRequestClassification:
                    return await self._advice_classifier.classify(
                        model_client,
                        current_user_text=current_user_text,
                        previous_user_text=previous_user_text,
                        previous_assistant_text=previous_assistant_text,
                    )

                classification = await self._classifier_reliability.call(
                    classify_request
                )
                classification_data = classification.to_policy_data()
            except AdviceClassificationFailure as exc:
                classification_failure_reason = exc.reason
                classification_data = classification_failure_policy_data(exc.reason)
            except Exception as exc:
                classification_failure_reason = "unavailable"
                classification_data = classification_failure_policy_data("unavailable")
                logger.warning(
                    "Advice classifier unavailable",
                    extra={"failure_type": type(exc).__name__},
                )

            self._governance.require_allowed(
                LifecyclePoint.POST_MODEL,
                "foundry.advice_classifier",
                policy_data=classification_data,
                source="chat",
            )
            classification_stop_reason = (
                classification_failure_reason
                or _classification_stop_reason(classification_data)
            )
            try:
                self._governance.require_allowed(
                    LifecyclePoint.INPUT,
                    "chat.input",
                    policy_data={
                        "message_count": len(request.messages),
                        **classification_data,
                    },
                    source="chat",
                )
            except GovernanceDeniedError as exc:
                if classification_stop_reason is None:
                    raise
                details = _governance_error_details(exc)
                details["classification_reason"] = classification_stop_reason
                raise ChatServiceError(
                    "The request could not be safely classified. Please try "
                    "again or rephrase the request.",
                    code="classification_unavailable",
                    status_code=503,
                    details=details,
                ) from exc

            if self._settings.agent_name:
                return await self._complete_prompt_agent(model_client, request)

            async def resolve_elicitation(_context: Any, _params: Any):
                if pending_approval is not None and pending_approval[1] is True:
                    return types.ElicitResult(action="accept", content={"approved": True})
                if pending_approval is not None and pending_approval[1] is False:
                    return types.ElicitResult(action="decline")
                return types.ElicitResult(action="cancel")

            async with httpx2.AsyncClient(
                auth=(
                    AgentAuth(
                        SidecarClient(
                            self._settings.sidecar_url,
                            timeout=self._governance.settings.operation_timeout_seconds,
                        ),
                        self._settings.interactive_agent_id,
                        caller,
                    )
                    if caller is not None
                    else None
                ),
                trust_env=False, follow_redirects=False,
                timeout=self._governance.settings.operation_timeout_seconds,
            ) as http, Client(
                streamable_http_client(self._settings.mcp_url, http_client=http),
                elicitation_callback=resolve_elicitation,
            ) as mcp_client:
                discovered = await self._mcp_reliability.call(
                    mcp_client.list_tools,
                    ignore_error=_identity_failure,
                )
                allowed_tools = [
                    tool
                    for tool in discovered.tools
                    if _tool_enabled_for_browser_chat(tool)
                ]
                tool_by_name = {tool.name: tool for tool in allowed_tools}
                model_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.input_schema,
                        },
                    }
                    for tool in allowed_tools
                ]
                messages: list[dict[str, Any]] = [
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    *[
                        {"role": message.role, "content": message.content}
                        for message in request.messages
                    ],
                ]
                if (
                    requested_outreach_member is not None
                    and pending_approval is None
                ):
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "The user explicitly requested a retention "
                                "outreach case. Call "
                                "prepare_member_outreach_case for "
                                f"{requested_outreach_member}."
                            ),
                        }
                    )
                if pending_approval is not None:
                    member_id, decision = pending_approval
                    if decision is None:
                        return self._finalize_response(
                            _outreach_approval_prompt(member_id),
                            tools_used,
                        )
                    if decision is False:
                        return self._finalize_response(
                            (
                                f"Understood. Preparation of the outreach case "
                                f"for {member_id} was declined. No operation "
                                "was executed."
                            ),
                            tools_used,
                        )
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                f"The user explicitly approved preparation of "
                                f"the read-only outreach case for {member_id}. "
                                "Call prepare_member_outreach_case for that "
                                "member now."
                            ),
                        }
                    )
                empty_response_retried = False
                model_attempt = 0
                model_attempt_limit = self._settings.max_tool_rounds + 1

                while model_attempt < model_attempt_limit:
                    model_attempt += 1
                    self._governance.require_allowed(
                        LifecyclePoint.PRE_MODEL,
                        "foundry.chat",
                        policy_data={
                            "message_count": len(messages),
                            "tool_count": len(model_tools),
                        },
                        source="chat",
                    )

                    async def request_completion() -> tuple[Any, str | None]:
                        completion_options: dict[str, Any] = {
                            "model": self._settings.model_deployment,
                            "messages": messages,
                            "tools": model_tools,
                            "tool_choice": "none",
                            "parallel_tool_calls": False,
                            "max_completion_tokens": (
                                self._settings.max_output_tokens
                            ),
                            "store": False,
                        }
                        if not empty_response_retried:
                            outreach_requested = (
                                not tools_used
                                and (
                                    requested_outreach_member is not None
                                    or (
                                        pending_approval is not None
                                        and pending_approval[1] is True
                                    )
                                )
                            )
                            completion_options["tool_choice"] = (
                                {
                                    "type": "function",
                                    "function": {
                                        "name": (
                                            "prepare_member_outreach_case"
                                        )
                                    },
                                }
                                if outreach_requested
                                else "auto"
                            )
                        if empty_response_retried:
                            completion_options.update(
                                reasoning_effort="minimal",
                                verbosity="low",
                            )
                        with genai_telemetry.inference_span(
                            model=self._settings.model_deployment,
                            model_client=model_client,
                            max_tokens=self._settings.max_output_tokens,
                        ) as inference:
                            try:
                                completion = await anyio.to_thread.run_sync(
                                    lambda: model_client.chat.completions.create(
                                        **completion_options,
                                    )
                                )
                            except APIStatusError as exc:
                                guardrail_code = _foundry_guardrail_code(exc)
                                if guardrail_code is None:
                                    raise
                                inference.fail(guardrail_code)
                                return None, guardrail_code
                            inference.record_response(completion)
                            return completion, None

                    completion, guardrail_code = await self._foundry_reliability.call(
                        request_completion,
                    )
                    content_filter_error = None
                    if guardrail_code is None:
                        for filtered_choice in completion.choices:
                            if (
                                getattr(filtered_choice, "finish_reason", None)
                                == "content_filter"
                            ):
                                guardrail_code = "content_filter"
                                content_filter_error = _model_stop_error(
                                    completion,
                                    filtered_choice,
                                    recovery_attempted=empty_response_retried,
                                )
                                break
                    if guardrail_code is not None:
                        decision = self._governance.record_external_denial(
                            LifecyclePoint.POST_MODEL,
                            "foundry.chat",
                            policy_name="azure-ai-foundry",
                            matched_rule=guardrail_code,
                            source="chat",
                        )
                        if content_filter_error is not None:
                            raise content_filter_error
                        raise GovernanceDeniedError(
                            "Azure AI Foundry guardrail denied the request.",
                            action="foundry.chat",
                            decision=decision,
                        )
                    self._governance.require_allowed(
                        LifecyclePoint.POST_MODEL,
                        "foundry.chat",
                        policy_data={
                            "choice_count": len(completion.choices),
                        },
                        source="chat",
                    )
                    choice = completion.choices[0]
                    assistant_message = choice.message
                    if not assistant_message.tool_calls:
                        if _is_empty_model_content(assistant_message.content):
                            stop_error = _model_stop_error(
                                completion,
                                choice,
                                recovery_attempted=empty_response_retried,
                            )
                            if stop_error is not None:
                                raise stop_error
                            if not empty_response_retried:
                                empty_response_retried = True
                                model_attempt_limit += 1
                                messages.append(
                                    {
                                        "role": "system",
                                        "content": (
                                            _EMPTY_RESPONSE_RECOVERY_INSTRUCTION
                                        ),
                                    }
                                )
                                continue
                            raise ChatServiceError(
                                "The model returned an empty response.",
                                code="invalid_model_response",
                                details=_empty_model_response_details(
                                    completion,
                                    choice,
                                ),
                            )
                        return self._finalize_response(
                            assistant_message.content,
                            tools_used,
                        )

                    messages.append(
                        {
                            "role": "assistant",
                            "content": assistant_message.content,
                            "tool_calls": [
                                tool_call.model_dump(exclude_none=True)
                                for tool_call in assistant_message.tool_calls
                            ],
                        }
                    )
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        if tool_name not in tool_by_name:
                            self._governance.require_allowed(
                                LifecyclePoint.PRE_TOOL, tool_name, source="chat",
                            )
                            raise ChatServiceError(
                                "The model selected an unknown tool.",
                                code="invalid_model_response",
                            )
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError as exc:
                            raise ChatServiceError(
                                "The model returned invalid tool arguments.",
                                code="invalid_model_response",
                            ) from exc
                        if not isinstance(arguments, dict):
                            raise ChatServiceError(
                                "The model returned invalid tool arguments.",
                                code="invalid_model_response",
                            )

                        policy_data: dict[str, object] = {
                            "tool_known": tool_name in tool_by_name,
                        }
                        review: RetentionReview | None = None
                        if tool_name == "prepare_member_outreach_case":
                            member_id = arguments.get("member_id")
                            if not isinstance(member_id, str) or not re.fullmatch(
                                r"MEM-\d{3}", member_id,
                            ):
                                raise ChatServiceError(
                                    "The model returned an invalid member identifier.",
                                    code="invalid_model_response",
                                )
                            self._governance.require_allowed(
                                LifecyclePoint.PRE_TOOL,
                                "get_member_profile",
                                source="chat",
                            )

                            async def read_retention_profile() -> Any:
                                with genai_telemetry.execute_tool_span(
                                    tool_name="get_member_profile",
                                    call_id=None,
                                ) as profile_execution:
                                    profile = await mcp_client.call_tool(
                                        "get_member_profile", {"member_id": member_id},
                                    )
                                    if profile.is_error:
                                        profile_execution.fail("tool_error")
                                    return profile

                            profile_result = await self._mcp_reliability.call(
                                read_retention_profile,
                                ignore_error=_identity_failure,
                            )
                            self._governance.require_allowed(
                                LifecyclePoint.POST_TOOL,
                                "get_member_profile",
                                policy_data=tool_response_policy_data(
                                    profile_result.structured_content,
                                ),
                                source="chat",
                            )
                            profile = profile_result.structured_content
                            if (
                                profile_result.is_error
                                or not isinstance(profile, dict)
                                or profile.get("member_id") != member_id
                            ):
                                raise ChatServiceError(
                                    "Outreach eligibility could not be verified. "
                                    "Staff must check the internal member record.",
                                    code="governance_denied",
                                    status_code=403,
                                )
                            try:
                                review = RetentionReview.model_validate(
                                    profile.get("retention_review", {"status": "unknown"}),
                                )
                            except ValidationError:
                                raise ChatServiceError(
                                    "The tool returned invalid outreach eligibility. "
                                    "Staff must verify the internal case records.",
                                    code="unsafe_tool_result",
                                ) from None
                            policy_data.update(review.policy_data())
                        try:
                            self._governance.require_allowed(
                                LifecyclePoint.PRE_TOOL,
                                tool_name,
                                policy_data=policy_data,
                                source="chat",
                            )
                        except GovernanceDeniedError as exc:
                            if review is not None and review.status != "routine_permitted":
                                raise ChatServiceError(
                                    review.staff_message(),
                                    code="governance_denied",
                                    status_code=403,
                                    details=_governance_error_details(exc),
                                ) from exc
                            raise
                        if (
                            tool_name == "prepare_member_outreach_case"
                            and pending_approval != (member_id, True)
                        ):
                            return self._finalize_response(
                                _outreach_approval_prompt(member_id),
                                tools_used,
                            )

                        async def call_tool() -> Any:
                            with genai_telemetry.execute_tool_span(
                                tool_name=tool_name,
                                call_id=getattr(tool_call, "id", None),
                            ) as tool_execution:
                                result = await mcp_client.call_tool(tool_name, arguments)
                                if result.is_error:
                                    tool_execution.fail("tool_error")
                                return result

                        result = await self._mcp_reliability.call(call_tool, ignore_error=_identity_failure)
                        self._governance.require_allowed(
                            LifecyclePoint.POST_TOOL,
                            tool_name,
                            policy_data={
                                **tool_response_policy_data(result.structured_content),
                                "is_error": result.is_error,
                            },
                            source="chat",
                        )
                        tools_used.append(tool_name)
                        if (
                            tool_name == "get_member_profile"
                            and not result.is_error
                        ):
                            return self._finalize_response(
                                _format_member_profile(
                                    _restrict_tool_payload(
                                        tool_name,
                                        result.structured_content,
                                    )
                                ),
                                tools_used,
                            )
                        tool_payload: Any
                        if result.is_error:
                            tool_payload = {
                                "error": "The requested tool could not complete the call."
                            }
                        else:
                            tool_payload = _restrict_tool_payload(
                                tool_name,
                                result.structured_content,
                            )
                        serialized = json.dumps(tool_payload, separators=(",", ":"))
                        if len(serialized) > 32_000:
                            raise ChatServiceError(
                                "The tool result exceeded the safe limit.",
                                code="unsafe_tool_result",
                            )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": serialized,
                            }
                        )
        except ChatServiceError:
            raise
        except GovernanceDeniedError as exc:
            raise _governance_service_error(exc) from exc
        except Exception as exc:
            known_error = _known_service_error(exc)
            if known_error is not None:
                raise known_error from exc
            logger.error("Chat service failed unexpectedly")
            raise ChatServiceError(
                "An upstream chat dependency could not complete the request.",
                code="upstream_failure",
            ) from exc
        finally:
            if model_client is not None:
                model_client.close()
            if project_client is not None:
                project_client.close()

        raise ChatServiceError(
            "The model exceeded the allowed tool-call rounds.",
            code="model_round_limit",
        )

    async def _complete_prompt_agent(
        self,
        model_client: _CompletionClient,
        request: ChatRequest,
    ) -> ChatResponse:
        """Invoke the configured Foundry Prompt Agent and apply chat guardrails."""
        messages = [
            {"type": "message", "role": "system", "content": SYSTEM_INSTRUCTIONS},
            *[
                {"type": "message", "role": message.role, "content": message.content}
                for message in request.messages
            ],
        ]
        self._governance.require_allowed(
            LifecyclePoint.PRE_MODEL,
            "foundry.chat",
            policy_data={"message_count": len(messages), "tool_count": 0},
            source="chat",
        )

        async def invoke_agent() -> tuple[Any | None, str | None]:
            try:
                response = await anyio.to_thread.run_sync(
                    lambda: model_client.responses.create(
                        model=self._settings.model_deployment,
                        input=messages,
                        max_output_tokens=self._settings.max_output_tokens,
                        store=False,
                        extra_body={
                            "agent_reference": {
                                "name": self._settings.agent_name,
                                "type": "agent_reference",
                            }
                        },
                    )
                )
            except APIStatusError as exc:
                guardrail_code = _foundry_guardrail_code(exc)
                if guardrail_code is None:
                    raise
                return None, guardrail_code
            incomplete_details = getattr(response, "incomplete_details", None)
            if getattr(incomplete_details, "reason", None) == "content_filter":
                return None, "content_filter"
            return response, None

        response, guardrail_code = await self._foundry_reliability.call(invoke_agent)
        if guardrail_code is not None:
            decision = self._governance.record_external_denial(
                LifecyclePoint.POST_MODEL,
                "foundry.chat",
                policy_name="azure-ai-foundry",
                matched_rule=guardrail_code,
                source="chat",
            )
            raise GovernanceDeniedError(
                "Azure AI Foundry guardrail denied the request.",
                action="foundry.chat",
                decision=decision,
            )
        if response is None or getattr(response, "status", "completed") != "completed":
            values = {
                "response_status": getattr(response, "status", "missing"),
                "incomplete_reason": getattr(
                    getattr(response, "incomplete_details", None), "reason", None
                ),
            }
            details = {
                key: value
                for key, value in values.items()
                if isinstance(value, str) and _SAFE_ERROR_VALUE.fullmatch(value)
            }
            logger.warning("Foundry Agent did not complete: %s", details)
            raise ChatServiceError(
                "The Foundry Agent returned an incomplete response.",
                code="invalid_model_response",
                details=details,
            )

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise ChatServiceError(
                "The Foundry Agent returned an empty response.",
                code="invalid_model_response",
            )

        output_items = getattr(response, "output", ()) or ()
        self._governance.require_allowed(
            LifecyclePoint.POST_MODEL,
            "foundry.chat",
            policy_data={"choice_count": len(output_items)},
            source="chat",
        )
        response_text = self._sanitize_response(output_text)
        tools_used = list(
            dict.fromkeys(
                item.name
                for item in output_items
                if getattr(item, "type", None) == "mcp_call"
                and isinstance(getattr(item, "name", None), str)
                and _SAFE_ERROR_VALUE.fullmatch(item.name)
            )
        )
        self._governance.require_allowed(
            LifecyclePoint.OUTPUT,
            "chat.output",
            policy_data={
                "response_length": len(response_text),
                "tool_count": len(tools_used),
            },
            source="chat",
        )
        return ChatResponse(message=response_text, tools_used=tools_used)

    def _sanitize_response(self, response: str) -> str:
        scoped = self._wealth_guardrail.sanitize_scope_claims(response)
        safe, _ = self._advice_guardrail.enforce_advice_boundaries(scoped)
        return safe

    def _finalize_response(
        self,
        response: str,
        tools_used: list[str],
    ) -> ChatResponse:
        """Apply output guardrails and record the final governance decision."""
        sanitized = self._sanitize_response(response)
        if _is_scope_refusal(sanitized):
            sanitized = SCOPE_REFUSAL_MESSAGE
        unique_tools = list(dict.fromkeys(tools_used))
        self._governance.require_allowed(
            LifecyclePoint.OUTPUT,
            "chat.output",
            policy_data={
                "response_length": len(sanitized),
                "tool_count": len(unique_tools),
            },
            source="chat",
        )
        policy_notice = None
        if _is_scope_refusal(sanitized):
            refusal = self._governance.evaluate(
                LifecyclePoint.OUTPUT,
                "chat.scope_refusal",
                source="chat",
            )
            policy_notice = PolicyNotice(
                decision=refusal.action,
                policy_name=refusal.policy_name,
                rule=refusal.matched_rule,
            )
        return ChatResponse(
            message=sanitized,
            tools_used=unique_tools,
            policy_notice=policy_notice,
        )
