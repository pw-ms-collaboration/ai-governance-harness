"""Start the browser chat service."""

from __future__ import annotations

import os
import sys

import uvicorn
from pydantic import ValidationError

from ai_governance_harness.chat.app import build_chat_app
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.governance.config import GovernanceSettings
from ai_governance_harness.mcp_server.telemetry import configure_azure_export

EXIT_SUCCESS = 0
EXIT_CONFIGURATION_ERROR = 2


def main() -> int:
    """Validate configuration and run the chat web application."""
    try:
        settings = ChatSettings.from_environment()
        governance_settings = GovernanceSettings.from_environment()
        configure_azure_export(
            service_name="ai-governance-harness-chat",
            environment=governance_settings.environment,
            region=os.getenv("AZURE_AI_PROJECT_REGION") or os.getenv("AZURE_REGION"),
            manual_only=True,
        )
    except ValidationError as exc:
        messages = "; ".join(
            error["msg"] for error in exc.errors(include_url=False, include_input=False)
        )
        print(f"Invalid chat configuration: {messages}", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR
    except ValueError:
        print("Invalid chat configuration value.", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR

    uvicorn.run(
        build_chat_app(settings),
        host=settings.host,
        port=settings.port,
        log_config=None,
        access_log=False,
    )
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
