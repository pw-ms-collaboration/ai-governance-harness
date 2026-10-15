---
title: Configuration Reference
description: Environment variables, defaults, runtime limits, and security prerequisites for the AI Governance Harness.
ms.date: 2026-10-14
ms.topic: reference
---

## Configuration Sources and Precedence

Start with the [team setup guide](getting-started.md) and
[.env.example](../.env.example). All commands below assume an activated
environment and the repository root as the working directory.

The launcher, Foundry client, and service configuration modules use
`python-dotenv`. Existing process environment values take precedence over
values in the local environment file. Governance settings consume that
environment; they do not independently load an environment file.

Settings and the policy engine are cached or constructed per process. Restart
the affected services after changing configuration or policy. A file edit is not a
policy hot reload. In separately managed processes, give chat and MCP the
same reviewed workload policy and confirm their policy digests agree.

Boolean settings accept `true/false`, `1/0`, `yes/no`, and `on/off`, ignoring
case and surrounding whitespace. An unrecognized boolean or an out-of-range
typed setting causes startup validation to fail rather than falling back.

## Foundry Connection and Identity

Source: [foundry_client.py](../src/ai_governance_harness/foundry_client.py).

| Variable                               | Default or requirement              | Meaning                                                                                           |
| -------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------- |
| `AZURE_AI_PROJECT_ENDPOINT`            | Set for the recommended chat path   | Foundry project endpoint used by `AIProjectClient`; use the endpoint supplied by the portal       |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME`       | Required to start chat              | Deployment name passed to the model, not a model-family name                                      |
| `AZURE_TENANT_ID`                      | Credential-chain default if unset   | Tenant for Azure credentials; also the fallback MCP authentication tenant                         |
| `AZURE_CLIENT_ID`                      | Optional                            | Identity configuration consumed by Azure Identity                                                 |
| `AZURE_CLIENT_SECRET`                  | Optional secret                     | Service-principal credential consumed by Azure Identity; do not commit or log it                  |
| `AZURE_AI_PROJECT_CONNECTION_STRING`   | Empty                               | Legacy connection branch; a nonempty value takes precedence over the endpoint                     |
| `AZURE_SUBSCRIPTION_ID`                | Optional legacy coordinate          | Used with resource group and project name only when neither connection string nor endpoint is set |
| `AZURE_RESOURCE_GROUP`                 | Optional legacy coordinate          | Resource group for that legacy coordinate branch                                                  |
| `AZURE_AI_PROJECT_NAME`                | Optional legacy coordinate          | Project name for that legacy coordinate branch                                                    |
| `AZURE_AI_PROJECT_REGION`              | Unset in typed server defaults      | Preferred region value for hosted MCP validation and telemetry resource metadata                  |
| `AZURE_REGION`                         | Fallback region                     | Used when `AZURE_AI_PROJECT_REGION` is absent or empty                                            |
| `AZURE_OPENAI_ENDPOINT`                | Optional sovereignty fallback       | Read by the sovereignty helper, not used to construct the chat model client                       |

The Foundry client uses `DefaultAzureCredential`. Developer authentication
normally comes from `az login`; an appropriately configured workload identity
or service principal can be used in a reviewed hosting design. Setting the
tenant variable does not replace signing Azure CLI into the correct tenant.

> [!IMPORTANT]
> Prefer the project endpoint and leave the connection string empty. The
> source contains older connection-string and coordinate branches, but SDK
> compatibility is not guaranteed by those branches. In the environment
> inspected for this guide, `azure-ai-projects` 2.8.0 requires `endpoint` and
> does not expose `AIProjectClient.from_connection_string`.

`python -m ai_governance_harness.foundry_client` constructs a client; it does
not issue an inference request or prove authorization. It also catches errors
and can exit normally after reporting failure. Use a successful governed chat
turn to establish end-to-end access.

### Region Checks Are Not Residency Proof

The example sovereignty helper recognizes `australiaeast` and
`australiasoutheast`. Hosted MCP requires an approved configured region. The
deterministic orchestrator also calls region and endpoint validation in
`--live` mode.

The browser chat entrypoint does not invoke those sovereignty checks before
calling Foundry; its region value is used for telemetry metadata. A configured
region is not verification of a deployment's actual processing location,
deployment type, failover, storage, or log residency. Validate those Azure
properties and your organization's regional policy independently.

## Browser Chat Settings

Sources: [chat/config.py](../src/ai_governance_harness/chat/config.py) and
[chat/service.py](../src/ai_governance_harness/chat/service.py).

| Variable                       | Default                     | Validation and behavior                                                                    |
| ------------------------------ | --------------------------- | ------------------------------------------------------------------------------------------ |
| `CHAT_HOST`                    | `127.0.0.1`                 | Nonempty bind address; keep local services on loopback                                     |
| `CHAT_PORT`                    | `8080`                      | Integer from 1 to 65,535                                                                   |
| `CHAT_HOSTED`                  | `false`                     | Explicit `true/false`; hosted mode requires EasyAuth, Prompt Agent mode, HTTPS origins and authenticated MCP snapshots |
| `CHAT_AUTH_TENANT_ID`           | Required in hosted mode     | Exact tenant claim expected in the platform-injected principal |
| `CHAT_AUTH_AUDIENCE`            | Required in hosted mode     | Exact chat audience claim expected in the platform-injected principal |
| `MCP_SERVER_URL`               | `http://127.0.0.1:8001/mcp` | Absolute HTTP(S) URL; no credentials, query, or fragment                                   |
| `CHAT_ALLOWED_ORIGINS`         | Loopback origins below      | Comma-separated explicit origins; wildcards rejected                                       |
| `CHAT_MAX_MESSAGES`            | `20`                        | Setting range 1-50, but request-schema hard cap is 20                                      |
| `CHAT_MAX_MESSAGE_LENGTH`      | `4000`                      | Setting range 100-20,000, but message-schema hard cap is 4,000                             |
| `CHAT_MAX_TOOL_ROUNDS`         | `4`                         | Setting range 1-8; model loop permits at most this value plus one model completion attempt |
| `CHAT_MAX_OUTPUT_TOKENS`       | `1200`                      | Setting range 100-4,000; sent as `max_completion_tokens`                                   |
| `CHAT_CLASSIFIER_MAX_OUTPUT_TOKENS` | `400`                  | Setting range 100-800; bounds the strict semantic-classifier response                      |
| `CHAT_MAX_REQUEST_BODY_SIZE`   | `65536` bytes               | Setting range 1,024-1,048,576; oversized JSON returns HTTP 413                             |

Default chat origins are `http://127.0.0.1:8080` and
`http://localhost:8080`. These are exact origins including the port. Changing
`CHAT_PORT` does not update the allowlist automatically.

The request schema accepts only `user` and `assistant` messages, rejects
extra fields, and requires the last message to be a user turn. Effective
message-count and message-length limits are the smaller of the configured
limit and the schema hard cap. Raising a setting does not enlarge that cap.

Local chat authenticates through the guarded mock sidecar. Hosted chat requires
`CHAT_HOSTED=true`, `MOCK_IDENTITY_ENABLED=false`, `CHAT_USE_PROMPT_AGENT=true`
and `FOUNDRY_AGENT_NAME`. It validates the tenant, audience and user object ID
in EasyAuth's platform-injected principal. All application routes except
`/health/live` and `/health/ready` require authentication; mock sign-in returns
404. The browser uses the EasyAuth session cookie rather than a mock token.

Mandatory Container Apps EasyAuth is the trusted boundary that validates tokens
and prevents client-supplied identity headers from becoming trusted principals.
Do not expose the application directly, disable platform authentication or
exclude application routes. Application header checks are not JWT verification
and cannot establish platform provenance independently.

Hosted chat records only a hashed caller reference and bounded identity labels.
It invokes the configured Foundry Prompt Agent through the existing workload
credential. Browser credentials and staff roles are not forwarded to Foundry or
MCP. The agent's configured MCP authorization remains separate from browser
sign-in; this mode does not implement real Entra Agent ID provisioning or
per-user delegated tool authorization. Local mock OBO behavior is unchanged.

## MCP Transport and HTTP Settings

Sources: [mcp_server/config.py](../src/ai_governance_harness/mcp_server/config.py)
and [mcp_server/security.py](../src/ai_governance_harness/mcp_server/security.py).

| Variable                             | Default                  | Validation and behavior                                                     |
| ------------------------------------ | ------------------------ | --------------------------------------------------------------------------- |
| `MCP_TRANSPORT`                      | `stdio`                  | `stdio` or `streamable-http`; the example file and launcher select HTTP     |
| `MCP_HOST`                           | `127.0.0.1`              | Nonempty bind address                                                       |
| `MCP_PORT`                           | `8001`                   | Integer from 1 to 65,535                                                    |
| `MCP_PATH`                           | `/mcp`                   | One absolute path; traversal, double leading slash, and null bytes rejected |
| `MCP_ENVIRONMENT`                    | `local`                  | `local`, `development`, `staging`, `production`, or `test`                  |
| `MCP_ALLOWED_ORIGINS`                | Loopback origins below   | Explicit comma-separated origins; wildcards rejected                        |
| `MCP_HOSTED`                         | `false`                  | Activates the trusted-platform identity and regional prerequisites          |
| `MCP_JSON_RESPONSE`                  | `false`                  | Keep false for streaming and the form-elicitation back-channel              |
| `MCP_MAX_REQUEST_BODY_SIZE`          | `1048576` bytes          | Range 1-4,194,304; enforced before protocol dispatch                        |
| `MCP_RATE_LIMIT_CAPACITY`            | `60`                     | Token-bucket capacity, range 1-10,000                                       |
| `MCP_RATE_LIMIT_REFILL_PER_SECOND`   | `1.0`                    | Refill rate greater than 0 and at most 1,000                                |
| `MCP_MAX_REPLICAS`                   | `3`                      | Validated value 1-300; does not deploy, limit, or autoscale replicas        |
| `CONTAINER_APP_REVISION`             | `local`                  | Revision label used in telemetry; not a deployment command                  |

Default MCP origins are `http://127.0.0.1` and `http://localhost`, without
nondefault ports. Browser chat calls its own origin, and the chat backend
calls MCP, so you do not need to enable direct browser-to-MCP access for the
reference UI. A custom browser MCP client needs its exact origin explicitly
allowed.

Streamable HTTP is session-based, not stateless. The middleware accepts
protocol-version headers `2025-11-25` and `2025-06-18`; this tuple is fixed in
code, not an environment setting. MCP initialization and session negotiation
are required before tool calls. An ordinary JSON POST or browser GET to the
MCP URL is not a substitute for an MCP client.

HTTP rate limiting is process-local and best-effort. Each authenticated local
mock or hosted principal gets a separate bucket keyed by its hash;
buckets are not shared between processes or replicas. Health and discovery
routes bypass these checks; the local snapshot route also bypasses them in
nonhosted mode.

### Hosted MCP Identity Prerequisites

Local HTTP uses the guarded mock JWT source, not anonymous access. The
[environment template](../.env.example) lists the issuer, JWKS, tenant,
audience, scope and interactive/reporting agent IDs. The combined launcher
derives these synthetic settings. Chat requires the loopback sidecar URL and
interactive agent ID and forwards OBO-shaped tokens on every MCP request.
See [local mock startup and testing](../README.md#start-mcp-and-the-chat-ui).

| Variable                    | Requirement                                        |
| --------------------------- | -------------------------------------------------- |
| `MCP_AUTH_TENANT_ID`        | Tenant; falls back to `AZURE_TENANT_ID`            |
| `MCP_AUTH_AUDIENCE`         | Expected audience claim                            |
| `MCP_AUTH_REQUIRED_SCOPE`   | Expected delegated scope in `scp`                  |
| `MCP_AUTH_REQUIRED_ROLE`    | Application-role alternative to the delegated scope |
| `MCP_AUTH_SNAPSHOT_ROLE`    | Separate application role for governance snapshots |
| `MCP_HOSTED_TOOL_CLIENT_ID` | Approved Foundry application client ID for hosted read-only tools |
| `MCP_RESOURCE_URL`          | Resource URL published in OAuth discovery          |
| `AGENT_ID_INTERACTIVE_ID`   | Allowlisted interactive agent ID |
| `AGENT_ID_REPORTING_ID`     | Separate allowlisted reporting agent ID |

With `MCP_HOSTED=true`, tenant, audience, resource URL, exactly one required
scope or application role, an approved region and Streamable HTTP are required.
Middleware expects trusted `x-ms-client-principal*` platform headers identifying
Entra ID. Optional interactive/reporting agent IDs must be supplied together;
that path retains the agent claim-shape checks used by local mock identities.

The existing application-role Foundry route instead sets
`MCP_HOSTED_TOOL_CLIENT_ID` and leaves both optional agent IDs unset. Only an
app-only principal with `Mcp.Tools.Invoke`, the configured `azp` or `appid`, no
delegated scope, and an object ID matching the platform principal can become
the bounded `tool_workload` actor. Its policy allows the four read-only insight
tools, not outreach preparation or arbitrary tools. No staff role is inferred.
The snapshot reader role remains unable to enter the MCP tool endpoint, and
the tool role cannot read snapshots. Real Entra Agent ID provisioning and
per-user delegation remain deferred.

> [!WARNING]
> Header parsing is not bearer-token signature validation. Your hosting
> platform must authenticate callers, remove untrusted incoming identity
> headers, inject validated headers, and prevent direct access around that
> platform. OAuth discovery metadata does not supply this infrastructure or
> authenticate the browser chat. Do not deploy by only setting these variables.

The hosted snapshot route is authenticated, while health and OAuth discovery
remain public. The local chat snapshot fetcher does not send a hosted
principal or credential; a hosted integration needs a reviewed identity flow.

## Mandatory Governance Settings

Source: [governance/config.py](../src/ai_governance_harness/governance/config.py).

| Variable                                  | Default                         | Validation and behavior                                                    |
| ----------------------------------------- | ------------------------------- | -------------------------------------------------------------------------- |
| `GOVERNANCE_ENABLED`                      | `true`                          | May be false only in explicit `test` mode with hosted mode false           |
| `GOVERNANCE_ENVIRONMENT`                  | `MCP_ENVIRONMENT`, then `local` | Same five environment names as MCP                                         |
| `GOVERNANCE_AGENT_ID`                     | `ai-governance-harness`         | 1-128 characters; must match the policy's exact `agent` binding            |
| `GOVERNANCE_POLICY_PATH`                  | Packaged default policy         | Custom policy must be an existing file when enforcement is enabled         |
| `GOVERNANCE_OPERATION_TIMEOUT_SECONDS`    | `30`                            | Greater than 0 and at most 300; wraps remote-operation boundaries          |
| `GOVERNANCE_CIRCUIT_FAILURE_THRESHOLD`    | `3`                             | Integer 1-100; separate circuits for Foundry, MCP, and observability       |
| `GOVERNANCE_CIRCUIT_RECOVERY_SECONDS`     | `30`                            | Greater than 0 and at most 3,600                                           |
| `GOVERNANCE_SANDBOX_PROVIDER`             | `none`                          | `none` or `docker`; executable capabilities require an integrated provider |

The [packaged policy](../src/ai_governance_harness/governance/policies/default.yaml)
has `default_action: deny` and is bound to `ai-governance-harness`. Changing
the workload ID alone does not grant another workload the existing allows.
There is no production audit-only toggle. Disabled enforcement is a test
fixture, not an adoption or troubleshooting mode.

`none` is appropriate for the current fixed read-only data tools. No runtime
entrypoint supplies a Docker sandbox provider, so selecting `docker` does
not create or activate one and leaves sandbox readiness false. New code,
shell, filesystem-write, or unrestricted-network capabilities require
explicit provider integration and execution-class checks, not an environment
change alone.

### Customize the Local Policy

Prefer tightening a reviewed policy before broadening the tool surface. For
example, a member-only team can deny cohort analytics without changing the
gateway or removing default-deny enforcement.

Copy the current default into a reviewed team configuration:

```sh
cp src/ai_governance_harness/governance/policies/default.yaml team-policy.yaml
```

Use `Copy-Item` instead of `cp` in PowerShell. Add the following entry to the
copy's existing `rules` list, retaining the surrounding policy fields and
existing rules:

```yaml
- name: deny-cohort-analytics-for-member-only-workload
  stage: pre_tool
  condition: "action.type == 'get_cohort_churn_analytics'"
  action: deny
```

Select the copy in both service environments:

```dotenv
GOVERNANCE_POLICY_PATH=team-policy.yaml
```

Strict-lint it before restarting:

```sh
agt --json lint-policy --strict team-policy.yaml
```

The engine's deny-overrides strategy makes this explicit deny win over the
existing action allow. Verify that a permitted member profile still works,
cohort analytics is denied through chat and direct MCP, and a direct Python
gateway caller cannot bypass the same rule. Restart both services and check
their loaded policy digests. Linting validates policy structure; behavioral
tests validate whether it enforces your intent.

Changing the workload ID also requires a matching policy `agent` binding and
review of request context. The current browser middleware labels its context
as the fixed harness workload in `local` mode with local authentication;
setting environment variables does not implement a hosted chat identity flow.

## Telemetry and TLS Settings

| Variable                                 | Default   | Behavior                                                                  |
| ---------------------------------------- | --------- | ------------------------------------------------------------------------- |
| `APPLICATIONINSIGHTS_CONNECTION_STRING`  | Empty     | Enables optional Azure Monitor export in both services                    |
| `REQUESTS_CA_BUNDLE`                     | Unset     | Optional approved PEM bundle used by compatible Requests/Azure HTTP paths |

Chat uses manual-only spans and metrics export, with logging export and
automatic HTTP/model instrumentation disabled. MCP emits explicit tool and
request instruments and structured audit logs. Review exporter destinations,
retention, access, and additional instrumentation before enabling export.
Application telemetry exclusions do not establish Azure service-side data
retention rules.

Use an organization-approved CA bundle for a corporate TLS proxy. Do not
disable certificate verification. `REQUESTS_CA_BUNDLE` does not automatically
configure every library's TLS trust, including all OpenAI/HTTPX or urllib
paths; troubleshoot the actual failing client with your platform team.

## Nondefault Ports and Paths

For a local launch on different ports, edit the environment values together:

```dotenv
MCP_PORT=9001
MCP_SERVER_URL=http://127.0.0.1:9001/mcp
CHAT_PORT=9090
CHAT_ALLOWED_ORIGINS=http://127.0.0.1:9090,http://localhost:9090
```

Run `ai-governance-dev` and open <http://127.0.0.1:9090>. MCP remains on
loopback. Existing exported variables still override the file.

For a custom MCP path, start the services separately and set both values:

```dotenv
MCP_PATH=/tools/mcp
MCP_SERVER_URL=http://127.0.0.1:8001/tools/mcp
```

Do not use the combined launcher for that path: it always derives `/mcp`.
The observability fetcher separately targets `/governance/snapshot` on the
configured MCP origin, not a path relative to `MCP_PATH`.

## Fixed Limits and Nonsettings

The following are implemented constants or separate cloud configuration,
not tunable environment values:

* At most 20 messages and 4,000 characters per message in the chat schema
* At most 32,000 characters in each serialized tool result forwarded to the model
* At most 262,144 bytes read from the MCP snapshot endpoint
* A 200-event process-memory ring per service, with 50 recent events exposed
  by each default snapshot and at most 100 merged recent events
* No persisted application conversation transcripts
* No environment variable that installs or assigns Foundry model guardrails
* No environment variable that implements hosted chat authentication,
  cross-replica rate limiting, external contact, or a production data source

AI-assisted configuration documentation requires maintainer review. Verify
defaults against the linked configuration modules when upgrading the package.
