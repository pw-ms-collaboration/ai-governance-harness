"""Foundry chat orchestration that executes tools only through MCP."""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from typing import Any, Literal, Protocol

import anyio
from mcp import Client
from openai import APIStatusError
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.foundry_client import get_foundry_client
from ai_governance_harness.governance import (
    GovernanceDeniedError,
    LifecyclePoint,
    get_governance_engine,
)
from ai_governance_harness.governance.reliability import ReliabilityGuard
from ai_governance_harness.governance.snapshot import (
    build_governance_snapshot,
    merge_governance_snapshots,
)
from ai_governance_harness.guardrails.advice_filter import (
    AdviceClassificationGuardrail,
    WholeOfWealthInvariantGuardrail,
    advice_request_policy_data,
    tool_response_policy_data,
)

SYSTEM_INSTRUCTIONS = (
    "You are an internal assistant for bank business analysts working only with "
    "synthetic customer account data. The only tool you can use is "
    "get_member_profile, which returns member details (name, tenure, risk "
    "profile, communication preference), account balance, phase, and investment "
    "option allocation. Use it for every profile fact and never invent tool results. "
    "Share only those profile fields. If asked for an email, phone number, or "
    "contact details, call get_member_profile and share the communication "
    "preference, stating that the record holds no email address or phone number. "
    "For any other customer information, "
    "including contributions, digital activity, interactions, churn signals, or "
    "cohort and FUM analytics, reply exactly: Sorry, I can’t assist "
    "with this request. I can only provide factual information and general "
    "guidance based on a member’s internal superannuation records, including "
    "their account profile, contributions, engagement activity, and recorded "
    "disengagement signals. Do not give personal financial advice to customers "
    "or recommend actions for them, and do not claim visibility into external "
    "assets. Keep responses concise."
)

SCOPE_REFUSAL_PREFIX = "Sorry, I can't assist with this request"
SCOPE_REFUSAL_MESSAGE = (
    "Sorry, I can’t assist with this request. I can only provide factual information "
    "and general guidance based on a member’s internal superannuation records, "
    "including their account profile, contributions, engagement activity, and "
    "recorded disengagement signals"
)

ALLOWED_CHAT_TOOLS = frozenset({"get_member_profile"})
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


def _restrict_tool_payload(tool_name: str, payload: Any) -> Any:
    """Reduce a member profile to permitted fields before the model sees it."""
    if tool_name != "get_member_profile" or not isinstance(payload, dict):
        return payload
    return {key: payload[key] for key in PROFILE_FIELDS if key in payload}


class ChatServiceError(RuntimeError):
    """Raised when a chat turn cannot be completed safely."""

    def __init__(
        self,
        message: str,
        *,
        code: ChatErrorCode = "chat_service_error",
        status_code: int = 502,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.details = dict(details or {})


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


def _known_service_error(error: BaseException) -> ChatServiceError | None:
    """Find a known service error wrapped by an asynchronous task group."""
    if isinstance(error, ChatServiceError):
        return error
    if isinstance(error, GovernanceDeniedError):
        return _governance_service_error(error)
    if isinstance(error, BaseExceptionGroup):
        for nested_error in error.exceptions:
            known_error = _known_service_error(nested_error)
            if known_error is not None:
                return known_error
    return None


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


class PolicyNotice(BaseModel):
    """Governance outcome shown beside a refused request. Contains no prompt content."""

    model_config = ConfigDict(extra="forbid")

    decision: str
    policy_name: str | None = None
    rule: str | None = None


class ChatResponse(BaseModel):
    """Sanitized response returned to the browser."""

    message: str
    tools_used: list[str]
    policy_notice: PolicyNotice | None = None


class _CompletionClient(Protocol):
    chat: Any

    def close(self) -> None: ...


class ChatService:
    """Run a bounded Foundry tool-calling loop against an MCP endpoint."""

    def __init__(self, settings: ChatSettings) -> None:
        self._settings = settings
        self._advice_guardrail = AdviceClassificationGuardrail()
        self._wealth_guardrail = WholeOfWealthInvariantGuardrail()
        self._governance = get_governance_engine()
        self._foundry_reliability = ReliabilityGuard(
            self._governance.settings,
            "foundry",
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
        snapshot_url = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                "/governance/snapshot",
                "",
                "",
            )
        )
        request = UrlRequest(
            snapshot_url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urlopen(
            request,
            timeout=self._governance.settings.operation_timeout_seconds,
        ) as response:
            payload = response.read(262_145)
        if len(payload) > 262_144:
            raise ValueError("MCP governance snapshot exceeded the safe limit.")
        document = json.loads(payload)
        if not isinstance(document, dict):
            raise ValueError("MCP governance snapshot must be an object.")
        return document

    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Complete one chat turn without persisting conversation content."""
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
        try:
            self._governance.require_allowed(
                LifecyclePoint.INPUT,
                "chat.input",
                policy_data={
                    "message_count": len(request.messages),
                    **advice_request_policy_data(
                        _active_advice_request_text(request.messages)
                    ),
                },
                source="chat",
            )
            project_client = get_foundry_client()
            model_client = project_client.get_openai_client()
            async with Client(self._settings.mcp_url) as mcp_client:
                discovered = await self._mcp_reliability.call(
                    mcp_client.list_tools,
                )
                allowed_tools = [
                    tool for tool in discovered.tools if tool.name in ALLOWED_CHAT_TOOLS
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

                for _ in range(self._settings.max_tool_rounds + 1):
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
                        try:
                            completion = await anyio.to_thread.run_sync(
                                lambda: model_client.chat.completions.create(
                                    model=self._settings.model_deployment,
                                    messages=messages,
                                    tools=model_tools,
                                    tool_choice="auto",
                                    parallel_tool_calls=False,
                                    max_completion_tokens=self._settings.max_output_tokens,
                                    store=False,
                                )
                            )
                        except APIStatusError as exc:
                            guardrail_code = _foundry_guardrail_code(exc)
                            if guardrail_code is None:
                                raise
                            return None, guardrail_code
                        return completion, None

                    completion, guardrail_code = await self._foundry_reliability.call(
                        request_completion,
                    )
                    if guardrail_code is None and any(
                        getattr(choice, "finish_reason", None) == "content_filter"
                        for choice in completion.choices
                    ):
                        guardrail_code = "content_filter"
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
                        if not assistant_message.content:
                            raise ChatServiceError(
                                "The model returned an empty response.",
                                code="invalid_model_response",
                            )
                        response = self._sanitize_response(
                            assistant_message.content
                        )
                        if _is_scope_refusal(response):
                            response = SCOPE_REFUSAL_MESSAGE
                        self._governance.require_allowed(
                            LifecyclePoint.OUTPUT,
                            "chat.output",
                            policy_data={
                                "response_length": len(response),
                                "tool_count": len(tools_used),
                            },
                            source="chat",
                        )
                        policy_notice = None
                        if _is_scope_refusal(response):
                            # Recorded, not enforced: the refusal is already the safe outcome.
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
                            message=response,
                            tools_used=list(dict.fromkeys(tools_used)),
                            policy_notice=policy_notice,
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
                        self._governance.require_allowed(
                            LifecyclePoint.PRE_TOOL,
                            tool_name,
                            policy_data={
                                "tool_known": tool_name in tool_by_name,
                            },
                            source="chat",
                        )
                        if tool_name not in tool_by_name:
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

                        async def call_tool() -> Any:
                            return await mcp_client.call_tool(tool_name, arguments)

                        result = await self._mcp_reliability.call(call_tool)
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
            logger.exception("Chat service failed unexpectedly")
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

    def _sanitize_response(self, response: str) -> str:
        scoped = self._wealth_guardrail.sanitize_scope_claims(response)
        safe, _ = self._advice_guardrail.enforce_advice_boundaries(scoped)
        return safe
