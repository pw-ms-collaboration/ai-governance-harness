---
title: AI Governance Harness
description: Local MCP server and Azure AI Foundry chat UI for synthetic superannuation governance scenarios
---

# AI Governance Harness

The AI Governance Harness is a local development application for exploring
governed AI interactions over synthetic superannuation data.

It provides:

* A protocol-compatible Model Context Protocol (MCP) server.
* Four typed, read-only governance tools.
* MCP support over stdio and stateless Streamable HTTP.
* A browser chat interface powered by an Azure AI Foundry model.
* Advice-boundary, provenance, sovereignty, request-security, and telemetry
  controls.
* Separate MCP and chat processes, plus one launcher that starts both.

The current implementation is intended for local use. Azure hosting and
deployment automation remain planned but are not active.

## How It Works

The browser never calls Foundry or the data gateway directly:

1. The browser sends the bounded conversation to the local chat service.
2. The chat service sends the conversation and discovered tool schemas to the
   configured Azure AI Foundry model.
3. When the model selects a tool, the chat service calls it through MCP
   Streamable HTTP.
4. The MCP server validates the request and executes the existing read-only
   gateway operation.
5. The tool result returns to the model, which prepares the response.
6. The response passes through the advice and disclosure guardrails before
   reaching the browser.

The UI and chat service do not persist conversation transcripts. Browser and
request memory are bounded, and prompts, member IDs, tool arguments, tool
results, tokens, and model responses are excluded from application telemetry.

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `get_member_profile` | Returns a synthetic member's internal fund profile |
| `get_member_disengagement_signals` | Returns factual churn and disengagement signals |
| `get_cohort_churn_analytics` | Returns aggregate cohort churn analytics |
| `get_fum_outflow_summary` | Returns aggregate funds-under-management outflow risk |

The remote tool surface does not accept filesystem paths, arbitrary data
filters, or write operations.

## Prerequisites

* Python 3.11, 3.12, or 3.13.
* Azure CLI.
* Access to an Azure AI Foundry project and model deployment.
* `uv` or standard Python packaging tools.

Confirm the selected interpreter:

```powershell
python --version
```

## Install the Project

Create and activate a virtual environment.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Install the project and development dependencies.

With `uv`:

```sh
uv sync --all-extras
```

Or with standard Python packaging tools:

```sh
python -m pip install -e ".[dev]"
```

The editable installation makes the package and these commands available:

* `ai-governance-mcp`
* `ai-governance-chat`
* `ai-governance-dev`

[pyproject.toml](./pyproject.toml) is the dependency source of truth. The
repository intentionally does not maintain a duplicate `requirements.txt`.

### Package Feeds

Public PyPI users do not need additional configuration.

On Microsoft-managed devices where public PyPI is blocked, use the approved CFS
Package Feed Proxy as the single package source. Do not combine it with public
PyPI through `--extra-index-url`.

PowerShell with `uv`:

```powershell
$env:UV_DEFAULT_INDEX = "https://packagefeedproxy.microsoft.io/pypi/simple/"
uv sync --all-extras
```

macOS or Linux with `uv`:

```sh
export UV_DEFAULT_INDEX="https://packagefeedproxy.microsoft.io/pypi/simple/"
uv sync --all-extras
```

Configure `pip` for the current user:

```sh
python -m pip config set global.index-url https://packagefeedproxy.microsoft.io/pypi/simple/
python -m pip install -e ".[dev]"
```

Inspect or remove the `pip` override:

```sh
python -m pip config get global.index-url
python -m pip config unset global.index-url
```

Clear the temporary `uv` setting with
`Remove-Item Env:UV_DEFAULT_INDEX` in PowerShell or
`unset UV_DEFAULT_INDEX` on macOS and Linux.

## Configure the Environment

Copy the example configuration:

PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```sh
cp .env.example .env
```

Do not commit `.env`. It may contain tenant, subscription, project, endpoint, or
credential information.

Configure these Foundry values:

```env
AZURE_TENANT_ID=<foundry-tenant-id>
AZURE_AI_PROJECT_ENDPOINT=<foundry-project-endpoint>
AZURE_AI_PROJECT_REGION=australiaeast
AZURE_AI_MODEL_DEPLOYMENT_NAME=<model-deployment-name>
```

The project client also supports a project connection string or the complete
subscription, resource-group, and project coordinate set. Leave
`AZURE_AI_PROJECT_CONNECTION_STRING` empty when using the project endpoint; a
non-empty placeholder takes precedence over the valid endpoint.

Configure the local services:

```env
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8001
MCP_PATH=/mcp

CHAT_HOST=127.0.0.1
CHAT_PORT=8080
MCP_SERVER_URL=http://127.0.0.1:8001/mcp
```

`MCP_PORT` and the port inside `MCP_SERVER_URL` must match. Both service ports
are configurable. The defaults use MCP port `8001` and chat port `8080`.

## Authenticate with Azure

Sign in to the tenant containing the Foundry project:

```sh
az login --tenant <foundry-tenant-id>
```

Confirm the active tenant and subscription:

```sh
az account show --query "{tenantId:tenantId, subscriptionId:id, name:name}" -o table
```

Test Foundry client creation:

```sh
python -m ai_governance_harness.foundry_client
```

Client creation confirms that configuration and credential construction
succeeded. A model call or authorized project operation is still required to
prove end-to-end project access.

## Start MCP and the Chat UI

### Start Both Services

The recommended local workflow is:

```sh
ai-governance-dev
```

The launcher:

1. Loads configuration from `.env`.
2. Confirms that the configured MCP and chat ports are available.
3. Starts the MCP service.
4. Waits for MCP readiness.
5. Starts the chat service.
6. Waits for chat readiness.
7. Opens the chat UI in the default browser.
8. Stops both child processes when you press `Ctrl+C`.

With the default configuration, open:

```text
http://127.0.0.1:8080
```

### Start the Services Separately

Start MCP in the first terminal:

```sh
ai-governance-mcp
```

Start the chat service in the second terminal:

```sh
ai-governance-chat
```

Both commands load `.env`. Separate terminals are useful when inspecting MCP
and chat logs independently.

### Run MCP over stdio

PowerShell:

```powershell
$env:MCP_TRANSPORT = "stdio"
ai-governance-mcp
```

macOS or Linux:

```sh
export MCP_TRANSPORT=stdio
ai-governance-mcp
```

The stdio process reserves standard output for MCP protocol messages and sends
diagnostics to standard error.

## Local Endpoints

With the default ports:

| Endpoint | Purpose |
|----------|---------|
| `http://127.0.0.1:8080` | Browser chat UI |
| `http://127.0.0.1:8080/api/chat` | Chat API used by the browser |
| `http://127.0.0.1:8080/health/live` | Chat liveness |
| `http://127.0.0.1:8080/health/ready` | Chat readiness |
| `http://127.0.0.1:8001/mcp` | MCP Streamable HTTP endpoint |
| `http://127.0.0.1:8001/health/live` | MCP liveness |
| `http://127.0.0.1:8001/health/ready` | MCP readiness |

The OAuth protected-resource metadata routes exist for future hosted
authentication work. Local development does not require Container Apps identity
headers.

## Use the Chat UI

The included dataset contains synthetic member IDs such as:

* `MEM-001`
* `MEM-002`
* `MEM-003`

Example questions:

* `Show me the profile for MEM-001.`
* `What are the churn signals for MEM-002?`
* `Summarize cohort churn risk and FUM at risk.`

Responses use synthetic in-fund data only. They do not represent a complete
financial position or personal financial advice. The response guardrails attach
the general-advice and in-fund provenance notices.

## Existing Command-Line Interface

The original deterministic CLI remains available and does not call Foundry or
cross the MCP transport:

```sh
python -m ai_governance_harness.cli profile MEM-001
python -m ai_governance_harness.cli churn MEM-002
python -m ai_governance_harness.cli prep MEM-003
python -m ai_governance_harness.cli fum-outflows
```

The `--live` option enables live configuration and sovereignty validation:

```sh
python -m ai_governance_harness.cli --live profile MEM-001
```

It still reads the local synthetic dataset and does not make a model inference
request.

## Validate the Project

Run all tests:

```sh
python -m pytest
```

Run linting:

```sh
python -m ruff check .
```

Build the package:

```sh
uv build
```

Audit installed dependencies:

```sh
python -m pip_audit
```

The test suite covers direct gateway behavior, protocol discovery and tool
calls, stdio and HTTP transports, request security, configuration, telemetry
privacy, chat orchestration, browser API behavior, and launcher-related service
contracts.

## Troubleshooting

### A launcher command is not found

Activate `.venv`, then reinstall the editable project:

```sh
python -m pip install -e ".[dev]"
```

Or resynchronize with `uv`:

```sh
uv sync --all-extras
```

### A configured port is already in use

Choose unused ports in `.env` and keep the MCP URL aligned:

```env
MCP_PORT=8101
CHAT_PORT=8180
MCP_SERVER_URL=http://127.0.0.1:8101/mcp
```

Restart `ai-governance-dev` after saving the file.

### The UI opens but chat requests fail

Check:

1. `AZURE_AI_MODEL_DEPLOYMENT_NAME` matches an existing deployment.
2. `AZURE_AI_PROJECT_ENDPOINT` identifies the intended Foundry project.
3. `az account show` reports the expected tenant and subscription.
4. `MCP_SERVER_URL` matches the running MCP host, port, and path.
5. Both readiness endpoints return `{"status":"ready"}`.

Restart the services after changing `.env`.

### Foundry authentication uses the wrong tenant

Run:

```sh
az logout
az login --tenant <foundry-tenant-id>
az account set --subscription <subscription-id>
```

Then confirm the active account before restarting the chat service.

### Public PyPI access fails

Microsoft-managed devices may require the CFS proxy described in
[Package Feeds](#package-feeds). Use one trusted index rather than combining
public and internal indexes.

## Current Scope

Implemented and locally validated:

* Python 3.11 through 3.13 project metadata and CI matrix.
* Four typed read-only MCP tools.
* stdio and stateless Streamable HTTP.
* Configurable MCP and chat hosts and ports.
* Request validation, bounded rate limiting, health routes, OAuth metadata, and
  privacy-safe telemetry.
* Foundry-powered MCP tool calling.
* Accessible dependency-free browser chat.
* Separate and combined local launchers.

Deferred:

* Azure Container Apps deployment.
* Deployed Microsoft Entra authentication.
* Infrastructure as code and deployment workflows.
* Remote browser and MCP acceptance testing.
