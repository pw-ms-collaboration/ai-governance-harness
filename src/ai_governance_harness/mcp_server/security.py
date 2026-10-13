"""Hosted HTTP request security for the MCP endpoint."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ai_governance_harness.mcp_server.config import ServerSettings
from ai_governance_harness.mcp_server.telemetry import (
    correlation_id_context,
    emit_audit_event,
    http_request_counter,
    http_request_duration,
    tracer,
)

_PUBLIC_PATHS = {
    "/health/live",
    "/health/ready",
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-protected-resource/mcp",
}


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class TokenBucketRateLimiter:
    """Process-local best-effort token bucket with bounded principal storage."""

    def __init__(
        self,
        capacity: int,
        refill_per_second: float,
        *,
        max_buckets: int = 10_000,
    ) -> None:
        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._max_buckets = max_buckets
        self._buckets: OrderedDict[str, _Bucket] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, principal_key: str) -> tuple[bool, int]:
        """Consume one token and return whether the request may proceed."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.pop(
                principal_key,
                _Bucket(tokens=float(self._capacity), updated_at=now),
            )
            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(
                float(self._capacity),
                bucket.tokens + elapsed * self._refill_per_second,
            )
            bucket.updated_at = now
            if bucket.tokens < 1:
                self._buckets[principal_key] = bucket
                retry_after = max(
                    1,
                    math.ceil((1 - bucket.tokens) / self._refill_per_second),
                )
                return False, retry_after

            bucket.tokens -= 1
            self._buckets[principal_key] = bucket
            while len(self._buckets) > self._max_buckets:
                self._buckets.popitem(last=False)
            return True, 0


def _decode_principal(header_value: str) -> dict[str, Any] | None:
    try:
        encoded = header_value + "=" * (-len(header_value) % 4)
        decoded = base64.b64decode(encoded, validate=True)
        if len(decoded) > 16_384:
            return None
        principal = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return principal if isinstance(principal, dict) else None


def _claim_values(principal: dict[str, Any]) -> dict[str, set[str]]:
    claims: dict[str, set[str]] = {}
    raw_claims = principal.get("claims")
    if not isinstance(raw_claims, list):
        return claims
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        claim_type = item.get("typ")
        claim_value = item.get("val")
        if isinstance(claim_type, str) and isinstance(claim_value, str):
            claims.setdefault(claim_type, set()).add(claim_value)
    return claims


def _contains_claim(
    claims: dict[str, set[str]],
    aliases: tuple[str, ...],
    expected: str,
) -> bool:
    return any(expected in claims.get(alias, set()) for alias in aliases)


def _validate_platform_principal(
    request: Request,
    settings: ServerSettings,
) -> tuple[str | None, str]:
    if request.headers.get("x-ms-client-principal-idp", "").lower() != "aad":
        return None, "invalid_identity_provider"

    principal_id = request.headers.get("x-ms-client-principal-id")
    encoded_principal = request.headers.get("x-ms-client-principal")
    if not principal_id or not encoded_principal:
        return None, "missing_platform_principal"

    principal = _decode_principal(encoded_principal)
    if principal is None:
        return None, "invalid_platform_principal"
    claims = _claim_values(principal)

    if not _contains_claim(
        claims,
        ("tid", "http://schemas.microsoft.com/identity/claims/tenantid"),
        settings.auth_tenant_id or "",
    ):
        return None, "invalid_tenant"
    if not _contains_claim(
        claims,
        ("aud",),
        settings.auth_audience or "",
    ):
        return None, "invalid_audience"

    scope_values = claims.get("scp", set())
    required_scope = settings.auth_required_scope or ""
    if not any(required_scope in value.split() for value in scope_values):
        return None, "missing_scope"

    principal_key = hashlib.sha256(principal_id.encode("utf-8")).hexdigest()
    return principal_key, "authenticated"


class RequestSecurityMiddleware(BaseHTTPMiddleware):
    """Reject unsafe MCP HTTP requests before protocol dispatch."""

    def __init__(self, app: Any, settings: ServerSettings) -> None:
        super().__init__(app)
        self._settings = settings
        self._limiter = TokenBucketRateLimiter(
            settings.rate_limit_capacity,
            settings.rate_limit_refill_per_second,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        correlation_id = str(uuid.uuid4())
        token = correlation_id_context.set(correlation_id)
        started_at = time.perf_counter()
        route_kind = "public" if request.url.path in _PUBLIC_PATHS else "mcp"
        outcome = "error"

        try:
            with tracer.start_as_current_span("http.server.request") as span:
                span.set_attribute("http.request.method", request.method)
                span.set_attribute("url.path", request.url.path)
                span.set_attribute(
                    "deployment.environment",
                    self._settings.environment,
                )

                rejection = await self._validate_request(request)
                if rejection is not None:
                    response = rejection
                else:
                    response = await call_next(request)
                outcome = "success" if response.status_code < 400 else "error"
                span.set_attribute("http.response.status_code", response.status_code)
                response.headers["X-Correlation-ID"] = correlation_id
                return response
        finally:
            elapsed = time.perf_counter() - started_at
            metric_attributes = {
                "http.request.method": request.method,
                "http.route.kind": route_kind,
                "outcome": outcome,
            }
            http_request_counter.add(1, metric_attributes)
            http_request_duration.record(elapsed, metric_attributes)
            correlation_id_context.reset(token)

    async def _validate_request(self, request: Request) -> Response | None:
        if request.url.path in _PUBLIC_PATHS:
            return None
        if request.url.path != self._settings.mcp_path:
            return JSONResponse({"error": "Not found."}, status_code=404)

        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in self._settings.allowed_origins:
            return JSONResponse({"error": "Origin is not allowed."}, status_code=403)

        if request.method == "POST":
            content_type = request.headers.get("content-type", "").split(";", 1)[0]
            if content_type.lower() != "application/json":
                return JSONResponse(
                    {"error": "Content type must be application/json."},
                    status_code=415,
                )
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    declared_size = int(content_length)
                except ValueError:
                    return JSONResponse(
                        {"error": "Content length is invalid."},
                        status_code=400,
                    )
                if declared_size > self._settings.max_request_body_size:
                    return JSONResponse({"error": "Request is too large."}, status_code=413)
            body = await request.body()
            if len(body) > self._settings.max_request_body_size:
                return JSONResponse({"error": "Request is too large."}, status_code=413)

        protocol_version = request.headers.get("mcp-protocol-version")
        if (
            protocol_version
            and protocol_version not in self._settings.supported_protocol_versions
        ):
            return JSONResponse(
                {"error": "Unsupported MCP protocol version."},
                status_code=400,
            )

        principal_key = "local-development"
        if self._settings.hosted:
            principal_key, auth_outcome = _validate_platform_principal(
                request,
                self._settings,
            )
            emit_audit_event(
                "mcp.authentication",
                outcome="success" if principal_key else "rejected",
                settings=self._settings,
                authentication_outcome=auth_outcome,
            )
            if principal_key is None:
                return JSONResponse(
                    {"error": "Authentication is required."},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )

        allowed, retry_after = self._limiter.allow(principal_key)
        if not allowed:
            return JSONResponse(
                {"error": "Rate limit exceeded."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        return None
