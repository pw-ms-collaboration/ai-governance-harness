# AI Governance Harness

**A local-first reference implementation for observable, default-deny AI agent
governance with Azure AI Foundry, Model Context Protocol, and Microsoft Agent
Governance Toolkit.**

[![Continuous integration](https://github.com/pw-ms-collaboration/ai-governance-harness/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/pw-ms-collaboration/ai-governance-harness/actions/workflows/ci.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-2EA44F)](./LICENSE)
![Python 3.11-3.13](https://img.shields.io/badge/Python-3.11--3.13-3776AB?logo=python&logoColor=white)
![MCP 2.x](https://img.shields.io/badge/Model_Context_Protocol-2.x-5A45FF)
![Agent Governance Toolkit 4.1](https://img.shields.io/badge/Agent_Governance_Toolkit-4.1-0078D4?logo=github&logoColor=white)
![Release v0.0.1 draft](https://img.shields.io/badge/release-v0.0.1_draft-F2C94C)

The harness combines a browser chat, a protocol-compatible MCP server, five
typed tools, and a shared policy gateway. Every model and tool path is governed,
observable, and designed to fail closed. The demonstration uses synthetic
superannuation data so teams can explore practical governance controls without
exposing real member information.

> [!IMPORTANT]
> This release is a local demonstration and reference architecture, not a
> production certification. Azure hosting and deployment automation remain
> planned.

## Quick Navigation

* [See what the project demonstrates](#what-this-project-demonstrates)
* [Tour the governance dashboard](#governance-dashboard-tour)
* [Understand the request flow](#how-it-works)
* [Review the MCP tools](#available-mcp-tools)
* [Install and configure the project](#install-the-project)
* [Start the local services](#start-mcp-and-the-chat-ui)
* [Read the architecture decisions](#architecture-decisions)
* [Run validation](#validate-the-project)
* [Troubleshoot common problems](#troubleshooting)

## Capabilities at a Glance

| Capability | What the repository demonstrates |
|---|---|
| Default-deny enforcement | Policy checks before and after model and tool activity across chat, MCP, and direct gateway calls |
| Observable governance | Live allow and deny decisions, active rules, runtime readiness, circuit state, sandbox posture, and OWASP Agentic evidence |
| Bounded MCP access | Five schema-validated tools over stdio and session-based Streamable HTTP, with no arbitrary paths or writes |
| Human approval | MCP form elicitation that proceeds only after validated approval and fails closed otherwise |
| Privacy-safe telemetry | Bounded events that exclude prompts, tool payloads, model responses, tokens, and identity claims |
| Reliability controls | Independent circuit breakers, timeouts, readiness checks, and sandbox capability classification |
| Reproducible assurance | Python 3.11-3.13 CI, strict policy linting, toolkit verification, dependency audit, SBOM generation, and automated tests |
| Maintainer guidance | Detailed ADRs, recovery steps, extension boundaries, screenshots, and troubleshooting guidance |

## Technology Stack

| Area | Tools and technologies | Role |
|---|---|---|
| Language and models | [Python](https://www.python.org/) 3.11-3.13, [Azure AI Foundry](https://ai.azure.com/) | Application runtime and model inference |
| Agent governance | [Microsoft Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) 4.1, `agt-sandbox` | Policy enforcement, evidence verification, identity contracts, and sandbox readiness |
| Agent protocol | [Model Context Protocol](https://modelcontextprotocol.io/) Python SDK 2.x | Tool discovery, invocation, form elicitation, stdio, and Streamable HTTP |
| Web runtime | [Starlette](https://www.starlette.io/), [Uvicorn](https://www.uvicorn.org/) | Local chat API, static dashboard, health endpoints, and HTTP transport |
| Data contracts | [Pydantic](https://docs.pydantic.dev/), [PyYAML](https://pyyaml.org/) | Strict request, response, configuration, policy, and evidence schemas |
| Observability | [OpenTelemetry](https://opentelemetry.io/), Azure Monitor OpenTelemetry | Privacy-safe traces, metrics, logs, and governance events |
| Identity | [Azure Identity](https://learn.microsoft.com/python/api/overview/azure/identity-readme) | Developer and workload authentication for Azure AI Foundry |
| Quality and supply chain | [pytest](https://pytest.org/), [Ruff](https://docs.astral.sh/ruff/), `pip-audit`, CycloneDX, OpenVEX | Tests, linting, dependency review, SBOM generation, and governed exceptions |
| Automation | [GitHub Actions](https://github.com/features/actions), `uv`, Hatchling | Multi-version CI, environment synchronization, and package builds |

## What This Project Demonstrates

This repository is a runnable reference implementation for governing an
AI-assisted application, not only a collection of policy documents. It shows
how a browser chat, an Azure AI Foundry model, an MCP server, typed tools, and a
shared data gateway can operate behind one observable, default-deny governance
boundary.

The demonstration is designed to help teams:

* see where policy is evaluated before and after model and tool activity;
* prove that direct MCP and legacy callers cannot bypass the shared gateway;
* inspect allow and deny decisions without exposing prompts or business data;
* understand reliability, sandbox readiness, policy, and OWASP Agentic posture;
* reproduce the same local setup before extending it to hosted infrastructure.

![AI Governance Harness browser chat and governance dashboard overview](./docs/images/dashboard-overview.png)

*The local browser experience combines a synthetic-data chat workspace with a
live governance control plane. The green readiness indicator means the chat and
MCP services are available; it is not a claim of production certification.*

## Governance Dashboard Tour

The governance panel is intentionally visible beside the user experience so a
demonstration audience can connect an AI action with the controls and evidence
that govern it. Its main areas are:

1. **Decision controls and totals** — refresh or pause the bounded live view,
   run an inert default-deny demonstration, and compare allowed, denied, total,
   and retained event counts.
2. **Runtime posture** — inspect chat and MCP readiness, enforcement state,
   sandbox requirements, policy digest, and independent circuit-breaker state.
3. **Recent decisions** — review privacy-safe lifecycle, action, outcome, rule,
   source, and latency data without revealing prompts, arguments, results,
   member data, or identity claims.
4. **Active policy rules** — see the exact workload policy and the allow rules
   operating above the unmatched-action default deny.
5. **OWASP Agentic evidence** — distinguish implemented, partial, deferred, and
   not-applicable controls together with evidence and known limitations. This
   is a repository self-assessment, not certification or a third-party audit.
6. **Privacy and retention** — confirm that dashboard events are bounded,
   process-local, sanitized, and cleared when services restart.

![Governance decision counters and recent allow and deny activity](./docs/images/governance-decisions.png)

*The fixed prohibited-action demonstration records a deny decision and states
that no operation was executed. The event table provides enough metadata to
understand enforcement without reproducing sensitive request content.*

![Runtime readiness, active policy rules, and OWASP Agentic evidence](./docs/images/governance-policy-evidence.png)

*The detailed view connects service readiness and circuit state to the active
default-deny policy and a concise sample of the repository-owned OWASP Agentic
evidence. Expand the live panel to inspect the complete rule and evidence sets.*

All screenshots in this README were captured from the local synthetic
demonstration. They contain no credentials, real member information, raw
prompts, tool arguments, tool results, or identity claims.

## How It Works

The browser never calls Foundry or the data gateway directly:

1. The browser sends the bounded conversation to the local chat service.
2. The governance boundary evaluates the input and pre-model lifecycle points.
3. The chat service sends the conversation and discovered tool schemas to the
   configured Azure AI Foundry model through a timeout and circuit breaker.
4. When the model selects a tool, the chat service evaluates it against the
   exact default-deny policy and calls it through MCP
   Streamable HTTP.
5. The MCP server validates the request. The shared gateway then independently
   enforces pre-tool and post-tool policy so direct legacy callers cannot
   bypass governance.
6. The tool result returns to the model, which prepares the response through
   the post-model policy point.
7. The response passes through output policy, advice, and disclosure guardrails
   before reaching the browser.

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
| `prepare_member_outreach_case` | Requests MCP form approval before preparing a synthetic, read-only outreach case |

The remote tool surface does not accept filesystem paths, arbitrary data
filters, or write operations.

### MCP Form Elicitation

The `prepare_member_outreach_case` tool demonstrates the MCP server requesting
structured human approval during a tool call. An elicitation-capable MCP client
receives a primitive boolean form explaining that the case uses synthetic
disengagement signals and that no message, notification, or other external
action will occur.

The tool proceeds only when the protocol response is `accept` and the validated
`approved` field is `true`. It fails closed when the user declines, cancels,
submits invalid content, selects `false`, or uses a client without form
elicitation support. Audit telemetry records only the approval outcome and tool
name; it does not record elicited content.

The MCP SDK negotiates the interaction for the active protocol revision. Legacy
clients receive an `elicitation/create` server request during the tool call.
Modern clients receive an `InputRequiredResult` and automatically retry the
tool with the validated form response and opaque request state. The tool
function and approval policy remain the same across stdio and Streamable HTTP.
The HTTP server uses MCP sessions because the negotiated 2025-11-25 revision
requires a server-to-client request channel for form elicitation. Streaming
responses are enabled by default with `MCP_JSON_RESPONSE=false`; setting it to
`true` disables that back-channel, so approval tools fail closed.

The browser chat does not yet provide a universal approval interface. Calling
this tool through a client without MCP elicitation support therefore returns a
sanitized tool error rather than bypassing approval.

### Retention eligibility and specialist referral

Routine outreach preparation uses trusted synthetic case records from
[`retention_cases.json`](./src/ai_governance_harness/data/synthetic/retention_cases.json).
The pre-tool policy permits only
`data.retention_handling_status == 'routine_permitted'`.
It blocks duplicate open retention cases, specialist handling, completed exits,
closed accounts and unconfirmed eligibility. The member profile exposes a
bounded `retention_review` for staff and chat preflight checks; case narratives
are not included.

| Internal case state | Behaviour |
|---------------------|-----------|
| Open routine retention case | Deny duplicate preparation; continue the existing case |
| Open specialist case | Deny routine preparation; provide staff referral instructions |
| Closed routine case | Require explicit clearance plus new signals, contact eligibility and cooling-off eligibility |
| Closed specialist case | Require explicit routine clearance; otherwise retain specialist routing |
| Closed account or completed exit | Deny ordinary retention preparation |
| Missing or unknown eligibility | Deny until staff verify the internal records |

Eligibility is checked before requesting MCP approval and rechecked when
preparing the response. Approval cannot override a business-policy denial.
Chat retrieves the profile through MCP before attempting outreach and presents
a policy-denial message with the next staff action. The MCP server independently
checks its trusted records, so direct clients cannot bypass the restriction.

Specialist handoff is a fixed staff-facing referral summary containing the
approved team and existing synthetic case reference. Staff must complete the
handoff through the fund's internal process. No specialist case is created, no
notification is sent and no member is contacted. Routine preparation is also
read-only: it does not persist a new case or change existing case status.

Demo personas:

* `MEM-001`: eligible, no existing case.
* `MEM-002`: closed routine case with explicit clearance, eligible.
* `MEM-003`: open specialist case, refer to complaints.
* `MEM-004`: open routine case, continue `CASE-004`.
* `MEM-005`: closed specialist case without clearance, refer to hardship.
* `MEM-006`: completed exit, ordinary retention preparation denied.
* `MEM-007`: closed specialist case explicitly cleared, eligible.

These are illustrative company-policy facts, not approved production rules.
Contact restrictions, new signals and cooling-off are explicit eligibility
statuses; no cooling-off duration is invented. An outreach signal can still be
surfaced even when preparation is blocked. Production integration must source
these facts and routing rules from approved internal systems.

## Agent Governance Toolkit

The application uses the released Agent Governance Toolkit 4.1 line and
`agt-sandbox` policy contracts as mandatory runtime dependencies. Public
Preview APIs are isolated behind
[`src/ai_governance_harness/governance/`](./src/ai_governance_harness/governance/)
so future toolkit upgrades do not spread across the application.

The packaged
[`default.yaml`](./src/ai_governance_harness/governance/policies/default.yaml)
policy:

* Binds rules to the exact `ai-governance-harness` workload ID.
* Defaults every unmatched action to deny.
* Allows only the five current read-only tools.
* Covers startup, input, model, tool, output, and shutdown lifecycle points.
* Treats required approval without an approval flow as denied.
* Fails closed when policy loading or evaluation fails.

Tool responses are scanned in memory using the existing personal-advice pattern
guardrail, including strings nested in dictionaries and lists. The
`deny-personal-advice-tool-response` post-tool rule blocks detected personalized
financial advice. Known tool-result allow rules require
`data.advice_scan_status == 'passed'`; missing or unknown scan status is denied.
Factual information and general guidance that do not match prohibited patterns
remain permitted.

The shared gateway protects direct callers, the MCP adapter checks complete
responses (including outreach cases), and the chat service checks structured
MCP results before passing them to the model. A blocked MCP response returns a
sanitized tool error, not a successful replacement payload. Only the scan
status and result type enter policy evaluation, never the response text.
The existing final chat-response guardrail remains in place.

This deterministic pattern scan is not a legal advice classifier and cannot
detect every paraphrase or contextual recommendation. Production use requires
compliance-reviewed detection and evaluation cases.

The five current tools read packaged synthetic data and do not execute
generated code, shell commands, untrusted files, or unrestricted network
requests. `GOVERNANCE_SANDBOX_PROVIDER=none` is therefore ready for the current
surface. Any future executable capability is denied unless an approved,
healthy Agent Sandbox provider is explicitly integrated. Merely setting a
provider name does not activate a privileged provider.

Policy decisions emit only allowlisted metadata: lifecycle point, outcome,
matched rule, policy name and digest, enforcement mode, and evaluation
latency. Prompts, tool arguments, results, member data, tokens, email
addresses, and raw identity claims are not emitted or persisted.

The repository has two complementary evidence files:

* [`agt-runtime-evidence.yaml`](./src/ai_governance_harness/governance/agt-runtime-evidence.yaml)
  is validated by `agt verify`.
* [`owasp-agentic.yaml`](./src/ai_governance_harness/governance/evidence/owasp-agentic.yaml)
  records the repository-specific ASI01-ASI10 posture and limitations.

Toolkit verification is an internal package-presence and runtime-evidence
self-assessment. It is not OWASP certification, a third-party audit, or proof
that model reasoning is safe. The repository matrix intentionally identifies
partial controls, including hosted principal propagation, supply-chain
provenance, external memory governance, universal human approval, and behavior
quarantine.

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

Configure governance:

```env
GOVERNANCE_ENABLED=true
GOVERNANCE_ENVIRONMENT=local
GOVERNANCE_AGENT_ID=ai-governance-harness
GOVERNANCE_OPERATION_TIMEOUT_SECONDS=30
GOVERNANCE_CIRCUIT_FAILURE_THRESHOLD=3
GOVERNANCE_CIRCUIT_RECOVERY_SECONDS=30
GOVERNANCE_SANDBOX_PROVIDER=none
```

Leave `GOVERNANCE_POLICY_PATH` unset to use the policy packaged with the
application. A custom path must identify a valid toolkit YAML policy. Runtime
governance can be disabled only when `GOVERNANCE_ENVIRONMENT=test`; local,
staging, production, and hosted modes reject disabled enforcement.

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
| `http://127.0.0.1:8080/api/governance/snapshot` | Merged privacy-safe chat and MCP governance snapshot |
| `http://127.0.0.1:8080/api/governance/demo/deny` | Inert default-deny demonstration |
| `http://127.0.0.1:8080/health/live` | Chat liveness |
| `http://127.0.0.1:8080/health/ready` | Chat governance and sandbox readiness |
| `http://127.0.0.1:8001/mcp` | MCP Streamable HTTP endpoint |
| `http://127.0.0.1:8001/governance/snapshot` | MCP process governance snapshot |
| `http://127.0.0.1:8001/health/live` | MCP liveness |
| `http://127.0.0.1:8001/health/ready` | MCP governance and sandbox readiness |

Chat API failures use a structured, privacy-safe error envelope:

```json
{
  "error": {
    "code": "governance_denied",
    "message": "Governance policy denied the requested operation.",
    "correlation_id": "request-reference",
    "details": {
      "lifecycle_point": "post_tool",
      "matched_rule": "deny-personal-advice-tool-response"
    }
  }
}
```

Governance denials return HTTP 403 and bounded policy metadata. Invalid requests
return HTTP 400. Model, MCP, or other upstream failures return HTTP 502 with a
different stable error code. Responses never include raw prompts, tool
arguments, tool results, credentials, or internal exception text.
The browser, static assets, and API responses use `Cache-Control: no-store` so
the UI error contract and governance table cannot drift behind the running
service after an update.

Personalized financial-advice requests are classified in memory before the
model call. Only the bounded `advice_request_status` reaches policy evaluation;
request text is not included in policy data or governance events. The
`deny-personal-advice-request` rule returns HTTP 403 and appears as a denial in
the governance panel. General factual questions continue through the normal
chat path. When a short follow-up supplies only a member ID, classification
also considers the immediately preceding user request so a multi-turn personal
advice request cannot bypass the input rule by deferring the identifier.
Failed and denied browser turns remain visible to the user but are removed from
the active request history, so a rejected intent cannot contaminate the next
independent question.

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

### Use the Governance Panel

The responsive governance panel beside the conversation explains the active
control plane without exposing request content. It shows:

* Allowed and denied decision totals.
* Recent policy decisions from the chat and MCP processes.
* Runtime readiness, policy digest, circuit states, and sandbox posture.
* Active default-deny policy rules.
* Repository-specific OWASP Agentic evidence and known limitations.
* Privacy and retention guarantees.

Use **Pause updates** to stop the five-second automatic refresh or **Refresh**
to request the current snapshot. Automatic refresh runs only while the page is
visible. **Demonstrate default deny** evaluates a fixed prohibited action,
records the denial, and never executes the action.

The panel retains at most 200 sanitized events in each process and shows at
most 100 merged events. Events remain in process memory and reset when the
services restart. Raw prompts, tool arguments and results, member data,
transcripts, credentials, and raw identity claims are not included.

## Architecture Decisions

> **Heads up — architecture decision records are part of the project contract.**
> Before changing governance enforcement, telemetry, sandboxing, dependency
> policy, package feeds, or the observability topology, read the related ADR.

An architecture decision record (ADR) captures an important design choice
together with its context, alternatives, tradeoffs, consequences, risks, and
exit strategy. Keeping this reasoning beside the code is a software architecture
best practice: it helps teammates understand not only **what** was built, but
**why** it was built that way and which assumptions must be re-evaluated before
the design changes.

ADRs are especially important for this harness because several safeguards are
load-bearing. A locally convenient change could otherwise weaken default-deny
enforcement, expose sensitive telemetry, bypass the reviewed dependency
exception, or imply sandbox and hosted-identity guarantees that are not yet
implemented. The records provide:

* a recovery path when a maintainer inherits or troubleshoots the system;
* explicit boundaries between implemented, deferred, and temporary behavior;
* evidence and measurable criteria for validating future changes;
* safe extension points for new providers, tools, policies, and deployments;
* an audit trail for security, compliance, reliability, and supply-chain
  decisions.

The detailed records under [`docs/planning/adrs/`](./docs/planning/adrs/)
describe the current design:

1. [Contain Agent Governance Toolkit behind a versioned adapter](./docs/planning/adrs/0001-contain-agent-governance-toolkit-behind-a-versioned-adapter.md)
2. [Enforce default deny at every execution boundary](./docs/planning/adrs/0002-enforce-default-deny-at-every-execution-boundary.md)
3. [Minimize identity and governance telemetry](./docs/planning/adrs/0003-minimize-identity-and-governance-telemetry.md)
4. [Use local-first reliability and sandbox readiness boundaries](./docs/planning/adrs/0004-use-local-first-reliability-and-sandbox-readiness-boundaries.md)
5. [Present governance through a same-origin observability panel](./docs/planning/adrs/0005-present-governance-through-a-same-origin-observability-panel.md)
6. [Govern Toolkit dependency risk with an expiring VEX exception](./docs/planning/adrs/0006-govern-toolkit-dependency-risk-with-an-expiring-vex-exception.md)
7. [Use feed-neutral manifests and repeatable team commands](./docs/planning/adrs/0007-use-feed-neutral-manifests-and-repeatable-team-commands.md)

### How to Use These Records

The records are initially `proposed`. Repository maintainers should:

1. Review the evidence, alternatives, consequences, and success criteria.
2. Change an applicable record to `accepted` before treating it as
   architectural authority.
3. Link significant implementation changes to the ADRs they implement or
   affect.
4. Create a new ADR when a decision changes materially; do not rewrite the
   history of an accepted record.
5. Mark the earlier record `superseded` and link both records so future
   maintainers can follow the decision lineage.

New records should use
[`docs/planning/adrs/.adr-config.yml`](./docs/planning/adrs/.adr-config.yml) for
the next monotonic identifier. Small implementation details that do not alter a
documented architectural outcome can remain in ordinary code review rather than
requiring another ADR.

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
ai-governance-audit
```

This command runs `pip-audit` with the temporary, reachability-backed VEX
exception in [`security/vex/`](./security/vex/). It fails closed if the
exception expires, reviewed package versions change, affected APIs become
reachable, VEX evidence drifts, or any unapproved vulnerability is found. The
current exception expires on 13 November 2026 and exists because Toolkit Core
4.1.0 requires `cryptography<49`, while clearing all three inherited advisories
requires `cryptography>=50`.

Do not force `cryptography>=50` or bypass `ai-governance-audit`. Upgrade to a
compatible released Toolkit version and remove the exception as soon as one is
available.

Run Agent Governance Toolkit checks:

```sh
agt --json doctor
agt --json lint-policy --strict src/ai_governance_harness/governance/policies/default.yaml
agt --json verify --evidence src/ai_governance_harness/governance/agt-runtime-evidence.yaml
```

On a Windows shell that is not UTF-8, set `PYTHONUTF8=1` before running `agt`.
The 4.1 CLI places `--json` before the command and does not expose a documented
`verify --strict` option; verification is strict by default.

Generate a reproducible CycloneDX SBOM:

```sh
cyclonedx-py environment --pyproject pyproject.toml --output-reproducible --output-file dist/sbom.cdx.json
```

The test suite covers direct gateway behavior, protocol discovery and tool
calls, stdio and HTTP transports, request security, configuration, telemetry
privacy, default-deny policy, legacy bypass prevention, circuit breaking,
sandbox failure, adversarial goal hijacking, chat orchestration, browser API
behavior, and launcher-related service contracts.

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
5. Both readiness endpoints report `"status":"ready"` with governance enabled
   and the sandbox either ready or not required for the read-only surface.

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

### Governance startup or readiness fails

Check that the configured policy exists and passes strict linting:

```sh
agt --json lint-policy --strict src/ai_governance_harness/governance/policies/default.yaml
```

An invalid or missing policy intentionally prevents startup. If a custom policy
caused the failure, restore `GOVERNANCE_POLICY_PATH` to the last known-good
policy or unset it to use the packaged default. Do not bypass the failure by
disabling governance outside the test environment.

If readiness reports a sandbox provider as `not_ready`, restore
`GOVERNANCE_SANDBOX_PROVIDER=none` for the current read-only tool surface.
Executable capabilities must remain disabled until a privileged provider is
separately approved, configured, and tested.

## Current Scope

Implemented and locally validated:

* Python 3.11 through 3.13 project metadata and CI matrix.
* Five typed read-only MCP tools.
* stdio and session-based Streamable HTTP.
* Configurable MCP and chat hosts and ports.
* Request validation, bounded rate limiting, health routes, OAuth metadata, and
  privacy-safe telemetry.
* Agent Governance Toolkit 4.1 default-deny lifecycle and tool enforcement.
* Toolkit circuit breakers, total operation timeouts, and sandbox readiness.
* Toolkit evidence verification, strict policy linting, dependency audit, and
  CycloneDX SBOM generation in CI.
* Foundry-powered MCP tool calling.
* Accessible dependency-free browser chat.
* Separate and combined local launchers.

Deferred:

* Azure Container Apps deployment.
* Deployed Microsoft Entra authentication.
* Privileged Docker, Azure Container Apps, or Hyperlight sandbox providers.
* A universal human-approval interface and external memory governance.
* Third-party OWASP certification or independent security audit.
* Infrastructure as code and deployment workflows.
* Remote browser and MCP acceptance testing.

## License

This project is available under the [MIT License](./LICENSE).
