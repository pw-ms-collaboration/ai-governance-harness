<!-- markdownlint-disable-file -->
# RPI Plan: Align Harness with Azure-Native Workshop Architecture

## Task Metadata

* Task ID: `azure-native-migration-2026-10-14`
* Task slug: `azure-native-services-migration`
* Plan date: 2026-10-14
* Sanitization: Environment-specific names, addresses, image identifiers, and identity IDs use placeholders. Findings describe planning-time observations, not current live inventory.

## Executive Summary

* Bottom line: Extend the current synthetic-data harness toward the workshop architecture with ACA, an APIM-backed MCP gateway, a browser chat UI in front of a Foundry Prompt Agent, identity, guardrails, and correlated Azure Monitor evidence.
* Why this matters: The current code is a local-style chat orchestrator with direct Foundry and MCP calls. The target architecture places Azure-native identity, guardrails, gateway controls, approval, and evidence across that flow.
* Planning result: Partial and not ready for implementation. The user confirmed the existing chat UI remains in front of a backend Foundry Prompt Agent. Existing ACA/MCP work, Azure feature availability, identity propagation, and audit-retention decisions still need preflight.
* Confidence and uncertainty: High confidence in the repo delta and release order. Azure region, tenant, Foundry agent/MCP feature availability, Entra Agent ID support, APIM MCP streaming and elicitation behavior, and business-approved audit retention are not established by repository evidence.

### What You May Not Know

* The existing `real-mcp-server` plan already owns the baseline ACA, Bicep, remote MCP authentication, and App Insights work. This plan depends on that baseline and avoids duplicating it.
* The Dockerfile still starts the local two-process supervisor. It is not the final hosted workload entrypoint.
* The current chat calls Foundry Chat Completions and directly calls MCP. It does not invoke a Foundry Prompt Agent or pass an authenticated agent token to MCP.
* The chat UI is the user-facing frontend; `ChatService` remains its API façade and invokes the Foundry Prompt Agent as the backend orchestrator.
* The image describes some gateway capabilities as preview. The deployment must verify current tenant, region, protocol, and client support before selecting the Foundry AI Gateway path; APIM remains the concrete gateway fallback.

## Phase Checklist

### Before

```mermaid
%%{init: {"themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "16px"}}}%%
flowchart LR
	USER["Workshop user"] --> UI["Browser chat"]
	UI --> CHAT["Chat service"]
	CHAT --> FOUNDRY["Foundry Chat Completions"]
	CHAT --> MCP["MCP Streamable HTTP"]
	MCP --> TOOLS["Typed synthetic-data tools"]
	TOOLS --> DATA["Synthetic JSON"]
	GOV["Existing AGT policy"] --> CHAT
	GOV --> MCP
	MCP --> EVENTS["Process-local events"]
```

### After

```mermaid
%%{init: {"themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "16px"}}}%%
flowchart LR
	USER["Workshop user"] --> UI["Added: Chat UI and API on ACA"]
	UI --> AGENT["Added: Foundry Prompt Agent"]
	ID["Added: Entra Agent ID"] -. assigned identity .-> AGENT
	ID -. scoped token .-> GATE["Added: APIM MCP gateway"]
	AGENT --> GATE
	GUARD["Added: Foundry guardrails"] --> AGENT
	GATE --> MCP["Added: Private MCP service on ACA"]
	GOV["Existing: AGT default-deny runtime"] --> UI
	GOV --> MCP
	MCP --> TOOLS["Typed tools"]
	TOOLS --> DATA["Synthetic JSON for pilot"]
	MCP <--> HUMAN["Added: selected human approval"]
	AGENT --> USER
	UI -. W3C trace context .-> MON["Added: Azure Monitor evidence"]
	AGENT -. traces and outcomes .-> MON
	GATE -. diagnostics .-> MON
	MCP -. sanitized events .-> MON
	PIPE["Added: Bicep and CI baseline"] --> UI
	PIPE --> MCP
	A2["Added after core gates: second agent"] --> GATE
	classDef new stroke-dasharray: 5 5
	class UI,MCP,PIPE,AGENT,ID,GATE,GUARD,HUMAN,MON,A2 new
```

The target keeps the synthetic MCP business-service boundary and existing AGT
policy. It adds a Foundry-hosted agent, agent identity, a single APIM-backed
gateway, Foundry guardrails, explicit approval for selected actions, and
correlated Azure-native evidence. The second agent is conditional stretch work.

The release sequence is incremental: P01 validates platform capability and the
inherited host baseline; P02 moves the synthetic pilot to the Foundry agent and
agent identity; P03 routes MCP through APIM; P04 verifies approval and evidence
before core promotion; P05 adds another agent only after core gates pass. Each
release keeps synthetic data and a rollback path.

<!-- rpi:phase id=P01 -->
### [ ] P01: Preflight and hosted baseline gate

Goals:
* Establish evidence-backed service choices and confirm that the existing hosted MCP foundation is complete before any new Azure service or production identity is introduced.

Dependencies:
* None. Existing deployment-plan work is a prerequisite to later phases, not assumed complete.

```mermaid
%%{init: {"themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "16px"}}}%%
flowchart LR
	USER["Workshop user"] --> UI["Added: Chat UI and API on ACA"]
	UI --> AGENT["Added: Foundry Prompt Agent"]
	ID["Added: Entra Agent ID"] -. assigned identity .-> AGENT
	ID -. scoped token .-> GATE["Added: APIM MCP gateway"]
	AGENT --> GATE
	GUARD["Added: Foundry guardrails"] --> AGENT
	GATE --> MCP["Added: Private MCP service on ACA"]
	GOV["Existing: AGT default-deny runtime"] --> UI
	GOV --> MCP
	MCP --> TOOLS["Typed tools"]
	TOOLS --> DATA["Synthetic JSON for pilot"]
	MCP <--> HUMAN["Added: selected human approval"]
	AGENT --> USER
	UI -. W3C trace context .-> MON["Added: Azure Monitor evidence"]
	AGENT -. traces and outcomes .-> MON
	GATE -. diagnostics .-> MON
	MCP -. sanitized events .-> MON
	PIPE["Added: Bicep and CI baseline"] --> UI
	PIPE --> MCP
	A2["Added after core gates: second agent"] --> GATE
	classDef new stroke-dasharray: 5 5
	class UI,MCP,PIPE,AGENT,ID,GATE,GUARD,HUMAN,MON,A2 new
	classDef phase fill:#fff3bf,color:#1f2328,stroke:#9a6700,stroke-width:2px
	class UI,MCP,PIPE phase
```

Highlighted work: confirm the existing ACA, Bicep, CI, and MCP boundaries before extending them.

<!-- rpi:task id=P01-T01 -->
#### [ ] P01-T01: Verify Foundry and gateway capabilities

Goals:
* Select an agent-to-MCP route only after proving support in the intended tenant, region, and protocol combination.

Requirements:
* `FR-001`, `FR-002`, `FR-004`, `NFR-002`, `NFR-005`.
* Acceptance: The decision record names the Foundry Agent Service type, Entra Agent ID capability, APIM or Foundry AI Gateway option, supported region, token audience/scope, and any preview dependency. It records an explicit supported fallback or a stop condition.
* Acceptance: The selected route supports the required MCP Streamable HTTP/session behavior and the selected approval interaction without bypassing the gateway.
* Verification: Platform owner confirms current product/region availability and quota; run a synthetic-tool protocol spike through the proposed Foundry-to-gateway-to-MCP route, including authentication failure and unsupported elicitation behavior.

Details:
* The supplied architecture describes Foundry AI Gateway MCP support as preview and identifies APIM as its implementation. Treat current availability and compatibility as a release gate, not as a guaranteed feature.
* Infrastructure as Code is supported for the surrounding resources: Microsoft Learn documents Bicep resources for the Foundry Cognitive Services account/project and project connections. The APIM `service/apis` Bicep schema includes MCP API type/properties, but the MCP properties use a preview API version. Confirm that API version and tier in the target subscription before deployment.
* The Foundry project provider exposes projects and connections but no agent/toolbox ARM resource type. Prompt Agent versions and MCP tool definitions are Foundry data-plane operations. The installed `azure-ai-projects` `2.8.0` exposes `MCPTool` and `PromptAgentDefinition`; `ChatService` invokes the agent with the supported Responses API `agent_reference` contract.
* Entra Agent ID lifecycle is managed through Foundry integration or Microsoft Graph, not as a native `Microsoft.CognitiveServices` Bicep resource. The existing Foundry agent has an identity object; verify its Entra Agent ID semantics and permissions instead of creating another identity by default. Bicep may orchestrate a Graph step only with explicitly approved Graph permissions and an idempotent lifecycle.
* `.env` identifies Foundry project `<foundry-project-name>` in `australiaeast`; the project resource exists and its configured `<model-deployment-name>` deployment reports `Succeeded`. The Azure CLI and `.env` tenant/subscription contexts match; identifiers are not recorded here.
* Read-only Foundry SDK queries found five agents. `<foundry-agent-name>` is enabled, version `1` is a `prompt` definition, and its identity record has both client and principal identifiers. Identifier values are intentionally omitted.
* Version `1` had no tools. Version `2` is now active with one MCP server entry, the four approved read-only tools, and project connection `<mcp-project-connection-name>`; version `1` and the original instructions remain unchanged. Invocation remains pending APIM API deployment and the agent app-role assignment.
* APIM `<apim-service-name>` in the selected resource group reports `Succeeded` at Developer tier, but its API list contains no MCP API. Foundry AI Gateway MCP routing and MCP streaming/session/elicitation behavior remain unverified.
* Confirmed user direction: keep Azure Container Apps as the workload host and use Foundry AI Gateway backed by APIM for eligible MCP tools when available in the target region and when MCP discovery, streaming/session, authentication, and elicitation tests pass. Use direct APIM as the approved fallback if that integration is unavailable or incompatible. Do not create a public direct-to-MCP route.
* Confirmed user direction: retain the existing chat UI in front of the Foundry Prompt Agent. `ChatService` remains the browser API façade and invokes the hosted agent; it does not replace the agent as backend orchestrator.
* Preserve the current direct Chat Completions path only as rollback until an authenticated synthetic end-to-end call proves the selected identity/token contract. The application workload identity and per-agent identity are separate principals with separate permissions.
* Read-only Azure checks used the target configured in `.env`: Foundry project `<foundry-project-name>`, resource group `<resource-group>`, and region `australiaeast`. The Azure CLI tenant/subscription context matched the configured tenant/subscription; identifiers are omitted from this artifact.
* The Foundry project resource exists in `australiaeast`, and its `<model-deployment-name>` deployment reports provisioning state `Succeeded`. APIM `<apim-service-name>` exists in `australiaeast`, reports provisioning state `Succeeded`, and uses the Developer tier. A read-only APIM API listing found no MCP API.
* `az ml workspace show` returns `ResourceNotFound` because this Foundry project is not an Azure ML workspace. Foundry SDK read-only queries succeeded when scoped to the user-provided CA bundle; TLS verification remained enabled. No Azure resource or persistent trust setting was changed.
* If the agent service cannot invoke the MCP endpoint through the gateway with the required identity and session behavior, retain the direct Chat Completions path for the pilot and return the architecture decision for owner review. Do not silently claim target alignment.

References:
* [src/ai_governance_harness/chat/service.py](../../../src/ai_governance_harness/chat/service.py): Current direct Foundry and MCP call path.
* [src/ai_governance_harness/mcp_server/config.py](../../../src/ai_governance_harness/mcp_server/config.py): Current hosted MCP auth and region requirements.
* [Foundry MCP tool support](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/model-context-protocol): Supported prompt-agent SDK/REST configuration, identity options, approval, and private MCP requirements.
* [Foundry project Bicep resource](https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/accounts/projects): ARM/Bicep project and identity properties.
* [Foundry project connection Bicep resource](https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/accounts/projects/connections): Connection resource schema and supported authentication types.
* [APIM API Bicep resource](https://learn.microsoft.com/en-us/azure/templates/microsoft.apimanagement/service/apis): MCP API type, transport properties, and preview API version.
* [Entra Agent ID creation](https://learn.microsoft.com/en-us/entra/agent-id/create-delete-agent-identities): Product and Microsoft Graph identity lifecycle.
* Workshop architecture supplied in the conversation: Foundry Prompt Agent, Entra Agent ID, and APIM-backed MCP gateway target.

Dependencies:
* None.

<!-- rpi:task id=P01-T02 -->
#### [ ] P01-T02: Verify the inherited ACA foundation

Goals:
* Use one evidenced and repeatable ACA deployment baseline instead of creating competing infrastructure plans.

Requirements:
* `FR-002`, `FR-006`, `NFR-001`, `NFR-002`, `NFR-005`.
* Acceptance: The existing plan's remote-security and deployment tasks are completed with implementation evidence for Bicep, container build, Entra ingress protection, private or protected MCP ingress, health probes, managed identity, and rollback.
* Acceptance: Chat and MCP use packaged synthetic data only; no `.env` file, key, connection string, or credential is present in the image or deployment artifact.
* Verification: Review the existing plan's changes record and deployed resource configuration; run container scan, readiness/liveness probes, authenticated ingress smoke tests, and an MCP call using the selected identity.

Details:
* The current [real-mcp-server plan](../../plans/2026-10-14/real-mcp-server-plan.md) owns baseline ACA, Bicep, remote MCP security, and deployment. Its P03/P04 tasks are unchecked in the available artifact. Complete or explicitly supersede that work before treating ACA as an available platform.
* Read-only ARM inventory found no Azure Container Apps environment or Container App in the selected resource group. It found an existing Application Insights component in `australiaeast`, using Log Analytics ingestion with a linked workspace and 90-day retention. Verify ownership, access, and policy suitability before routing this app's telemetry there.
* The existing APIM service is Developer tier with `virtualNetworkType: None` and currently reports outbound IP `<apim-outbound-ipv4>`. The approved MVP template restricts external MCP ACA ingress to that `/32` and also requires Entra authentication; this is not private networking and the allowlist must be revalidated at deployment.
* Local security verification: `tests/test_mcp_http.py` and `tests/test_mcp_config.py` passed 21 tests; `tests/test_telemetry.py` and `tests/test_governance.py` passed 43 tests, for 64 focused tests total. These prove application middleware/configuration and telemetry behavior only, not Azure Container Apps built-in Entra authentication or deployed network isolation.
* Bicep CLI `0.48.1` is installed. Existing [infra/main.bicep](../../../infra/main.bicep) compiles after AVM modules are restored. The earlier role-disabled full-template `what-if` reported 9 creates and 19 ignores. After the Owner role was added, a refreshed `what-if` with role assignments enabled and the published image tag reported 11 creates and 19 ignores, including both Bicep role assignments; the bootstrapped ACR was ignored with no modify/delete changes. This remains preview-only because the chat secret was a placeholder; no deployment was applied.
* Built and pushed `<registry-name>.azurecr.io/<image-repository>:<image-tag>` with digest `sha256:<image-digest>`. Both image entrypoints became ready in local containers; the hosted-config MCP image rejected an unauthenticated POST with HTTP 401. The chat image readiness passed, but no agent invocation was attempted because APIM is not deployed.
* Added [infra/bootstrap-acr.bicep](../../../infra/bootstrap-acr.bicep) with the same deterministic registry name, Basic SKU, and disabled admin account as the full template. Bootstrap `what-if` predicted one ACR create and 18 ignored resources; deployment `<acr-bootstrap-deployment-name>` then succeeded. The full template now references that registry as existing, preserving its policy-managed tags and properties.
* The user authorized and applied infrastructure bootstrap deployment `<acr-bootstrap-deployment-name>`. The registry reports `Succeeded`, Basic SKU, and disabled admin user. The Foundry project connection, Prompt Agent version 2, and `Mcp.Tools.Invoke` app-role assignment were configured separately; no Container Apps/APIM infrastructure or Bicep Azure RBAC assignments were deployed.
* An earlier `what-if` including role assignments was rejected because the current principal lacked `Microsoft.Authorization/roleAssignments/write`. The new Owner assignment resolves that preview blocker; the role-enabled preview succeeded, but deployment still requires separate apply approval.
* The local `.env` `AZURE_CLIENT_ID` remains the `<local-workload-service-principal-name>` service principal; local startup explicitly uses `AzureCliCredential`, while ACA uses the workload managed identity.
* The chat and MCP API registrations, client IDs, API audience, `Mcp.Tools.Invoke` app-role definition and Foundry Agent Identity assignment, agentic-identity connection, and Prompt Agent version 2 are configured. The chat client secret and web redirect remain pending. The application image is published, but APIM/ACA are not deployed, so end-to-end validation remains outstanding.
* The existing [infra/main.bicep](../../../infra/main.bicep) is staged in the worktree. Preserve its ownership/state; only update it as needed with review. Do not duplicate the existing plan's infrastructure tasks here.

References:
* [.copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md](../../plans/2026-10-14/real-mcp-server-plan.md): Baseline security and ACA deployment task ownership.
* [Dockerfile](../../../Dockerfile): Current image starts the development supervisor and is not yet a hosted startup contract.
* [README.md](../../../README.md): Current local services and Azure hosting status.

Dependencies:
* None; must complete before `P02-T01` deployment.

<!-- rpi:task id=P01-T03 -->
#### [ ] P01-T03: Approve audit and retention requirements

Goals:
* Distinguish operational telemetry from durable business audit evidence before enabling retention or exporting sensitive events.

Requirements:
* `FR-005`, `FR-006`, `NFR-003`, `NFR-004`, `NFR-006`; product `NFR-007`.
* Acceptance: Use the user-approved existing Application Insights resource only for privacy-filtered operational telemetry; document table-specific retention and confirm workspace access/privacy policy before the workload emits data.
* Acceptance: Durable business-audit storage remains deferred until owners define event categories, retention, access, deletion, incident retrieval, and immutability needs; operational diagnostics are not presented as compliance audit evidence.
* Verification: Query the configured resource and workspace retention before enabling export; test representative serialized events against the prohibited-field denylist; after ACA identity exists, verify its least-privilege write access without exposing credentials.

Details:
* Product `NFR-007` says audit events, retention periods, and record access remain to be specified. Do not take retention durations from an earlier plan as approved policy.
* Confirmed user direction: reuse the existing Australia East Application Insights component and its linked Log Analytics workspace for privacy-filtered operational telemetry. The component reports 90 days, the workspace default is 30 days, and core Application Insights tables such as requests, dependencies, events, exceptions, metrics, and traces report 90 days. Do not generalize 90 days to every workspace table.
* App Insights/Log Analytics identity and privacy access settings still require review; there is no ACA app identity in the selected resource group to validate as the telemetry writer. Keep business-audit requirements separate and do not add immutable Storage until owners approve them.
* Use Application Insights and Log Analytics for operational traces, metrics, and logs. Add Azure Storage with immutability only if owners require tamper-resistant audit retention and approve its access, deletion, and residency model.

References:
* [docs/project-planning/member-wealth-insights-agent.md](../../../docs/project-planning/member-wealth-insights-agent.md): `NFR-007` and its open audit requirements.
* [docs/planning/adrs/0003-minimize-identity-and-governance-telemetry.md](../../../docs/planning/adrs/0003-minimize-identity-and-governance-telemetry.md): Existing in-memory, privacy-safe telemetry boundary.
* [src/ai_governance_harness/mcp_server/telemetry.py](../../../src/ai_governance_harness/mcp_server/telemetry.py): Current allowlisted log attributes and optional Azure Monitor export.

Dependencies:
* None.

<!-- rpi:phase id=P02 -->
### [ ] P02: Foundry agent and identity pilot release

Goals:
* Move model orchestration behind the selected Foundry Prompt Agent while preserving user-visible behavior, the exact MCP tool allowlist, and default-deny governance.

Dependencies:
* `P01-T01` confirms feature compatibility.
* `P01-T02` confirms the hosted application baseline.

```mermaid
%%{init: {"themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "16px"}}}%%
flowchart LR
	USER["Workshop user"] --> UI["Added: Chat UI and API on ACA"]
	UI --> AGENT["Added: Foundry Prompt Agent"]
	ID["Added: Entra Agent ID"] -. assigned identity .-> AGENT
	ID -. scoped token .-> GATE["Added: APIM MCP gateway"]
	AGENT --> GATE
	GUARD["Added: Foundry guardrails"] --> AGENT
	GATE --> MCP["Added: Private MCP service on ACA"]
	GOV["Existing: AGT default-deny runtime"] --> UI
	GOV --> MCP
	MCP --> TOOLS["Typed tools"]
	TOOLS --> DATA["Synthetic JSON for pilot"]
	MCP <--> HUMAN["Added: selected human approval"]
	AGENT --> USER
	UI -. W3C trace context .-> MON["Added: Azure Monitor evidence"]
	AGENT -. traces and outcomes .-> MON
	GATE -. diagnostics .-> MON
	MCP -. sanitized events .-> MON
	PIPE["Added: Bicep and CI baseline"] --> UI
	PIPE --> MCP
	A2["Added after core gates: second agent"] --> GATE
	classDef new stroke-dasharray: 5 5
	class UI,MCP,PIPE,AGENT,ID,GATE,GUARD,HUMAN,MON,A2 new
	classDef phase fill:#fff3bf,color:#1f2328,stroke:#9a6700,stroke-width:2px
	class AGENT,ID,GUARD phase
```

Highlighted work: `AGENT`, `ID`, and `GUARD` establish the hosted model and identity control plane.

<!-- rpi:task id=P02-T01 -->
#### [ ] P02-T01: Configure the Foundry Prompt Agent

Goals:
* Make a versioned Foundry Prompt Agent the model-facing component for the existing chat workflow.

Requirements:
* `FR-001`, `FR-004`, `NFR-001`, `NFR-003`, `NFR-005`.
* Acceptance: The agent has bounded instructions and only the approved MCP tool definitions; unknown or unregistered tools cannot execute.
* Acceptance: Foundry-native guardrails are configured at supported agent/model intervention points, with the existing advice, scope, disclosure, and AGT checks retained as complementary controls.
* Acceptance: The previous direct Chat Completions path remains available for rollback until the hosted-agent vertical slice meets parity checks.
* Verification: Run synthetic conversation evaluations for each tool, unknown-tool denial, advice-boundary cases, unsupported whole-of-wealth claims, refusal/content-filter cases, and empty or malformed model output; compare expected outcomes to the direct-call baseline.

Details:
* This task changes the current orchestration boundary, not the synthetic MCP data contract. Keep the MCP tool schema and policy action names stable unless a separately reviewed contract change is required.
* Bicep does not declare the Foundry agent version or its MCP tool list. Use the Foundry data-plane SDK or REST API after infrastructure deployment. Select a supported `azure-ai-projects` version with MCP tool types, or implement the documented REST calls behind the Foundry client boundary if the selected SDK release lacks them.
* Version 1 remains unchanged. Version 2 is active with the same configured model and instruction text plus one MCP server restricted to `get_member_profile`, `get_member_disengagement_signals`, `get_cohort_churn_analytics`, and `get_fum_outflow_summary`. Approval is disabled only for these read-only tools. The agent app-role grant is complete; version 2 has not been invoked because the APIM route is not deployed.
* Do not represent Foundry guardrails as replacing the repository's runtime governance policy. Record model, agent version, evaluation set, and guardrail configuration in deployment evidence.

References:
* [src/ai_governance_harness/chat/service.py](../../../src/ai_governance_harness/chat/service.py): Existing Chat Completions tool loop and output sanitization.
* [src/ai_governance_harness/governance/policies/default.yaml](../../../src/ai_governance_harness/governance/policies/default.yaml): Exact default-deny action policy.
* [src/ai_governance_harness/guardrails/advice_filter.py](../../../src/ai_governance_harness/guardrails/advice_filter.py): Existing deterministic advice and scope guardrails.
* [Foundry MCP tool support](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/model-context-protocol): Data-plane creation of MCP-enabled prompt-agent versions and approval behavior.

Dependencies:
* `P01-T01`
* `P01-T02`

<!-- rpi:task id=P02-T02 -->
#### [ ] P02-T02: Bind the agent to Entra Agent ID

Goals:
* Give each deployed agent a distinct authenticated identity that can be authorized downstream without exposing raw identity claims to telemetry.

Requirements:
* `FR-003`, `FR-005`, `NFR-001`, `NFR-002`, `NFR-003`.
* Acceptance: Agent identity, token issuer, tenant, audience, required app role or scope, token lifetime, and authorized tool/resource mapping are documented and enforced; an unrecognized identity or token fails closed.
* Acceptance: The workload's Foundry permissions use managed identity or the supported agent identity mechanism with least privilege; secrets are not stored in application settings when identity-based access is available.
* Verification: Exercise valid, missing, expired, wrong-tenant, wrong-audience, missing-role, and revoked-authorization cases in an integration environment; verify logs contain only approved authentication outcomes or opaque identifiers.

Details:
* `DefaultAzureCredential` currently authenticates the application to Foundry; it is not itself an Entra Agent ID. Do not infer per-agent identity from the app's managed identity.
* The existing Foundry agent has an `AgentIdentity` object with client and principal identifiers. Verify that this is the approved Entra Agent ID for the target workload and that APIM/MCP validates the intended audience and permissions. Do not print or log the identifier values.
* Created project connection `<mcp-project-connection-name>` through the supported project connection ARM API with `AgenticIdentityToken`, the APIM MCP target, and the MCP API audience. The `Mcp.Tools.Invoke` app-role assignment is complete; deployed token validation remains outstanding. No secret is stored. Do not place client secrets or Graph tokens in Bicep parameters.
* Confirm how the hosted agent obtains and presents a token to the chosen MCP gateway. If the product supplies an identity bridge, validate its trust and claim contract; never authorize from arbitrary caller-supplied headers.

References:
* [src/ai_governance_harness/foundry_client.py](../../../src/ai_governance_harness/foundry_client.py): Current application credential path.
* [src/ai_governance_harness/governance/context.py](../../../src/ai_governance_harness/governance/context.py): Existing bounded workload and identity context.
* [src/ai_governance_harness/governance/agt-runtime-evidence.yaml](../../../src/ai_governance_harness/governance/agt-runtime-evidence.yaml): Current hosted principal propagation limitation.
* [Entra Agent ID creation](https://learn.microsoft.com/en-us/entra/agent-id/create-delete-agent-identities): Microsoft Graph identity lifecycle and permissions.
* [Foundry MCP tool support](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/model-context-protocol): Agentic identity authentication for MCP connections.

Dependencies:
* `P01-T01`
* `P02-T01`

<!-- rpi:task id=P02-T03 -->
#### [ ] P02-T03: Adapt chat to invoke the hosted agent

Goals:
* Keep the current browser experience while switching its backend from direct model/tool orchestration to a versioned Foundry agent invocation.

Requirements:
* `FR-001`, `FR-005`, `NFR-001`, `NFR-005`.
* Acceptance: The chat API preserves request bounds, safe error responses, output guardrails, readiness reporting, and the current synthetic-data user journey.
* Acceptance: Hosted startup is non-interactive, binds only required interfaces, does not open a browser, and reports readiness only when required configuration and dependencies are valid.
* Verification: Run existing chat and governance tests plus hosted-agent contract tests; start the container without `.env`, verify `/health/live` and `/health/ready`, and complete profile, cohort/FUM, refusal, and policy-denial smoke scenarios. These hosted checks remain outstanding.

Details:
* The [infra/main.bicep](../../../infra/main.bicep) Container Apps modules override the Dockerfile's local `ai-governance-dev` command with separate `ai-governance-chat` and `ai-governance-mcp` entry points.
* `ChatSettings` enables the Prompt Agent route only when `CHAT_USE_PROMPT_AGENT=true` and `FOUNDRY_AGENT_NAME` is set. The local launcher forces the flag to `false`; the direct Chat Completions/MCP route remains the local default and rollback path.
* Local development defaults to `AzureCliCredential` so `.env` service-principal credentials cannot silently override the signed-in demo identity. ACA explicitly selects `DefaultAzureCredential` to resolve the workload managed identity.
* ACA sets `CHAT_USE_PROMPT_AGENT=true` and the existing agent name. Prompt Agent version 2 and its agentic-identity project connection are configured, but the identity role grant, deployed APIM route, and end-to-end invocation are outstanding.
* Keep the browser-facing same-origin API. The browser must not call Foundry, APIM, or MCP directly.

References:
* [Dockerfile](../../../Dockerfile): Current local supervisor entrypoint.
* [src/ai_governance_harness/chat/__main__.py](../../../src/ai_governance_harness/chat/__main__.py): Current Uvicorn startup contract.
* [src/ai_governance_harness/chat/app.py](../../../src/ai_governance_harness/chat/app.py): Current browser API and health routes.

Dependencies:
* `P01-T02`
* `P02-T01`
* `P02-T02`

<!-- rpi:phase id=P03 -->
### [ ] P03: Gateway-integrated core release

Goals:
* Give the Foundry agent one authenticated, policy-controlled MCP entry point and prevent bypass of the gateway to the business service.

Dependencies:
* `P01-T01` confirms gateway/protocol support.
* `P01-T02` confirms private backend deployment.
* `P02-T01` and `P02-T02` establish the agent and its identity.

```mermaid
%%{init: {"themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "16px"}}}%%
flowchart LR
	USER["Workshop user"] --> UI["Added: Chat UI and API on ACA"]
	UI --> AGENT["Added: Foundry Prompt Agent"]
	ID["Added: Entra Agent ID"] -. assigned identity .-> AGENT
	ID -. scoped token .-> GATE["Added: APIM MCP gateway"]
	AGENT --> GATE
	GUARD["Added: Foundry guardrails"] --> AGENT
	GATE --> MCP["Added: Private MCP service on ACA"]
	GOV["Existing: AGT default-deny runtime"] --> UI
	GOV --> MCP
	MCP --> TOOLS["Typed tools"]
	TOOLS --> DATA["Synthetic JSON for pilot"]
	MCP <--> HUMAN["Added: selected human approval"]
	AGENT --> USER
	UI -. W3C trace context .-> MON["Added: Azure Monitor evidence"]
	AGENT -. traces and outcomes .-> MON
	GATE -. diagnostics .-> MON
	MCP -. sanitized events .-> MON
	PIPE["Added: Bicep and CI baseline"] --> UI
	PIPE --> MCP
	A2["Added after core gates: second agent"] --> GATE
	classDef new stroke-dasharray: 5 5
	class UI,MCP,PIPE,AGENT,ID,GATE,GUARD,HUMAN,MON,A2 new
	classDef phase fill:#fff3bf,color:#1f2328,stroke:#9a6700,stroke-width:2px
	class ID,GATE,MCP phase
```

Highlighted work: `ID`, `GATE`, and `MCP` enforce the authenticated, non-bypassable tool route.

<!-- rpi:task id=P03-T01 -->
#### [ ] P03-T01: Publish the MCP API through APIM

Goals:
* Route agent MCP discovery and calls through one gateway while keeping the business service private.

Requirements:
* `FR-002`, `FR-005`, `FR-006`, `NFR-001`, `NFR-002`, `NFR-005`.
* Acceptance: Foundry agent configuration points to the APIM MCP endpoint; no public direct route to the backend is available, and APIM applies the approved authentication, rate, network, and diagnostic policies.
* Acceptance: The gateway preserves the required MCP protocol version, session behavior, streaming, and approval channel; no policy rewrite changes tool names, schemas, or error semantics.
* Verification: Through the gateway, test tool listing and invocation, valid and invalid tokens, rate limit, backend outage, connection reset, protected-resource discovery, and approval elicitation. Repeat the direct-backend test from an untrusted network and confirm it is unreachable.

Details:
* Prefer APIM as the stable API boundary. Enable a Foundry AI Gateway MCP integration only when `P01-T01` proves its support and operations contract for this tenant and region.
* The APIM API ARM schema supports `apiType: 'mcp'` and streamable transport through a preview API version. Use Bicep for that APIM API and policies only after target subscription validation; keep agent creation/tool binding in the Foundry data plane.
* If APIM cannot proxy the necessary MCP protocol behavior, stop this release for architecture review. A temporary direct route may be used only in a non-production private spike and must not be described as satisfying the target gateway control.

References:
* [src/ai_governance_harness/chat/service.py](../../../src/ai_governance_harness/chat/service.py): Current direct MCP URL and client behavior.
* [src/ai_governance_harness/mcp_server/http_app.py](../../../src/ai_governance_harness/mcp_server/http_app.py): Current Streamable HTTP endpoint and discovery routes.
* [docs/planning/adrs/0005-present-governance-through-a-same-origin-observability-panel.md](../../../docs/planning/adrs/0005-present-governance-through-a-same-origin-observability-panel.md): Current same-origin browser-to-chat boundary.
* [APIM API Bicep resource](https://learn.microsoft.com/en-us/azure/templates/microsoft.apimanagement/service/apis): `mcp` API type and streamable transport properties.

Dependencies:
* `P01-T01`
* `P01-T02`
* `P02-T01`
* `P02-T02`

<!-- rpi:task id=P03-T02 -->
#### [ ] P03-T02: Authorize agent identity at MCP

Goals:
* Ensure the MCP business service authorizes the verified agent identity and requested tool rather than trusting network location alone.

Requirements:
* `FR-003`, `NFR-001`, `NFR-002`, `NFR-003`.
* Acceptance: The backend validates a cryptographically authenticated identity or a documented trusted gateway token contract, validates issuer/tenant/audience and the required delegated scope or application role, and maps identity to an explicit tool permission set.
* Acceptance: Missing, invalid, replayed, or over-privileged identity requests fail before tool execution; bypass attempts cannot call the backend directly.
* Verification: Integration tests cover each invalid token/claim case and each tool permission; deployed tests prove the gateway forwards only the validated identity contract and that MCP rejects spoofed headers.

Details:
* The current `MCP_HOSTED` validation trusts platform identity headers in its intended platform boundary. Reassess that trust when APIM becomes the front door; do not retain a header contract whose issuer is no longer the trusted authenticator.
* Hosted MCP configuration now requires exactly one of a delegated scope or application role. The deployment selects `Mcp.Tools.Invoke`, and middleware validates that role from the platform principal claims. APIM validates the token audience; the Foundry Agent role assignment and deployed identity test remain incomplete.
* Preserve the default-deny policy in [default.yaml](../../../src/ai_governance_harness/governance/policies/default.yaml). Keep identity attributes bounded and avoid adding raw claims, member IDs, or tokens to governance events.

References:
* [src/ai_governance_harness/mcp_server/security.py](../../../src/ai_governance_harness/mcp_server/security.py): Current hosted principal validation.
* [src/ai_governance_harness/mcp_server/config.py](../../../src/ai_governance_harness/mcp_server/config.py): Current audience, tenant, scope, and resource configuration.
* [src/ai_governance_harness/governance/policies/default.yaml](../../../src/ai_governance_harness/governance/policies/default.yaml): Exact action allowlist and default deny.

Dependencies:
* `P02-T02`
* `P03-T01`

<!-- rpi:phase id=P04 -->
### [ ] P04: Core controls and promotion gate

Goals:
* Demonstrate guardrails, selected human approval, privacy-safe distributed evidence, and operational recovery across the complete Azure request path.

Dependencies:
* `P02` and `P03` are complete.
* `P01-T03` audit/retention decisions are approved.

```mermaid
%%{init: {"themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "16px"}}}%%
flowchart LR
	USER["Workshop user"] --> UI["Added: Chat UI and API on ACA"]
	UI --> AGENT["Added: Foundry Prompt Agent"]
	ID["Added: Entra Agent ID"] -. assigned identity .-> AGENT
	ID -. scoped token .-> GATE["Added: APIM MCP gateway"]
	AGENT --> GATE
	GUARD["Added: Foundry guardrails"] --> AGENT
	GATE --> MCP["Added: Private MCP service on ACA"]
	GOV["Existing: AGT default-deny runtime"] --> UI
	GOV --> MCP
	MCP --> TOOLS["Typed tools"]
	TOOLS --> DATA["Synthetic JSON for pilot"]
	MCP <--> HUMAN["Added: selected human approval"]
	AGENT --> USER
	UI -. W3C trace context .-> MON["Added: Azure Monitor evidence"]
	AGENT -. traces and outcomes .-> MON
	GATE -. diagnostics .-> MON
	MCP -. sanitized events .-> MON
	PIPE["Added: Bicep and CI baseline"] --> UI
	PIPE --> MCP
	A2["Added after core gates: second agent"] --> GATE
	classDef new stroke-dasharray: 5 5
	class UI,MCP,PIPE,AGENT,ID,GATE,GUARD,HUMAN,MON,A2 new
	classDef phase fill:#fff3bf,color:#1f2328,stroke:#9a6700,stroke-width:2px
	class HUMAN,MON phase
```

Highlighted work: `HUMAN` and `MON` make approval outcomes and service evidence visible.

<!-- rpi:task id=P04-T01 -->
#### [ ] P04-T01: Gate selected high-risk tools with approval

Goals:
* Require an explicit, attributable human decision before configured high-risk tool actions proceed.

Requirements:
* `FR-004`, `FR-005`, `NFR-001`, `NFR-003`.
* Acceptance: Product/security owners name the protected actions and approver roles; no blanket approval is inferred from chat access or agent identity.
* Acceptance: Decline, cancellation, timeout, invalid response, unsupported elicitation client, and missing approval all prevent execution and return a clear sanitized outcome.
* Verification: Run end-to-end approval accept/decline/cancel/timeout/unsupported-client scenarios through the selected Foundry/APIM/MCP path; assert the protected operation executes only after approved authorization and is recorded without approval form contents.

Details:
* The current `prepare_member_outreach_case` flow is an elicitation example for a synthetic read-only preparation action; it performs no member contact. Keep that property unless a separately approved business capability and threat model authorize a side effect.
* If Foundry Agent Service cannot complete MCP elicitation, define an explicit approval API/UI at the chat boundary. Never silently retry without approval or treat tool annotations as enforcement.

References:
* [src/ai_governance_harness/mcp_server/server.py](../../../src/ai_governance_harness/mcp_server/server.py): Existing approval annotations and elicitation flow.
* [src/ai_governance_harness/chat/static/index.html](../../../src/ai_governance_harness/chat/static/index.html): Current browser UI has no general approval workflow.
* Workshop architecture supplied in the conversation: human approval cross-cutting control.

Dependencies:
* `P02-T01`
* `P03-T01`
* `P03-T02`

<!-- rpi:task id=P04-T02 -->
#### [ ] P04-T02: Correlate Azure-native operational evidence

Goals:
* Let operators follow one request across chat, Foundry, APIM, and MCP while keeping telemetry privacy-safe and separating diagnostics from regulated audit records.

Requirements:
* `FR-005`, `FR-006`, `NFR-003`, `NFR-004`, `NFR-006`; product `NFR-007`.
* Acceptance: W3C trace context is propagated across every network boundary; the user-safe response exposes a trace reference, and logs join to the trace without using raw prompts, member identifiers, tool arguments/results, tokens, or raw claims.
* Acceptance: Azure Monitor/Application Insights receives service traces, metrics, and logs for the chat, Foundry agent, APIM, and MCP components with `service.name`, `service.version`, `deployment.environment`, `telemetry.sdk.name`, `telemetry.sdk.language`, and `telemetry.sdk.version`; metric attributes remain bounded and durations use seconds.
* Acceptance: Operational retention, audit retention, access roles, deletion, and optional immutable storage match the owner-approved `P01-T03` decision.
* Verification: Execute one synthetic request and retrieve one end-to-end trace with Foundry, APIM, and MCP spans plus the approved tool outcome; inject unique synthetic PII markers and prove they are absent from logs, spans, metric dimensions, and audit records.

Details:
* Current MCP telemetry optionally configures Azure Monitor, while chat and MCP correlation IDs are generated independently and governance history is process-local. Add context propagation and configure export for each service rather than assuming the existing event panel is durable evidence.
* Follow OpenTelemetry semantic conventions where available, W3C Trace Context for propagation, and the repository telemetry vocabulary. Use low-cardinality metrics; place per-request correlation only in traces/logs, not metric labels.
* Use Azure Monitor/Application Insights and Log Analytics for operations. Use immutable Azure Storage only if the approved audit requirements require it; do not treat ordinary diagnostic logs as tamper-proof audit records.

References:
* [src/ai_governance_harness/mcp_server/telemetry.py](../../../src/ai_governance_harness/mcp_server/telemetry.py): Current MCP-only Azure Monitor setup and allowlist.
* [src/ai_governance_harness/governance/events.py](../../../src/ai_governance_harness/governance/events.py): Bounded process-local governance events.
* [docs/planning/adrs/0003-minimize-identity-and-governance-telemetry.md](../../../docs/planning/adrs/0003-minimize-identity-and-governance-telemetry.md): Privacy and non-persistence constraints.
* [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/): Standard instrumentation vocabulary.
* [W3C Trace Context](https://www.w3.org/TR/trace-context/): Cross-service trace propagation contract.

Dependencies:
* `P01-T03`
* `P02-T03`
* `P03-T01`
* `P03-T02`

<!-- rpi:task id=P04-T03 -->
#### [ ] P04-T03: Pass core release security and operations gates

Goals:
* Promote only a tested synthetic-data release with known access, failure, latency, scaling, and rollback behavior.

Requirements:
* `FR-001` through `FR-006`; `NFR-001` through `NFR-006`; product `NFR-001`, `NFR-002`, `NFR-003`, `NFR-004`, and `NFR-007` where their measurement conditions are approved.
* Acceptance: CI passes unit, contract, policy, security, container, and integration suites; a deployed smoke suite proves the complete identity-to-agent-to-gateway-to-MCP path and denies unknown tools and invalid identities.
* Acceptance: Readiness/liveness, APIM/backend outage, Foundry timeout, gateway throttling, replica restart, deployment rollback, and alert routing behave as documented; no release uses real member data.
* Acceptance: Product latency and availability targets are measured against an approved workload and observation window; do not claim NFR conformance while BRD measurement conditions remain open.
* Verification: Record test results, image digest/SBOM, deployment revision, configuration references without secrets, sample trace IDs, alert test result, and rollback evidence in the changes record; obtain engineering, security, and business-owner approval before pilot promotion.

Details:
* The BRD gives initial latency and availability targets but leaves measurement boundaries and load profile open. Resolve those before using them as release gates.
* Keep rollout staged by environment and revision. Maintain a tested rollback to the prior direct-chat pilot until the new Foundry agent and gateway path has passed the same synthetic scenario suite.

References:
* [docs/project-planning/member-wealth-insights-agent.md](../../../docs/project-planning/member-wealth-insights-agent.md): Product latency, availability, privacy, and audit requirements.
* [tests/](../../../tests/): Existing automated verification suite.
* [security/vex/README.md](../../../security/vex/README.md): Existing dependency and exception-management posture.

Dependencies:
* `P02-T01`
* `P02-T02`
* `P02-T03`
* `P03-T01`
* `P03-T02`
* `P04-T01`
* `P04-T02`

<!-- rpi:phase id=P05 -->
### [ ] P05: Add multi-agent orchestration as a stretch release

Goals:
* Add a second bounded business agent only after the single-agent architecture has passed all core release gates, reusing the same identity, APIM, MCP, approval, and evidence contracts.

Dependencies:
* `P04-T03` is complete and core release gates are green.

```mermaid
%%{init: {"themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "16px"}}}%%
flowchart LR
	USER["Workshop user"] --> UI["Added: Chat UI and API on ACA"]
	UI --> AGENT["Added: Foundry Prompt Agent"]
	ID["Added: Entra Agent ID"] -. assigned identity .-> AGENT
	ID -. scoped token .-> GATE["Added: APIM MCP gateway"]
	AGENT --> GATE
	GUARD["Added: Foundry guardrails"] --> AGENT
	GATE --> MCP["Added: Private MCP service on ACA"]
	GOV["Existing: AGT default-deny runtime"] --> UI
	GOV --> MCP
	MCP --> TOOLS["Typed tools"]
	TOOLS --> DATA["Synthetic JSON for pilot"]
	MCP <--> HUMAN["Added: selected human approval"]
	AGENT --> USER
	UI -. W3C trace context .-> MON["Added: Azure Monitor evidence"]
	AGENT -. traces and outcomes .-> MON
	GATE -. diagnostics .-> MON
	MCP -. sanitized events .-> MON
	PIPE["Added: Bicep and CI baseline"] --> UI
	PIPE --> MCP
	A2["Added after core gates: second agent"] --> GATE
	classDef new stroke-dasharray: 5 5
	class UI,MCP,PIPE,AGENT,ID,GATE,GUARD,HUMAN,MON,A2 new
	classDef phase fill:#fff3bf,color:#1f2328,stroke:#9a6700,stroke-width:2px
	class A2,GATE phase
```

Highlighted work: `A2` adds an agent; `GATE` remains the common approved tool path.

<!-- rpi:task id=P05-T01 -->
#### [ ] P05-T01: Add the second business agent

Goals:
* Support a second narrowly scoped agent without introducing a new data-access or governance bypass.

Requirements:
* `FR-001`, `FR-002`, `FR-003`, `FR-006`, `NFR-001`, `NFR-003`, `NFR-004`.
* Acceptance: Each agent has its own registered identity, policy scope, instructions, evaluation suite, and explicitly allowed tools; both route through the same APIM MCP gateway and backend authorization contract.
* Acceptance: Sequential or handoff orchestration cannot elevate privileges, transfer unapproved data, bypass human approval, or lose the end-to-end trace reference.
* Verification: Run cross-agent authorization tests, wrong-agent/wrong-tool denials, synthetic data separation checks, handoff failure tests, and trace queries for each orchestration pattern; compare latency and error rates to the approved single-agent baseline.

Details:
* Candidate agents are Member Insights and FUM Insights from the workshop architecture. Keep multi-agent orchestration out of core scope until `P04-T03` is green.
* Prefer the Microsoft Agent Framework only after validating its hosting, identity, and tracing compatibility with the selected Foundry/APIM path.

References:
* Workshop architecture supplied in the conversation: sequential or handoff multi-agent stretch goal.
* [src/ai_governance_harness/mcp_server/server.py](../../../src/ai_governance_harness/mcp_server/server.py): Shared current MCP tool catalog.
* [src/ai_governance_harness/governance/policies/default.yaml](../../../src/ai_governance_harness/governance/policies/default.yaml): Current workload-bound default-deny policy.

Dependencies:
* `P04-T03`

## User Decisions and Requirements

### Confirmed User Direction

* Create a new implementation plan from the prior repository findings and supplied workshop architecture.
* Prefer native Azure services where practical and deliver the work through incremental releases.
* Give implementation tasks checkable acceptance conditions and verification methods.
* Keep the existing chat UI in front of a backend Foundry Prompt Agent; retain `ChatService` as the UI/API façade.
* Use the Azure target configured in `.env` for preflight; do not apply Azure infrastructure without separate approval.
* Scope the MVP to a three-day hackathon and target a demo by end of day on 2026-10-14; reuse existing Azure resources where practical and defer production-grade networking/audit hardening.
* Create separate single-tenant Entra app registrations for chat EasyAuth and the MCP API; keep the existing `AZURE_CLIENT_ID` workload service principal distinct.
* Do not change application source or deploy Azure resources as part of this planning task.

### Planning Decisions and Feedback

| Group | Decision or feedback item | Status | Owner | Rationale or input needed | Evidence | Planning impact |
|---|---|---|---|---|---|---|
| D1 | Use ACA as the workload host and Foundry AI Gateway backed by APIM for eligible MCP tools; fall back to direct APIM only if the integrated gateway is unavailable or fails protocol checks. | Confirmed direction | User/platform owner | User approved the conditional route. Tenant availability, region, MCP protocol, and preview support remain verification gates, not provisioning approval. | User approval, workshop architecture, existing MCP deployment plan, and read-only APIM inventory | Gates `P01-T01`, `P01-T02`, `P03-T01`, and `P03-T02`; no public direct-to-MCP route. |
| D2 | Keep the current chat UI/API façade in front of a Foundry Prompt Agent with a distinct Entra Agent ID; retain direct Chat Completions only as rollback until the authenticated route passes. | Confirmed direction | User/platform owner | User clarified that the chat UI is in front of the Prompt Agent. A separate workload managed identity serves application-to-Foundry access where supported; tenant protocol and identity support remain verification gates. | User confirmation, workshop architecture, current Foundry client and chat service | Gates `P01-T01`, `P02-T01`, and `P02-T02`; no cutover before an authenticated synthetic vertical slice passes. |
| D3 | Reuse the existing Australia East Application Insights/Log Analytics workspace for operational telemetry with table-specific retention; keep durable business-audit policy separate. | Confirmed direction | User/platform owner; business data owner and security/compliance owner for audit policy | The user approved operational reuse. The component reports 90 days; workspace default is 30 days; core Application Insights tables report 90 days. Workload access/privacy configuration remains to be reviewed. Product NFR `NFR-007` leaves durable business-audit requirements unspecified. | User approval and read-only Application Insights, workspace, and table-retention queries; product requirements and telemetry ADR | Gates `P01-T03` and `P04-T02`; operational telemetry is not durable compliance audit evidence. |
| D4 | Select the Azure subscription, Foundry project, and region for read-only feature and deployment-baseline verification. | Resolved | User/platform owner | The user pointed to `.env` as the target configuration. Its tenant/subscription matched the Azure CLI context and identified the Foundry project, resource group, and `australiaeast` region. | `.env` target plus read-only Azure Resource Manager and deployment-list queries | Environment selection is complete; P01-T01 Foundry Agent/Gateway feature support and P01-T02 hosted baseline remain unverified or absent. |
| D5 | For the hackathon MVP, reuse the existing APIM and use Entra-protected external ACA ingress restricted to the APIM outbound IP; defer VNet/private networking. | Confirmed direction | User/platform owner | User approved the MVP topology. The template applies an APIM `/32` ingress allowlist plus Entra token validation; validate the IP remains current at deployment. Use synthetic data and don't claim private networking. | User approval, read-only APIM egress query, and Bicep preview | Permits the MVP topology; no Azure apply without separate authorization. |
| D6 | Require Azure-hosted Foundry Prompt Agent/APIM/ACA architecture for today's demo rather than substitute the local harness. | Confirmed direction | User/platform owner | User explicitly chose the Azure-hosted architecture. Current local health is useful only as fallback; do not present it as the target architecture. | User confirmation and end-of-day hackathon scope | Keeps hosted agent, APIM MCP route, ACA, and actual smoke test as demo gates; surface schedule risk honestly. |
| D7 | Create separate single-tenant app registrations for the chat web client and MCP API. | Resolved | User/platform owner | Created `<chat-app-registration-name>` (`<chat-client-id>`) and `<mcp-api-registration-name>` (`<mcp-api-client-id>`). The MCP API registration has identifier URI `api://<mcp-api-client-id>`, application role `Mcp.Tools.Invoke`, and delegated scope `Mcp.Tools.Read`; the role is assigned to the Foundry Agent Identity. | User request and Entra verification | Use the app IDs as Bicep inputs. Chat redirect and client secret remain pending. |

### Planning Participation

* Decision participation: User-owned, standalone planning default. Material Azure feature and retention decisions remain explicit gates rather than assumed approvals.
* Planning delegation: Adaptive, default provenance. The phases are sequential and share one architecture boundary, so the primary planner authors them together without delegation.

## Planning Readiness and Next Step

| Field | Record |
|---|---|
| Planning execution and readiness | Partial; D5-D7 are confirmed. The ACR bootstrap, agentic-identity connection, Prompt Agent version 2, `Mcp.Tools.Invoke` assignment, and versioned image push are complete. Both Bicep templates compile, 176 tests pass, and local/image smoke checks pass. The latest Owner-authorized full-template What-If predicts 11 creates and 19 ignores, including both Bicep role assignments; the ACR is ignored. No Container Apps/APIM infrastructure was applied. |
| Blockers | Configure chat EasyAuth secret/redirect; obtain separate approval for the full Azure apply; deploy APIM/ACA and invoke version 2 through the MCP route. VNet/private networking and durable audit are deferred. |
| Latest critique | Not run. |
| Relevant research | Not activated; supplied architecture, prior planning artifacts, and repository code establish the current design delta. |
| Plan | `.copilot-tracking/plans/2026-10-14/azure-native-services-migration-plan.md` |
| Changes-record role | `.copilot-tracking/changes/2026-10-14/azure-native-services-migration-changes.md` will record implementation evidence if this plan proceeds. |
| Continuation owner | User, standalone planning. |
| Required gates or confirmations | Add the chat redirect URI after ACA FQDN exists; securely supply the chat client secret; obtain separate approval before full Azure apply; complete hosted chat/MCP smoke tests after deployment. |
| Next action | Complete chat EasyAuth secret/redirect setup, then request explicit approval to apply the role-enabled deployment plan. After ACA/APIM are deployed, invoke version 2 and verify all four tools with synthetic data. |

## Goals

* Establish an incremental migration path from direct local-style Foundry calls to the supplied Foundry Prompt Agent and MCP gateway architecture.
* Preserve the typed, default-deny MCP tool boundary and synthetic-data scope while Azure-native identity, gateway, and observability controls are added.
* Make each release independently verifiable and prevent preview-feature assumptions from becoming production dependencies.

## Scope and Non-Goals

### In Scope

* A prerequisite-aware release plan building on the existing ACA/MCP deployment plan.
* Azure Container Apps, Azure AI Foundry, Microsoft Entra Agent ID, Azure API Management, Azure Monitor/Application Insights, and optional Key Vault or immutable Storage where requirements justify them.
* Changes needed to startup, configuration, identity propagation, gateway routing, approval, trace correlation, privacy-safe telemetry, deployment automation, and operational verification.
* Synthetic-data pilot validation before any live member data integration.

### Non-Goals

* Provisioning Azure resources, changing application code, or deploying during planning.
* Connecting production member data, choosing business risk thresholds, or claiming regulatory approval.
* Making multi-agent orchestration part of the core release; it remains a stretch goal.

## Functional Requirements

* FR-001: Route user requests through the selected Foundry Prompt Agent and only its explicitly approved MCP tools.
* FR-002: Route remote MCP traffic through one governed APIM boundary, or a verified Foundry AI Gateway backed by APIM, before the business service.
* FR-003: Authenticate and authorize the agent identity at the gateway and MCP service; do not trust caller-supplied identity headers.
* FR-004: Require explicit human approval for configured high-risk tools and fail closed on decline, cancellation, unsupported client, timeout, or invalid approval.
* FR-005: Return a user-safe result, block reason, or approval outcome with a trace/correlation reference that joins the service flow.
* FR-006: Make approved tool calls, governance decisions, outcomes, and service health observable through Azure-native operational services without collecting raw prompts or member payloads.

## Non-Functional Requirements

* NFR-001: Governance remains default-deny at model, gateway, and tool execution boundaries; missing identity, policy, or dependency readiness blocks protected actions.
* NFR-002: All user-facing ingress uses HTTPS; private MCP connectivity and deployment region meet the approved data-residency boundary.
* NFR-003: Logs, spans, metrics, and audit records exclude raw prompts, tool arguments/results, member identifiers, tokens, and raw identity claims unless an approved redaction contract explicitly permits a field.
* NFR-004: Cross-service traces use W3C trace context and bounded attributes; metrics use low-cardinality dimensions and UCUM units; telemetry resources identify service, version, environment, and SDK.
* NFR-005: Container health probes, scaling, session behavior, dependency timeouts, rollback, and alerting are validated before production promotion.
* NFR-006: Audit retention, access, deletion, and immutability are explicitly approved by data and security owners before durable audit evidence is enabled.

## Risks and Open Questions

| Priority | Type | Risk, question, or planning item | Affected work | Impact | Smallest action or evidence needed | Owner |
|---|---|---|---|---|---|---|
| High | Open question | Can active Prompt Agent version 2 invoke the APIM MCP endpoint using the configured agentic-identity connection and `Mcp.Tools.Invoke` role? | `P02-T01`, `P02-T02`, `P03-T02` | The MCP tool, connection, and app-role assignment are configured, but the APIM API is not deployed, so no authenticated tool call has run. | Deploy the APIM MCP route and execute one synthetic call for each allowlisted tool; verify authentication and default-deny behavior. | Platform owner |
| High | Open question | Does the target APIM service support the documented preview MCP API schema and preserve streaming, sessions, protected-resource discovery, and elicitation? | `P01-T01`, `P03-T01` | APIM MCP API is declarative in the preview ARM schema, but a schema-supported deployment does not prove protocol behavior or tenant availability. | Validate the API version in Bicep/what-if and run MCP conformance tests through the gateway. | Platform owner |
| High | Open question | Which network topology should protect ACA MCP ingress without disrupting the existing APIM `<existing-apim-api-name>`? | `P01-T02`, `P03-T01` | APIM has no VNet and no discovered stable egress IP; target plan language calls for private or protected ingress. | Choose dedicated APIM/VNet, approve in-place APIM VNet integration, or explicitly approve protected external ACA ingress. | User/platform owner |
| High | Open question | What audit events, retention period, access roles, deletion process, and tamper-resistance level are required? | `P01-T03`, `P04-T02` | Determines Application Insights/Log Analytics scope versus a dedicated audit store. | Obtain approved requirements from business data owner and security/compliance. | Business/security owners |
| Medium | Risk | The existing development launcher and Dockerfile are not suitable as a hosted production startup contract. | `P02-T03` | Browser launch, loopback binds, and coupled process lifecycle may prevent reliable ACA health and scaling. | Define explicit hosted entrypoints and test container lifecycle/probes. | Engineering |
| Medium | Risk | A Foundry-hosted agent, APIM gateway, and MCP backend can each emit overlapping telemetry with different identifiers. | `P04-T01` | Evidence may be incomplete or misleading if trace context is not propagated. | Define end-to-end trace contract and prove one trace through all hops. | Observability owner |
| Medium | Open question | Does the human-approval client path exist in the Foundry Prompt Agent experience, or is a separate business UI required? | `P04-T03` | Elicitation currently exists for a single synthetic read-only action, not universal approval. | Verify client support and define explicit high-risk action list and approval UX. | Product/security owner |

## Dependencies

* [`.copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md`](../../plans/2026-10-14/real-mcp-server-plan.md): Its P03/P04 work owns baseline hosted MCP security, telemetry, ACA, Bicep, and deployment. Confirm completion and implementation evidence before using those controls as deployed facts.
* [`.copilot-tracking/plans/2026-10-14/integrate-agent-governance-toolkit-plan.md`](../../plans/2026-10-14/integrate-agent-governance-toolkit-plan.md): Defines the current required default-deny runtime layer. Keep it complementary to Foundry guardrails unless maintainers explicitly revise that architecture.
* [docs/project-planning/member-wealth-insights-agent.md](../../../docs/project-planning/member-wealth-insights-agent.md): Product needs synthetic-data pilot, advice boundaries, regional controls, and currently unresolved audit requirements.

## Sources

* [README.md](../../../README.md): Current local run model, direct Foundry/MCP flow, synthetic-data boundary, and statement that Azure hosting automation is planned.
* [Dockerfile](../../../Dockerfile): Current container starts the development supervisor.
* [src/ai_governance_harness/chat/service.py](../../../src/ai_governance_harness/chat/service.py): Current Chat Completions, direct MCP calls, and snapshot proxy.
* [src/ai_governance_harness/foundry_client.py](../../../src/ai_governance_harness/foundry_client.py): Current project client and `DefaultAzureCredential` integration.
* [src/ai_governance_harness/mcp_server/config.py](../../../src/ai_governance_harness/mcp_server/config.py): Hosted MCP configuration, region checks, and auth contract.
* [src/ai_governance_harness/mcp_server/server.py](../../../src/ai_governance_harness/mcp_server/server.py): Current typed MCP tools and one elicitation-based approval example.
* [docs/planning/adrs/0003-minimize-identity-and-governance-telemetry.md](../../../docs/planning/adrs/0003-minimize-identity-and-governance-telemetry.md): Privacy and bounded-retention contract.
* [docs/planning/adrs/0005-present-governance-through-a-same-origin-observability-panel.md](../../../docs/planning/adrs/0005-present-governance-through-a-same-origin-observability-panel.md): Current same-origin operator panel and partial-state behavior.
* Workshop architecture supplied in the conversation: target flow, cross-cutting controls, and stretch goals.

## Critique Disposition

* Critique candidate identity: `azure-native-migration-2026-10-14`, initial implementation-plan draft.
* Critique depth and provenance: Standard is the default; no critique dispatched because planning readiness is partial and material Azure capability and audit decisions remain gated.
* Critique execution: Not run.
* Single invocation consumed: No.

| Critique run and finding | Disposition | Action owner | Exact resolving evidence | Decision route | Plan response or residual risk |
|---|---|---|---|---|---|
| None | Not applicable | Planner | No critique execution | Not applicable | Reassess critique only after P01 decisions are resolved and the plan is implementation-ready. |

## Artifact Self-Check

* [x] Executive summary, What You May Not Know, and Phase Checklist precede supporting planning details.
* [x] User direction, decisions, readiness, goals, scope, requirements, risks, dependencies, and sources align with the phase checklist.
* [x] Each functional and non-functional requirement is cited by at least one task.
* [x] Each phase has Goals, Dependencies, a phase diagram, and tasks; each task has Goals, Requirements, Details, References, and Dependencies.
* [x] Every implementation task includes acceptance conditions and a verification method inside its Requirements block.
* [x] Before shows only the existing local flow; After shows the target architecture and labels planned components as added.
* [x] Phase diagrams reuse After nodes and relationships and identify highlighted work in prose.
* [x] Mermaid initialization uses the required font family and size; highlighted nodes have explicit readable colors.
* [ ] Mermaid diagram rendering was not visually checked in light and dark themes in this planning task.
* [x] Decision gates, risks, owners, and next actions are recorded; no Azure availability or audit-retention assumptions are presented as confirmed facts.
* [x] Delegation is recorded as adaptive; sequential phases were authored together without delegation.
* [x] No source code or Azure resources were changed by this plan-authoring task.
* Checked sections: `Task Metadata`, `Executive Summary`, `Phase Checklist`, `User Decisions and Requirements`, `Planning Readiness and Next Step`, `Goals`, `Scope and Non-Goals`, `Functional Requirements`, `Non-Functional Requirements`, `Risks and Open Questions`, `Dependencies`, `Sources`, `Critique Disposition`, `Follow-Up Items`, and `Handoff`.
* Missing or limited sections: Tenant-specific Azure capability evidence and owner approval for audit retention remain required before implementation readiness.

## Follow-Up Items

* Plan live member-data integration separately after the synthetic pilot, with approved source systems, data access roles, privacy review, and operational ownership. This plan intentionally stops at packaged synthetic data; business data and platform owners must define the next scope.

## Handoff

* Implementation handoff is blocked pending `D1`-`D3` evidence and decisions captured through `P01`.
* Do not start `/rpi-implement` yet. After the preflight updates this plan to implementation-ready, use `/rpi-implement` with `.copilot-tracking/changes/2026-10-14/azure-native-services-migration-changes.md` as the changes-record path.