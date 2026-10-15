"""Starlette web application for the browser chat experience."""

from __future__ import annotations

import base64
import hashlib
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
from ai_governance_harness.identity.sidecar import SidecarClient
from ai_governance_harness.mock_identity_guard import require_mock_identity_allowed

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = logging.getLogger(__name__)


def _hosted_principal_hash(request: Request, settings: ChatSettings) -> str | None:
    """Read bounded user claims injected by the required EasyAuth boundary."""
    encoded = request.headers.getlist("x-ms-client-principal")
    principal_ids = request.headers.getlist("x-ms-client-principal-id")
    providers = request.headers.getlist("x-ms-client-principal-idp")
    if len(encoded) != 1 or len(principal_ids) != 1 or providers != ["aad"]:
        return None
    if (
        len(encoded[0]) > 24_000
        or not 1 <= len(principal_ids[0]) <= 128
        or not principal_ids[0].strip()
    ):
        return None
    try:
        document = json.loads(base64.b64decode(encoded[0], validate=True))
        if not isinstance(document, dict) or not isinstance(document.get("claims"), list):
            return None
        aliases = {
            "http://schemas.microsoft.com/identity/claims/tenantid": "tid",
            "http://schemas.microsoft.com/identity/claims/objectidentifier": "oid",
        }
        claims: dict[str, str] = {}
        for item in document["claims"]:
            if not isinstance(item, dict):
                return None
            name, value = item.get("typ"), item.get("val")
            if not isinstance(name, str) or not isinstance(value, str):
                return None
            name = aliases.get(name, name)
            if name in {"tid", "aud", "oid", "idtyp"}:
                if name in claims:
                    return None
                claims[name] = value
        if (
            claims.get("tid") != settings.auth_tenant_id
            or claims.get("aud") != settings.auth_audience
            or claims.get("oid") != principal_ids[0]
            or claims.get("idtyp", "user") != "user"
        ):
            return None
    except (ValueError, UnicodeDecodeError):
        return None
    return hashlib.sha256(principal_ids[0].encode("utf-8")).hexdigest()


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
        principal_hash = None
        if self._settings.hosted:
            if request.url.path == "/api/mock-identity/signin":
                return JSONResponse({"error": "Not found."}, status_code=404)
            if request.url.path not in {"/health/live", "/health/ready"}:
                principal_hash = _hosted_principal_hash(request, self._settings)
                if principal_hash is None:
                    return JSONResponse(
                        {"error": {
                            "code": "authentication_required",
                            "message": "Sign in through Microsoft Entra.",
                            "correlation_id": correlation_id,
                        }},
                        status_code=401,
                        headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
                    )
        context = GovernanceContext(
            boundary="chat",
            workload_id="ai-governance-harness",
            environment="production" if self._settings.hosted else "local",
            correlation_id=correlation_id,
            authentication_outcome="authenticated" if principal_hash else "local",
            principal_hash=principal_hash,
            actor="interactive" if principal_hash else None,
            token_type="user" if principal_hash else None,
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
    sidecar = None if settings.hosted else SidecarClient(
        settings.sidecar_url,
        timeout=get_governance_engine().settings.operation_timeout_seconds,
    )
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

    async def identity_mode(_: Request) -> JSONResponse:
        return JSONResponse({"mode": "easy_auth" if settings.hosted else "mock"})

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
            return JSONResponse({"error": "Check AZURE_AI_EVAL_JUDGE_DEPLOYMENT_NAME, AZURE_AI_PROJECT_ENDPOINT, and the evaluator registry before running an evaluation. AZURE_AI_EVALUATOR_REGISTRY is an optional path override."}, status_code=503)
        except (OSError, ValueError) as error:
            logger.warning("Managed evaluation job access failed: %s", type(error).__name__)
            return JSONResponse({"error": "Managed evaluation job artifacts could not be read or created."}, status_code=500)

    def service_error(error: ChatServiceError) -> JSONResponse:
        public_error: dict[str, object] = {
            "code": error.code, "message": str(error),
            "correlation_id": get_governance_context().correlation_id or "unavailable",
        }
        if error.details:
            public_error["details"] = error.details
        return JSONResponse(
            {"error": public_error}, status_code=error.status_code,
            headers={"WWW-Authenticate": "Bearer"} if error.status_code == 401 else {},
        )

    async def signin(request: Request) -> JSONResponse:
        if sidecar is None:
            return JSONResponse({"error": "Not found."}, status_code=404)
        if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
            return JSONResponse({"error": "Content type must be application/json."}, status_code=415)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                return JSONResponse({"error": "Request is too large."}, status_code=413)
        try:
            require_mock_identity_allowed("chat-signin", bind_host=settings.host)
            status, document = await sidecar.signin(bytes(body))
        except ValueError:
            return JSONResponse({"error": "Not found."}, status_code=404)
        except ChatServiceError as error:
            return service_error(error)
        return JSONResponse(document, status_code=status, headers={"Cache-Control": "no-store"})

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
            if settings.hosted:
                result = await chat_service.complete(payload, None)
                return JSONResponse(result.model_dump())
            if sidecar is None:
                raise RuntimeError("Local identity sidecar is unavailable.")
            caller = await sidecar.validate(request.headers.getlist("authorization"))
            context = get_governance_context().model_copy(update={
                "boundary": "chat", "actor": "interactive", "token_type": "user",
                "principal_hash": caller.principal_hash, "authentication_outcome": "authenticated",
            })
            with governance_context(context):
                result = await chat_service.complete(payload, caller)
        except ChatServiceError as error:
            return service_error(error)
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
            Route("/api/identity", identity_mode, methods=["GET"]),
            Route("/api/mock-identity/signin", signin, methods=["POST"]),
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
