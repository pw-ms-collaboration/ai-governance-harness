---
id: '0008'
title: Use Microsoft Entra Agent ID for agent identity
status: proposed
proposed_date: 2026-10-14
deciders:
  - Repository maintainers
consulted:
  - AI governance engineering team
informed:
  - Security engineering
  - Platform architecture
tags:
  - identity
  - security
  - governance
supersedes: null
superseded-by: null
related:
  - path: 0002-enforce-default-deny-at-every-execution-boundary.md
    relation: influences
  - path: 0003-minimize-identity-and-governance-telemetry.md
    relation: influences
  - path: 0009-enforce-agent-and-staff-identity-through-governance-policy-context.md
    relation: influences
  - path: 0010-use-a-local-only-mock-entra-agent-id-issuer-for-the-mvp.md
    relation: influences
asr_triggers:
  - kind: security
    evidence: Staff identity must reach the MCP boundary and agents need least-privilege, distinct identities.
    note: Shared or over-privileged identities would allow member data access outside a staff member's role.
  - kind: compliance
    evidence: The security plan requires Entra ID for all staff and agent access inherited from the user.
    note: Audit and access reviews need per-agent attribution and sponsor accountability.
  - kind: evolvability
    evidence: Hosted identity is deferred and the MVP uses a mock that must be replaceable by configuration.
    note: The target contract must stay stable while hosting and tenant access arrive later.
affected_components:
  - src/ai_governance_harness/chat/service.py
  - src/ai_governance_harness/chat/app.py
  - src/ai_governance_harness/mcp_server/security.py
  - src/ai_governance_harness/mcp_server/config.py
  - src/ai_governance_harness/foundry_client.py
  - src/ai_governance_harness/governance/agt-runtime-evidence.yaml
  - src/ai_governance_harness/governance/evidence/owasp-agentic.yaml
effort: L
success_criteria:
  - metric: Agent actions attributable to a specific agent identity
    target: 100 percent of MCP and Foundry calls carry an agent identity as actor
    measurement_window: Every hosted acceptance run
    source: MCP validator audit events and Entra sign-in logs
  - metric: Client secrets on agent identity blueprints
    target: Zero in every environment
    measurement_window: Every production handshake review
    source: Blueprint credential inventory
  - metric: Member-level tool calls without a staff OBO token
    target: Zero
    measurement_window: Every test and hosted acceptance run
    source: MCP authorization tests
---

# Use Microsoft Entra Agent ID for agent identity

## Context

The harness has one reasoning agent, the chat orchestrator, which calls an
Azure AI Foundry model and chooses MCP tools that read synthetic member data.
Today it sends no credential to MCP, the toolkit evidence marks hosted principal
validation as deferred, and OWASP ASI03 is partial because end-user identity is
not propagated. The security plan requires Entra ID for all staff, agent access
inherited from the signed-in user, four staff roles, and authorization enforced
outside the model.

Microsoft Entra Agent ID gives agents a dedicated identity type: a blueprint
holds credentials and policy, and agent identities created from it act on
behalf of users (OBO) or autonomously. Microsoft guidance says not to represent
an agent with an app registration, a plain service principal, or a user
account.

> Evidence: [`security.py`](../../../src/ai_governance_harness/mcp_server/security.py) validates hosted Easy Auth headers (`tid`, `aud`, `scp`) but no roles or actor.
> Evidence: [`agt-runtime-evidence.yaml`](../../../src/ai_governance_harness/governance/agt-runtime-evidence.yaml) records `hosted_principal_validation: deferred`.
> Evidence: [Plan your agent identity architecture](https://learn.microsoft.com/en-us/entra/agent-id/how-to-plan-agent-identity-architecture) recommends one blueprint per trust boundary and one agent identity per logical agent.

How should the harness identify its agents and carry staff identity to the MCP
boundary when it is hosted?

## Decision Drivers

* Staff identity must reach MCP so authorization uses the staff member's role (security plan §5).
* Each agent needs least privilege, its own audit trail, and an independent kill switch.
* Agents must not be modeled as app registrations, service principals, or users (Microsoft guidance).
* The in-process default-deny governance gateway must stay in the request path (ADR 0001, ADR 0002).
* No client secrets in hosted environments; credentials isolated per environment.
* The Python runtime must be supported without hand-written token exchange.

## Considered Options

1. Self-hosted orchestrator with a repository-provisioned blueprint per environment, two agent identities, and the Entra SDK for AgentID sidecar.
2. Move orchestration to Foundry Agent Service and use its auto-provisioned agent identity.
3. Use a managed identity or app registration per service as the agent's identity.
4. One agent identity per environment that performs both OBO and app-only calls.

## Decision Outcome

Chosen option: "Self-hosted orchestrator with a repository-provisioned
blueprint", because it is the only option that follows Agent ID guidance while
keeping the governance gateway in the request path.

Per environment (development, production):

* **Blueprint** `AGH Member Insights ({env})`:
  * a user sponsor and technical owners;
  * a user-assigned managed identity as its federated credential;
  * exposes `access_agent`, and pre-authorizes the chat client app;
  * the MCP `Tools.Read` scope as an inheritable delegated permission.
* **Agent identity** `member-insights-interactive`:
  * acts on behalf of signed-in staff (OBO) to call MCP;
  * holds an inference-only Azure role on the Foundry resource.
* **Agent identity** `member-insights-reporting`:
  * calls MCP app-only with the `Reports.Aggregate.Read` app role;
  * limited to the aggregate tools.
* **Chat client app registration** `agh-chat-web`:
  * staff sign in through it and receive a user token for the blueprint;
  * assignment required, assigned to the four staff security groups.
* **MCP API app registration** `agh-mcp-api`:
  * a protected resource API, not an agent;
  * `Tools.Read` scope, `Staff.*` app roles assigned to security groups, and the `Reports.Aggregate.Read` app role.
* **Token acquisition:** the chat service and the reporting job use the Entra
  SDK for AgentID sidecar on localhost (`/Validate`, `/AuthorizationHeader`,
  `/AuthorizationHeaderUnauthenticated`).
* **MCP validation:** checks `tid`, `aud`, `scp` or `roles`, the `azp` allowlist,
  `idtyp`, and the `xms_act_fct`/`xms_sub_fct` facets before governance runs.
* **Deferred:** Conditional Access for agents needs Microsoft 365 E7 or
  Agent 365 plus Entra P1/E3, which the tenant does not have.

| Driver | Self-hosted + blueprint | Foundry Agent Service | Managed identity or app registration | Single agent identity |
|--------|-------------------------|-----------------------|--------------------------------------|-----------------------|
| Staff identity at MCP | Strong | Strong | Weak | Strong |
| Follows Agent ID guidance | Strong | Strong | None | Medium |
| Least privilege per agent | Strong | Medium | Weak | Weak |
| Governance gateway in path | Strong | Weak | Strong | Strong |
| Implementation effort | Medium | Low | Low | Medium |

### Consequences

* Good, because staff role and agent identity reach MCP in validated token claims.
* Good, because the interactive identity never holds the aggregate app role, so a hijacked chat turn cannot switch to app-only access.
* Good, because disabling the blueprint or one agent identity stops its tokens.
* Good, because no client secrets exist in any environment.
* Bad, because the repository owns provisioning, and the role requests and admin consent it depends on.
* Bad, because the sidecar adds a container per service, and hosting it on Azure Container Apps is undocumented.
* Bad, because the earlier plan to use the chat managed identity for the MCP token is replaced and must be re-planned.
* Neutral, because Conditional Access for agents can be added later without changing the topology.

### Confirmation

* Hosted acceptance proves that a staff OBO token reaches MCP with
  `idtyp=user` and the interactive `azp`, and that the reporting app-only token
  carries `idtyp=app`.
* An identity admin confirms in a production handshake: the blueprint, sponsor,
  consent, managed-identity credential, and the absence of secrets.

## Pros and Cons of the Options

### Self-hosted orchestrator with a repository-provisioned blueprint

* Good, because it follows Agent ID guidance and keeps governance in-process.
* Bad, because tenant roles (Agent ID Developer) and admin consent are prerequisites.

### Foundry Agent Service identity

* Good, because Foundry provisions the blueprint and handles token exchange.
* Bad, because orchestration leaves the harness, and unpublished agents share one project identity.

### Managed identity or app registration as the agent

* Good, because it is familiar and needs no sidecar.
* Bad, because it has no sponsor, no agent-specific audit, and no blueprint lifecycle, and Microsoft guidance rejects it.

### Single agent identity for both patterns

* Good, because there are fewer directory objects.
* Bad, because the interactive path would hold aggregate app-only access, and the audit trail mixes both patterns.

## Architecture

Numbered edges follow one staff chat turn. Dotted edges are credential,
assignment, or control relationships.

```mermaid
flowchart TB
  subgraph users["Staff"]
    B["Browser chat UI"]
  end

  subgraph entra["Microsoft Entra tenant, one set per environment"]
    WEB["App registration: agh-chat-web<br/>client app, assignment required"]
    BP["Agent identity blueprint: AGH Member Insights<br/>exposes access_agent, pre-authorizes agh-chat-web<br/>FIC to managed identity, inheritable Tools.Read"]
    AI1["Agent identity: member-insights-interactive<br/>OBO only, Azure role on Foundry"]
    AI2["Agent identity: member-insights-reporting<br/>app role Reports.Aggregate.Read"]
    MCPAPP["App registration: agh-mcp-api<br/>scope Tools.Read, app roles Staff.* and Reports.Aggregate.Read"]
    GRP["Security groups, fixed membership<br/>Analysts, Retention Specialists,<br/>Compliance Reviewers, Administrators"]
    BP --> AI1
    BP --> AI2
    GRP -. "assigned" .-> WEB
    GRP -. "assigned Staff.* app roles" .-> MCPAPP
  end

  subgraph azure["Azure subscription, Australia East"]
    MI["User-assigned managed identity"]
    subgraph chatapp["Chat Container App"]
      CHAT["Chat service and orchestrator<br/>governance adapter: AgentMesh PolicyEngine<br/>boundary = chat, actor = interactive"]
      SC1["Entra SDK for AgentID sidecar<br/>localhost only"]
    end
    subgraph job["Reporting job"]
      REP["Reporting agent<br/>aggregate tools only"]
      SC2["Entra SDK for AgentID sidecar<br/>localhost only"]
    end
    subgraph mcpapp["MCP Container App"]
      EA["Container Apps authentication<br/>signature, tid, aud"]
      VAL["MCP validator<br/>azp allowlist, idtyp, xms facets, scp, roles"]
      GOV["Governance adapter: AgentMesh PolicyEngine<br/>default deny, boundary = mcp<br/>staff role matrix"]
      GW["Shared gateway and typed tools"]
      DATA[("Synthetic member data")]
    end
    FDY["Azure AI Foundry model"]
  end

  OPS["Operator kill switch<br/>disable blueprint or agent identity"]

  B -->|"1. sign in through agh-chat-web<br/>user token aud = blueprint"| WEB
  B -->|"2. /api/chat + Bearer user token"| CHAT
  CHAT -->|"3. /Validate and token requests"| SC1
  SC1 -->|"4. blueprint FIC + fmi_path<br/>OBO or app-only exchange"| BP
  MI -. "federated credential" .-> BP
  SC1 -. "managed identity token" .-> MI
  CHAT -->|"5. inference, app-only token<br/>Azure role on this resource only"| FDY
  CHAT -->|"6. tool call + OBO token<br/>idtyp = user, azp = interactive, roles = Staff.*"| EA
  REP --> SC2
  SC2 -->|"app-only exchange"| BP
  SC2 -. "managed identity token" .-> MI
  REP -->|"tool call + app token<br/>idtyp = app, azp = reporting<br/>roles = Reports.Aggregate.Read"| EA
  EA --> VAL --> GOV --> GW --> DATA
  OPS -. "stops token issuance" .-> BP
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| No Agent ID Developer role or admin consent in the tenant | Use the local mock (ADR 0010) until access is granted; alternatively, an admin creates the blueprints and adds a developer as owner. |
| Sidecar unsupported on Azure Container Apps | Run a development spike first; fall back to AKS with Workload ID. |
| The browser cannot obtain a blueprint-audience token through Container Apps authentication | Fall back to MSAL authorization code with PKCE in the browser. |
| `xms_*` claims missing from MCP tokens | Inspect development tokens; configure optional claims on the MCP API registration; MCP denies when they are absent. |
| Conditional Access for agents not licensed | Rely on the blueprint kill switch, sponsors, sign-in alerts, and MCP enforcement. |

## Rollback / Exit Strategy

Disable the affected agent identity or blueprint in Entra; MCP then rejects its
tokens and the harness fails closed. Do not fall back to anonymous or managed
identity access to MCP. To leave Agent ID entirely, write a superseding ADR.

## Affected Components

* Chat service token acquisition and Bearer handling.
* MCP request security, hosted settings, and claim normalization.
* Foundry client credential in hosted mode.
* Toolkit runtime evidence and OWASP ASI03 evidence.
* Infrastructure as code for Entra objects, managed identity, and Container Apps.

## Recovery and Extension Runbook

1. Check that the blueprint and both agent identities are enabled and have current sponsors.
2. Confirm that the managed-identity federated credential matches the hosting environment.
3. Decode a development MCP token and confirm `aud`, `azp`, `idtyp`, `scp` or `roles`, and `xms_act_fct`.
4. To add an agent, create an agent identity under the same blueprint when it shares the runtime; create a new blueprint when it crosses a trust boundary.
5. Never add a client secret to fix an authentication failure in a hosted environment.
