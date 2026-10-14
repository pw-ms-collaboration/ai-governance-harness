<!-- markdownlint-disable-file -->
# RPI Changes: Azure-Native Services Migration

## Metadata

* Task ID: `azure-native-migration-2026-10-14`
* Related plan: [.copilot-tracking/plans/2026-10-14/azure-native-services-migration-plan.md](../../plans/2026-10-14/azure-native-services-migration-plan.md)
* Implementation date: 2026-10-14

## Execution Status

* Status: Partial
* Declared invocation scope: ACR bootstrap stage
* Completed scope markers: None
* Remaining active marker: `P01-T02`
* Status basis: Added and compiled a registry bootstrap template and completed a read-only What-If. Azure resources were not applied.

## Completed Work

### Added an ACR bootstrap stage

* Related phase or task: `P01-T02`
* Files:
  * [infra/bootstrap-acr.bicep](../../../infra/bootstrap-acr.bicep)
* Behavior or functionality changed: Added a standalone Basic ACR deployment with the same deterministic name, disabled admin account, and tags as the full template. The output exposes the registry name and login server for image publishing before the full Container Apps deployment.
* Validation: Bootstrap and full Bicep templates compiled. Bootstrap What-If predicted one ACR create and 18 ignored resources. No Azure resources were applied.

## Remaining Work

* Obtain explicit authorization and ACR create permission before applying the bootstrap stage.
* Build and push the completed application image after the registry exists.
* Complete Prompt Agent/MCP authentication integration, Entra app-role assignment, chat secret setup, and full-template deployment permissions before the production-shaped What-If and separately approved apply.