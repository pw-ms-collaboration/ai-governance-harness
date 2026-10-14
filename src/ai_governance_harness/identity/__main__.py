"""Run the explicitly enabled local mock issuer."""

import sys

import uvicorn
from dotenv import load_dotenv

from ai_governance_harness.identity.app import build_identity_app
from ai_governance_harness.identity.config import IdentitySettings


def main() -> int:
    """Refuse unsafe configuration before generating keys or binding."""
    load_dotenv()
    try:
        settings = IdentitySettings.from_environment()
        app = build_identity_app(settings)
    except ValueError:
        print("Invalid or unsafe mock identity configuration.", file=sys.stderr)
        return 2
    uvicorn.run(
        app, host=settings.host, port=settings.port, access_log=False, log_config=None
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
