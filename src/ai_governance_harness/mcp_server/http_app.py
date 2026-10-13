"""Starlette application for hosted MCP, health, and authorization discovery."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ai_governance_harness.mcp_server.config import ServerSettings
from ai_governance_harness.mcp_server.security import RequestSecurityMiddleware
from ai_governance_harness.mcp_server.server import mcp


def build_http_app(settings: ServerSettings) -> Starlette:
    """Build the stateless MCP HTTP app and its public operational routes."""

    async def liveness(_: Request) -> JSONResponse:
        return JSONResponse({"status": "live"})

    async def readiness(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ready"})

    async def protected_resource_metadata(_: Request) -> JSONResponse:
        if not all(
            (
                settings.resource_url,
                settings.auth_tenant_id,
                settings.auth_required_scope,
            )
        ):
            return JSONResponse({"error": "Not configured."}, status_code=404)
        issuer = f"https://login.microsoftonline.com/{settings.auth_tenant_id}/v2.0"
        return JSONResponse(
            {
                "resource": settings.resource_url,
                "authorization_servers": [issuer],
                "bearer_methods_supported": ["header"],
                "scopes_supported": [settings.auth_required_scope],
            }
        )

    app = mcp.streamable_http_app(
        streamable_http_path=settings.mcp_path,
        json_response=settings.json_response,
        stateless_http=True,
        max_request_body_size=settings.max_request_body_size,
        host=settings.host,
    )
    app.routes.extend(
        [
            Route("/health/live", liveness, methods=["GET"]),
            Route("/health/ready", readiness, methods=["GET"]),
            Route(
                "/.well-known/oauth-protected-resource",
                protected_resource_metadata,
                methods=["GET"],
            ),
            Route(
                "/.well-known/oauth-protected-resource/mcp",
                protected_resource_metadata,
                methods=["GET"],
            ),
        ]
    )
    app.add_middleware(RequestSecurityMiddleware, settings=settings)
    return app
