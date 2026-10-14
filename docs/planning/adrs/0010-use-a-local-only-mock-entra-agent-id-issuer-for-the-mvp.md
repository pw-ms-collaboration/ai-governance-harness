---
id: '0010'
title: Use a local-only mock Entra Agent ID issuer for the MVP
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
  - mvp
supersedes: null
superseded-by: null
related:
  - path: 0002-enforce-default-deny-at-every-execution-boundary.md
    relation: influenced-by
  - path: 0005-present-governance-through-a-same-origin-observability-panel.md
    relation: influenced-by
  - path: 0008-use-microsoft-entra-agent-id-for-agent-identity.md
    relation: influenced-by
  - path: 0009-enforce-agent-and-staff-identity-through-governance-policy-context.md
    relation: influenced-by
asr_triggers:
  - kind: security
    evidence: The mock issues tokens for any synthetic persona without authentication.
    note: If it ran outside local mode it would be an authentication bypass for member data.
  - kind: evolvability
    evidence: Real Entra Agent ID is unavailable during the hackathon but is the target in ADR 0008.
    note: Chat and MCP must switch from the mock to Entra by configuration, not by rewriting validation.
affected_components:
  - src/ai_governance_harness/dev_launcher.py
  - src/ai_governance_harness/chat/app.py
  - src/ai_governance_harness/chat/service.py
  - src/ai_governance_harness/chat/static/app.js
  - src/ai_governance_harness/chat/static/index.html
  - src/ai_governance_harness/mcp_server/security.py
  - src/ai_governance_harness/mcp_server/config.py
  - pyproject.toml
effort: M
success_criteria:
  - metric: Mock identity service starting when hosted or in staging or production
    target: Zero; startup fails closed
    measurement_window: Every test run
    source: Startup guard tests
  - metric: MCP tool calls accepted with an unsigned, expired, wrong-audience, or unknown-agent token
    target: Zero
    measurement_window: Every test run
    source: MCP jwt principal source tests
  - metric: Staff role matrix outcomes demonstrable in the local UI
    target: Allow and deny shown for every persona
    measurement_window: Hackathon demonstration
    source: Manual demo script and governance panel
---

# Use a local-only mock Entra Agent ID issuer for the MVP

## Context

ADR 0008 selects Microsoft Entra Agent ID, and ADR 0009 makes governance
decisions depend on validated agent and staff identity. Creating agent identity
blueprints requires the Agent ID Developer role and admin consent of Agent ID
Graph permissions. The developer has neither and cannot obtain them for the
hackathon. The MVP still needs to demonstrate staff identity reaching MCP,
OBO and app-only agent tokens, and the staff role matrix.

> Evidence: [Create an agent identity blueprint](https://learn.microsoft.com/en-us/entra/agent-id/create-blueprint) requires Agent ID Developer or Agent ID Administrator, and admin consent of `AgentIdentityBlueprint.Create`.
> Evidence: [`security.py`](../../../src/ai_governance_harness/mcp_server/security.py) treats non-hosted requests as `local-development` with no authentication, which is the seam for a pluggable principal source.
> Evidence: [Token claims reference for agent IDs](https://learn.microsoft.com/en-us/entra/agent-id/agent-token-claims) defines the OBO and app-only claim shapes the mock reproduces.

How can the MVP prove the identity design without tenant access, without
creating a production bypass?

## Decision Drivers

* Demonstrate staff OBO, reporting app-only, and the staff role matrix end to end.
* Exercise the same signature, claim, and policy code paths that real Entra will use.
* Switch to real Entra Agent ID by configuration, not by rewriting validation.
* The mock must never run in hosted, staging, or production environments.
* Keep the browser same-origin (ADR 0005) and keep tokens out of storage and telemetry (ADR 0003).
* Keep stdio MCP and the legacy CLI usable without bypassing the role matrix.

## Considered Options

1. A signed-token mock issuer as a separate local service, with sidecar-compatible endpoints and a public signing key (JWKS).
2. An unsigned in-process claims stub trusted in local mode.
3. Faked Container Apps authentication headers injected by a local proxy.
4. A mock issuer embedded in the chat process.

## Decision Outcome

Chosen option: "Signed-token mock issuer as a separate local service", because
it is the only option that exercises real signature and claim validation while
keeping the signing key out of the chat and MCP processes.

**`ai-governance-identity`** on `127.0.0.1:8002`, started first by `ai-governance-dev`:

* An RS256 key generated in memory at startup and never written.
* Entra v2-shaped discovery and JWKS.
* `/mock/signin` for four synthetic staff personas.
* Sidecar-compatible `/Validate`, `/AuthorizationHeader/mcp` (OBO-shaped),
  `/AuthorizationHeaderUnauthenticated/mcp` (app-only), and `/healthz`.
* Tokens carry the claim shapes from ADR 0008: `aud`, `azp`, `idtyp`, `scp` or
  `roles`, and `xms_act_fct`/`xms_sub_fct`.
* Unknown agent identities, and agent identities used on the wrong endpoint,
  are rejected.

**Chat:**

* The browser chooses a persona through a labelled "Mock identity" switcher and
  `/api/mock-identity/signin`, a same-origin route that forwards to the mock.
* The token is kept in page memory and sent as a Bearer token to `/api/chat`.
* Chat validates the token through `/Validate`, and gets an OBO-shaped MCP
  token for each tool call.

**MCP:** a principal-source setting chooses `easy_auth` (hosted, existing) or
`jwt`. The `jwt` source verifies the signature against the JWKS, pins issuer,
audience and algorithm, and derives the ADR 0009 identity fields. Anything
missing or unrecognised is denied.

**Token-less callers:** stdio MCP and the legacy CLI use an opt-in
`MOCK_IDENTITY_LOCAL_PERSONA` with `boundary = local`. When it is unset, they
are denied.

**Reporting:** a small app-only reporting command demonstrates the second agent
identity.

**Guard:** the identity service, the chat mock routes, and the MCP `jwt` mock
trust all refuse to start unless the environment is `local`, `development`, or
`test` and the service is not hosted. All identifiers are synthetic, and the UI
and governance panel label the identity as mock.

**Foundry:** Foundry inference keeps `DefaultAzureCredential` (developer
sign-in), because the mock cannot issue Azure tokens. ADR 0008's agent identity
for Foundry waits for real Entra.

**Exit criterion:** supersede this ADR when Agent ID Developer access or
blueprint ownership is available and ADR 0008's development environment passes
acceptance.

| Driver | Signed mock service | Unsigned stub | Faked headers proxy | Mock in chat |
|--------|---------------------|---------------|---------------------|--------------|
| Real validation exercised | Strong | None | Weak | Strong |
| Switch to Entra by configuration | Strong | Weak | Medium | Medium |
| Key isolation from callers | Strong | Not applicable | Not applicable | Weak |
| Demonstrates OBO and app-only | Strong | Medium | Weak | Strong |
| Effort | Medium | Low | Medium | Medium |

### Consequences

* Good, because the hackathon demo shows real allow and deny outcomes driven by signed identity.
* Good, because the MCP `jwt` source and claim normalization carry over unchanged to real Entra.
* Good, because the signing key never leaves the identity process, and resets on restart.
* Bad, because a service that issues any persona is an authentication bypass if the guard is defeated.
* Bad, because the demo proves role enforcement, not role assignment, consent, Conditional Access, or Foundry agent identity.
* Bad, because a third local process and a direct `PyJWT[crypto]` dependency are added, and `cryptography` must stay below 49 (ADR 0006).
* Neutral, because restarting the identity service invalidates earlier tokens and the UI must sign in again.

### Confirmation

* Tests assert that every mock component refuses to start when hosted, `staging`, or `production`.
* Tests reject unsigned, expired, wrong-issuer, wrong-audience, and unknown-agent tokens.
* Tests deny each persona outside the ADR 0009 matrix.
* `ai-governance-audit` passes after adding the dependency.
* The README, governance panel, and OWASP ASI03 evidence state "mock identity", and toolkit evidence keeps `hosted_principal_validation: deferred`.

## Pros and Cons of the Options

### Signed-token mock service

* Good, because it mirrors the real process boundaries and sidecar API.
* Bad, because it adds a service to start, test, and document.

### Unsigned claims stub

* Good, because it is the fastest to build.
* Bad, because it proves no validation and normalizes trusting unsigned identity.

### Faked authentication headers

* Good, because it reuses the hosted Easy Auth validator.
* Bad, because it skips the chat OBO flow and turns on header trust locally.

### Mock in chat

* Good, because there is one fewer process.
* Bad, because the chat service would hold the key for tokens it is meant to obtain from elsewhere.

## Architecture

```mermaid
flowchart LR
  subgraph dev["Developer machine, 127.0.0.1 only, environment = local"]
    L["ai-governance-dev launcher<br/>starts identity, then MCP, then chat"]
    B["Browser chat UI<br/>Mock identity persona switcher<br/>token kept in page memory"]
    subgraph idsvc["ai-governance-identity :8002, mock Entra and sidecar"]
      KEY["RS256 key generated in memory<br/>at startup, never written"]
      SIGNIN["/mock/signin<br/>four synthetic staff personas"]
      SIDE["/Validate<br/>/AuthorizationHeader/mcp, OBO-shaped<br/>/AuthorizationHeaderUnauthenticated/mcp, app-only"]
      JWKS["Discovery and JWKS<br/>Entra v2 issuer shape"]
    end
    subgraph chat["Chat service :8080"]
      PROXY["/api/mock-identity/signin<br/>same-origin proxy"]
      CHAT["/api/chat<br/>orchestrator and governance adapter<br/>boundary = chat"]
    end
    subgraph mcp["MCP server :8001"]
      JWT["Principal source: jwt<br/>signature, iss, aud, RS256<br/>derive actor, token_type, staff_role"]
      GOV["Governance adapter: AgentMesh PolicyEngine<br/>default deny, boundary = mcp<br/>staff role matrix"]
      GW["Shared gateway and typed tools"]
      DATA[("Synthetic member data")]
    end
    REP["Reporting command<br/>app-only, aggregate tools"]
    LOCAL["stdio MCP client or legacy CLI<br/>MOCK_IDENTITY_LOCAL_PERSONA<br/>unset = deny, boundary = local"]
  end

  AZ["Developer az login<br/>DefaultAzureCredential"]
  FDY["Azure AI Foundry model, cloud"]
  GUARD["Startup guard: mock refuses to run<br/>when hosted, staging, or production"]

  L -. "starts" .-> idsvc
  L -. "starts" .-> mcp
  L -. "starts" .-> chat
  B -->|"1. choose persona"| PROXY
  PROXY -->|"2. forward"| SIGNIN
  SIGNIN -->|"3. user token, aud = mock blueprint"| B
  B -->|"4. /api/chat + Bearer"| CHAT
  CHAT -->|"5. validate, get OBO-shaped MCP token"| SIDE
  CHAT -->|"6. tool call + Bearer"| JWT
  JWT -. "fetch and cache keys" .-> JWKS
  JWT --> GOV --> GW --> DATA
  CHAT -->|"inference"| FDY
  AZ -. "developer credential" .-> CHAT
  REP -->|"app-only token"| SIDE
  REP -->|"tool call + Bearer"| JWT
  LOCAL -->|"configured persona"| GOV
  KEY -. "signs" .-> SIGNIN
  KEY -. "signs" .-> SIDE
  KEY -. "publishes" .-> JWKS
  GUARD -. "enforces" .-> idsvc
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Mock runs outside local mode | Startup guards in all three services, bind to `127.0.0.1`, and tests for every disallowed environment. |
| Demo read as a real Entra integration | Label the identity as mock in the UI, governance panel, README, and OWASP evidence. |
| Existing tests and README flows break under role rules | Fixtures mint mock tokens or set `MOCK_IDENTITY_LOCAL_PERSONA`; update README examples. |
| Identity service down at MCP startup | The launcher starts identity first; MCP readiness reports the JWKS state and fails closed. |
| Dependency audit drift | Pin a `PyJWT[crypto]` version compatible with `cryptography<49`; run `ai-governance-audit`. |

## Rollback / Exit Strategy

* To retire the mock:
  * switch the MCP principal source to `easy_auth`, or to `jwt` against the real Entra JWKS;
  * point chat at the real Entra SDK sidecar and remove the persona switcher;
  * remove the identity service from the launcher;
  * supersede this ADR.
* If the guard is ever found bypassable: stop the identity service, remove the
  mock routes, and restore default deny for all tool calls until it is fixed.

## Affected Components

* New local identity service and its launcher entry point.
* Chat API authentication, mock sign-in route, and UI persona switcher.
* MCP principal source configuration and `jwt` validation.
* Dependency manifest and audit.
* Tests, README, governance panel, and OWASP evidence wording.

## Recovery and Extension Runbook

1. If the UI reports an invalid token after a restart, sign in again; the signing key is regenerated on every start.
2. If MCP denies everything, check that the identity service is ready and that MCP readiness reports the JWKS as loaded.
3. To add a persona, add a synthetic persona, the matching `Staff.*` role value, and the ADR 0009 matrix rules and tests.
4. Never set a mock environment variable in a hosted deployment; the guard must reject it.
