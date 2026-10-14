<!-- markdownlint-disable-file -->
# RPI Changes: Azure-Native Services Migration

## Metadata

* Task ID: `azure-native-migration-2026-10-14`
* Related plan: [.copilot-tracking/plans/2026-10-14/azure-native-services-migration-plan.md](../../plans/2026-10-14/azure-native-services-migration-plan.md)
* Implementation date: 2026-10-14

## Execution Status

* Status: Partial
* Declared invocation scope: ACR bootstrap and MCP app-role authorization
* Completed scope markers: None
* Remaining active markers: `P01-T02`, `P03-T02`
* Status basis: Deployed only the ACR bootstrap stage and added locally tested app-role authorization support. The full application deployment remains incomplete.

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

## Remaining Work

* Configure the Foundry Agent's MCP tool and assign `Mcp.Tools.Invoke`; complete ChatService-to-Prompt-Agent integration.
* Build and push the completed application image to the deployed registry.
* Complete chat EasyAuth secret/redirect configuration and obtain role-assignment rights before the production-shaped What-If and separately approved apply.