"""Read-only, paginated Foundry evaluation views for the local browser UI."""

import json
import logging
import math
import os
import re
from functools import partial
from urllib.parse import urlsplit

import anyio
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import AzureError
from openai import OpenAIError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.evaluation.agent_contracts import (
    AgentEvaluationError,
    private_text,
)
from ai_governance_harness.evaluation.register_agent_evaluators import (
    FOUNDRY_HEADERS,
    _validate_endpoint,
)
from ai_governance_harness.foundry_client import get_azure_credential

logger = logging.getLogger(__name__)
IDENTITY = re.compile(r"[A-Za-z0-9_.-]{1,256}")


def safe_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Invalid Foundry text field.")
    if not value.strip():
        return ""
    try:
        return private_text(value)
    except AgentEvaluationError:
        return "[Content withheld by the evaluation privacy guard]"


def report_link(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme == "https"
        and parsed.hostname in {"ai.azure.com", "foundry.azure.com"}
        and not parsed.username
        and not parsed.password
        and safe_text(value) == value
    ):
        return value
    return None


def run_summary(run: dict) -> dict:
    return {
        "id": run["id"],
        "name": safe_text(run.get("name")),
        "created_at": run.get("created_at"),
        "status": safe_text(run.get("status")),
        "counts": run.get("result_counts"),
        "report_url": report_link(run.get("report_url")),
        "error": safe_text((run.get("error") or {}).get("message")),
    }


def sample_response(sample: dict) -> str | None:
    parts = []
    for message in sample.get("output") or []:
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, str):
            if content.lstrip().startswith("{"):
                try:
                    envelope = json.loads(content)
                except json.JSONDecodeError:
                    envelope = None
                if (
                    isinstance(envelope, dict)
                    and envelope.get("type") == "output_text"
                    and isinstance(envelope.get("text"), str)
                    and set(envelope) <= {"type", "text", "annotations", "logprobs"}
                ):
                    content = envelope["text"]
            parts.append(content)
        elif isinstance(content, list):
            for part in content:
                if part.get("type") in {"text", "output_text"}:
                    parts.append(part["text"])
                elif part.get("type") == "refusal":
                    parts.append(part["refusal"])
    return safe_text("\n".join(parts)) if parts else None


def output_item(item: dict) -> dict:
    data = item.get("datasource_item") or {}
    item_error = item.get("error") or (item.get("sample") or {}).get("error")
    if isinstance(item_error, dict) and not any(item_error.values()):
        item_error = None
    metrics = []
    for metric in item.get("results") or []:
        error = metric.get("error") or item_error
        status = metric.get("status", "completed")
        if item.get("status") in {"error", "skipped", "failed"}:
            status = item["status"]
        score = metric.get("score")
        passed = metric.get("passed")
        valid_score = type(score) in (int, float, bool) and math.isfinite(score)
        if (
            error
            or status != "completed"
            or not valid_score
            or type(passed) is not bool
        ):
            status = "error" if error or status == "completed" else status
            score = passed = None
        metrics.append(
            {
                "name": safe_text(metric.get("name")),
                "status": status,
                "score": score,
                "passed": passed,
                "reason": safe_text(metric.get("reason")),
                "error": safe_text(
                    error.get("message") if isinstance(error, dict) else error
                ),
            }
        )
    return {
        "id": item["id"],
        "case_id": safe_text(data.get("id") or data.get("case_id")),
        "category": safe_text(data.get("category")),
        "status": safe_text(item.get("status")),
        "prompt": safe_text(data.get("prompt")),
        "response": (
            safe_text(data["response"])
            if data.get("response") is not None
            else sample_response(item.get("sample") or {})
        ),
        "expected_behavior": safe_text(data.get("expected_behavior")),
        "metrics": metrics,
    }


def page_payload(page, mapper) -> dict:
    rows = [
        mapper(item.model_dump(mode="json", exclude={"data_source"}))
        for item in page.data
    ]
    if any(
        not isinstance(row["id"], str) or not IDENTITY.fullmatch(row["id"])
        for row in rows
    ):
        raise ValueError("Invalid Foundry item identity.")
    more = page.has_next_page()
    if more and not rows:
        raise ValueError("Invalid empty Foundry page.")
    return {
        "items": rows,
        "next": rows[-1]["id"] if more else None,
        "source": "foundry",
    }


def read_foundry(eval_id: str | None, run_id: str | None, after: str | None) -> dict:
    endpoint = _validate_endpoint(os.getenv("AZURE_AI_PROJECT_ENDPOINT"))
    options = {"limit": 20, "order": "desc", "extra_headers": FOUNDRY_HEADERS}
    if after:
        options["after"] = after
    with get_azure_credential() as credential:
        with AIProjectClient(
            endpoint=endpoint,
            credential=credential,
            retry_total=0,
            connection_timeout=30,
            read_timeout=30,
        ) as project:
            with project.get_openai_client(timeout=30, max_retries=0) as client:
                if eval_id is None:
                    return page_payload(
                        client.evals.list(**options),
                        lambda row: {
                            "id": row["id"],
                            "name": safe_text(row.get("name")),
                        },
                    )
                if run_id is None:
                    return page_payload(
                        client.evals.runs.list(eval_id=eval_id, **options),
                        run_summary,
                    )
                run = client.evals.runs.retrieve(
                    run_id=run_id,
                    eval_id=eval_id,
                    extra_headers=FOUNDRY_HEADERS,
                ).model_dump(mode="json", exclude={"data_source"})
                if run.get("eval_id") != eval_id or run.get("id") != run_id:
                    raise ValueError("Foundry run identity mismatch.")
                page = client.evals.runs.output_items.list(
                    run_id=run_id,
                    eval_id=eval_id,
                    **options,
                )
                if any(
                    item.eval_id != eval_id or item.run_id != run_id
                    for item in page.data
                ):
                    raise ValueError("Foundry output identity mismatch.")
                return {**page_payload(page, output_item), "run": run_summary(run)}


def routes(settings: ChatSettings) -> list[Route]:
    async def endpoint(request: Request) -> JSONResponse:
        if settings.host not in {
            "127.0.0.1",
            "localhost",
            "::1",
        } or request.url.hostname not in {
            "127.0.0.1",
            "localhost",
            "::1",
            "testserver",
        }:
            return JSONResponse(
                {"error": "Foundry results require a loopback chat binding."},
                status_code=403,
            )
        eval_id = request.path_params.get("eval_id")
        run_id = request.path_params.get("run_id")
        after = request.query_params.get("after")
        if any(
            value is not None and not IDENTITY.fullmatch(value)
            for value in (eval_id, run_id, after)
        ):
            return JSONResponse(
                {"error": "Invalid Foundry resource or cursor."}, status_code=400
            )
        try:
            payload = await anyio.to_thread.run_sync(
                partial(read_foundry, eval_id, run_id, after)
            )
        except AgentEvaluationError:
            return JSONResponse(
                {
                    "error": "Configure a valid AZURE_AI_PROJECT_ENDPOINT to read Foundry results."
                },
                status_code=503,
            )
        except (AzureError, OpenAIError) as error:
            logger.warning("Foundry evaluation read failed: %s", type(error).__name__)
            return JSONResponse(
                {
                    "error": "Foundry results could not be retrieved. Check project access and try again."
                },
                status_code=502,
            )
        except (ValueError, KeyError, TypeError) as error:
            logger.warning(
                "Invalid Foundry evaluation response: %s", type(error).__name__
            )
            return JSONResponse(
                {"error": "Foundry returned invalid evaluation data."}, status_code=502
            )
        return JSONResponse(payload)

    return [
        Route("/api/foundry/evaluations", endpoint, methods=["GET"]),
        Route("/api/foundry/evaluations/{eval_id}/runs", endpoint, methods=["GET"]),
        Route(
            "/api/foundry/evaluations/{eval_id}/runs/{run_id}",
            endpoint,
            methods=["GET"],
        ),
    ]
