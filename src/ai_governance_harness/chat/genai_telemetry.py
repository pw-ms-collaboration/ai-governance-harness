"""OpenTelemetry GenAI semantic conventions for the chat agent.

Follows https://github.com/open-telemetry/semantic-conventions-genai (status:
Development). Spans and metrics carry metadata only. The opt-in content
attributes (``gen_ai.input.messages``, ``gen_ai.output.messages``,
``gen_ai.system_instructions``, ``gen_ai.tool.definitions``,
``gen_ai.tool.call.arguments`` and ``gen_ai.tool.call.result``) are never
recorded, so prompts and member data stay out of telemetry.

MCP ``tools/call`` client and server spans come from the MCP Python SDK, which
also propagates W3C trace context through ``params._meta``.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.trace import Span, SpanKind, StatusCode

INSTRUMENTATION_NAME = "ai-governance-harness-genai"
INSTRUMENTATION_VERSION = "0.1.0"
PROVIDER_NAME = "azure.ai.openai"
AGENT_NAME = "superannuation-governance-assistant"
AGENT_DESCRIPTION = "Governed chat agent over synthetic superannuation MCP tools."
TOOL_TYPE = "extension"

_CLIENT_DURATION_BUCKETS = (
    0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 5.12, 10.24, 20.48,
    40.96, 81.92,
)
_AGENT_DURATION_BUCKETS = (
    0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2, 102.4, 204.8, 409.6,
)

tracer = trace.get_tracer(INSTRUMENTATION_NAME, INSTRUMENTATION_VERSION)
_meter = metrics.get_meter(INSTRUMENTATION_NAME, INSTRUMENTATION_VERSION)

operation_duration = _meter.create_histogram(
    "gen_ai.client.operation.duration",
    unit="s",
    description="GenAI operation duration.",
    explicit_bucket_boundaries_advisory=_CLIENT_DURATION_BUCKETS,
)
input_token_usage = _meter.create_counter(
    "gen_ai.client.inference.usage.input_tokens",
    unit="{token}",
    description="Input tokens used, including cached tokens.",
)
output_token_usage = _meter.create_counter(
    "gen_ai.client.inference.usage.output_tokens",
    unit="{token}",
    description="Output tokens used, including reasoning tokens.",
)
tool_duration = _meter.create_histogram(
    "gen_ai.execute_tool.duration",
    unit="s",
    description="Duration of a single tool execution.",
    explicit_bucket_boundaries_advisory=_CLIENT_DURATION_BUCKETS,
)
agent_duration = _meter.create_histogram(
    "gen_ai.invoke_agent.duration",
    unit="s",
    description="End-to-end duration of one agent invocation.",
    explicit_bucket_boundaries_advisory=_AGENT_DURATION_BUCKETS,
)


def error_type(exc: BaseException) -> str:
    """Return a low-cardinality ``error.type`` without exception messages."""
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code:
        return code
    return type(exc).__qualname__


def server_attributes(model_client: Any) -> dict[str, Any]:
    """Derive ``server.address`` and ``server.port`` from an OpenAI client."""
    base_url = getattr(model_client, "base_url", None)
    host = getattr(base_url, "host", None)
    if not isinstance(host, str) or not host:
        return {}
    port = getattr(base_url, "port", None)
    if not isinstance(port, int):
        scheme = getattr(base_url, "scheme", "https")
        port = 80 if scheme == "http" else 443
    return {"server.address": host, "server.port": port}


def _fail(span: Span, attributes: dict[str, Any], kind: str) -> None:
    attributes["error.type"] = kind
    span.set_attribute("error.type", kind)
    span.set_status(StatusCode.ERROR)


@contextmanager
def invoke_agent_span(*, model: str) -> Iterator[Span]:
    """Wrap one chat turn in an ``invoke_agent`` INTERNAL span."""
    attributes: dict[str, Any] = {
        "gen_ai.operation.name": "invoke_agent",
        "gen_ai.provider.name": PROVIDER_NAME,
        "gen_ai.agent.name": AGENT_NAME,
        "gen_ai.request.model": model,
    }
    started_at = time.perf_counter()
    with tracer.start_as_current_span(
        f"invoke_agent {AGENT_NAME}",
        kind=SpanKind.INTERNAL,
        attributes={
            **attributes,
            "gen_ai.agent.description": AGENT_DESCRIPTION,
            "gen_ai.output.type": "text",
        },
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        try:
            yield span
        except BaseException as exc:
            _fail(span, attributes, error_type(exc))
            raise
        finally:
            agent_duration.record(time.perf_counter() - started_at, attributes)


class SpanRecorder:
    """Share failure state between a GenAI span and its duration metric."""

    def __init__(self, span: Span, attributes: dict[str, Any]) -> None:
        self._span = span
        self._attributes = attributes

    def fail(self, kind: str) -> None:
        """Mark the operation as failed with a bounded ``error.type``."""
        _fail(self._span, self._attributes, kind)


class InferenceRecorder(SpanRecorder):
    """Record response metadata for one ``chat`` inference span."""

    def record_response(self, completion: Any) -> None:
        """Copy id, model, finish reasons and token usage onto the span."""
        response_id = getattr(completion, "id", None)
        if isinstance(response_id, str) and response_id:
            self._span.set_attribute("gen_ai.response.id", response_id)
        response_model = getattr(completion, "model", None)
        if isinstance(response_model, str) and response_model:
            self._span.set_attribute("gen_ai.response.model", response_model)
            self._attributes["gen_ai.response.model"] = response_model
        finish_reasons = [
            reason
            for choice in getattr(completion, "choices", None) or []
            if isinstance(reason := getattr(choice, "finish_reason", None), str)
        ]
        if finish_reasons:
            self._span.set_attribute("gen_ai.response.finish_reasons", finish_reasons)

        usage = getattr(completion, "usage", None)
        token_attributes = {
            key: value
            for key, value in self._attributes.items()
            if key != "error.type"
        }
        token_attributes["gen_ai.token.modality"] = "text"
        input_tokens = getattr(usage, "prompt_tokens", None)
        if isinstance(input_tokens, int):
            self._span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
            input_token_usage.add(input_tokens, token_attributes)
        output_tokens = getattr(usage, "completion_tokens", None)
        if isinstance(output_tokens, int):
            self._span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
            output_token_usage.add(output_tokens, token_attributes)
        cached = getattr(
            getattr(usage, "prompt_tokens_details", None), "cached_tokens", None
        )
        if isinstance(cached, int):
            self._span.set_attribute("gen_ai.usage.cache_read.input_tokens", cached)
        reasoning = getattr(
            getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None
        )
        if isinstance(reasoning, int):
            self._span.set_attribute("gen_ai.usage.reasoning.output_tokens", reasoning)


@contextmanager
def inference_span(
    *,
    model: str,
    model_client: Any,
    max_tokens: int | None = None,
) -> Iterator[InferenceRecorder]:
    """Wrap one model call in a ``chat {model}`` CLIENT span."""
    attributes: dict[str, Any] = {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": PROVIDER_NAME,
        "gen_ai.request.model": model,
        **server_attributes(model_client),
    }
    span_attributes: dict[str, Any] = {**attributes, "gen_ai.output.type": "text"}
    if max_tokens is not None:
        span_attributes["gen_ai.request.max_tokens"] = max_tokens
    started_at = time.perf_counter()
    with tracer.start_as_current_span(
        f"chat {model}",
        kind=SpanKind.CLIENT,
        attributes=span_attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        recorder = InferenceRecorder(span, attributes)
        try:
            yield recorder
        except BaseException as exc:
            recorder.fail(error_type(exc))
            raise
        finally:
            operation_duration.record(time.perf_counter() - started_at, attributes)


@contextmanager
def execute_tool_span(
    *,
    tool_name: str,
    call_id: str | None,
) -> Iterator[SpanRecorder]:
    """Wrap one tool execution in an ``execute_tool {tool}`` INTERNAL span."""
    attributes: dict[str, Any] = {
        "gen_ai.operation.name": "execute_tool",
        "gen_ai.tool.name": tool_name,
        "gen_ai.tool.type": TOOL_TYPE,
        "gen_ai.agent.name": AGENT_NAME,
    }
    span_attributes = dict(attributes)
    if call_id:
        span_attributes["gen_ai.tool.call.id"] = call_id
    started_at = time.perf_counter()
    with tracer.start_as_current_span(
        f"execute_tool {tool_name}",
        kind=SpanKind.INTERNAL,
        attributes=span_attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        recorder = SpanRecorder(span, attributes)
        try:
            yield recorder
        except BaseException as exc:
            recorder.fail(error_type(exc))
            raise
        finally:
            tool_duration.record(time.perf_counter() - started_at, attributes)
