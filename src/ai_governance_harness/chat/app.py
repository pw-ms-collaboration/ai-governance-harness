"""Starlette web application for the browser chat experience."""

from __future__ import annotations

from pathlib import Path

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
        return JSONResponse({"status": "ready"})

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
            Route("/health/live", liveness, methods=["GET"]),
            Route("/health/ready", readiness, methods=["GET"]),
        ]
    )
    app.add_middleware(BrowserSecurityMiddleware, settings=settings)
    return app
