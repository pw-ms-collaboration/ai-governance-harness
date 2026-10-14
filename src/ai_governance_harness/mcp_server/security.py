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
from dataclasses import asdict
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from ai_governance_harness.identity.claims import (
    NormalizedIdentity,
    Rejection,
    normalize_claims,
)
from ai_governance_harness.identity.constants import STAFF_ROLES
from ai_governance_harness.identity.tokens import InvalidIdentityToken, bearer_token
from ai_governance_harness.identity.verification import JwtVerifier

from ai_governance_harness.governance.context import (
    GovernanceContext,
    get_governance_context,
    reset_governance_context,
    set_governance_context,
)
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
_LOCAL_OPERATIONAL_PATHS = {
    "/governance/snapshot",
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
) -> NormalizedIdentity | Rejection:
    if request.headers.get("x-ms-client-principal-idp", "").lower() != "aad":
        return Rejection("invalid_platform_principal")

    principal_id = request.headers.get("x-ms-client-principal-id")
    encoded_principal = request.headers.get("x-ms-client-principal")
    if not principal_id or not encoded_principal:
        return Rejection("invalid_platform_principal")

    principal = _decode_principal(encoded_principal)
    if principal is None:
        return Rejection("invalid_platform_principal")
    claims = _claim_values(principal)

    if not _contains_claim(
        claims,
        ("tid", "http://schemas.microsoft.com/identity/claims/tenantid"),
        settings.auth_tenant_id or "",
    ):
        return Rejection("invalid_tenant")
    allowed_audiences = settings.auth_audiences or (
        (settings.auth_audience,) if settings.auth_audience else ()
    )
    matched_audience = next(
        (audience for audience in allowed_audiences
         if _contains_claim(claims, ("aud",), audience)),
        None,
    )
    if matched_audience is None:
        return Rejection("invalid_audience")

    request_path = request.scope.get("path", "")
    required_role = (
        settings.auth_snapshot_role
        if request_path in _LOCAL_OPERATIONAL_PATHS and settings.auth_snapshot_role
        else settings.auth_required_role
    )
    if required_role:
        if not _contains_claim(
            claims,
            (
                "roles",
                "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
            ),
            required_role,
        ):
            return Rejection("invalid_platform_principal")
    else:
        scope_values = claims.get("scp", set())
        required_scope = settings.auth_required_scope or ""
        if not any(required_scope in value.split() for value in scope_values):
            return Rejection("invalid_platform_principal")
    aliases = {
        "http://schemas.microsoft.com/identity/claims/objectidentifier": "oid",
        "http://schemas.microsoft.com/ws/2008/06/identity/claims/role": "roles",
        "http://schemas.microsoft.com/identity/claims/scope": "scp",
    }
    normalized: dict[str, object] = {}
    for name, values in claims.items():
        name = aliases.get(name, name)
        if name in normalized:
            return Rejection("invalid_platform_principal")
        if name in {"roles", "xms_act_fct", "xms_sub_fct"}:
            normalized[name] = [part for value in values for part in value.split()]
        elif len(values) == 1:
            normalized[name] = next(iter(values))
        else:
            return Rejection("invalid_platform_principal")
    if not settings.interactive_agent_id or not settings.reporting_agent_id:
        role_values = normalized.get("roles", [])
        staff_roles = [role for role in role_values if role in STAFF_ROLES]
        staff_role = STAFF_ROLES[staff_roles[0]] if len(staff_roles) == 1 else "none"
        return NormalizedIdentity(
            actor="interactive",
            token_type="user",
            staff_role=staff_role,
            principal_hash=hashlib.sha256(principal_id.encode("utf-8")).hexdigest(),
        )
    identity_settings = settings.model_copy(update={"auth_audience": matched_audience})
    return normalize_claims(normalized, settings=identity_settings)


class RequestSecurityMiddleware(BaseHTTPMiddleware):
    """Reject unsafe MCP HTTP requests before protocol dispatch."""

    def __init__(self, app: Any, settings: ServerSettings, verifier: JwtVerifier | None = None) -> None:
        super().__init__(app)
        self._settings = settings
        self._verifier = verifier
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
        governance_token = set_governance_context(
            GovernanceContext(
                boundary="mcp",
                workload_id="ai-governance-harness",
                environment=self._settings.environment,
                correlation_id=correlation_id,
                authentication_outcome=(
                    "unauthenticated" if self._settings.hosted else "local"
                ),
            )
        )
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
            reset_governance_context(governance_token)
            correlation_id_context.reset(token)

    async def _validate_request(self, request: Request) -> Response | None:
        if request.url.path in _PUBLIC_PATHS:
            return None
        if (
            request.url.path in _LOCAL_OPERATIONAL_PATHS
            and not self._settings.hosted
        ):
            return None
        if request.url.path not in {
            self._settings.mcp_path,
            *_LOCAL_OPERATIONAL_PATHS,
        }:
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

        if self._settings.principal_source == "easy_auth":
            identity = _validate_platform_principal(request, self._settings)
        else:
            try:
                token = bearer_token(request.headers.getlist("authorization"))
                if self._verifier is None:
                    raise InvalidIdentityToken("invalid_token")
                claims = await run_in_threadpool(self._verifier.verify, token)
                identity = normalize_claims(claims, settings=self._settings)
            except InvalidIdentityToken:
                identity = Rejection("invalid_token")
        rejected = isinstance(identity, Rejection)
        emit_audit_event(
            "mcp.authentication",
            outcome="rejected" if rejected else "success",
            settings=self._settings,
            authentication_outcome=identity.reason if rejected else "authenticated",
        )
        if isinstance(identity, Rejection):
            return JSONResponse(
                {"error": "Authentication is required."},
                status_code=401, headers={"WWW-Authenticate": "Bearer"},
            )
        context = get_governance_context().model_copy(update={
            **asdict(identity), "boundary": "mcp", "authentication_outcome": "authenticated",
        })
        request.state.governance_context = context
        set_governance_context(context)
        principal_key = identity.principal_hash

        allowed, retry_after = self._limiter.allow(principal_key)
        if not allowed:
            return JSONResponse(
                {"error": "Rate limit exceeded."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        return None
