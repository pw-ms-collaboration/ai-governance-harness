<!-- markdownlint-disable-file -->
# RPI Changes: Azure-Native Services Migration

## Metadata

* Task ID: `azure-native-migration-2026-10-14`
* Related plan: [.copilot-tracking/plans/2026-10-14/azure-native-services-migration-plan.md](../../plans/2026-10-14/azure-native-services-migration-plan.md)
* Implementation date: 2026-10-14

## Execution Status

* Status: Partial
* Declared invocation scope: ACR bootstrap, MCP app-role support, Prompt Agent chat adapter, and local/hosted mode isolation
* Completed scope markers: None
* Remaining active markers: `P01-T02`, `P02-T01`, `P02-T02`, `P02-T03`, `P03-T02`
* Status basis: Deployed only the ACR bootstrap stage; app-role authorization, Prompt Agent invocation, and local/hosted mode isolation are locally tested. Remote agent configuration and full application deployment remain incomplete.

## Completed Work

### Added an ACR bootstrap stage

* Related phase or task: `P01-T02`
* Files:
  * [infra/bootstrap-acr.bicep](../../../infra/bootstrap-acr.bicep)
* Behavior or functionality changed: Added and deployed a standalone Basic ACR with the same deterministic name, disabled admin account, and tags as the full template. Its outputs provide the registry name and login server for image publishing before the full Container Apps deployment.
* Validation: Bootstrap and full Bicep templates compiled. Bootstrap What-If predicted one ACR create and 18 ignored resources. Deployment `bootstrap-acr-20261014` succeeded; the registry is Basic with admin access disabled. No other Azure resources were applied.

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
* Validation: All 170 tests passed, Ruff passed, and the full Bicep template compiled. The final full-template What-If predicted 9 creates and 19 ignores; the ACR was ignored, with no modify/delete changes. Role assignments were disabled and placeholder image/secret values were used.

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

## Remaining Work
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

## Remaining Work

* Configure the Foundry Agent's MCP tool and assign `Mcp.Tools.Invoke`; pass a hosted synthetic vertical slice.
* Build and push the completed application image to the deployed registry after the vertical slice passes.
* Complete chat EasyAuth secret/redirect configuration and obtain role-assignment rights before the production-shaped What-If and separately approved apply.