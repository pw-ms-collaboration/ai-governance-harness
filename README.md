# ai-governance-harness

Harness for AI governance, evaluation, and safety with Azure AI Foundry integration.

## Architecture & Cross-Tenant Setup

This repository is designed to connect to an **Azure AI Foundry** project residing in **any Azure Entra tenant**, even if your developer account, Git repository, or default Azure subscription belongs to a different tenant.

### 1. Prerequisites

- Python 3.10+
- Azure CLI (`az`) installed (e.g. `brew install azure-cli`)
- Access to the target Azure AI Foundry project

### 2. Quickstart

1. Create and activate a Python virtual environment:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

3. Configure your environment:
   ```sh
   cp .env.example .env
   ```
   Fill in your Foundry project details in `.env`:
   - `AZURE_TENANT_ID`: The tenant ID where your Azure AI Foundry project resides.
   - `AZURE_AI_PROJECT_CONNECTION_STRING` **or** `AZURE_SUBSCRIPTION_ID` + `AZURE_RESOURCE_GROUP` + `AZURE_AI_PROJECT_NAME`.

4. Authenticate against the target tenant:
   ```sh
   az login --tenant <YOUR_FOUNDRY_TENANT_ID>
   ```

5. Test the connection:
   ```sh
   python -m ai_governance_harness.foundry_client
   ```

