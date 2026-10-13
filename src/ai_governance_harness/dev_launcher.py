"""Start the MCP and chat services together for local development."""

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
        return f"http://{self.host}:{self.port}{self.health_path}"


def _port_is_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((host, port))
    except OSError:
        return False
    return True


def _wait_until_ready(service: Service, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
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
    raise RuntimeError(f"{service.name} did not become ready within 30 seconds.")


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
    """Start both local services and open the chat UI."""
    load_dotenv()
    mcp_host = os.getenv("MCP_HOST", "127.0.0.1")
    chat_host = os.getenv("CHAT_HOST", "127.0.0.1")
    try:
        mcp_port = int(os.getenv("MCP_PORT", "8001"))
        chat_port = int(os.getenv("CHAT_PORT", "8080"))
    except ValueError:
        print("MCP_PORT and CHAT_PORT must be integers.", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR

    services = [
        Service("MCP server", "ai_governance_harness.mcp_server", mcp_host, mcp_port, "/health/ready"),
        Service("chat UI", "ai_governance_harness.chat", chat_host, chat_port, "/health/ready"),
    ]
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

    env = os.environ.copy()
    env.update(
        {
            "MCP_TRANSPORT": "streamable-http",
            "MCP_HOST": mcp_host,
            "MCP_PORT": str(mcp_port),
            "MCP_HOSTED": "false",
            "MCP_SERVER_URL": f"http://{mcp_host}:{mcp_port}/mcp",
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

        ui_url = f"http://{chat_host}:{chat_port}"
        print(f"MCP server ready at http://{mcp_host}:{mcp_port}/mcp")
        print(f"Chat UI ready at {ui_url}")
        print("Press Ctrl+C to stop both services.")
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
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAILURE
    finally:
        for process in reversed(processes):
            _stop_process(process)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
