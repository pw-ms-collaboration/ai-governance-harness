"""MCP JWT and normalization rejection contracts."""

import base64
import json
import time
from dataclasses import asdict
from io import BytesIO

import jwt
import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

from ai_governance_harness.identity import verification
from ai_governance_harness.identity.app import MockIssuer
from ai_governance_harness.identity.claims import (
    NormalizedIdentity,
    Rejection,
    normalize_claims,
)
from ai_governance_harness.identity.config import IdentitySettings
from ai_governance_harness.identity.constants import (
    INTERACTIVE_ID,
    REPORTING_ID,
    MCP_API_ID,
    PERSONAS,
    STAFF_ROLES,
)
from ai_governance_harness.identity.tokens import InvalidIdentityToken, bearer_token
from ai_governance_harness.identity.verification import JwtVerifier
from ai_governance_harness.mcp_server.http_app import build_http_app
from ai_governance_harness.mcp_server.security import _validate_platform_principal


@pytest.fixture
def signed_identity(mock_mcp_settings, monkeypatch):
    settings = mock_mcp_settings()
    issuer = MockIssuer(IdentitySettings())

    class Opener:
        def open(self, request, timeout):
            return BytesIO(json.dumps({"keys": [issuer.public_jwk]}).encode())

    monkeypatch.setattr(verification, "build_opener", lambda *args: Opener())
    verifier = JwtVerifier(
        issuer=settings.jwt_issuer,
        jwks_url=settings.jwt_jwks_url,
        audience=settings.auth_audience,
        tenant=settings.auth_tenant_id,
    )
    assert verifier.refresh()
    claims = {
        "aud": MCP_API_ID,
        "oid": PERSONAS["analyst"],
        "sub": PERSONAS["analyst"],
        "azp": INTERACTIVE_ID,
        "idtyp": "user",
        "scp": "Tools.Read",
        "xms_act_fct": "11",
        "roles": ["Staff.Analyst"],
    }
    return settings, issuer, verifier, claims


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": None},
        {"nbf": None},
        {"iat": None},
        {"exp": 1},
        {"nbf": int(time.time()) + 3600},
        {"iat": int(time.time()) + 3600},
        {"iss": "http://wrong-issuer"},
        {"aud": "wrong-audience"},
        {"tid": "wrong-tenant"},
        {"azp": "unknown"},
        {"idtyp": "app"},
        {"azp": REPORTING_ID},
        {"xms_act_fct": ""},
        {"xms_sub_fct": "13"},
        {"scp": ""},
        {"oid": ""},
        {"oid": []},
        {"xms_act_fct": 11},
        {"roles": "Staff.Analyst"},
    ],
)
def test_given_bad_claims_when_authenticating_then_reject(signed_identity, overrides):
    settings, issuer, verifier, claims = signed_identity
    token = issuer.issue({**claims, **overrides}, lifetime=600)
    try:
        verified = verifier.verify(token)
    except InvalidIdentityToken:
        return
    assert isinstance(normalize_claims(verified, settings=settings), Rejection)


def test_given_unsigned_wrong_key_or_algorithm_when_verifying_then_reject(
    signed_identity,
):
    from cryptography.hazmat.primitives import serialization
    import hashlib
    import hmac

    settings, issuer, verifier, claims = signed_identity
    other = MockIssuer(IdentitySettings())
    public_key = issuer._key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    signing_input = b".".join(
        jwt.utils.base64url_encode(json.dumps(value).encode())
        for value in ({"alg": "HS256", "kid": issuer.kid}, claims)
    )
    confused_token = signing_input + b"." + jwt.utils.base64url_encode(
        hmac.new(public_key, signing_input, hashlib.sha256).digest()
    )
    tokens = [
        jwt.encode(claims, "", algorithm="none"),
        confused_token.decode(),
        other.issue(claims, lifetime=600),
    ]
    other.kid = issuer.kid
    tokens.append(other.issue(claims, lifetime=600))
    for token in tokens:
        with pytest.raises(InvalidIdentityToken):
            verifier.verify(token)
    valid = issuer.issue(claims, lifetime=600)
    assert verifier.verify(valid)["azp"] == INTERACTIVE_ID
    verifier._keys = {other.public_jwk["kid"]: jwt.PyJWK.from_dict(other.public_jwk)}
    verifier._last_fetch = float("-inf")
    assert verifier.verify(valid)["azp"] == INTERACTIVE_ID


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [""],
        ["Bearer invalid"],
        ["Bearer " + "x" * 20000],
        ["Bearer a.b.c", "Bearer a.b.c"],
    ],
)
def test_given_bad_header_when_parsing_then_reject(headers):
    with pytest.raises(InvalidIdentityToken):
        bearer_token(headers)


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        ([], "none"),
        (["Staff.Unknown"], "none"),
        (["Staff.Analyst", "Staff.RetentionSpecialist"], "none"),
        (["Staff.Analyst", "Staff.Unknown"], "none"),
        *[([name], role) for name, role in STAFF_ROLES.items()],
    ],
)
def test_given_staff_roles_when_normalizing_then_same_easy_auth_result(
    signed_identity, roles, expected
):
    settings, issuer, verifier, claims = signed_identity
    claims = {**claims, "roles": roles, "xms_act_fct": ["11"]}
    decoded = verifier.verify(issuer.issue(claims, lifetime=600))
    identity = normalize_claims(decoded, settings=settings)
    assert isinstance(identity, NormalizedIdentity) and identity.staff_role == expected
    platform_claims = [
        {"typ": key, "val": str(value)}
        for key, values in decoded.items()
        for value in (values if isinstance(values, list) else [values])
    ]
    encoded = base64.b64encode(json.dumps({"claims": platform_claims}).encode())
    request = Request(
        {
            "type": "http",
            "headers": [
                (b"x-ms-client-principal-idp", b"aad"),
                (b"x-ms-client-principal-id", b"opaque"),
                (b"x-ms-client-principal", encoded),
            ],
        }
    )
    assert asdict(_validate_platform_principal(request, settings)) == asdict(identity)


def test_given_unavailable_jwks_when_checking_readiness_then_fail_closed(
    mock_mcp_settings, monkeypatch
):
    monkeypatch.setattr(JwtVerifier, "refresh", lambda self: False)
    with TestClient(build_http_app(mock_mcp_settings())) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["identity"]["jwks"] == "unavailable"
        assert client.post("/mcp", json={}).status_code == 401


def test_given_jwks_fetch_failure_when_refreshing_then_clear_keys_and_rate_limit(
    signed_identity, monkeypatch
):
    from urllib.error import URLError

    settings, issuer, verifier, claims = signed_identity
    calls = []

    class FailedOpener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            raise URLError("unavailable")

    monkeypatch.setattr(verification, "build_opener", lambda *args: FailedOpener())
    verifier._last_fetch = float("-inf")
    assert not verifier.refresh() and not verifier.ready
    token = issuer.issue(claims, lifetime=600)
    for _ in range(3):
        with pytest.raises(InvalidIdentityToken):
            verifier.verify(token)
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("GOVERNANCE_ENVIRONMENT", "staging"),
        ("MCP_ENVIRONMENT", "production"),
        ("MCP_HOSTED", "true"),
        ("CONTAINER_APP_NAME", "hosted"),
    ],
)
def test_given_mock_hosting_when_configuring_jwt_then_refuse(
    mock_mcp_settings, monkeypatch, name, value
):
    settings = mock_mcp_settings()
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        type(settings).model_validate(settings.model_dump())


def test_given_unsafe_urls_or_bind_when_configuring_then_refuse(mock_mcp_settings):
    for overrides in (
        {"jwt_issuer": "https://login.example/tenant"},
        {"jwt_jwks_url": "http://external.example/keys"},
        {"host": "0.0.0.0"},
        {"interactive_agent_id": REPORTING_ID},
    ):
        with pytest.raises(ValueError):
            mock_mcp_settings(**overrides)


def test_given_bearer_and_claims_when_running_middleware_then_telemetry_is_private(
    signed_identity, monkeypatch, caplog
):
    import logging
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
    from ai_governance_harness.governance import (
        engine,
        get_governance_context,
        LifecyclePoint,
    )
    from ai_governance_harness.governance.events import governance_events
    from ai_governance_harness.mcp_server import security
    from ai_governance_harness.mcp_server.telemetry import PrivacySafeJsonFormatter

    settings, issuer, verifier, claims = signed_identity
    token = issuer.issue(
        {
            **claims,
            "preferred_username": "private-user@example.test",
            "xms_par_app_azp": "private-blueprint-marker",
        },
        lifetime=600,
    )
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(engine, "tracer", provider.get_tracer("test"))
    monkeypatch.setattr(security, "tracer", provider.get_tracer("test"))
    caplog.set_level(logging.INFO)
    governance_events.clear()

    async def endpoint(request):
        assert request.state.governance_context == get_governance_context()
        decision = engine.get_governance_engine().evaluate(
            LifecyclePoint.PRE_TOOL,
            "get_cohort_churn_analytics",
        )
        return JSONResponse({"allowed": decision.allowed})

    app = Starlette(routes=[Route("/mcp", endpoint, methods=["POST"])])
    app.add_middleware(
        security.RequestSecurityMiddleware, settings=settings, verifier=verifier
    )
    with TestClient(app) as client:
        assert client.post(
            "/mcp", json={}, headers={"Authorization": "Bearer " + token}
        ).json()["allowed"]
    formatter = PrivacySafeJsonFormatter("test", "local")
    serialized = (
        json.dumps(governance_events.snapshot())
        + "".join(formatter.format(record) for record in caplog.records)
        + json.dumps([dict(span.attributes) for span in exporter.get_finished_spans()])
    )
    for marker in (
        token,
        claims["oid"],
        claims["azp"],
        "private-user@example.test",
        "private-blueprint-marker",
    ):
        assert marker not in serialized
    assert "authorization" not in serialized.lower()
    provider.shutdown()
