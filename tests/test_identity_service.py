"""Focused mock sidecar contract and key-hygiene tests."""

import json
import time

import jwt
import pytest
from starlette.testclient import TestClient

from ai_governance_harness.identity import __main__ as identity_main
from ai_governance_harness.identity.app import MockIssuer, build_identity_app
from ai_governance_harness.identity.config import IdentitySettings
from ai_governance_harness.identity.constants import (
    BLUEPRINT_ID,
    INTERACTIVE_ID,
    MCP_API_ID,
    PERSONAS,
    REPORTING_ID,
    STAFF_ROLES,
    TENANT_ID,
)


@pytest.fixture
def identity_client(monkeypatch):
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "true")
    monkeypatch.setenv("GOVERNANCE_ENVIRONMENT", "test")
    monkeypatch.setenv("MCP_ENVIRONMENT", "test")
    monkeypatch.setenv("MCP_HOSTED", "false")
    with TestClient(build_identity_app(IdentitySettings())) as client:
        yield client


def decode(client, token, audience):
    jwk = client.get(f"/{TENANT_ID}/discovery/v2.0/keys").json()["keys"][0]
    return jwt.decode(
        token,
        jwt.PyJWK.from_dict(jwk).key,
        algorithms=["RS256"],
        audience=audience,
        issuer=IdentitySettings().issuer,
    )


@pytest.mark.parametrize("persona", PERSONAS)
def test_given_persona_when_signing_in_and_exchanging_then_claim_contract(
    identity_client, persona
):
    client = identity_client
    signin = client.post("/mock/signin", json={"persona": persona}).json()
    user = decode(client, signin["access_token"], BLUEPRINT_ID)
    assert user["oid"] == PERSONAS[persona]
    assert user["scp"] == "access_agent" and "roles" not in user
    assert user["exp"] - user["iat"] <= 3600
    headers = {"Authorization": f"Bearer {signin['access_token']}"}
    validated = client.get("/Validate", headers=headers)
    assert validated.status_code == 200
    assert signin["access_token"] not in validated.text
    result = client.get(
        "/AuthorizationHeader/mcp",
        params={"AgentIdentity": INTERACTIVE_ID},
        headers=headers,
    )
    obo = decode(client, result.json()["authorizationHeader"].split()[1], MCP_API_ID)
    assert obo["oid"] == user["oid"] and obo["azp"] == INTERACTIVE_ID
    assert obo["roles"] == [
        next(role for role, name in STAFF_ROLES.items() if name == persona)
    ]
    assert obo["xms_act_fct"] == "11" and obo["scp"] == "Tools.Read"
    assert obo["exp"] - obo["iat"] <= 600
    assert (
        client.get(
            "/Validate", headers={"Authorization": result.json()["authorizationHeader"]}
        ).status_code
        == 401
    )


def test_given_reporting_agent_when_getting_header_then_app_only_contract(
    identity_client,
):
    result = identity_client.get(
        "/AuthorizationHeaderUnauthenticated/mcp",
        params={"AgentIdentity": REPORTING_ID},
    )
    claims = decode(
        identity_client, result.json()["authorizationHeader"].split()[1], MCP_API_ID
    )
    assert claims["idtyp"] == "app" and claims["oid"] == claims["sub"]
    assert claims["azp"] == REPORTING_ID and claims["xms_sub_fct"] == "11"
    assert claims["roles"] == ["Reports.Aggregate.Read"] and "scp" not in claims


@pytest.mark.parametrize(
    ("path", "agent", "status"),
    [
        ("/AuthorizationHeader/mcp", REPORTING_ID, 400),
        ("/AuthorizationHeader/mcp", "unknown", 400),
        ("/AuthorizationHeader/mcp", "", 400),
        ("/AuthorizationHeaderUnauthenticated/mcp", INTERACTIVE_ID, 400),
        ("/AuthorizationHeaderUnauthenticated/mcp", "", 400),
        ("/AuthorizationHeader/unknown", INTERACTIVE_ID, 404),
        ("/AuthorizationHeader/mcp", INTERACTIVE_ID, 401),
    ],
)
def test_given_misuse_when_requesting_header_then_reject(
    identity_client, path, agent, status
):
    assert (
        identity_client.get(path, params={"AgentIdentity": agent}).status_code == status
    )


def test_given_bad_signin_or_token_when_requesting_then_reject(identity_client):
    assert identity_client.post("/mock/signin", json={"persona": []}).status_code == 400
    assert identity_client.post("/mock/signin", content="bad").status_code == 415
    assert (
        identity_client.post(
            "/mock/signin",
            content="x" * 4097,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    for header in ("Bearer invalid", "", "Bearer " + "x" * 20000):
        assert (
            identity_client.get(
                "/Validate", headers={"Authorization": header}
            ).status_code
            == 401
        )


def test_given_expired_subject_when_validating_then_reject(monkeypatch):
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "true")
    issuer = MockIssuer(IdentitySettings())
    token = issuer.issue({"aud": BLUEPRINT_ID, "exp": int(time.time()) - 1}, lifetime=1)
    with pytest.raises(ValueError):
        issuer.validate_user([f"Bearer {token}"])


def test_given_service_instances_when_created_then_ephemeral_public_keys_only(
    identity_client, tmp_path, monkeypatch, caplog
):
    monkeypatch.chdir(tmp_path)
    first = identity_client.get(f"/{TENANT_ID}/discovery/v2.0/keys").json()["keys"][0]
    with TestClient(build_identity_app(IdentitySettings())) as second:
        other = second.get(f"/{TENANT_ID}/discovery/v2.0/keys").json()["keys"][0]
    assert first["kid"] != other["kid"] and first["n"] != other["n"]
    assert not {"d", "p", "q", "dp", "dq", "qi"} & first.keys()
    assert not list(tmp_path.iterdir())
    token = identity_client.post("/mock/signin", json={"persona": "analyst"}).json()[
        "access_token"
    ]
    assert token not in caplog.text
    assert all(oid not in caplog.text for oid in PERSONAS.values())
    assert "private" not in json.dumps(first)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MOCK_IDENTITY_ENABLED", "false"),
        ("MCP_HOSTED", "true"),
        ("GOVERNANCE_ENVIRONMENT", "staging"),
        ("GOVERNANCE_ENVIRONMENT", "production"),
        ("MCP_ENVIRONMENT", "staging"),
        ("MCP_ENVIRONMENT", "production"),
        ("CONTAINER_APP_NAME", "hosted"),
        ("MOCK_IDENTITY_HOST", "0.0.0.0"),
    ],
)
def test_given_unsafe_startup_when_running_then_no_bind(monkeypatch, name, value):
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "true")
    monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        identity_main.uvicorn, "run", lambda *a, **kw: pytest.fail("must not bind")
    )
    assert identity_main.main() == 2
