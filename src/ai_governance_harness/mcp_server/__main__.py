"""Start the MCP server over stdio or session-based Streamable HTTP."""

from __future__ import annotations

import sys

from pydantic import ValidationError
import uvicorn

from ai_governance_harness.governance import (
    GovernanceContext,
    LifecyclePoint,
    get_governance_engine,
    governance_context,
)
from ai_governance_harness.mock_identity_guard import resolve_local_persona
from ai_governance_harness.mcp_server.config import ServerSettings
from ai_governance_harness.mcp_server.http_app import build_http_app
from ai_governance_harness.mcp_server.server import mcp
from ai_governance_harness.mcp_server.telemetry import (
    configure_telemetry,
    emit_audit_event,
)
from ai_governance_harness.mcp_server.tools import initialize_gateway

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFIGURATION_ERROR = 2


def run_server(settings: ServerSettings) -> None:
    """Validate application data and run the selected MCP transport."""
    governance = get_governance_engine()
    governance.require_allowed(
        LifecyclePoint.STARTUP,
        "agent.startup",
        source="mcp",
    )
    initialize_gateway()
    emit_audit_event("mcp.readiness", outcome="ready", settings=settings)
    try:
        if settings.transport == "stdio":
            with governance_context(GovernanceContext(
                boundary="local",
                environment=settings.environment,
                staff_role=resolve_local_persona(),
            )):
                mcp.run("stdio")
            return

        uvicorn.run(
            build_http_app(settings),
            host=settings.host,
            port=settings.port,
            log_config=None,
            access_log=False,
        )
    finally:
        governance.require_allowed(
            LifecyclePoint.SHUTDOWN,
            "agent.shutdown",
            source="mcp",
        )


def main() -> int:
    """Load settings and start the MCP server."""
    try:
        settings = ServerSettings.from_environment()
        configure_telemetry(settings)
        emit_audit_event("mcp.startup", outcome="started", settings=settings)
        run_server(settings)
    except ValidationError as exc:
        messages = "; ".join(
            error["msg"] for error in exc.errors(include_url=False, include_input=False)
        )
        print(f"Invalid MCP configuration: {messages}", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR
    except ValueError:
        print("Invalid MCP configuration value.", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR
    except FileNotFoundError as exc:
        print(f"MCP data initialization failed: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    except KeyboardInterrupt:
        return 130
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
