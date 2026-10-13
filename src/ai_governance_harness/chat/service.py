"""Foundry chat orchestration that executes tools only through MCP."""

from __future__ import annotations

import json
from typing import Any, Literal, Protocol

import anyio
from mcp import Client
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.foundry_client import get_foundry_client
from ai_governance_harness.guardrails.advice_filter import (
    AdviceClassificationGuardrail,
    DisclosureAttacher,
    WholeOfWealthInvariantGuardrail,
)

SYSTEM_INSTRUCTIONS = (
    "You are an internal superannuation information assistant working only with "
    "synthetic in-fund data. Use the available tools for every member, cohort, "
    "risk, or FUM fact. Never invent tool results. Do not provide personal "
    "financial product advice or claim visibility into external assets. Explain "
    "uncertainty and keep responses concise."
)


class ChatServiceError(RuntimeError):
    """Raised when a chat turn cannot be completed safely."""


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


class ChatResponse(BaseModel):
    """Sanitized response returned to the browser."""

    message: str
    tools_used: list[str]


class _CompletionClient(Protocol):
    chat: Any

    def close(self) -> None: ...


class ChatService:
    """Run a bounded Foundry tool-calling loop against an MCP endpoint."""

    def __init__(self, settings: ChatSettings) -> None:
        self._settings = settings
        self._advice_guardrail = AdviceClassificationGuardrail()
        self._wealth_guardrail = WholeOfWealthInvariantGuardrail()

    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Complete one chat turn without persisting conversation content."""
        if len(request.messages) > self._settings.max_messages:
            raise ChatServiceError("The conversation is too long.")
        if any(
            len(message.content) > self._settings.max_message_length
            for message in request.messages
        ):
            raise ChatServiceError("A message exceeds the configured length.")

        project_client = get_foundry_client()
        model_client: _CompletionClient | None = None
        tools_used: list[str] = []
        try:
            model_client = project_client.get_openai_client()
            async with Client(self._settings.mcp_url) as mcp_client:
                discovered = await mcp_client.list_tools()
                tool_by_name = {tool.name: tool for tool in discovered.tools}
                model_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.input_schema,
                        },
                    }
                    for tool in discovered.tools
                ]
                messages: list[dict[str, Any]] = [
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    *[
                        {"role": message.role, "content": message.content}
                        for message in request.messages
                    ],
                ]

                for _ in range(self._settings.max_tool_rounds + 1):
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
                    choice = completion.choices[0]
                    assistant_message = choice.message
                    if not assistant_message.tool_calls:
                        if not assistant_message.content:
                            raise ChatServiceError("The model returned an empty response.")
                        return ChatResponse(
                            message=self._sanitize_response(assistant_message.content),
                            tools_used=list(dict.fromkeys(tools_used)),
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
                            raise ChatServiceError("The model selected an unknown tool.")
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError as exc:
                            raise ChatServiceError(
                                "The model returned invalid tool arguments."
                            ) from exc
                        if not isinstance(arguments, dict):
                            raise ChatServiceError(
                                "The model returned invalid tool arguments."
                            )

                        result = await mcp_client.call_tool(tool_name, arguments)
                        tools_used.append(tool_name)
                        tool_payload: Any
                        if result.is_error:
                            tool_payload = {
                                "error": "The requested tool could not complete the call."
                            }
                        else:
                            tool_payload = result.structured_content
                        serialized = json.dumps(tool_payload, separators=(",", ":"))
                        if len(serialized) > 32_000:
                            raise ChatServiceError("The tool result exceeded the safe limit.")
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": serialized,
                            }
                        )
        except ChatServiceError:
            raise
        except Exception as exc:
            raise ChatServiceError(
                "The chat service could not complete the request."
            ) from exc
        finally:
            if model_client is not None:
                model_client.close()
            project_client.close()

        raise ChatServiceError("The model exceeded the allowed tool-call rounds.")

    def _sanitize_response(self, response: str) -> str:
        scoped = self._wealth_guardrail.sanitize_scope_claims(response)
        safe, _ = self._advice_guardrail.enforce_advice_boundaries(scoped)
        return DisclosureAttacher.attach_disclosures(safe)
