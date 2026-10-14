---
title: Team Getting Started Guide
description: Install and run the reference harness with local policies and separately configured Foundry model guardrails.
ms.date: 2026-10-14
ms.topic: tutorial
---

For all environment variables, defaults, and advanced prerequisites, use the
[configuration reference](configuration.md).
For component relationships and extension boundaries, read the
[architecture and control guide](architecture-and-controls.md).

## Scope and Safety Boundary

Use the harness to learn and adapt a governed application pattern: a browser
chat, an Azure AI Foundry model deployment, an MCP tool server, and a shared
default-deny policy gateway. The example workload uses synthetic
superannuation member data. It is not a production deployment or a compliance
certification.

Two different control planes are involved:

* Repository controls govern application lifecycle points, permitted tools,
  tool results, final responses, reliability, and telemetry.
* Foundry model guardrails govern supported model input and output risks in
  Azure. They are configured outside this repository and must be verified on
  the deployment you select.

An allow decision in one layer does not authorize bypassing the other. The
Foundry configuration described by the project owner is not exported here;
its controls, thresholds, and deployment assignments cannot be inferred from
the local policy or dashboard.

## Prerequisites

* Python 3.11, 3.12, or 3.13, the versions exercised by repository CI
* Git and either `uv` or Python's `venv` and `pip`
* Azure CLI for interactive developer authentication
* An Azure AI Foundry project, model deployment, and permission to invoke it
* Network access to your approved package source and Azure endpoints

You can exercise the deterministic CLI and unit tests without making model
calls. Browser chat requires a configured Foundry deployment. Cloud inference
and optional Azure Monitor export can incur charges.

## Install the Package

Run commands from the repository root. With `uv`:

```sh
uv sync --all-extras
```

On macOS or Linux, activate the environment before invoking installed commands:

```sh
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Alternatively, create a virtual environment and install using `pip`:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

For Windows, use `python -m venv .venv` and the PowerShell activation command
above. Dependency declarations and console commands are defined in
[pyproject.toml](../pyproject.toml). Use your organization's approved package
index as a single source, not an additional index combined with public PyPI;
see the [README package-feed instructions](../README.md#package-feeds).

## Configure Local Services

Copy the example file on macOS or Linux:

```sh
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit the local configuration with your project details. The following values
are placeholders, not usable credentials or endpoints:

```dotenv
AZURE_TENANT_ID=<foundry-tenant-id>
AZURE_AI_PROJECT_ENDPOINT=<foundry-project-endpoint>
AZURE_AI_PROJECT_CONNECTION_STRING=
AZURE_AI_MODEL_DEPLOYMENT_NAME=<model-deployment-name>
AZURE_AI_PROJECT_REGION=australiaeast

MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8001
MCP_PATH=/mcp
MCP_JSON_RESPONSE=false
MCP_SERVER_URL=http://127.0.0.1:8001/mcp
CHAT_HOST=127.0.0.1
CHAT_PORT=8080

GOVERNANCE_ENABLED=true
GOVERNANCE_ENVIRONMENT=local
GOVERNANCE_AGENT_ID=ai-governance-harness
GOVERNANCE_SANDBOX_PROVIDER=none
```

Leave `GOVERNANCE_POLICY_PATH` unset to use the packaged policy. Leave
`APPLICATIONINSIGHTS_CONNECTION_STRING` empty until telemetry export has been
approved. Do not commit your local environment file or real credentials.

The application loads the environment file without overriding existing
process environment variables. A previously exported value can therefore
take precedence over an edit to the file.

## Authenticate and Start

Sign in to the tenant that owns the Foundry project:

```sh
az login --tenant <foundry-tenant-id>
az account show --query "{tenantId:tenantId, subscriptionId:id}" -o table
ai-governance-dev
```

The launcher checks the local mock guard and occupied ports, starts the mock
issuer, waits for its health endpoint, starts MCP and waits for JWKS readiness,
then starts chat and opens <http://127.0.0.1:8080>. Press `Ctrl+C` to stop all
three child processes.

> [!WARNING]
> `ai-governance-dev` is a local-development launcher. It sets
> `MCP_HOSTED=false`, forces Streamable HTTP, and derives `MCP_SERVER_URL`
> using the configured MCP host and port with the fixed `/mcp` path. Do not
> use it as a hosted deployment entrypoint. The mock issuer is an intentional
> local authentication simulation and must remain on loopback.

For separate processes, run `ai-governance-identity`, `ai-governance-mcp`, then
`ai-governance-chat` in separate activated terminals using the local mock
settings in [.env.example](../.env.example). On macOS or Linux, the
[Makefile](../Makefile) also provides `make install` and `make run`.

## Verify the First Run

Readiness probes with the default ports:

```sh
curl --fail http://127.0.0.1:8001/health/ready
curl --fail http://127.0.0.1:8080/health/ready
curl --fail http://127.0.0.1:8002/healthz
```

Readiness is not proof of a successful model call or of the deployed Foundry
guardrails. In the chat UI, sign in as the local mock Retention Specialist,
then ask `Show me the profile for MEM-001.` to exercise
the model, MCP transport, typed tool, shared gateway, and output controls.
Use the governance panel's default-deny demonstration to observe a denial
without executing a prohibited operation.

A deterministic local smoke test, which does not call Foundry:

```sh
export MOCK_IDENTITY_ENABLED=true
export MOCK_IDENTITY_LOCAL_PERSONA=retention_specialist
python -m ai_governance_harness.cli profile MEM-001
```

PowerShell users should set these with `$env:NAME = "value"`. An unset local
mock persona denies data tools. See the [persona matrix and reporting
instructions](../README.md#use-the-chat-ui) for analyst aggregate access and
the roles that deny all data tools.

## Foundry Model Guardrails

The project owner has separately configured model-level guardrails in
Foundry. Before adopting the example, identify the guardrail assigned to your
model deployment and confirm its supported risks, intervention points, and
actions with your security and Responsible AI owners.

The official [Foundry guardrails overview](https://learn.microsoft.com/en-us/azure/foundry/guardrails/guardrails-overview)
distinguishes model input/output controls from Foundry Agent Service's
preview tool-call/tool-response controls. This local MCP application is not
a Foundry Agent Service agent; model guardrails do not replace the local
tool authorization and result checks.

### Verify Foundry Guardrails

Treat these as team adoption steps, not a claim that cloud settings have been
verified during documentation authoring:

1. Open the intended project in Foundry and identify the exact deployment
  configured in `AZURE_AI_MODEL_DEPLOYMENT_NAME`.
2. Inspect its assigned guardrail. If your team needs a custom policy, follow
  Microsoft's [guardrail configuration guidance](https://learn.microsoft.com/en-us/azure/foundry/guardrails/how-to-create-guardrails)
  with the required resource permissions. Do not assume your deployment uses
  the project owner's configuration or an unmodified default policy.
3. Review each required risk, supported input/output intervention point,
  severity threshold where applicable, and annotation versus blocking action.
  Verify model/region support and preview limitations before relying on a control.
4. Assign the reviewed guardrail to the deployment. Changing local YAML or
  region variables does not create, change, or assign a Foundry guardrail.
5. Exercise a benign synthetic chat turn and security-approved negative
  cases through the actual deployment. Validate both false positives and
  expected blocks using your organization's approved evaluation material.
6. For a provider block, confirm the browser's sanitized denial and the
  dashboard's `azure-ai-foundry` / `content_filter` post-model event. Local
  advice policy can deny a turn before it reaches Azure, so that alone is
  not evidence of a Foundry block.
7. Separately exercise unknown-tool denial, unsafe-result denial, and human
  approval refusal. Model-content controls do not authorize tools or replace
  those application checks.
8. Record effective guardrail settings and change ownership in an approved
  location. Retest after model, deployment, guardrail, SDK, or tool changes.
  Keep sensitive project coordinates and evaluation transcripts out of
  public documentation and application telemetry.

For portal configuration, Microsoft currently documents **Build > Guardrails**:
create or edit controls, select the target under **Add models**, review the
policy, and create or save it. Configuring the resource requires **Foundry
Account Owner** or higher. Assignment changes take effect immediately; test
on a nonproduction deployment first. The management API represents guardrails
as RAI policies and assigns a model deployment through `raiPolicyName`, not
through the harness's local YAML or environment variables.

Capture at least the following onboarding evidence:

| Evidence item                             | Team responsibility                                        |
| ----------------------------------------- | ---------------------------------------------------------- |
| Deployment and guardrail assignment       | Confirm the application calls the reviewed deployment      |
| Risks, intervention points, and actions   | Record what detects, annotates, and blocks                 |
| Thresholds and supported capabilities     | Review per-category cutoffs and feature/model availability |
| Benign and approved negative test results | Confirm success and blocks through the actual application  |
| Owner, review date, and change process    | Keep the cloud and local policy baselines current          |

Microsoft documents `Microsoft.DefaultV2` as the default model guardrail,
with model-specific controls. That is a documented default, not verification
of this project's assigned custom guardrail. See
[default safety policies](https://learn.microsoft.com/en-us/azure/foundry/guardrails/default-safety-policies)
and the [local provider-denial handling](architecture-and-controls.md#provider-denial-handling).

## Development and Assurance Commands

Run focused tests while changing one component; before handing an adaptation
to another team, run the repository's broader checks:

```sh
python -m pytest
python -m ruff check .
agt --json doctor
agt --json lint-policy --strict src/ai_governance_harness/governance/policies/default.yaml
agt --json verify --evidence src/ai_governance_harness/governance/agt-runtime-evidence.yaml
python -m build
ai-governance-audit
```

On Windows, set `$env:PYTHONUTF8 = "1"` before the `agt` commands. On macOS
or Linux, [Makefile](../Makefile) provides `make test`, `make lint`,
`make governance`, `make build`, and `make audit`. `make check` combines
lint, tests, governance validation, and build; it does not include the audit.
The [CI workflow](../.github/workflows/ci.yml) also generates an SBOM and
checks Python 3.11-3.13.

The dependency exception in
[security/vex/audit-policy.yaml](../security/vex/audit-policy.yaml) expires on
`2026-11-13`. Do not copy advisory ignores to another application or bypass
the wrapper. Changed versions, expired evidence, or newly reachable affected
APIs require reassessment, not disabling the gate.

### Restore the Demonstration Dataset

The packaged five-file dataset is generated by:

```sh
python -m ai_governance_harness.synthetic_data.generator
```

This command overwrites the synthetic fixtures in the source package; run it
only when you intend to regenerate them, then review the diff and restart
MCP. It is not a required first-run step when the packaged files are present.
The separate [data/generator.py](../src/ai_governance_harness/data/generator.py)
produces a different nested profile file and is not the gateway dataset
generator. `SuperannuationDataGateway(data_directory=...)` supports an
explicit Python-side fixture directory for tests; no remote tool exposes it.

## Operations and Troubleshooting

Health and governance endpoints with the default ports:

| Service   | Path                           | Meaning                                                      |
| --------- | ------------------------------ | ------------------------------------------------------------ |
| Chat      | `/health/live`                 | Process liveness                                             |
| Chat      | `/health/ready`                | Local governance/sandbox readiness, not model access         |
| Chat      | `/api/governance/snapshot`     | Bounded merged local and MCP state                           |
| Chat      | `/api/governance/demo/deny`    | POST: inert default-deny evaluation, no operation            |
| MCP       | `/health/live`                 | Process liveness                                             |
| MCP       | `/health/ready`                | Local governance/sandbox readiness                           |
| MCP       | `/governance/snapshot`         | Bounded MCP process state; protected in hosted mode          |
| MCP       | `/mcp`                         | Session-based protocol endpoint, not a plain REST tool route |

When troubleshooting, retain safe correlation IDs and decision metadata.
Do not paste raw prompts, synthetic or real member records, tool payloads,
tokens, identity headers, or credentials into logs or public issue reports.

| Symptom                                | Check and recovery                                                                                                                |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Console command not found              | Activate the environment and install/synchronize the package                                                                      |
| Port already occupied                  | Choose unused ports and update URL/origin values together; see [port configuration](configuration.md#nondefault-ports-and-paths)  |
| Chat HTTP 403 with an origin error     | Allow the exact browser origin including its port; origin checks are not login                                                    |
| Chat HTTP 403 `governance_denied`      | Inspect lifecycle, rule, and policy metadata; distinguish local denial from `azure-ai-foundry` provider denial                    |
| Chat HTTP 400, 413, or 415             | Check message schema, bounded body size, and `application/json` content type                                                      |
| Chat HTTP 502                          | Check Foundry credentials/deployment, MCP availability, tool-result bounds, and model-round budget                                |
| Model-round-limit error                | Review whether the task can complete within the bounded loop; do not remove governance or allow arbitrary tools                   |
| MCP HTTP 401 in hosted mode            | Validate trusted platform authentication and required tenant/audience/scope; local chat does not forward hosted identity          |
| MCP HTTP 429                           | Honor `Retry-After`; review approved rate capacity and request patterns                                                           |
| Approval tool refuses                  | Use an elicitation-capable MCP client with HTTP streaming; never simulate approval in tool arguments                              |
| Policy fails at startup                | Strict-lint the custom policy, check its path and workload binding, restore the reviewed policy, and restart both processes       |
| Sandbox readiness is false             | For the unchanged read-only demo, use `none`; executable tools still need an approved provider integration                        |
| Dashboard is partial                   | Check MCP's snapshot endpoint and separate observability circuit; readiness alone does not prove model access                     |
| Foundry connection-string error        | Use a project endpoint and clear the legacy connection string; see [SDK caveat](configuration.md#foundry-connection-and-identity) |
| Dependency audit fails                 | Review the expiry, exact package versions, affected-API scan, VEX set, and newly reported advisories with the maintainer          |

Stop the combined launcher with `Ctrl+C`. For independently started services,
stop their own terminal processes. `make stop` kills any process listening on
the configured ports, not only harness-owned processes; confirm ownership
before using it.

## Before Hosting or Using Real Data

Do not treat the [Dockerfile](../Dockerfile) as a production deployment. It
runs the local launcher, whose default bindings are loopback, and does not
provide ingress, TLS, identity, secrets management, or Azure resource setup.
The workspace's preconfigured task can also contain machine-specific paths;
the installed console commands are the portable startup path.

Before changing the local/synthetic boundary, assign owners and review:

* Authenticated chat access and trusted MCP ingress, with end-user/workload
  identity propagation and real data entitlements
* Actual Azure processing/storage/telemetry locations and regional constraints
* Secret management, TLS, approved egress, and production data contracts
* Cross-instance rate limits, session routing, reliability budgets, and
  operational recovery
* Approved human workflows for every write or external side effect
* Sandbox integration for executable capabilities and governed external memory
* Deployed Foundry guardrail assignments and approved end-to-end safety tests
* Logging/retention/privacy review, dependency provenance, and removal or
  reassessment of temporary VEX exceptions

## Review Before Adoption

Read the [architecture decisions](../README.md#architecture-decisions),
keep enforcement enabled, and retain the synthetic dataset until your data,
identity, privacy, and hosting changes have been reviewed. AI-assisted
documentation requires maintainer review, especially for safety and
production-readiness claims.
