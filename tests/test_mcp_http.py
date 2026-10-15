"""HTTP runtime wiring tests for the MCP server."""

from __future__ import annotations

import base64
import json

import pytest
from starlette.testclient import TestClient

from ai_governance_harness.mcp_server import __main__ as entrypoint
from ai_governance_harness.mcp_server.config import ServerSettings
from ai_governance_harness.mcp_server.http_app import build_http_app
from ai_governance_harness.mcp_server.server import mcp


def test_given_http_settings_when_running_server_then_uses_session_json_transport(
    monkeypatch, mock_mcp_settings,
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
    settings = mock_mcp_settings(
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
        "interactive_agent_id": "interactive-agent",
        "reporting_agent_id": "reporting-agent",
    }
    values.update(overrides)
    return ServerSettings(**values)


def _principal_headers(
    *,
    tenant: str = "tenant-123",
    audience: str = "api://mcp-server",
    scope: str | None = "Mcp.Tools.Read",
    role: str | None = None,
    client_id: str = "interactive-agent",
    token_type: str = "user",
    object_id: str = "opaque-principal-id",
) -> dict[str, str]:
    claims = [
        {"typ": "tid", "val": tenant},
        {"typ": "aud", "val": audience},
    ]
    if scope is not None:
        claims.append({"typ": "scp", "val": scope})
    claims.extend([
        {"typ": "oid", "val": object_id},
        {"typ": "azp", "val": client_id},
        {"typ": "idtyp", "val": token_type},
        {"typ": "xms_act_fct", "val": "11"},
    ])
    if role is not None:
        claims.append({"typ": "roles", "val": role})
    principal = {"claims": claims}
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {
        "X-MS-CLIENT-PRINCIPAL-IDP": "aad",
        "X-MS-CLIENT-PRINCIPAL-ID": "opaque-principal-id",
        "X-MS-CLIENT-PRINCIPAL": encoded,
        "Content-Type": "application/json",
    }


@pytest.mark.parametrize(
    ("overrides", "expected_status"),
    [
        ({}, 200),
        ({"audience": "mcp-server-client-id"}, 200),
        ({"client_id": "unknown-agent"}, 401),
        ({"token_type": ""}, 401),
        ({"token_type": "user"}, 401),
        ({"object_id": "different-object"}, 401),
        ({"role": "Mcp.Governance.Read"}, 401),
        ({"scope": "Mcp.Tools.Read"}, 401),
        ({"tenant": "wrong-tenant"}, 401),
    ],
)
def test_given_hosted_tool_workload_when_dispatching_then_binds_role_and_caller(
    overrides, expected_status,
):
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from ai_governance_harness.governance import (
        GovernanceEngine, GovernanceSettings, LifecyclePoint, get_governance_context,
    )
    from ai_governance_harness.mcp_server.security import RequestSecurityMiddleware

    settings = _hosted_settings(
        auth_required_scope=None, auth_required_role="Mcp.Tools.Invoke",
        auth_snapshot_role="Mcp.Governance.Read",
        auth_audiences=("api://mcp-server", "mcp-server-client-id"),
        interactive_agent_id=None, reporting_agent_id=None,
        hosted_tool_client_id="hosted-foundry-agent",
    )
    engine = GovernanceEngine(GovernanceSettings(environment="test"))

    async def endpoint(request):
        context = get_governance_context()
        return JSONResponse({
            "identity": context.identity_attributes(),
            "profile_allowed": engine.evaluate(
                LifecyclePoint.PRE_TOOL, "get_member_profile", context=context,
            ).allowed,
            "outreach_allowed": engine.evaluate(
                LifecyclePoint.PRE_TOOL, "prepare_member_outreach_case", context=context,
                policy_data={"retention_handling_status": "routine_permitted"},
            ).allowed,
        })

    app = Starlette(routes=[Route("/mcp", endpoint, methods=["POST"])])
    app.add_middleware(RequestSecurityMiddleware, settings=settings)
    claims = {
        "client_id": "hosted-foundry-agent", "token_type": "app",
        "scope": None, "role": "Mcp.Tools.Invoke", **overrides,
    }
    with TestClient(app) as client:
        response = client.post("/mcp", headers=_principal_headers(**claims), json={})

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json() == {
            "identity": {"boundary": "mcp", "actor": "tool_workload", "token_type": "app", "staff_role": "none"},
            "profile_allowed": True, "outreach_allowed": False,
        }


@pytest.mark.parametrize("overrides", [
    {"auth_snapshot_role": None},
    {"auth_snapshot_role": "Mcp.Tools.Invoke"},
    {"auth_required_role": "Other.Role"},
    {"interactive_agent_id": "interactive", "reporting_agent_id": "reporting"},
])
def test_given_unsafe_hosted_tool_configuration_when_constructing_then_rejects(overrides):
    values = {
        "auth_required_scope": None, "auth_required_role": "Mcp.Tools.Invoke",
        "auth_snapshot_role": "Mcp.Governance.Read",
        "interactive_agent_id": None, "reporting_agent_id": None,
        "hosted_tool_client_id": "hosted-foundry-agent", **overrides,
    }
    with pytest.raises(ValueError, match="Hosted tool identity requires"):
        _hosted_settings(**values)


def test_given_bound_tool_workload_when_reading_snapshot_then_reader_role_stays_separate():
    settings = _hosted_settings(
        auth_required_scope=None, auth_required_role="Mcp.Tools.Invoke",
        auth_snapshot_role="Mcp.Governance.Read",
        interactive_agent_id=None, reporting_agent_id=None,
        hosted_tool_client_id="hosted-foundry-agent",
    )
    with TestClient(build_http_app(settings)) as client:
        denied = client.get("/governance/snapshot", headers=_principal_headers(
            scope=None, role="Mcp.Tools.Invoke", client_id="hosted-foundry-agent", token_type="app",
        ))
        allowed = client.get("/governance/snapshot", headers=_principal_headers(
            scope=None, role="Mcp.Governance.Read", client_id="chat-snapshot-reader", token_type="app",
        ))

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_given_hosted_mcp_without_principal_when_posting_then_returns_401() -> None:
    # Arrange
    client = TestClient(build_http_app(_hosted_settings()))

    # Act
    response = client.post("/mcp", json={})

    # Assert
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert "X-Correlation-ID" in response.headers


def test_given_hosted_http_when_discovering_then_lists_tools_without_session_state() -> None:
    settings = _hosted_settings(json_response=True)
    headers = {
        **_principal_headers(),
        "Accept": "application/json, text/event-stream",
    }
    with TestClient(build_http_app(settings), base_url="http://127.0.0.1:8001") as client:
        initialized = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "hosted-transport-test", "version": "1"},
            },
        })
        discovered = client.post("/mcp", headers={
            **headers, "MCP-Protocol-Version": "2025-06-18",
        }, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    assert initialized.status_code == 200
    assert "mcp-session-id" not in initialized.headers
    assert discovered.status_code == 200
    assert {tool["name"] for tool in discovered.json()["result"]["tools"]} == {
        "get_member_profile", "get_member_disengagement_signals",
        "get_cohort_churn_analytics", "get_fum_outflow_summary",
        "prepare_member_outreach_case",
    }


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


def test_given_local_mode_when_getting_governance_then_snapshot_is_available(mock_mcp_settings, monkeypatch) -> None:
    from ai_governance_harness.identity.verification import JwtVerifier
    monkeypatch.setattr(JwtVerifier, "refresh", lambda self: False)
    settings = mock_mcp_settings()
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


@pytest.mark.parametrize(
    ("role", "endpoint", "expected_status"),
    [
        ("Mcp.Governance.Read", "/governance/snapshot", 200),
        ("Mcp.Governance.Read", "/mcp", 401),
        ("Mcp.Tools.Invoke", "/governance/snapshot", 401),
    ],
)
def test_given_snapshot_role_when_requesting_then_enforces_read_only_boundary(
    role: str, endpoint: str, expected_status: int,
) -> None:
    settings = _hosted_settings(
        auth_required_scope=None,
        auth_required_role="Mcp.Tools.Invoke",
        auth_snapshot_role="Mcp.Governance.Read",
    )
    client = TestClient(build_http_app(settings))

    response = client.get(endpoint, headers=_principal_headers(scope=None, role=role))

    assert response.status_code == expected_status


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


def test_given_required_application_role_when_getting_governance_then_authenticates() -> None:
    # Arrange
    settings = _hosted_settings(
        auth_required_scope=None,
        auth_required_role="Mcp.Tools.Invoke",
    )
    client = TestClient(build_http_app(settings))

    # Act
    response = client.get(
        "/governance/snapshot",
        headers=_principal_headers(scope=None, role="Mcp.Tools.Invoke"),
    )

    # Assert
    assert response.status_code == 200


def test_given_alternate_valid_api_audience_when_getting_governance_then_authenticates() -> None:
    # Arrange
    settings = _hosted_settings(
        auth_audience=None,
        auth_audiences=("api://mcp-server", "mcp-server-client-id"),
        auth_required_scope=None,
        auth_required_role="Mcp.Tools.Invoke",
    )
    client = TestClient(build_http_app(settings))

    # Act
    response = client.get(
        "/governance/snapshot",
        headers=_principal_headers(
            audience="mcp-server-client-id",
            scope=None,
            role="Mcp.Tools.Invoke",
        ),
    )

    # Assert
    assert response.status_code == 200


def test_given_application_role_mode_when_getting_resource_metadata_then_omits_scopes() -> None:
    # Arrange
    settings = _hosted_settings(
        auth_required_scope=None,
        auth_required_role="Mcp.Tools.Invoke",
    )
    client = TestClient(build_http_app(settings))

    # Act
    response = client.get("/.well-known/oauth-protected-resource/mcp")

    # Assert
    assert response.status_code == 200
    assert "scopes_supported" not in response.json()


def test_given_scope_only_when_application_role_required_then_returns_401() -> None:
    # Arrange
    settings = _hosted_settings(
        auth_required_scope=None,
        auth_required_role="Mcp.Tools.Invoke",
    )
    client = TestClient(build_http_app(settings))

    # Act
    response = client.get(
        "/governance/snapshot",
        headers=_principal_headers(),
    )

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
