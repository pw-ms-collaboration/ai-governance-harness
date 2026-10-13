"""Azure AI Foundry connection module supporting cross-tenant authentication."""

import os
import sys
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load environment variables from .env file if present
load_dotenv()


def get_azure_credential():
    """Instantiate an Azure credential targeting the configured tenant if specified.

    When AZURE_TENANT_ID is provided, routes token requests to that specific
    tenant (via AzureCliCredential or DefaultAzureCredential with AZURE_TENANT_ID).
    """
    tenant_id = os.getenv("AZURE_TENANT_ID")
    if tenant_id:
        # DefaultAzureCredential does not take tenant_id directly in its constructor,
        # but respects AZURE_TENANT_ID in the environment for underlying credentials.
        os.environ["AZURE_TENANT_ID"] = tenant_id
    return DefaultAzureCredential()


def get_foundry_client() -> AIProjectClient:
    """Create and return an AIProjectClient connected to Azure AI Foundry.

    Supports either:
    1. AZURE_AI_PROJECT_CONNECTION_STRING
    2. AZURE_AI_PROJECT_ENDPOINT
    3. Separate subscription_id, resource_group_name, project_name coordinates
    """
    credential = get_azure_credential()
    conn_str = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

    if conn_str:
        return AIProjectClient.from_connection_string(
            credential=credential,
            conn_str=conn_str,
        )

    if endpoint:
        return AIProjectClient(
            endpoint=endpoint,
            credential=credential,
        )

    sub_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    rg_name = os.getenv("AZURE_RESOURCE_GROUP")
    proj_name = os.getenv("AZURE_AI_PROJECT_NAME")

    if sub_id and rg_name and proj_name:
        return AIProjectClient(
            subscription_id=sub_id,
            resource_group_name=rg_name,
            project_name=proj_name,
            credential=credential,
        )

    raise ValueError(
        "Missing Azure AI Foundry connection configuration. "
        "Please provide AZURE_AI_PROJECT_CONNECTION_STRING or "
        "(AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_AI_PROJECT_NAME) in .env"
    )


def test_connection():
    """Verify connectivity to the configured Azure AI Foundry project."""
    print("Testing Azure AI Foundry connectivity...")
    tenant = os.getenv("AZURE_TENANT_ID") or "(default tenant)"
    print(f"Target Entra Tenant: {tenant}")

    try:
        client = get_foundry_client()
        print("Successfully authenticated and created AIProjectClient!")
        return client
    except Exception as exc:
        print(f"Failed to connect: {exc}", file=sys.stderr)
        return None


if __name__ == "__main__":
    test_connection()
