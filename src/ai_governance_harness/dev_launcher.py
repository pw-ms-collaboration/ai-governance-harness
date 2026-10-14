"""Start mock identity, MCP and chat together for local development."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass

from dotenv import load_dotenv
from ai_governance_harness.identity.config import IdentitySettings
from ai_governance_harness.identity.constants import (
    TENANT_ID, MCP_API_ID, INTERACTIVE_ID, REPORTING_ID,
)
from ai_governance_harness.mock_identity_guard import require_mock_identity_allowed

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFIGURATION_ERROR = 2


@dataclass(frozen=True)
class Service:
    """One managed local development process."""

    name: str
    module: str
    host: str
    port: int
    health_path: str

    @property
    def health_url(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}{self.health_path}"


def _port_is_available(host: str, port: int) -> bool:
    try:
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((host, port))
    except OSError:
        return False
    return True


def _wait_until_ready(service: Service, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"{service.name} exited before becoming ready with code {process.returncode}."
            )
        try:
            with urllib.request.urlopen(service.health_url, timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.25)
    raise RuntimeError(f"{service.name} did not become ready within 60 seconds.")


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    """Start the three guarded local services and open the chat UI."""
    load_dotenv()
    mcp_host = os.getenv("MCP_HOST", "127.0.0.1")
    chat_host = os.getenv("CHAT_HOST", "127.0.0.1")
    try:
        if all(os.getenv(name, "local") in {"local", "development", "test"}
               for name in ("GOVERNANCE_ENVIRONMENT", "MCP_ENVIRONMENT")):
            os.environ["MOCK_IDENTITY_ENABLED"] = "true"
        identity = IdentitySettings.from_environment()
        for host in (identity.host, mcp_host, chat_host):
            require_mock_identity_allowed("launcher", bind_host=host)
        mcp_port = int(os.getenv("MCP_PORT", "8001"))
        chat_port = int(os.getenv("CHAT_PORT", "8080"))
        if not all(1 <= port <= 65535 for port in (mcp_port, chat_port)):
            raise ValueError("Invalid port")
    except ValueError:
        print("Invalid or unsafe local mock launcher configuration.", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR

    services = [
        Service("mock identity", "ai_governance_harness.identity", identity.host, identity.port, "/healthz"),
        Service("MCP server", "ai_governance_harness.mcp_server", mcp_host, mcp_port, "/health/ready"),
        Service("chat UI", "ai_governance_harness.chat", chat_host, chat_port, "/health/ready"),
    ]
    if len({service.port for service in services}) != len(services):
        print("Local service ports must be distinct.", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR
    unavailable = [
        f"{service.name} ({service.host}:{service.port})"
        for service in services
        if not _port_is_available(service.host, service.port)
    ]
    if unavailable:
        print(
            "Cannot start because these addresses are already in use: "
            + ", ".join(unavailable),
            file=sys.stderr,
        )
        return EXIT_CONFIGURATION_ERROR

    mcp_url_host = f"[{mcp_host}]" if ":" in mcp_host else mcp_host
    chat_url_host = f"[{chat_host}]" if ":" in chat_host else chat_host
    ui_url = f"http://{chat_url_host}:{chat_port}"
    mcp_url = f"http://{mcp_url_host}:{mcp_port}/mcp"
    env = os.environ.copy()
    env.update(
        {
            "MCP_TRANSPORT": "streamable-http",
            "MCP_HOST": mcp_host,
            "MCP_PORT": str(mcp_port),
            "MCP_HOSTED": "false",
            "MCP_PATH": "/mcp",
            "MCP_PRINCIPAL_SOURCE": "jwt",
            "MCP_JWT_ISSUER": identity.issuer,
            "MCP_JWT_JWKS_URL": identity.jwks_url,
            "MCP_AUTH_AUDIENCE": MCP_API_ID,
            "MCP_AUTH_TENANT_ID": TENANT_ID,
            "MCP_AUTH_REQUIRED_SCOPE": "Tools.Read",
            "AGENT_ID_INTERACTIVE_ID": INTERACTIVE_ID,
            "AGENT_ID_REPORTING_ID": REPORTING_ID,
            "AGENT_ID_SIDECAR_URL": identity.base_url,
            "CHAT_ALLOWED_ORIGINS": ui_url,
            "MCP_SERVER_URL": mcp_url,
            "CHAT_USE_PROMPT_AGENT": "false",
            "AZURE_CREDENTIAL_MODE": os.getenv("AZURE_CREDENTIAL_MODE", "azure-cli"),
            "CHAT_HOST": chat_host,
            "CHAT_PORT": str(chat_port),
        }
    )
    processes: list[subprocess.Popen[bytes]] = []
    try:
        for service in services:
            process = subprocess.Popen(
                [sys.executable, "-m", service.module],
                env=env,
            )
            processes.append(process)
            _wait_until_ready(service, process)

        print(f"Local mock identity ready at {identity.base_url} (not Microsoft Entra)")
        print(f"MCP server ready at {mcp_url}")
        print(f"Chat UI ready at {ui_url}")
        print("Press Ctrl+C to stop all three services.")
        webbrowser.open(ui_url)

        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        failed = next(
            (
                service
                for service, process in zip(services, processes, strict=True)
                if process.poll() is not None
            ),
            None,
        )
        if failed:
            print(f"{failed.name} stopped unexpectedly.", file=sys.stderr)
            return EXIT_FAILURE
    except KeyboardInterrupt:
        return EXIT_SUCCESS
    except (RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAILURE
    finally:
        for process in reversed(processes):
            _stop_process(process)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
