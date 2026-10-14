"""Tests for Foundry credential selection."""

from __future__ import annotations

import pytest

from ai_governance_harness import foundry_client


def test_given_azure_cli_mode_when_creating_credential_then_uses_cli_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    expected_credential = object()
    monkeypatch.setenv("AZURE_CREDENTIAL_MODE", "azure-cli")
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant-123")
    monkeypatch.setattr(
        foundry_client,
        "AzureCliCredential",
        lambda *, tenant_id: (expected_credential, tenant_id),
    )

    # Act
    credential, selected_tenant = foundry_client.get_azure_credential()

    # Assert
    assert credential is expected_credential
    assert selected_tenant == "tenant-123"


def test_given_default_mode_when_creating_credential_then_uses_default_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    expected_credential = object()
    monkeypatch.setenv("AZURE_CREDENTIAL_MODE", "default")
    monkeypatch.setattr(
        foundry_client,
        "DefaultAzureCredential",
        lambda: expected_credential,
    )

    # Act
    credential = foundry_client.get_azure_credential()

    # Assert
    assert credential is expected_credential


def test_given_invalid_credential_mode_when_creating_credential_then_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("AZURE_CREDENTIAL_MODE", "unknown")

    # Act & Assert
    with pytest.raises(ValueError, match="AZURE_CREDENTIAL_MODE"):
        foundry_client.get_azure_credential()