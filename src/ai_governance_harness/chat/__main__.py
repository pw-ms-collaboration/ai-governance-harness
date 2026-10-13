"""Start the browser chat service."""

from __future__ import annotations

import sys

import uvicorn
from pydantic import ValidationError

from ai_governance_harness.chat.app import build_chat_app
from ai_governance_harness.chat.config import ChatSettings

EXIT_SUCCESS = 0
EXIT_CONFIGURATION_ERROR = 2


def main() -> int:
    """Validate configuration and run the chat web application."""
    try:
        settings = ChatSettings.from_environment()
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
