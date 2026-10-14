# Member Whole-of-Wealth Insights & Interaction Advisory Agent - Architecture View

> Document ID: `ARCH-2026-SUPER-001`
> Related PRD: [`docs/project-planning/member-wealth-insights-agent.md`](../project-planning/member-wealth-insights-agent.md)
> Related BRD: [`docs/project-planning/member-wealth-insights-agent-brd.md`](../project-planning/member-wealth-insights-agent-brd.md)
> Related Security Plan: [`docs/project-planning/member-wealth-insights-agent-security-plan.md`](../project-planning/member-wealth-insights-agent-security-plan.md)
> Date: 2026-10-13
> Status: Approved Architecture Baseline

---

## 1. Architecture Overview

The **Member Whole-of-Wealth Insights & Interaction Advisory Agent** is an enterprise AI co-pilot designed for internal superannuation staff (contact centre consultants, retention specialists, and business analysts). It aggregates internal superannuation account and activity profiles, diagnoses member disengagement trends and Funds Under Management (FUM) outflow risks, and generates contextual preparation briefs for staff interactions.

### Core Architectural Principles

1. **Strict Advice Boundary (ASIC RG 244 / Corporations Act 2001 (Cth)):** The agent operates solely as an internal staff advisory tool providing factual analysis and general guidance. A deterministic compliance filter blocks any personal financial advice or recommendations tailored to individual goals.
2. **Data Minimisation & Sovereignty (APRA CPS 234 / CON-002 / CON-003):** Initial MVP operates entirely on synthetic member data modeled in JSON with no real personal PII. Processing conforms to Australian sovereign boundary requirements.
3. **Dual Execution Runtime:** The system supports both offline deterministic execution (mock LLM with rule-based heuristics) for CI/CD and safety evaluations, and live cloud execution via Azure AI Foundry and Entra ID cross-tenant authentication.
4. **Governed AI Lifecycle:** The system includes an automated evaluation harness verifying advice boundaries, profile grounding, and prompt injection defense.

---

## 2. C4 Level 1: System Context Diagram

The System Context diagram illustrates the system boundaries, users, and external integrations.

```mermaid
---
config:
  flowchart:
    subGraphTitleMargin:
      bottom: 30
---
flowchart TB
    subgraph layout_top[" "]
        person_staff(["`**Superannuation Staff**
*[Person]*
Contact Centre Consultants, Retention Specialists & Business Analysts`"])
    end

    subgraph sys_boundary["`**Superannuation Fund Boundary** *[Boundary]*`"]
        sys_agent["`**Member Wealth Insights & Advisory Agent**
*[Software System]*
Aggregates internal profiles, calculates churn/FUM outflow analytics, and generates staff guidance briefs.`"]
        ext_json_store[("`**Synthetic Member Data Store**
*[Internal Data Store]*
Encrypted JSON repository of synthetic member profiles, balances, and interaction logs.`")]
    end

    subgraph layout_bottom[" "]
        ext_entra["`**Microsoft Entra ID**
*[External System]*
Identity and Access Management with cross-tenant OAuth authentication.`"]
        ext_foundry["`**Azure AI Foundry**
*[External System]*
Cloud AI model inference, agent catalog, and telemetry tracking.`"]
    end

    person_staff -->|"`Looks up member profiles, requests churn diagnostics & interaction briefs`
*[HTTPS / CLI]*"| sys_agent
    sys_agent -->|"`Authenticates staff and service principals`
*[OAuth 2.0 / MSAL]*"| ext_entra
    sys_agent -->|"`Queries member balances, contributions & interactions`
*[File I/O / JSON]*"| ext_json_store
    sys_agent -->|"`Dispatches prompt completion & model inference`
*[REST / TLS 1.3]*"| ext_foundry

    style sys_boundary fill:none,stroke:#888888,stroke-dasharray:5 5,color:#888888
    style layout_top fill:none,stroke:none
    style layout_bottom fill:none,stroke:none

    classDef person fill:#08427b,stroke:#052e56,color:#ffffff
    classDef system fill:#1168bd,stroke:#0b4884,color:#ffffff
    classDef external fill:#999999,stroke:#6b6b6b,color:#ffffff

    class person_staff person
    class sys_agent,ext_json_store system
    class ext_entra,ext_foundry external
```

---

## 3. C4 Level 2: Container Diagram

The Container diagram decomposes the system into runnable modules and services.

```mermaid
---
config:
  flowchart:
    subGraphTitleMargin:
      bottom: 30
---
flowchart TB
    person_staff(["`**Superannuation Staff**
*[Person]*`"])

    subgraph sys_agent["`**Member Wealth Insights & Advisory Agent** *[Software System]*`"]
        ctr_agent_runner("`**Advisory Agent Runner**
*[Python Application]*
Orchestrates profile retrieval, analytics dispatch, brief synthesis, and response formatting.`")
        ctr_guardrail("`**Advice Boundary Guardrail**
*[Python Service]*
Deterministic pre/post filter enforcing ASIC RG 244 General Advice warnings and blocking personal advice.`")
        ctr_analytics("`**Churn & FUM Analytics Engine**
*[Python Service]*
Calculates individual contribution/activity deviations and aggregates cohort FUM leakage.`")
        ctr_repo("`**Member Repository & Data Access**
*[Python Module]*
Provides typed querying and cohort filtering over member records.`")
        ctr_eval_harness("`**AI Governance & Evaluation Harness**
*[Python / Pytest]*
Runs safety benchmarks, advice boundary evaluators, and grounding verification.`")
        ctr_data_store[("`**Synthetic Data Store**
*[JSON File Store]*
Synthetic member profiles, contributions, digital activity, and closure inquiries.`")]
    end

    ext_foundry["`**Azure AI Foundry**
*[Cloud Service]*`"]

    person_staff -->|"`Requests consultation brief or cohort report`"| ctr_agent_runner
    ctr_agent_runner -->|"`Fetches member profile and interaction history`"| ctr_repo
    ctr_agent_runner -->|"`Invokes churn & FUM outflow diagnostics`"| ctr_analytics
    ctr_analytics -->|"`Reads contribution and activity history`"| ctr_repo
    ctr_repo -->|"`Reads synthetic JSON records`"| ctr_data_store
    ctr_agent_runner -->|"`Generates candidate brief via LLM or local template`"| ext_foundry
    ctr_agent_runner -->|"`Passes candidate output for compliance audit`"| ctr_guardrail
    ctr_guardrail -->>|"`Returns validated brief with General Advice warning`"| person_staff
    ctr_eval_harness -->|"`Evaluates guardrail and agent responses against test benchmarks`"| ctr_agent_runner

    style sys_agent fill:none,stroke:#888888,stroke-dasharray:5 5,color:#888888

    classDef person fill:#08427b,stroke:#052e56,color:#ffffff
    classDef container fill:#438dd5,stroke:#2e6295,color:#ffffff
    classDef external fill:#999999,stroke:#6b6b6b,color:#ffffff

    class person_staff person
    class ctr_agent_runner,ctr_guardrail,ctr_analytics,ctr_repo,ctr_eval_harness,ctr_data_store container
    class ext_foundry external
```

---

## 4. C4 Level 3: Component Diagram

The Component diagram details the internal Python classes, models, and services inside the application container.

```mermaid
---
config:
  flowchart:
    subGraphTitleMargin:
      bottom: 30
---
flowchart TB
    subgraph bnd_models["`**Domain Models (ai_governance_harness.models)**`"]
        cmp_member_model["`**MemberProfile**
*[Pydantic Model]*
Profile demographics, balances, options`"]
        cmp_contrib_model["`**ContributionRecord**
*[Pydantic Model]*
Employer & voluntary contributions`"]
        cmp_digital_model["`**DigitalActivityRecord**
*[Pydantic Model]*
Monthly logins, app sessions`"]
        cmp_ix_model["`**InteractionRecord**
*[Pydantic Model]*
Closure inquiries, contact log`"]
    end

    subgraph bnd_services["`**Core Services & Engines**`"]
        cmp_repo["`**MemberRepository**
*[Repository Service]*
JSON loader and cohort query methods`"]
        cmp_churn["`**ChurnAnalytics**
*[Analytics Engine]*
Baseline deviation detection and attribution`"]
        cmp_fum["`**FUMDiagnostics**
*[Diagnostics Engine]*
Cohort FUM leakage sizing`"]
        cmp_guardrail["`**AdviceBoundaryGuardrail**
*[Compliance Guardrail]*
Regex and keyword rule-based filter`"]
        cmp_agent["`**AdvisoryAgent**
*[Agent Orchestrator]*
Synthesizes staff briefs`"]
        cmp_foundry["`**FoundryClient**
*[Client Module]*
Cross-tenant AIProjectClient factory (foundry_client.py)`"]
    end

    subgraph bnd_eval["`**Governance & Evaluation Suite**`"]
        cmp_eval_advice["`**AdviceBoundaryEvaluator**
*[Evaluator]*
Detects personal financial advice breaches`"]
        cmp_eval_grounding["`**GroundingEvaluator**
*[Evaluator]*
Detects hallucinations of external wealth`"]
        cmp_eval_runner["`**GovernanceTestRunner**
*[Pytest Suite]*
Automated regression tests`"]
    end

    cmp_repo --> cmp_member_model
    cmp_member_model --> cmp_contrib_model
    cmp_member_model --> cmp_digital_model
    cmp_member_model --> cmp_ix_model

    cmp_churn --> cmp_repo
    cmp_fum --> cmp_churn
    cmp_agent --> cmp_repo
    cmp_agent --> cmp_churn
    cmp_agent --> cmp_guardrail
    cmp_agent --> cmp_foundry

    cmp_eval_runner --> cmp_eval_advice
    cmp_eval_runner --> cmp_eval_grounding
    cmp_eval_runner --> cmp_agent

    style bnd_models fill:none,stroke:#888888,stroke-dasharray:5 5,color:#888888
    style bnd_services fill:none,stroke:#888888,stroke-dasharray:5 5,color:#888888
    style bnd_eval fill:none,stroke:#888888,stroke-dasharray:5 5,color:#888888

    classDef component fill:#85bbf0,stroke:#5d82a8,color:#000000
    class cmp_member_model,cmp_contrib_model,cmp_digital_model,cmp_ix_model,cmp_repo,cmp_churn,cmp_fum,cmp_guardrail,cmp_agent,cmp_foundry,cmp_eval_advice,cmp_eval_grounding,cmp_eval_runner component
```

---

## 5. Security & Trust Boundaries

Aligning with **Security Plan SEC-2026-SUPER-001**:

```mermaid
flowchart LR
    subgraph TB1["Trust Boundary 1: User Identity"]
        U[Internal Staff User] -->|Entra ID Auth| G1[Authentication Gate]
    end

    subgraph TB2["Trust Boundary 2: Agent Runtime & Core Services"]
        G1 --> A[Advisory Agent Core]
        A --> B[Deterministic Guardrails]
        A --> C[Analytics Engine]
    end

    subgraph TB3["Trust Boundary 3: Data Access Layer"]
        C --> D[MemberRepository]
        D -->|Read-only File IO| E[(Synthetic JSON File Store)]
    end

    subgraph TB4["Trust Boundary 4: External Services"]
        A -.->|TLS 1.3 / Australian Region| F[Azure AI Foundry Inference]
    end

    classDef boundary fill:#f0f7ff,stroke:#0366d6,stroke-width:2px,color:#000000
    class TB1,TB2,TB3,TB4 boundary
```

### Trust Boundary Details:

1. **User Identity Boundary:** Enforces least-privilege role-based access control (RBAC). Only authenticated staff with appropriate consultant or analyst credentials can request briefs.
2. **Agent Runtime Boundary:** All prompt templates and LLM completions pass through deterministic validation. Prompt injection patterns and system instruction overrides are blocked.
3. **Data Boundary:** Strictly synthetic data. No external financial accounts are linked. File store access is read-only.
4. **Cloud Processing Boundary:** Live inference calls to Azure AI Foundry are restricted to Australian cloud regions (Australia East / Southeast) to satisfy `CON-002` Data Sovereignty.

---

## 6. Identity Architecture (Microsoft Entra Agent ID)

The chat orchestrator is the only agent. It gets its identity from **Microsoft Entra Agent ID**, while the MCP server stays a protected resource API. Staff identity travels to the MCP boundary in validated token claims, and the shared governance policy turns those claims into allow or deny decisions. See [ADR 0008](../planning/adrs/0008-use-microsoft-entra-agent-id-for-agent-identity.md), [ADR 0009](../planning/adrs/0009-enforce-agent-and-staff-identity-through-governance-policy-context.md), and [ADR 0010](../planning/adrs/0010-use-a-local-only-mock-entra-agent-id-issuer-for-the-mvp.md).

### 6.1 Target: Azure with Entra Agent ID

One agent identity blueprint per environment holds the credential, a user-assigned managed identity federated credential. Two agent identities are created from it:

* `member-insights-interactive` acts on behalf of signed-in staff (OBO).
* `member-insights-reporting` acts as itself (app-only) and is limited to aggregate tools.

The chat service and the reporting job get tokens through the Entra SDK for AgentID sidecar. MCP validates the token claims before the AgentMesh policy engine applies the staff role matrix. Numbered edges follow one staff chat turn; dotted edges are credential, assignment, or control relationships.

![Target identity architecture on Azure with Microsoft Entra Agent ID](../images/identity-architecture-azure.png)

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

### 6.2 Local MVP: mock identity service

Entra Agent ID roles are not available for the hackathon MVP. A local-only mock, `ai-governance-identity` on port 8002, stands in for Entra and the sidecar:

* It signs tokens with an in-memory RS256 key and publishes a JWKS.
* It serves the same sidecar endpoints and mints the same claim shapes as Entra.
* Staff personas are chosen in the chat UI.

MCP verifies the signatures, and the same governance policy applies. Foundry inference uses the developer's `az login`. The mock refuses to start when hosted or in staging or production.

![Local MVP identity architecture with the mock identity service](../images/identity-architecture-local.png)

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

### 6.3 Staff Role Matrix

Every combination not listed is denied by default.

| Caller | Aggregate tools | Member-level tools | Outreach case |
|--------|-----------------|--------------------|---------------|
| Analyst (OBO) | Allow | Deny | Deny |
| Retention Specialist (OBO) | Allow | Allow | Allow, MCP elicitation still required |
| Compliance Reviewer (OBO) | Deny | Deny | Deny |
| Administrator (OBO) | Deny | Deny | Deny |
| Reporting agent (app-only) | Allow | Deny | Deny |

---

## 7. Regulatory & Compliance Architecture (ASIC RG 244)

The core compliance filter enforces the statutory boundary between General Advice and Personal Advice under Australian law:

```mermaid
flowchart TD
    Prompt[Staff Inquiry or Profile Lookup] --> CheckInput{Input Validation}
    CheckInput -->|Direct personal recommendation query| Refusal[Return Refusal: Personal Financial Advice Prohibited]
    CheckInput -->|Valid contextual lookup| Agent[Agent Synthesizes Member Context]
    Agent --> Output[Raw LLM or Template Brief]
    Output --> CheckOutput{Compliance Output Filter}
    CheckOutput -->|Contains prohibited recommendations e.g., 'You should invest in...'| Redaction[Redact & Flag Compliance Breach]
    CheckOutput -->|Factual Information & General Analysis| AppendWarning[Append Mandatory ASIC General Advice Warning]
    AppendWarning --> Deliver[Deliver Staff Brief with Talking Points]
```

---

## 8. Next Steps & Implementation Mapping

This architecture view maps directly to the active RPI implementation phases:

* **Phase P01**: `MemberProfile` data models, synthetic JSON generator, and `MemberRepository`.
* **Phase P02**: `ChurnAnalytics` and `FUMDiagnostics`.
* **Phase P03**: `AdviceBoundaryGuardrail` and `AdvisoryAgent`.
* **Phase P04**: `AdviceBoundaryEvaluator`, `GroundingEvaluator`, and automated pytest test suites.
