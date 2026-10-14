"""Bounded sidecar calls and request-local bearer forwarding."""

from __future__ import annotations

import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

import anyio
import httpx2
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from ai_governance_harness.errors import ChatServiceError
from ai_governance_harness.identity.config import require_loopback_url
from ai_governance_harness.identity.tokens import InvalidIdentityToken, bearer_token
from ai_governance_harness.identity.verification import _NoRedirect

tracer = trace.get_tracer("ai-governance-harness.identity")


class CallerIdentity(BaseModel):
    """Request-local subject credential excluded from serialization and repr."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    token: SecretStr = Field(exclude=True, repr=False)
    principal_hash: str = Field(min_length=64, max_length=64)


def authentication_required() -> ChatServiceError:
    """Build a bounded credential-rejection response."""
    return ChatServiceError(
        "Sign in with a valid mock identity.",
        code="authentication_required",
        status_code=401,
    )


def identity_unavailable() -> ChatServiceError:
    """Build a bounded identity service failure response."""
    return ChatServiceError(
        "The identity service is unavailable.",
        code="identity_unavailable",
        status_code=503,
    )


class SidecarClient:
    """Call the local sidecar without persisting credentials or logging claims."""

    def __init__(self, base_url: str, *, timeout: float) -> None:
        self.base_url = require_loopback_url(base_url)
        self.timeout = timeout

    def _request(
        self, path: str, *, token: str | None = None, body: bytes | None = None
    ) -> tuple[int, dict]:
        headers = {"Accept": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, headers=headers, data=body)
        with tracer.start_as_current_span(
            "get.identity.sidecar",
            kind=SpanKind.CLIENT,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                opener = build_opener(ProxyHandler({}), _NoRedirect())
                try:
                    response = opener.open(request, timeout=self.timeout)
                except HTTPError as error:
                    response = error
                with response:
                    status = response.code
                    payload = response.read(65_537)
                span.set_attribute("http.response.status_code", status)
                if len(payload) > 65_536:
                    raise ValueError("Oversized response")
                document = json.loads(payload)
                if not isinstance(document, dict):
                    raise ValueError("Invalid response")
                return status, document
            except (URLError, OSError, ValueError, TypeError):
                raise identity_unavailable() from None

    async def signin(self, body: bytes) -> tuple[int, dict]:
        """Proxy a bounded local sign-in response."""
        return await anyio.to_thread.run_sync(
            lambda: self._request("/mock/signin", body=body)
        )

    async def validate(self, headers: list[str]) -> CallerIdentity:
        """Validate a subject token and retain only its hash and hidden token."""
        try:
            token = bearer_token(headers)
        except InvalidIdentityToken:
            raise authentication_required() from None
        status, payload = await anyio.to_thread.run_sync(
            lambda: self._request("/Validate", token=token)
        )
        if status in {400, 401, 403}:
            raise authentication_required()
        if status != 200:
            raise identity_unavailable()
        claims = payload.get("claims")
        if (
            payload.get("protocol") != "Bearer"
            or not isinstance(claims, dict)
            or not isinstance(claims.get("oid"), str)
            or not claims["oid"]
            or claims.get("idtyp") != "user"
            or claims.get("scp") != "access_agent"
        ):
            raise authentication_required()
        return CallerIdentity(
            token=SecretStr(token),
            principal_hash=hashlib.sha256(claims["oid"].encode()).hexdigest(),
        )

    async def authorization(
        self, agent_id: str, *, caller: CallerIdentity | None = None
    ) -> str:
        """Get an OBO or app-only header for exactly one outgoing request."""
        endpoint = (
            "/AuthorizationHeader/mcp"
            if caller is not None
            else "/AuthorizationHeaderUnauthenticated/mcp"
        )
        path = endpoint + "?" + urlencode({"AgentIdentity": agent_id})
        status, payload = await anyio.to_thread.run_sync(
            lambda: self._request(
                path,
                token=caller.token.get_secret_value() if caller is not None else None,
            )
        )
        if status in {401, 403}:
            raise authentication_required()
        if status != 200:
            raise identity_unavailable()
        header = payload.get("authorizationHeader")
        try:
            if not isinstance(header, str):
                raise InvalidIdentityToken("invalid_token")
            bearer_token([header])
        except InvalidIdentityToken:
            raise identity_unavailable() from None
        return header


class AgentAuth(httpx2.Auth):
    """Fetch a fresh agent header for every MCP HTTP request."""

    def __init__(
        self,
        sidecar: SidecarClient,
        agent_id: str,
        caller: CallerIdentity | None = None,
    ) -> None:
        self._sidecar = sidecar
        self._agent_id = agent_id
        self._caller = caller

    async def async_auth_flow(self, request):
        request.headers["Authorization"] = await self._sidecar.authorization(
            self._agent_id, caller=self._caller
        )
        response = yield request
        if response.status_code == 401:
            raise authentication_required()
