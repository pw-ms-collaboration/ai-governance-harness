"""HTTP runtime wiring tests for the MCP server."""

from __future__ import annotations

import base64
import json

from starlette.testclient import TestClient

from ai_governance_harness.mcp_server import __main__ as entrypoint
from ai_governance_harness.mcp_server.config import ServerSettings
from ai_governance_harness.mcp_server.http_app import build_http_app
from ai_governance_harness.mcp_server.server import mcp


def test_given_http_settings_when_running_server_then_uses_session_json_transport(
    monkeypatch,
) -> None:
    # Arrange
    app = object()
    calls: list[tuple[object, dict[str, object]]] = []
    monkeypatch.setattr(entrypoint, "initialize_gateway", lambda: None)
    monkeypatch.setattr(entrypoint, "emit_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(entrypoint, "build_http_app", lambda settings: app)
    monkeypatch.setattr(
        entrypoint.uvicorn,
        "run",
        lambda application, **kwargs: calls.append((application, kwargs)),
    )
    settings = ServerSettings(
        transport="streamable-http",
        host="127.0.0.1",
        port=8765,
        mcp_path="/custom-mcp",
        json_response=True,
    )

    # Act
    entrypoint.run_server(settings)

    # Assert
    assert calls == [
        (
            app,
            {
                "host": "127.0.0.1",
                "port": 8765,
                "log_config": None,
                "access_log": False,
            },
        )
    ]


def test_given_custom_mcp_path_when_building_app_then_registers_only_that_path() -> None:
    # Act
    app = mcp.streamable_http_app(
        streamable_http_path="/custom-mcp",
        json_response=True,
        stateless_http=False,
    )

    # Assert
    assert [route.path for route in app.routes] == ["/custom-mcp"]


def _hosted_settings(**overrides: object) -> ServerSettings:
    values: dict[str, object] = {
        "transport": "streamable-http",
        "hosted": True,
        "region": "australiaeast",
        "auth_tenant_id": "tenant-123",
        "auth_audience": "api://mcp-server",
        "auth_required_scope": "Mcp.Tools.Read",
        "resource_url": "https://mcp.example/mcp",
        "allowed_origins": ("https://chat.example",),
    }
    values.update(overrides)
    return ServerSettings(**values)


def _principal_headers(
    *,
    tenant: str = "tenant-123",
    audience: str = "api://mcp-server",
    scope: str = "Mcp.Tools.Read",
) -> dict[str, str]:
    principal = {
        "claims": [
            {"typ": "tid", "val": tenant},
            {"typ": "aud", "val": audience},
            {"typ": "scp", "val": scope},
        ]
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {
        "X-MS-CLIENT-PRINCIPAL-IDP": "aad",
        "X-MS-CLIENT-PRINCIPAL-ID": "opaque-principal-id",
        "X-MS-CLIENT-PRINCIPAL": encoded,
        "Content-Type": "application/json",
    }


def test_given_hosted_mcp_without_principal_when_posting_then_returns_401() -> None:
    # Arrange
    client = TestClient(build_http_app(_hosted_settings()))

    # Act
    response = client.post("/mcp", json={})

    # Assert
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert "X-Correlation-ID" in response.headers


def test_given_public_operational_paths_when_unauthenticated_then_remain_available() -> None:
    # Arrange
    client = TestClient(build_http_app(_hosted_settings()))

    # Act
    live = client.get("/health/live")
    ready = client.get("/health/ready")
    metadata = client.get("/.well-known/oauth-protected-resource/mcp")

    # Assert
    assert live.json() == {"status": "live"}
    readiness = ready.json()
    assert readiness["status"] == "ready"
    assert readiness["governance"]["status"] == "ready"
    assert readiness["governance"]["enforcement"] == "enabled"
    assert len(readiness["governance"]["policy_digest"]) == 64
    assert metadata.json() == {
        "resource": "https://mcp.example/mcp",
        "authorization_servers": [
            "https://login.microsoftonline.com/tenant-123/v2.0"
        ],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["Mcp.Tools.Read"],
    }


def test_given_local_mode_when_getting_governance_then_snapshot_is_available() -> None:
    settings = ServerSettings(transport="streamable-http", hosted=False)
    client = TestClient(build_http_app(settings))

    response = client.get("/governance/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "ai-governance-observability/v1"
    assert payload["source"] == "mcp"
    assert payload["privacy"]["raw_prompts"] is False


def test_given_hosted_mode_when_getting_governance_then_authentication_is_required() -> None:
    client = TestClient(build_http_app(_hosted_settings()))

    unauthenticated = client.get("/governance/snapshot")
    authenticated = client.get(
        "/governance/snapshot",
        headers=_principal_headers(),
    )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200
    assert authenticated.json()["schema"] == "ai-governance-observability/v1"


def test_given_wrong_tenant_or_audience_when_posting_then_returns_401() -> None:
    # Arrange
    client = TestClient(build_http_app(_hosted_settings()))

    # Act
    wrong_tenant = client.post(
        "/mcp",
        headers=_principal_headers(tenant="other-tenant"),
        json={},
    )
    wrong_audience = client.post(
        "/mcp",
        headers=_principal_headers(audience="api://other"),
        json={},
    )

    # Assert
    assert wrong_tenant.status_code == 401
    assert wrong_audience.status_code == 401


def test_given_wrong_identity_provider_when_posting_then_returns_401() -> None:
    # Arrange
    client = TestClient(build_http_app(_hosted_settings()))
    headers = _principal_headers()
    headers["X-MS-CLIENT-PRINCIPAL-IDP"] = "untrusted"

    # Act
    response = client.post("/mcp", headers=headers, json={})

    # Assert
    assert response.status_code == 401


def test_given_missing_required_scope_when_posting_then_returns_401() -> None:
    # Arrange
    client = TestClient(build_http_app(_hosted_settings()))
    headers = _principal_headers(scope="Mcp.Tools.Write")

    # Act
    response = client.post("/mcp", headers=headers, json={})

    # Assert
    assert response.status_code == 401


def test_given_disallowed_origin_when_posting_then_rejects_before_authentication() -> None:
    # Arrange
    client = TestClient(build_http_app(_hosted_settings()))
    headers = _principal_headers()
    headers["Origin"] = "https://attacker.example"

    # Act
    response = client.post("/mcp", headers=headers, json={})

    # Assert
    assert response.status_code == 403


def test_given_oversized_body_when_posting_then_returns_413() -> None:
    # Arrange
    settings = _hosted_settings(max_request_body_size=16)
    client = TestClient(build_http_app(settings))

    # Act
    response = client.post(
        "/mcp",
        headers=_principal_headers(),
        content=json.dumps({"value": "x" * 32}),
    )

    # Assert
    assert response.status_code == 413


def test_given_unsupported_protocol_version_when_posting_then_returns_400() -> None:
    # Arrange
    client = TestClient(build_http_app(_hosted_settings()))
    headers = _principal_headers()
    headers["MCP-Protocol-Version"] = "1900-01-01"

    # Act
    response = client.post("/mcp", headers=headers, json={})

    # Assert
    assert response.status_code == 400


def test_given_exhausted_local_bucket_when_posting_then_returns_429() -> None:
    # Arrange
    settings = _hosted_settings(
        rate_limit_capacity=1,
        rate_limit_refill_per_second=0.01,
    )
    headers = _principal_headers()

    # Act
    with TestClient(build_http_app(settings)) as client:
        first = client.post("/mcp", headers=headers, json={})
        second = client.post("/mcp", headers=headers, json={})

    # Assert
    assert first.status_code != 429
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) >= 1
