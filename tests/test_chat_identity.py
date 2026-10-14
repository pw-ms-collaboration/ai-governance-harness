"""Authentication, OBO forwarding, privacy and circuit isolation."""

import json

import httpx2
import pytest
from starlette.testclient import TestClient

from ai_governance_harness.chat.app import build_chat_app
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.chat.service import (
    ChatService,
    ChatServiceError,
    _identity_failure,
)
from ai_governance_harness.governance import get_governance_context
from ai_governance_harness.identity.constants import INTERACTIVE_ID
from ai_governance_harness.identity.sidecar import (
    AgentAuth,
    SidecarClient,
    authentication_required,
    identity_unavailable,
)

pytestmark = pytest.mark.usefixtures("mock_chat_environment")


@pytest.fixture
def hosted_chat_settings(monkeypatch):
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "false")
    return ChatSettings(
        hosted=True, host="0.0.0.0", model_deployment="test",
        agent_name="test-agent", auth_tenant_id="test-tenant",
        auth_audience="api://test-chat", mcp_url="https://gateway.example/mcp",
        mcp_snapshot_url="https://gateway.example/snapshot",
        mcp_snapshot_audience="api://test-mcp",
        allowed_origins=("https://chat.example",),
    )


def _easy_auth_headers(**overrides):
    import base64

    claims = {
        "tid": "test-tenant", "aud": "api://test-chat",
        "oid": "private-user-id", "idtyp": "user", **overrides,
    }
    encoded = base64.b64encode(json.dumps({
        "claims": [{"typ": name, "val": value} for name, value in claims.items()],
    }).encode()).decode()
    return {
        "X-MS-CLIENT-PRINCIPAL": encoded,
        "X-MS-CLIENT-PRINCIPAL-ID": "private-user-id",
        "X-MS-CLIENT-PRINCIPAL-IDP": "aad",
    }


def test_given_hosted_identity_when_chatting_then_no_mock_sidecar_or_token_forwarding(
    hosted_chat_settings, monkeypatch, caplog,
):
    from ai_governance_harness.chat.service import ChatResponse

    def reject_sidecar(*args, **kwargs):
        pytest.fail("Hosted chat constructed a mock sidecar")

    monkeypatch.setattr(SidecarClient, "__init__", reject_sidecar)

    class Service:
        async def complete(self, request, caller):
            context = get_governance_context()
            assert caller is None
            assert context.authentication_outcome == "authenticated"
            assert context.actor == "interactive"
            assert len(context.principal_hash) == 64
            assert "private-user-id" not in context.model_dump_json()
            return ChatResponse(message="ok", tools_used=[])

    with TestClient(build_chat_app(hosted_chat_settings, Service())) as client:
        response = client.post(
            "/api/chat", headers=_easy_auth_headers(),
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
        assert client.get("/api/identity", headers=_easy_auth_headers()).json() == {
            "mode": "easy_auth",
        }
        assert client.post("/api/mock-identity/signin", json={}).status_code == 404
    assert response.status_code == 200
    assert "private-user-id" not in caplog.text
    assert get_governance_context().actor is None


@pytest.mark.parametrize("overrides", [
    {"tid": "wrong"}, {"aud": "wrong"}, {"oid": "wrong"}, {"idtyp": "app"},
])
def test_given_invalid_hosted_identity_when_chatting_then_rejects_before_service(
    hosted_chat_settings, overrides,
):
    with TestClient(build_chat_app(hosted_chat_settings)) as client:
        response = client.post("/api/chat", headers=_easy_auth_headers(**overrides), json={})
    assert response.status_code == 401


@pytest.mark.parametrize("endpoint", ["/", "/api/chat", "/api/identity", "/api/governance/snapshot"])
def test_given_anonymous_hosted_request_when_accessing_then_requires_authentication(
    hosted_chat_settings, endpoint,
):
    with TestClient(build_chat_app(hosted_chat_settings)) as client:
        assert client.get(endpoint).status_code == 401
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200


@pytest.mark.parametrize("overrides", [
    {"agent_name": None}, {"auth_tenant_id": None}, {"auth_audience": " "},
    {"mcp_url": "http://gateway.example/mcp"},
    {"mcp_snapshot_url": None, "mcp_snapshot_audience": None},
    {"allowed_origins": ("http://chat.example",)},
])
def test_given_unsafe_hosted_settings_when_configuring_then_fails_closed(
    hosted_chat_settings, overrides,
):
    with pytest.raises(ValueError):
        ChatSettings.model_validate({**hosted_chat_settings.model_dump(), **overrides})


def test_given_mock_enabled_when_configuring_hosted_chat_then_refuses(
    hosted_chat_settings, monkeypatch,
):
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "true")
    with pytest.raises(ValueError, match="disable mock identity"):
        ChatSettings.model_validate(hosted_chat_settings.model_dump())


@pytest.mark.parametrize("malformation", [
    "base64", "json", "oversized", "duplicate_header", "duplicate_claim",
    "alias_collision", "missing_claim", "provider", "empty_id",
])
def test_given_malformed_platform_principal_when_accessing_then_rejects(
    hosted_chat_settings, malformation,
):
    import base64

    headers = _easy_auth_headers()
    if malformation in {"duplicate_claim", "alias_collision", "missing_claim"}:
        document = json.loads(base64.b64decode(headers["X-MS-CLIENT-PRINCIPAL"]))
        if malformation == "missing_claim":
            document["claims"] = [item for item in document["claims"] if item["typ"] != "aud"]
        else:
            document["claims"].append({
                "typ": "tid" if malformation == "duplicate_claim" else
                    "http://schemas.microsoft.com/identity/claims/tenantid",
                "val": "test-tenant",
            })
        headers["X-MS-CLIENT-PRINCIPAL"] = base64.b64encode(json.dumps(document).encode()).decode()
    elif malformation == "base64":
        headers["X-MS-CLIENT-PRINCIPAL"] = "invalid!"
    elif malformation == "json":
        headers["X-MS-CLIENT-PRINCIPAL"] = base64.b64encode(b"[]").decode()
    elif malformation == "oversized":
        headers["X-MS-CLIENT-PRINCIPAL"] = "x" * 24_001
    elif malformation == "provider":
        headers["X-MS-CLIENT-PRINCIPAL-IDP"] = "untrusted"
    elif malformation == "empty_id":
        headers["X-MS-CLIENT-PRINCIPAL-ID"] = " "
    request_headers = list(headers.items())
    if malformation == "duplicate_header":
        request_headers.append(("X-MS-CLIENT-PRINCIPAL", headers["X-MS-CLIENT-PRINCIPAL"]))

    with TestClient(build_chat_app(hosted_chat_settings)) as client:
        response = client.get("/api/identity", headers=request_headers)

    assert response.status_code == 401


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def chat_settings():
    return ChatSettings(
        model_deployment="test",
        sidecar_url="http://127.0.0.1:8002",
        interactive_agent_id=INTERACTIVE_ID,
    )


@pytest.fixture
def validated_sidecar(monkeypatch):
    calls = []

    def request(self, path, *, token=None, body=None):
        calls.append((path, token))
        if path == "/Validate":
            return 200, {
                "protocol": "Bearer",
                "claims": {
                    "oid": "private-subject-oid",
                    "idtyp": "user",
                    "scp": "access_agent",
                },
            }
        if path == "/mock/signin":
            return 200, {
                "access_token": "signed.subject.token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "persona": "analyst",
            }
        return 200, {
            "authorizationHeader": f"Bearer signed.request{len(calls)}.signature"
        }

    monkeypatch.setattr(SidecarClient, "_request", request)
    return calls


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "invalid"}, {"Authorization": "Bearer " + "x" * 20000}],
)
def test_given_missing_or_malformed_bearer_when_chatting_then_401_before_service(
    chat_settings, headers
):
    class NeverCalled:
        async def complete(self, request, caller):
            pytest.fail("Unauthenticated request reached service")

    with TestClient(build_chat_app(chat_settings, NeverCalled())) as client:
        result = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hello"}]},
            headers=headers,
        )
    assert result.status_code == 401
    assert result.headers["WWW-Authenticate"] == "Bearer"
    assert result.json()["error"]["code"] == "authentication_required"
    assert "correlation_id" in result.json()["error"]


def test_given_valid_identity_when_chatting_then_context_and_repr_are_private(
    chat_settings, validated_sidecar, caplog
):
    from ai_governance_harness.chat.service import ChatResponse

    class Service:
        async def complete(self, request, caller):
            context = get_governance_context()
            assert context.boundary == "chat" and context.actor == "interactive"
            assert context.token_type == "user" and context.staff_role is None
            assert context.principal_hash == caller.principal_hash
            assert "signed.subject.token" not in repr(caller) + caller.model_dump_json()
            return ChatResponse(message="ok", tools_used=[])

    with TestClient(build_chat_app(chat_settings, Service())) as client:
        result = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hello"}]},
            headers={"Authorization": "Bearer signed.subject.token"},
        )
        signin = client.post("/api/mock-identity/signin", json={"persona": "analyst"})
        assert signin.json()["access_token"] == "signed.subject.token"
        assert signin.headers["Cache-Control"] == "no-store"
    assert result.status_code == 200 and result.json()["message"] == "ok"
    assert "signed.subject.token" not in caplog.text
    assert "private-subject-oid" not in caplog.text
    assert get_governance_context().actor is None


@pytest.mark.parametrize(
    ("error", "status"),
    [(authentication_required(), 401), (identity_unavailable(), 503)],
)
def test_given_sidecar_failure_when_chatting_then_structured_response(
    chat_settings, monkeypatch, error, status
):
    async def reject(self, headers):
        raise error

    monkeypatch.setattr(SidecarClient, "validate", reject)
    with TestClient(build_chat_app(chat_settings)) as client:
        response = client.post(
            "/api/chat", json={"messages": [{"role": "user", "content": "hello"}]}
        )
    assert response.status_code == status
    assert response.json()["error"]["code"] == error.code
    assert "token" not in response.json()["error"]["message"]


@pytest.mark.anyio
async def test_given_multiple_http_requests_when_using_auth_then_fresh_obo_each_time(
    validated_sidecar, caller_identity
):
    observed = []

    async def handle(request):
        observed.append(request.headers["Authorization"])
        return httpx2.Response(200, json={})

    auth = AgentAuth(
        SidecarClient("http://127.0.0.1:8002", timeout=1),
        INTERACTIVE_ID,
        caller_identity,
    )
    async with httpx2.AsyncClient(
        auth=auth, transport=httpx2.MockTransport(handle)
    ) as client:
        for method in ("POST", "GET", "POST", "DELETE"):
            await client.request(method, "http://127.0.0.1:8001/mcp")
    assert len(set(observed)) == 4
    assert len(validated_sidecar) == 4
    assert all(
        "AuthorizationHeader/mcp?AgentIdentity=" in path
        for path, _ in validated_sidecar
    )
    assert all(
        token == caller_identity.token.get_secret_value()
        for _, token in validated_sidecar
    )


@pytest.mark.anyio
async def test_given_identity_failures_when_using_mcp_circuit_then_not_counted(
    chat_settings,
):
    service = ChatService(chat_settings)

    async def invalid():
        raise ExceptionGroup("transport", [authentication_required()])

    for _ in range(5):
        with pytest.raises(ExceptionGroup):
            await service._mcp_reliability.call(invalid, ignore_error=_identity_failure)
    assert service._mcp_reliability.state == "closed"
    assert service._mcp_reliability._breaker.failure_count == 0


@pytest.mark.anyio
async def test_given_mcp_401_when_using_auth_then_authentication_required(
    validated_sidecar, caller_identity
):
    auth = AgentAuth(
        SidecarClient("http://127.0.0.1:8002", timeout=1),
        INTERACTIVE_ID,
        caller_identity,
    )
    async with httpx2.AsyncClient(
        auth=auth, transport=httpx2.MockTransport(lambda r: httpx2.Response(401))
    ) as client:
        with pytest.raises(ChatServiceError) as error:
            await client.post("http://127.0.0.1:8001/mcp", json={})
    assert error.value.code == "authentication_required"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("GOVERNANCE_ENVIRONMENT", "staging"),
        ("MCP_ENVIRONMENT", "production"),
        ("MCP_HOSTED", "true"),
        ("CONTAINER_APP_NAME", "hosted"),
        ("MOCK_IDENTITY_ENABLED", "false"),
    ],
)
def test_given_unsafe_environment_when_configuring_chat_then_refuse(
    chat_settings, monkeypatch, name, value
):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        ChatSettings.model_validate(chat_settings.model_dump())


def test_given_non_loopback_bind_or_missing_settings_when_configuring_then_refuse(
    chat_settings,
):
    for update in (
        {"host": "0.0.0.0"},
        {"sidecar_url": ""},
        {"interactive_agent_id": ""},
    ):
        with pytest.raises(ValueError):
            ChatSettings.model_validate({**chat_settings.model_dump(), **update})


def test_given_mock_disabled_after_start_when_signing_in_then_route_unavailable(
    chat_settings, monkeypatch
):
    app = build_chat_app(chat_settings)
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "false")
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/mock-identity/signin", json={"persona": "analyst"}
            ).status_code
            == 404
        )


def test_given_sidecar_network_failure_when_requesting_then_no_sensitive_error(
    monkeypatch,
):
    from ai_governance_harness.identity import sidecar
    from urllib.error import URLError

    class Unavailable:
        def open(self, *args, **kwargs):
            raise URLError("Bearer raw-secret private-user@example.test")

    monkeypatch.setattr(sidecar, "build_opener", lambda *args: Unavailable())
    with pytest.raises(ChatServiceError) as error:
        SidecarClient("http://127.0.0.1:8002", timeout=1)._request(
            "/Validate", token="raw-secret"
        )
    assert error.value.code == "identity_unavailable"
    assert "raw-secret" not in json.dumps(error.value.__dict__) + str(error.value)
