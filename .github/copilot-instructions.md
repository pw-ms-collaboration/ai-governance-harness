---
description: "Project preference for PRD clarification questions."
---

# PRD Clarification Preferences

* Provide concrete, selectable options for every Product Requirements
  Document (PRD) clarification question, including follow-up questions.
* Ask one question at a time through the available question tool.
* When a recommendation is justified, place that option first and label
  it "(Recommended)". Do not treat a recommendation as user approval.
* Allow a custom answer through the question interface when supported.
  Do not add generic "Other" options when the interface supplies one.
* Apply this preference throughout PRD discovery, authoring, and review.

## Microsoft Entra Agent ID
- To give an AI agent its own identity in Microsoft Entra, create an agent identity blueprint, then create agent identities from it.
- Don't create or reuse a standard app registration or service principal to represent an agent. Never use `az ad app create`, `New-MgApplication`, `New-AzADApplication`, or `POST /applications` to create an agent identity.
- In .NET, use the Microsoft.Identity.Web.AgentIdentities package: call builder.Services.AddAgentIdentities(), then acquire tokens with WithAgentIdentity(agentIdentity) (app-only) or WithAgentUserIdentity(agentIdentity, user) (on behalf of a user).
- Requires the Agent ID Developer or Agent ID Administrator role and the AgentIdentityBlueprint.Create permission.
- Reference: /entra/agent-id/how-to-plan-agent-identity-architecture
