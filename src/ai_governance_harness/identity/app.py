"""Guarded mock of the Entra Agent ID sidecar protocol, never for hosting."""

from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ai_governance_harness.identity.config import IdentitySettings
from ai_governance_harness.identity.constants import (
    BLUEPRINT_ID,
    CHAT_CLIENT_ID,
    INTERACTIVE_ID,
    MCP_API_ID,
    MCP_LIFETIME,
    PERSONAS,
    REPORTING_ID,
    REPORTING_OBJECT_ID,
    STAFF_ROLES,
    TENANT_ID,
    USER_LIFETIME,
)
from ai_governance_harness.identity.tokens import InvalidIdentityToken, bearer_token
from ai_governance_harness.mock_identity_guard import require_mock_identity_allowed

logger = logging.getLogger(__name__)


class MockIssuer:
    """Own one ephemeral RSA key and issue only synthetic local identities."""

    def __init__(self, settings: IdentitySettings) -> None:
        require_mock_identity_allowed("identity", bind_host=settings.host)
        self.settings = settings
        self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.kid = uuid4().hex
        self.public_jwk = {
            **jwt.algorithms.RSAAlgorithm.to_jwk(self._key.public_key(), as_dict=True),
            "kid": self.kid,
            "use": "sig",
            "alg": "RS256",
        }

    def issue(self, claims: dict[str, object], *, lifetime: int) -> str:
        """Sign fixed-shape claims with a bounded lifetime."""
        now = int(time.time())
        return jwt.encode(
            {
                "iss": self.settings.issuer,
                "tid": TENANT_ID,
                "ver": "2.0",
                "iat": now,
                "nbf": now,
                "exp": now + lifetime,
                **claims,
            },
            self._key,
            algorithm="RS256",
            headers={"kid": self.kid},
        )

    def validate_user(self, headers: list[str]) -> dict[str, object]:
        """Validate a blueprint-audience subject token without echoing it."""
        try:
            token = bearer_token(headers)
            claims = jwt.decode(
                token,
                self._key.public_key(),
                algorithms=["RS256"],
                audience=BLUEPRINT_ID,
                issuer=self.settings.issuer,
                options={"require": ["exp", "iat", "nbf", "oid", "tid", "sub"]},
            )
            if (
                claims["tid"] != TENANT_ID
                or claims.get("idtyp") != "user"
                or claims.get("azp") != CHAT_CLIENT_ID
                or claims.get("scp") != "access_agent"
                or claims["oid"] not in PERSONAS.values()
            ):
                raise InvalidIdentityToken("invalid_token")
            return claims
        except (jwt.PyJWTError, InvalidIdentityToken, TypeError):
            raise InvalidIdentityToken("invalid_token") from None


def build_identity_app(settings: IdentitySettings) -> Starlette:
    """Build the guarded service, keeping private key material in memory."""
    issuer = MockIssuer(settings)

    def response(payload: dict, status: int = 200) -> JSONResponse:
        return JSONResponse(
            payload, status_code=status, headers={"Cache-Control": "no-store"}
        )

    async def health(_: Request) -> JSONResponse:
        return response({"status": "ready"})

    async def discovery(_: Request) -> JSONResponse:
        return response(
            {
                "issuer": settings.issuer,
                "jwks_uri": settings.jwks_url,
                "id_token_signing_alg_values_supported": ["RS256"],
            }
        )

    async def jwks(_: Request) -> JSONResponse:
        return response({"keys": [issuer.public_jwk]})

    async def signin(request: Request) -> JSONResponse:
        if (
            request.headers.get("content-type", "").split(";")[0].lower()
            != "application/json"
        ):
            return response({"error": "invalid_content_type"}, 415)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                return response({"error": "request_too_large"}, 413)
        try:
            data = json.loads(body)
        except (ValueError, UnicodeError):
            return response({"error": "unknown_persona"}, 400)
        persona = data.get("persona") if isinstance(data, dict) else None
        if not isinstance(persona, str) or persona not in PERSONAS:
            return response({"error": "unknown_persona"}, 400)
        oid = PERSONAS[persona]
        token = issuer.issue(
            {
                "aud": BLUEPRINT_ID,
                "sub": oid,
                "oid": oid,
                "scp": "access_agent",
                "idtyp": "user",
                "azp": CHAT_CLIENT_ID,
            },
            lifetime=USER_LIFETIME,
        )
        return response(
            {
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": USER_LIFETIME,
                "persona": persona,
            }
        )

    async def validate(request: Request) -> JSONResponse:
        try:
            claims = issuer.validate_user(request.headers.getlist("authorization"))
        except InvalidIdentityToken:
            logger.info("mock.identity.rejected", extra={"reason": "invalid_token"})
            return response({"error": "invalid_token"}, 401)
        return response(
            {
                "protocol": "Bearer",
                "claims": {
                    key: claims[key]
                    for key in ("oid", "tid", "aud", "scp", "idtyp", "azp", "exp")
                },
            }
        )

    async def authorization(request: Request) -> JSONResponse:
        app_only = request.url.path.startswith("/AuthorizationHeaderUnauthenticated/")
        if request.path_params["api"] != "mcp":
            return response({"error": "unknown_api"}, 404)
        expected = REPORTING_ID if app_only else INTERACTIVE_ID
        if request.query_params.getlist("AgentIdentity") != [expected]:
            return response({"error": "invalid_agent_identity"}, 400)
        claims: dict[str, object] = {
            "aud": MCP_API_ID,
            "azp": expected,
            "xms_act_fct": "11",
            "xms_par_app_azp": BLUEPRINT_ID,
        }
        if app_only:
            claims.update(
                {
                    "oid": REPORTING_OBJECT_ID,
                    "sub": REPORTING_OBJECT_ID,
                    "idtyp": "app",
                    "roles": ["Reports.Aggregate.Read"],
                    "xms_sub_fct": "11",
                }
            )
        else:
            try:
                user = issuer.validate_user(request.headers.getlist("authorization"))
            except InvalidIdentityToken:
                return response({"error": "invalid_token"}, 401)
            persona = next(name for name, oid in PERSONAS.items() if oid == user["oid"])
            role = next(role for role, name in STAFF_ROLES.items() if name == persona)
            claims.update(
                {
                    "oid": user["oid"],
                    "sub": user["oid"],
                    "idtyp": "user",
                    "scp": "Tools.Read",
                    "roles": [role],
                }
            )
        return response(
            {
                "authorizationHeader": "Bearer "
                + issuer.issue(claims, lifetime=MCP_LIFETIME)
            }
        )

    app = Starlette(
        routes=[
            Route("/healthz", health),
            Route(f"/{TENANT_ID}/v2.0/.well-known/openid-configuration", discovery),
            Route(f"/{TENANT_ID}/discovery/v2.0/keys", jwks),
            Route("/mock/signin", signin, methods=["POST"]),
            Route("/Validate", validate),
            Route("/AuthorizationHeader/{api}", authorization),
            Route("/AuthorizationHeaderUnauthenticated/{api}", authorization),
        ]
    )
    return app
