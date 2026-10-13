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
from ai_governance_harness.chat.service import (
    ChatRequest,
    ChatService,
    ChatServiceError,
)
from ai_governance_harness.governance import (
    GovernanceContext,
    LifecyclePoint,
    get_governance_engine,
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
        return response


def build_chat_app(
    settings: ChatSettings,
    service: ChatService | None = None,
) -> Starlette:
    """Build the static UI and chat API application."""
    chat_service = service or ChatService(settings)

    async def index(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    async def stylesheet(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "app.css", media_type="text/css")

    async def javascript(_: Request) -> FileResponse:
        return FileResponse(
            STATIC_DIR / "app.js",
            media_type="text/javascript",
        )

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

    async def demonstrate_default_deny(_: Request) -> JSONResponse:
        decision = get_governance_engine().evaluate(
            LifecyclePoint.PRE_TOOL,
            "demo.prohibited_action",
            policy_data={"inert_demonstration": True},
            source="demo",
        )
        return JSONResponse(
            {
                "executed": False,
                "decision": decision.action,
                "allowed": decision.allowed,
                "lifecycle_point": decision.lifecycle_point.value,
                "matched_rule": decision.matched_rule,
                "message": (
                    "A fixed prohibited action was evaluated. "
                    "No operation was executed."
                ),
            }
        )

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
        except ChatServiceError:
            return JSONResponse(
                {"error": "The chat service could not complete the request."},
                status_code=502,
            )
        return JSONResponse(result.model_dump())

    app = Starlette(
        routes=[
            Route("/", index, methods=["GET"]),
            Route("/static/app.css", stylesheet, methods=["GET"]),
            Route("/static/app.js", javascript, methods=["GET"]),
            Route("/api/chat", chat, methods=["POST"]),
            Route(
                "/api/governance/snapshot",
                governance_snapshot,
                methods=["GET"],
            ),
            Route(
                "/api/governance/demo/deny",
                demonstrate_default_deny,
                methods=["POST"],
            ),
            Route("/health/live", liveness, methods=["GET"]),
            Route("/health/ready", readiness, methods=["GET"]),
        ]
    )
    app.add_middleware(BrowserSecurityMiddleware, settings=settings)
    return app
