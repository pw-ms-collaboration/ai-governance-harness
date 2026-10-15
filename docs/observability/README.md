---
title: Import the AI Governance Observability workbook
description: Manually import the local workbook definition into Azure Monitor.
---

## Import the workbook

The [workbook JSON](./ai-governance-observability.workbook.json) is a complete
Azure Workbook definition, not an ARM deployment template. Import it through the
workbook's Advanced Editor. No CLI deployment or Bicep is required.

1. Open Application Insights `rg-aigovernance-applicationinsight` in Azure Portal.
2. Select **Workbooks**, then **New** or an empty workbook template.
3. Enter **Edit** mode and open **Advanced Editor** using the `</>` toolbar
   control. Select the workbook JSON view, not an ARM template view.
4. Replace the editor contents with the entire workbook JSON file.
5. Select **Apply**, then **Done Editing**.
6. Select **Save** and name it **AI Governance Observability**. Choose resource
   group `rg-aigovernance-amp-guardrails-hack` and location **Australia East**.
   Use a different name if you want to preserve an already saved copy.
7. Start with the **1 hour** time range. Select **24 hours** if there has been
   little recent agent activity.

The resource ID is already configured for the existing Application Insights
resource. To use another resource, replace the ID in `fallbackResourceIds` and
every query item's `content.crossComponentResources`. The file contains resource
identifiers, not connection strings, credentials, or telemetry records.

## Included views

* Last received telemetry for chat and MCP, with explicit no-data states.
* Governance decisions by service and outcome.
* Weighted mean policy evaluation duration in milliseconds.
* MCP HTTP request volume.
* MCP tool-call volume by tool name.
* Recorded span duration and failures.
* The latest 100 spans with operation and parent IDs.

The queries were validated against the existing Application Insights resource
before export. Azure resource persistence was verified separately; portal
rendering still requires an authenticated visual check after import.

## Interpret the results

The workbook displays telemetry that the application already exports. Importing
it does not enable collection, create alerts, or add distributed-trace
correlation.

An empty chart does not prove the service is healthy or unhealthy. Check the
selected time range, resource access, export configuration, and ingestion delay.
The tool chart needs actual MCP tool calls; a governance deny demonstration
alone does not invoke a tool.

OTel spans appear in the Application Insights `requests` and `dependencies`
tables. The `traces` table contains log records. These queries are scoped to
Application Insights, not directly to a Log Analytics workspace.

Governance denials are policy outcomes, not necessarily failed spans. Span
percentiles describe retained spans and may be affected by sampling. They are
not policy-histogram percentiles. Governance counters sum exported values;
evaluation duration uses aggregated sums and counts.

To investigate a trace, copy an `operation_Id` from the recent-span table and
use the example query at the bottom of the workbook. A complete cross-service
tree is visible only where the application propagates trace context.

## Reference

[Create or edit an Azure Workbook](https://learn.microsoft.com/azure/azure-monitor/visualize/workbooks-create-workbook)
describes the Azure Portal editing workflow.
