"""Tests for the local development launcher."""

import socket

from ai_governance_harness import dev_launcher


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