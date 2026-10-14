"""Starlette web application for the browser chat experience."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.chat.insights import InsightsHistory, InsightsUnavailableError
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
        routes=[
            Route("/", index, methods=["GET"]),
            Route("/static/app.css", stylesheet, methods=["GET"]),
            Route("/static/app.js", javascript, methods=["GET"]),
            Route("/static/insights.js", insights_javascript, methods=["GET"]),
            Route("/static/tabs.js", tabs_javascript, methods=["GET"]),
            Route("/static/flow.js", flow_javascript, methods=["GET"]),
            Route("/api/chat", chat, methods=["POST"]),
            Route("/api/observability/history", insights_history, methods=["GET"]),
            Route(
                "/api/governance/snapshot",
                governance_snapshot,
                methods=["GET"],
            ),
            Route("/health/live", liveness, methods=["GET"]),
            Route("/health/ready", readiness, methods=["GET"]),
        ]
    )
    app.add_middleware(BrowserSecurityMiddleware, settings=settings)
    return app
