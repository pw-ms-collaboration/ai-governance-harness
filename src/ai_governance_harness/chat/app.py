"""Starlette web application for the browser chat experience."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import anyio
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.chat.evaluations import LocalEvaluationJobs
from ai_governance_harness.chat.foundry_evaluations import routes as foundry_routes
from ai_governance_harness.chat.insights import InsightsHistory, InsightsUnavailableError
from ai_governance_harness.chat.managed_evaluations import ManagedEvaluationJobs
from ai_governance_harness.evaluation.agent_contracts import AgentEvaluationError
from ai_governance_harness.chat.service import (
    ChatRequest,
    ChatService,
    ChatServiceError,
)
from ai_governance_harness.governance import (
    GovernanceContext,
    get_governance_engine,
    get_governance_context,
    governance_context,
)
from ai_governance_harness.governance.sandbox import SandboxGuard

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = logging.getLogger(__name__)


class BrowserSecurityMiddleware(BaseHTTPMiddleware):
    """Apply origin checks and browser security headers."""

    def __init__(self, app, settings: ChatSettings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in self._settings.allowed_origins:
            return JSONResponse({"error": "Origin is not allowed."}, status_code=403)

        correlation_id = request.headers.get("x-correlation-id") or uuid4().hex
        context = GovernanceContext(
            workload_id="ai-governance-harness",
            environment="local",
            correlation_id=correlation_id,
            authentication_outcome="local",
        )
        with governance_context(context):
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response


def build_chat_app(
    settings: ChatSettings,
    service: ChatService | None = None,
    *,
    evaluation_directory: Path = Path(".local/evaluations"),
) -> Starlette:
    """Build the static UI and chat API application."""
    chat_service = service or ChatService(settings)
    insights = InsightsHistory(settings.application_insights_app_id)
    pricing = {
        "currency": settings.token_price_currency,
        "input_per_million": settings.token_price_input_per_million,
        "cached_input_per_million": settings.token_price_cached_input_per_million,
        "output_per_million": settings.token_price_output_per_million,
        "model": settings.model_deployment,
    }

    async def insights_history(request: Request) -> JSONResponse:
        if settings.host not in {"127.0.0.1", "localhost", "::1"}:
            return JSONResponse(
                {"error": "Azure history is available only with a loopback chat binding."},
                status_code=403,
            )
        host = request.url.hostname
        if host not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return JSONResponse({"error": "History host is not allowed."}, status_code=403)
        try:
            hours = int(request.query_params.get("hours", "1"))
            if hours not in (1, 4, 24):
                raise ValueError
        except ValueError:
            return JSONResponse({"error": "Select a 1, 4, or 24 hour range."}, status_code=400)
        try:
            snapshot = await insights.snapshot(hours)
        except InsightsUnavailableError as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)
        return JSONResponse(
            {**snapshot, "pricing": pricing}, headers={"Cache-Control": "no-store"}
        )

    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with anyio.create_task_group() as tasks:
            app.state.evaluation_jobs = LocalEvaluationJobs(evaluation_directory, tasks)
            app.state.managed_evaluation_jobs = ManagedEvaluationJobs(
                evaluation_directory, tasks, settings.model_deployment
            )
            yield
            tasks.cancel_scope.cancel()

    async def index(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    async def stylesheet(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "app.css", media_type="text/css")

    async def javascript(_: Request) -> FileResponse:
        return FileResponse(
            STATIC_DIR / "app.js",
            media_type="text/javascript",
        )

    async def insights_javascript(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "insights.js", media_type="text/javascript")

    async def tabs_javascript(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "tabs.js", media_type="text/javascript")

    async def flow_javascript(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "flow.js", media_type="text/javascript")

    async def foundry_javascript(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "foundry-evaluations.js", media_type="text/javascript")

    async def liveness(_: Request) -> JSONResponse:
        return JSONResponse({"status": "live"})

    async def readiness(_: Request) -> JSONResponse:
        governance = get_governance_engine()
        sandbox = SandboxGuard(governance.settings)
        ready = governance.ready and sandbox.ready
        status = "ready" if ready else "not_ready"
        return JSONResponse(
            {
                "status": status,
                "governance": {
                    "status": "ready" if governance.ready else "not_ready",
                    "enforcement": (
                        "enabled"
                        if governance.settings.enabled
                        else "disabled_for_test"
                    ),
                    "policy_digest": governance.policy_digest,
                },
                "sandbox": {
                    "status": (
                        "not_required_for_read_only"
                        if sandbox.provider_kind == "none"
                        else ("ready" if sandbox.ready else "not_ready")
                    ),
                    "provider": sandbox.provider_kind,
                },
            },
            status_code=200 if ready else 503,
        )

    async def governance_snapshot(_: Request) -> JSONResponse:
        return JSONResponse(await chat_service.governance_snapshot())

    async def evaluations(request: Request) -> JSONResponse:
        jobs: LocalEvaluationJobs = request.app.state.evaluation_jobs
        try:
            if request.method == "POST":
                already_running = jobs.active_run_id is not None
                job = jobs.start()
                return JSONResponse(
                    job.model_dump(mode="json"),
                    status_code=409 if already_running else 202,
                    headers={"Cache-Control": "no-store"},
                )
            run_id = request.path_params.get("run_id")
            job = jobs.read(run_id) if run_id is not None else jobs.latest()
            return JSONResponse(
                job.model_dump(mode="json") if job else None,
                headers={"Cache-Control": "no-store"},
            )
        except FileNotFoundError:
            return JSONResponse({"error": "Evaluation run not found."}, status_code=404)
        except (OSError, ValueError):
            logger.exception("Could not access local evaluation job.")
            return JSONResponse(
                {"error": "Local evaluation artifacts could not be read or created."},
                status_code=500,
            )

    async def managed_evaluations(request: Request) -> JSONResponse:
        if settings.host not in {"127.0.0.1", "localhost", "::1"} or request.url.hostname not in {
            "127.0.0.1", "localhost", "::1", "testserver",
        }:
            return JSONResponse({"error": "Managed evaluation requires a loopback chat binding."}, status_code=403)
        jobs: ManagedEvaluationJobs = request.app.state.managed_evaluation_jobs
        try:
            if request.method == "POST":
                if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
                    return JSONResponse({"error": "Content type must be application/json."}, status_code=415)
                body = await request.body()
                if len(body) > settings.max_request_body_size:
                    return JSONResponse({"error": "Request is too large."}, status_code=413)
                try:
                    confirmation = json.loads(body)
                except (json.JSONDecodeError, UnicodeError):
                    confirmation = None
                if not isinstance(confirmation, dict) or set(confirmation) != {
                    "confirm_inference", "confirm_submit",
                } or any(value is not True for value in confirmation.values()):
                    return JSONResponse({"error": "Confirm model inference and Foundry submission before starting an evaluation."}, status_code=400)
                already_running = jobs.active_run_id is not None
                job = jobs.start()
                return JSONResponse(job.model_dump(mode="json"), status_code=409 if already_running else 202)
            run_id = request.path_params.get("run_id")
            job = jobs.read(run_id) if run_id else jobs.latest()
            return JSONResponse(job.model_dump(mode="json") if job else None)
        except FileNotFoundError:
            return JSONResponse({"error": "Managed evaluation job not found."}, status_code=404)
        except AgentEvaluationError as error:
            logger.warning("Managed evaluation configuration failed: %s", type(error).__name__)
            return JSONResponse({"error": "Check AZURE_AI_EVALUATOR_REGISTRY, AZURE_AI_EVAL_JUDGE_DEPLOYMENT_NAME, and AZURE_AI_PROJECT_ENDPOINT before running an evaluation."}, status_code=503)
        except (OSError, ValueError) as error:
            logger.warning("Managed evaluation job access failed: %s", type(error).__name__)
            return JSONResponse({"error": "Managed evaluation job artifacts could not be read or created."}, status_code=500)

    async def chat(request: Request) -> JSONResponse:
        content_type = request.headers.get("content-type", "").split(";", 1)[0]
        if content_type.lower() != "application/json":
            return JSONResponse(
                {"error": "Content type must be application/json."},
                status_code=415,
            )
        body = await request.body()
        if len(body) > settings.max_request_body_size:
            return JSONResponse({"error": "Request is too large."}, status_code=413)
        try:
            payload = ChatRequest.model_validate_json(body)
        except ValidationError:
            return JSONResponse(
                {"error": "The chat request is invalid."},
                status_code=400,
            )
        try:
            result = await chat_service.complete(payload)
        except ChatServiceError as error:
            public_error: dict[str, object] = {
                "code": error.code,
                "message": str(error),
                "correlation_id": (
                    get_governance_context().correlation_id or "unavailable"
                ),
            }
            if error.details:
                public_error["details"] = error.details
            return JSONResponse(
                {"error": public_error},
                status_code=error.status_code,
            )
        return JSONResponse(result.model_dump())

    app = Starlette(
        lifespan=lifespan,
        routes=[
            *foundry_routes(settings),
            Route("/api/foundry/evaluation-jobs", managed_evaluations, methods=["GET", "POST"]),
            Route("/api/foundry/evaluation-jobs/{run_id}", managed_evaluations, methods=["GET"]),
            Route("/", index, methods=["GET"]),
            Route("/static/app.css", stylesheet, methods=["GET"]),
            Route("/static/app.js", javascript, methods=["GET"]),
            Route("/static/insights.js", insights_javascript, methods=["GET"]),
            Route("/static/tabs.js", tabs_javascript, methods=["GET"]),
            Route("/static/flow.js", flow_javascript, methods=["GET"]),
            Route("/static/foundry-evaluations.js", foundry_javascript, methods=["GET"]),
            Route("/api/chat", chat, methods=["POST"]),
            Route("/api/observability/history", insights_history, methods=["GET"]),
            Route(
                "/api/governance/snapshot",
                governance_snapshot,
                methods=["GET"],
            ),
            Route(
                "/api/governance/evaluations",
                evaluations,
                methods=["GET", "POST"],
            ),
            Route(
                "/api/governance/evaluations/{run_id}",
                evaluations,
                methods=["GET"],
            ),
            Route("/health/live", liveness, methods=["GET"]),
            Route("/health/ready", readiness, methods=["GET"]),
        ]
    )
    app.add_middleware(BrowserSecurityMiddleware, settings=settings)
    return app
