---
title: AI Governance Harness
description: Setup and validation guide for the AI governance harness and Azure AI Foundry configuration
---

## ai-governance-harness

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

2. Install the project and its development dependencies. Editable installation
   makes `ai_governance_harness` importable when running the documented module
   commands:
   ```sh
   python -m pip install -e ".[dev]"
   ```

3. Configure your environment:
   ```sh
   cp .env.example .env
   ```
   Fill in your Foundry project details in `.env`:
   - `AZURE_TENANT_ID`: The tenant ID where your Azure AI Foundry project resides.
   - One connection option: `AZURE_AI_PROJECT_CONNECTION_STRING`,
     `AZURE_AI_PROJECT_ENDPOINT`, or the full coordinate set
     `AZURE_SUBSCRIPTION_ID` + `AZURE_RESOURCE_GROUP` + `AZURE_AI_PROJECT_NAME`.
   - `AZURE_AI_PROJECT_REGION`: Set this to the project's actual Azure region
     when the endpoint hostname does not identify its region. The sovereignty
     guardrail currently permits `australiaeast` and `australiasoutheast`.

4. Authenticate against the target tenant:
   ```sh
   az login --tenant <YOUR_FOUNDRY_TENANT_ID>
   ```

5. Confirm the active Azure CLI tenant and subscription:
   ```sh
   az account show --query "{tenantId:tenantId, subscriptionId:id, name:name}" -o table
   ```

6. Test the Foundry client configuration:
   ```sh
   python -m ai_governance_harness.foundry_client
   ```

   This loads `.env`, creates the configured credential and `AIProjectClient`,
   and reports setup errors. Client creation alone may not prove the identity has
   permission to call project APIs; a real authorized Foundry operation is needed
   to verify access end to end.

### Validate the Configuration

Run the automated local checks:

```sh
pytest
```

The sovereignty guardrail reads `AZURE_AI_PROJECT_REGION` or `AZURE_REGION` for
general Foundry endpoint hostnames such as `*.services.ai.azure.com`. It rejects
regions outside `australiaeast` and `australiasoutheast`; set the region to the
project's actual Azure deployment region, not just the region you intend to use.

The CLI can be smoke-tested with:

```sh
python -m ai_governance_harness.cli --live profile MEM-001
```

`--live` enables the live-mode configuration and sovereignty checks, but the
current profile command still reads the repository's local synthetic data. It
does not make a Foundry inference request, so use the connection test and an
authorized Foundry API operation when validating remote access.

