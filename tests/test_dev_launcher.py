"""Tests for the local development launcher."""

import socket
import pytest

from ai_governance_harness import dev_launcher

pytestmark = pytest.mark.usefixtures("mock_chat_environment")


def test_given_available_port_when_checked_then_reuses_closed_address(monkeypatch):
    # Arrange
    calls: list[tuple[object, ...]] = []

    class Probe:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def setsockopt(self, *args):
            calls.append(("setsockopt", *args))

        def bind(self, address):
            calls.append(("bind", address))

    monkeypatch.setattr(dev_launcher.socket, "socket", lambda *args: Probe())

    # Act
    available = dev_launcher._port_is_available("127.0.0.1", 8001)

    # Assert
    assert available is True
    assert calls == [
        ("setsockopt", socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),
        ("bind", ("127.0.0.1", 8001)),
    ]


def test_given_launcher_when_child_fails_then_start_order_and_cleanup(monkeypatch, capsys):
    processes = []
    ready = []
    envs = []

    class Process:
        returncode = 1

        def __init__(self, command, env):
            self.module = command[-1]
            self.stopped = False
            processes.append(self)
            envs.append(env)

        def poll(self):
            return 1 if len(processes) == 3 and self.module.endswith("mcp_server") else None

        def terminate(self):
            self.stopped = True

        def wait(self, timeout):
            return 0

    monkeypatch.setattr(dev_launcher.subprocess, "Popen", Process)
    monkeypatch.setattr(dev_launcher, "_port_is_available", lambda *args: True)
    monkeypatch.setattr(dev_launcher, "_wait_until_ready", lambda service, process: ready.append(service.name))
    monkeypatch.setattr(dev_launcher.webbrowser, "open", lambda url: None)
    assert dev_launcher.main() == 1
    assert ready == ["mock identity", "MCP server", "chat UI"]
    assert processes[0].stopped and processes[2].stopped
    assert all(env["MOCK_IDENTITY_ENABLED"] == "true" and env["MCP_PRINCIPAL_SOURCE"] == "jwt" for env in envs)
    assert "not Microsoft Entra" in capsys.readouterr().out


def test_given_occupied_port_when_launching_then_no_process(monkeypatch):
    monkeypatch.setattr(dev_launcher, "_port_is_available", lambda *args: False)
    monkeypatch.setattr(dev_launcher.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("must not start"))
    assert dev_launcher.main() == 2


@pytest.mark.parametrize(("name", "value"), [
    ("GOVERNANCE_ENVIRONMENT", "staging"), ("MCP_ENVIRONMENT", "production"),
    ("MCP_HOSTED", "true"), ("CONTAINER_APP_NAME", "hosted"),
    ("CHAT_HOST", "0.0.0.0"), ("MCP_PORT", "8002"),
])
def test_given_unsafe_config_when_launching_then_refuse(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    monkeypatch.setattr(dev_launcher.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("must not start"))
    assert dev_launcher.main() == 2