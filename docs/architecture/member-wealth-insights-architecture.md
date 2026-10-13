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

## 6. Regulatory & Compliance Architecture (ASIC RG 244)

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

## 7. Next Steps & Implementation Mapping

This architecture view maps directly to the active RPI implementation phases:

* **Phase P01**: `MemberProfile` data models, synthetic JSON generator, and `MemberRepository`.
* **Phase P02**: `ChurnAnalytics` and `FUMDiagnostics`.
* **Phase P03**: `AdviceBoundaryGuardrail` and `AdvisoryAgent`.
* **Phase P04**: `AdviceBoundaryEvaluator`, `GroundingEvaluator`, and automated pytest test suites.
