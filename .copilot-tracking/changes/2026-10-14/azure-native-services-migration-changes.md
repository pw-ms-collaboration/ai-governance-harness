<!-- markdownlint-disable-file -->
# RPI Changes: Azure-Native Services Migration

## Metadata

* Task ID: `azure-native-migration-2026-10-14`
* Related plan: [.copilot-tracking/plans/2026-10-14/azure-native-services-migration-plan.md](../../plans/2026-10-14/azure-native-services-migration-plan.md)
* Implementation date: 2026-10-14

## Execution Status

* Status: Partial
* Declared invocation scope: ACR bootstrap, MCP app-role support, Prompt Agent chat adapter, local/hosted mode isolation, remote MCP tool configuration, and image publication
* Completed scope markers: None
* Remaining active markers: `P01-T02`, `P02-T01`, `P02-T02`, `P02-T03`, `P03-T02`
* Status basis: Deployed the ACR bootstrap stage and published the Linux/AMD64 image; configured the agentic-identity connection, Prompt Agent version 2, and `Mcp.Tools.Invoke` app-role assignment. The deployed MCP route, hosted invocation, and full application deployment remain incomplete.

## Completed Work

### Added an ACR bootstrap stage

* Related phase or task: `P01-T02`
* Files:
  * [infra/bootstrap-acr.bicep](../../../infra/bootstrap-acr.bicep)
* Behavior or functionality changed: Added and deployed a standalone Basic ACR with the same deterministic name, disabled admin account, and tags as the full template. Its outputs provide the registry name and login server for image publishing before the full Container Apps deployment.
* Validation: Bootstrap and full Bicep templates compiled. Bootstrap What-If predicted one ACR create and 18 ignored resources. Infrastructure deployment `bootstrap-acr-20261014` succeeded; the registry is Basic with admin access disabled. No other infrastructure resources were applied in that deployment.

### Added MCP application-role authorization

* Related phase or task: `P03-T02`
* Files:
  * [infra/main.bicep](../../../infra/main.bicep)
  * [src/ai_governance_harness/mcp_server/config.py](../../../src/ai_governance_harness/mcp_server/config.py)
  * [src/ai_governance_harness/mcp_server/http_app.py](../../../src/ai_governance_harness/mcp_server/http_app.py)
  * [src/ai_governance_harness/mcp_server/security.py](../../../src/ai_governance_harness/mcp_server/security.py)
  * [tests/test_mcp_config.py](../../../tests/test_mcp_config.py)
  * [tests/test_mcp_http.py](../../../tests/test_mcp_http.py)
* Behavior or functionality changed: Hosted MCP can require exactly one delegated scope or application role. The deployment now requires `Mcp.Tools.Invoke`; the middleware accepts role claims and retains delegated-scope support. The full template references the bootstrapped ACR as existing to avoid changing policy-managed tags or properties, and both Container Apps wait for the conditional `AcrPull` assignment when it is enabled.
* Validation: All 170 tests passed, Ruff passed, and the full Bicep template compiled. The final full-template What-If predicted 9 creates and 19 ignores; the ACR was ignored, with no modify/delete changes. Bicep Azure RBAC assignments were disabled and placeholder image/secret values were used; the `Mcp.Tools.Invoke` Graph assignment was completed separately.

### Added an optional Prompt Agent chat route

* Related phase or task: `P02-T03`
* Files:
  * [.env.example](../../../.env.example)
  * [infra/main.bicep](../../../infra/main.bicep)
  * [src/ai_governance_harness/chat/config.py](../../../src/ai_governance_harness/chat/config.py)
  * [src/ai_governance_harness/chat/service.py](../../../src/ai_governance_harness/chat/service.py)
  * [tests/test_chat_config.py](../../../tests/test_chat_config.py)
  * [tests/test_chat_service.py](../../../tests/test_chat_service.py)
* Behavior or functionality changed: Optional `FOUNDRY_AGENT_NAME` selects the installed SDK's Responses API `agent_reference` route. The direct Chat Completions/MCP orchestration remains available when the setting is absent. Both routes retain request governance, response sanitization, and safe error handling.
* Validation: All 171 repository tests passed, Ruff passed, Bicep compiled, and full-template What-If with the existing agent name predicted 9 creates and 19 ignores; the ACR remained ignored. No remote agent configuration or additional Azure resource deployment occurred.

### Kept local and hosted modes isolated

* Related phase or task: `P02-T03`
* Files:
  * [.env](../../../.env)
  * [.env.example](../../../.env.example)
  * [infra/main.bicep](../../../infra/main.bicep)
  * [src/ai_governance_harness/dev_launcher.py](../../../src/ai_governance_harness/dev_launcher.py)
  * [src/ai_governance_harness/foundry_client.py](../../../src/ai_governance_harness/foundry_client.py)
  * [tests/test_foundry_client.py](../../../tests/test_foundry_client.py)
* Behavior or functionality changed: Local startup forces `CHAT_USE_PROMPT_AGENT=false` and defaults to `AzureCliCredential`, avoiding accidental selection of the `.env` service principal. ACA explicitly enables Prompt Agent mode and uses `DefaultAzureCredential` for its managed identity.
* Validation: All 176 repository tests passed, Ruff passed, and Bicep compiled. The isolated local launcher reached ready on both services and returned HTTP 200 for a synthetic profile request while Prompt Agent mode was injected as true; the launcher still used the local direct route. The final full-template What-If predicted 9 creates and 19 ignores, with the ACR ignored. The isolated test pair was stopped, then the standard local pair was started and verified ready with the chat UI responding HTTP 200 on port `8080`.

### Configured the Prompt Agent MCP connection

* Related phase or task: `P02-T01`, `P02-T02`, `P03-T02`
* Azure configuration: Created remote-tool project connection `aighack-mcp-agent` with agentic identity, target `https://ajhackathon.azure-api.net/aighack-mcp/mcp`, and audience `api://ef56b0a6-b773-4c10-8cd2-db2433281896`.
* Behavior or functionality changed: Created Prompt Agent version 2 with one MCP server entry and an allowlist containing only `get_member_profile`, `get_member_disengagement_signals`, `get_cohort_churn_analytics`, and `get_fum_outflow_summary`. Approval is disabled for these read-only tools. Version 1 and the prompt instructions remain unchanged.
* Validation: ARM read-back confirmed the connection auth type, target, and audience. Foundry read-back confirmed version 2 is active with the MCP entry; the version 1 and version 2 models match and their instruction hashes are identical. Graph read-back confirmed the app-role assignment. No tool invocation was attempted because the APIM MCP API is not deployed.

### Built and published the application image

* Related phase or task: `P01-T02`, `P02-T03`
* Image: `aighack4oy7zgd25qpjc.azurecr.io/ai-governance-harness:demo-20261014-mcp-agent-v2`
* Digest: `sha256:7c6b00c0deb123a8abd3ce4ef57bf8d7889af1b4a09c3d3c412620858013741f`
* Behavior or functionality changed: Built for `linux/amd64` and pushed to the bootstrapped ACR. `.dockerignore` excludes `.env`, `.git`, and tracking artifacts.
* Validation: ACR confirmed the pushed tag. The image's chat and MCP entrypoints both reached ready in local containers, and unauthenticated MCP POST returned HTTP 401. The real-tag full-template What-If predicted 9 creates and 19 ignores, with the ACR ignored; no Azure app resources were applied. APIM-backed Prompt Agent invocation remains untested because the APIM route is not deployed.

## Remaining Work

* Deploy the APIM MCP API and pass a hosted synthetic vertical slice through version 2.
* Complete chat EasyAuth secret/redirect configuration and obtain Azure `roleAssignments/write` permission before the production-shaped What-If and separately approved apply.