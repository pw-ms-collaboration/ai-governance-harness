"""Starlette application for hosted MCP, health, and authorization discovery."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.concurrency import run_in_threadpool

from ai_governance_harness.governance import get_governance_engine
from ai_governance_harness.governance.sandbox import SandboxGuard
from ai_governance_harness.governance.snapshot import build_governance_snapshot
from ai_governance_harness.mcp_server.config import ServerSettings
from ai_governance_harness.mcp_server.security import RequestSecurityMiddleware
from ai_governance_harness.mcp_server.server import mcp
from ai_governance_harness.identity.verification import JwtVerifier


def build_http_app(settings: ServerSettings) -> Starlette:
    """Build the session-based MCP HTTP app and its public operational routes."""
    verifier = None
    if settings.principal_source == "jwt":
        if not (settings.jwt_issuer and settings.jwt_jwks_url and settings.auth_audience and settings.auth_tenant_id):
            raise ValueError("JWT configuration is incomplete.")
        verifier = JwtVerifier(
            issuer=settings.jwt_issuer,
            jwks_url=settings.jwt_jwks_url,
            audience=settings.auth_audience,
            tenant=settings.auth_tenant_id,
            timeout=min(get_governance_engine().settings.operation_timeout_seconds, 5),
        )
        verifier.refresh()

    async def liveness(_: Request) -> JSONResponse:
        return JSONResponse({"status": "live"})

    async def readiness(_: Request) -> JSONResponse:
        governance = get_governance_engine()
        sandbox = SandboxGuard(governance.settings)
        if verifier is not None and not verifier.ready:
            await run_in_threadpool(verifier.refresh)
        ready = governance.ready and sandbox.ready and (verifier is None or verifier.ready)
        status = "ready" if ready else "not_ready"
        return JSONResponse(
            {
                "status": status,
                "identity": {
                    "principal_source": settings.principal_source,
                    "jwks": "not_required" if verifier is None else ("loaded" if verifier.ready else "unavailable"),
                },
                "governance": {
                    "status": status,
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
        governance = get_governance_engine()
        return JSONResponse(
            build_governance_snapshot(
                governance,
                source="mcp",
            )
        )

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
        stateless_http=False,
        max_request_body_size=settings.max_request_body_size,
        host=settings.host,
    )
    app.routes.extend(
        [
            Route("/health/live", liveness, methods=["GET"]),
            Route("/health/ready", readiness, methods=["GET"]),
            Route(
                "/governance/snapshot",
                governance_snapshot,
                methods=["GET"],
            ),
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
    app.add_middleware(RequestSecurityMiddleware, settings=settings, verifier=verifier)
    return app
