"""Explicit identity fixtures; anonymous remains the default."""

from collections.abc import Iterator

import pytest

from ai_governance_harness.governance import GovernanceContext, governance_context
from ai_governance_harness.identity.config import IdentitySettings
from ai_governance_harness.identity.constants import (
    TENANT_ID,
    MCP_API_ID,
    INTERACTIVE_ID,
    REPORTING_ID,
)
from ai_governance_harness.mcp_server.config import ServerSettings
from ai_governance_harness.identity.sidecar import CallerIdentity
from pydantic import SecretStr


@pytest.fixture
def mock_chat_environment(monkeypatch):
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "true")
    monkeypatch.setenv("MCP_HOSTED", "false")
    monkeypatch.setenv("GOVERNANCE_ENVIRONMENT", "test")
    monkeypatch.setenv("MCP_ENVIRONMENT", "test")
    monkeypatch.setenv("AGENT_ID_SIDECAR_URL", "http://127.0.0.1:8002")
    monkeypatch.setenv("AGENT_ID_INTERACTIVE_ID", INTERACTIVE_ID)


@pytest.fixture
def caller_identity():
    return CallerIdentity(
        token=SecretStr("test.subject.signature"), principal_hash="a" * 64
    )


@pytest.fixture
def mock_mcp_settings(monkeypatch):
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "true")
    monkeypatch.setenv("MCP_HOSTED", "false")
    monkeypatch.setenv("GOVERNANCE_ENVIRONMENT", "test")
    monkeypatch.setenv("MCP_ENVIRONMENT", "test")

    def build(**overrides):
        identity = IdentitySettings()
        return ServerSettings(
            **{
                "transport": "streamable-http",
                "principal_source": "jwt",
                "jwt_issuer": identity.issuer,
                "jwt_jwks_url": identity.jwks_url,
                "auth_tenant_id": TENANT_ID,
                "auth_audience": MCP_API_ID,
                "auth_required_scope": "Tools.Read",
                "interactive_agent_id": INTERACTIVE_ID,
                "reporting_agent_id": REPORTING_ID,
                **overrides,
            }
        )

    return build


@pytest.fixture
def mcp_caller(request: pytest.FixtureRequest) -> Iterator[None]:
    values = {
        "boundary": "mcp",
        "actor": "interactive",
        "token_type": "user",
        "staff_role": "retention_specialist",
    }
    values.update(getattr(request, "param", {}))
    with governance_context(GovernanceContext(**values)):
        yield


@pytest.fixture
def chat_caller() -> Iterator[None]:
    with governance_context(GovernanceContext(boundary="chat", actor="interactive")):
        yield


@pytest.fixture
def local_persona(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("MOCK_IDENTITY_ENABLED", "true")
    monkeypatch.setenv("MOCK_IDENTITY_LOCAL_PERSONA", "retention_specialist")
    with governance_context(
        GovernanceContext(
            boundary="local",
            staff_role="retention_specialist",
        )
    ):
        yield
