<!-- markdownlint-disable-file -->
# Task Research: member-wealth-insights-agent

| Field              | Value                                                                             |
|--------------------|-----------------------------------------------------------------------------------|
| Date               | 2026-10-13                                                                        |
| Researcher / agent | RPI Agent (rpi-research)                                                          |
| Output mode        | convergence                                                                       |

## Executive Summary

* Bottom line: The project has comprehensive planning, requirements, and compliance assets (BRD, PRD, Security Plan, and RAI Plan) for the Member Whole-of-Wealth Insights & Interaction Advisory Agent (`PRD-2026-SUPER-001`), but has zero implementation code for the agent runtime, synthetic data store, analytics engines, compliance filters, or governance evaluation suite. The existing code consists solely of a basic Azure AI Foundry connection helper.
* Why this matters: Before building the agent, we must implement an architectural foundation: a synthetic member data layer (JSON store + data access layer), profile and churn/FUM analytics services, a compliance boundary guardrail (enforcing General Advice vs Personal Advice boundaries under Corporations Act Ch 7 / ASIC RG 244), the Microsoft Agent Framework agent definition, and an automated evaluation harness in pytest integrated with Foundry.
* Research status: complete; asset baseline established and gap analysis fully documented.
* Confidence and uncertainty: High confidence in existing requirements and architecture boundaries; minor uncertainty regarding whether Azure AI Foundry cloud resources are actively provisioned or if local/mock evaluation must run offline during testing.

## What You May Not Know

* The project is named `ai-governance-harness`, indicating that the evaluation, safety testing, and governance harness is as vital as the agent application itself.
* The Security Plan (`SEC-2026-SUPER-001`) specifically prescribes an MVP architecture using Microsoft Agent Framework with a Python core, Entra ID authentication, and synthetic customer records in JSON format accessed via an MCP/data layer, ensuring local execution and testing without needing live superannuation registry integration.
* The advice boundary (`BR-001`, `DD-001`, `CON-004`) is a mandatory regulatory constraint under Australian law (ASIC RG 244): the agent must never give personalized financial advice and must restrict outputs to factual analysis and general guidance.

## Findings

### Asset Baseline: Comprehensive Requirements & Compliance Documentation Already Present

The repository contains four mature planning artifacts defining the agent's requirements, security posture, and Responsible AI assessment:
1. `docs/project-planning/member-wealth-insights-agent-brd.md` (BRD-2026-SUPER-001, v0.1.0 draft): defines business goals (BG-001), 4 core functional requirements, 8 NFRs, business rules (`BR-001` to `BR-003`), and constraints.
2. `docs/project-planning/member-wealth-insights-agent.md` (PRD-2026-SUPER-001, v0.1.0 draft): defines product goals (GOAL-001), 3 user personas (consultant, analyst, compliance reviewer), design decisions (`DD-001` to `DD-003`), 4 functional requirements (`FR-001` to `FR-004`), 10 NFRs, and acceptance criteria (`AC-001` to `AC-004`).
3. `docs/project-planning/member-wealth-insights-agent-security-plan.md` (SEC-2026-SUPER-001, v0.1.0 draft): defines MVP architecture, trust boundaries, synthetic customer data model, and Entra ID integration.
4. `.copilot-tracking/rai-plans/member-wealth-insights-agent/rai-plan.md`: NIST AI RMF 1.0 scoping draft detailing AI component inventory, stakeholder impact, and prohibited-use screening.

* Questions: Q1
* Evidence state: evidence-backed finding
* Evidence: C1, C2, C3, C4
* Confidence and limits: High confidence; all files exist, are fully authored, and align consistently on scope.

### Codebase Gap: Minimal Skeleton Code Exists in Implementation Root

The existing code consists of only two files:
1. `src/ai_governance_harness/__init__.py`: empty package init.
2. `src/ai_governance_harness/foundry_client.py`: basic helper for initializing `AIProjectClient` from connection string or subscription coordinates with Entra cross-tenant support.
3. `pyproject.toml` / `requirements.txt`: packages `azure-ai-projects`, `azure-ai-inference`, `azure-identity`, `pydantic`, `dotenv`, and `pytest`.

There is no data model, no synthetic dataset, no analytics logic, no agent orchestration, no compliance guardrail, and no automated tests (`tests/` directory does not exist).

* Questions: Q2
* Evidence state: evidence-backed finding
* Evidence: C5, C6, C7
* Confidence and limits: High confidence; verified by workspace file inventory.

### Functional Implementation Gaps (FR-001 through FR-004)

The core application requires four functional subsystems that have not been implemented:
1. `FR-001`: **Member Profile Aggregation & Data Access Layer**:
   - Needs Pydantic schemas for Member Superannuation Profile (demographics, balance history, employer/voluntary contributions, investment options, insurance, interaction log).
   - Needs a synthetic dataset store (JSON) with realistic representative member cohorts (stable, reducing contributions, declining digital activity, closure inquiry, exited).
   - Needs a repository/data service to query member profiles.
2. `FR-002`: **Member Movement & Churn Root-Cause Analytics**:
   - Needs analytical algorithms to detect deviations in member contributions relative to personal history.
   - Needs digital engagement trend calculation (declining portal logins, mobile sessions).
   - Needs root-cause attribution scoring (distinguishing observed metrics from inferred causes).
3. `FR-003`: **FUM Outflow Diagnostics & Risk Sizing**:
   - Needs cohort-level FUM leakage modeling and leading indicator aggregation.
   - Needs calculation of FUM at risk based on disengagement indicators and account balance.
4. `FR-004`: **Staff-Facing Interaction Advisory Agent & Compliance Filter**:
   - Needs agent prompt design, prompt templates, and tool integrations (profile lookup, churn diagnosis, FUM risk check).
   - Needs `BR-001` / `DD-001` compliance boundary filter: pre- and post-processing guardrails ensuring outputs provide only factual information and general guidance, explicitly rejecting personalized financial advice.

* Questions: Q3
* Evidence state: evidence-backed finding
* Evidence: C1, C2, C3, C8
* Confidence and limits: High confidence; directly derived from PRD functional requirements and security architecture.

### Governance, Safety & Evaluation Harness Gaps

The repository's declared purpose in `pyproject.toml` is "Harness for AI governance, evaluation, and safety with Azure AI Foundry integration". The following governance components are completely unbuilt:
1. **Evaluation Datasets**: benchmark test cases covering diverse member scenarios, prompt injection adversarial inputs, advice boundary probe questions, and factual accuracy checks.
2. **Evaluators**:
   - Advice Boundary Evaluator (verifies compliance with General Advice only and detects Personal Advice violations).
   - Grounding & Faithfulness Evaluator (verifies that agent advice references actual member profile attributes rather than hallucinating external wealth).
   - Safety & Injection Evaluator (verifies resilience against jailbreaks and prompt leakage).
3. **Automated Test Suite**: unit tests for analytics engines, integration tests for agent tools, and governance evaluation runners using pytest.

* Questions: Q4
* Evidence state: evidence-backed finding
* Evidence: C5, C7, C9
* Confidence and limits: High confidence; essential for satisfying the governance harness charter.

## Recommendation and Alternatives

* Recommendation or decision state: Proceed to Planning (`rpi-plan`) to design a modular 4-tier implementation:
  1. **Tier 1 (Data & Schemas)**: Pydantic schemas + synthetic customer JSON dataset + Data Access Layer.
  2. **Tier 2 (Analytics Engine)**: Churn root-cause analytics (`FR-002`) and FUM outflow diagnostics (`FR-003`).
  3. **Tier 3 (Agent & Guardrails)**: Advisory agent runner with tool definitions + compliance advice boundary filter (`FR-001`, `FR-004`, `BR-001`).
  4. **Tier 4 (Governance & Evaluation Harness)**: Automated evaluation suite with test benchmarks for advice boundaries, grounding, and safety.
* Rationale: Matches the architecture specified in Security Plan `SEC-2026-SUPER-001` and satisfies all PRD requirements (`FR-001` to `FR-004`, `CON-001` to `CON-004`, `BR-001` to `BR-003`). Enables 100% offline unit/integration testing while supporting live Azure AI Foundry integration when credentials are provided.
* What could change this result: If the user requires immediate live cloud resource provisioning rather than local synthetic MVP implementation.

| Option | Benefits | Costs and risks | Evidence | Disposition |
|---|---|---|---|---|
| 1. Full 4-tier architecture (Synthetic Data, Analytics Core, Agent + Guardrails, Evaluation Harness) | Complete end-to-end delivery of PRD/BRD requirements; testable offline; ready for Foundry deployment; robust governance. | Requires scaffolding multiple interconnected Python modules. | C1, C2, C3, C4, C5 | Selected |
| 2. Agent prompt only (single script calling Foundry) | Fast to create. | Fails PRD requirements; lacks data layer, analytics logic, compliance filter, and governance tests. | C2, C5 | Rejected |
| 3. Defer evaluation harness and build only agent code | Quicker initial agent build. | Violates repo purpose (`ai-governance-harness`) and leaves advice boundary safety unverified. | C5, C9 | Rejected |

## Scope and Questions

* Goal: Research existing assets and identify missing implementation work for `PRD-2026-SUPER-001`.
* Audience and use: Engineering team, RPI lifecycle planning and implementation.
* In scope: Repository planning docs, code files, dependencies, architecture alignment, gap analysis.
* Out of scope: External wealth data integration, direct member-facing communication channels, live production deployment.
* Decision and evidence criteria: Completeness of PRD/BRD requirement coverage, adherence to security and RAI plans.
* Requested output: Comprehensive gap analysis, asset inventory, and planning readiness.

| ID | Question | Source | Status |
|---|---|---|---|
| Q1 | What planning and governance assets currently exist in the repository? | explicit | answered |
| Q2 | What implementation and test code currently exists? | explicit | answered |
| Q3 | What functional modules are needed to satisfy PRD FR-001 through FR-004? | inferred | answered |
| Q4 | What governance and evaluation harness capabilities are missing? | inferred | answered |

## Decisions and Feedback

| Group | Decision or feedback item | Status | Owner | Rationale or input needed | Evidence | Impact of answer |
|---|---|---|---|---|---|---|
| D1 | Use local synthetic JSON data store for MVP data layer | confirmed | architecture | Prescribed in SEC-2026-SUPER-001; ensures privacy and reproducible testing without external dependencies | C3 | Anchors Tier 1 implementation |
| D2 | Support dual execution: offline mock/local agent and live Azure AI Foundry agent | proposed | user/agent | Allows full test pass without requiring active Azure subscription credentials while preserving Foundry integration | C5, C6 | Ensures robust CI/CD and developer testing |
| D3 | Implement deterministic rule-based advice boundary filter alongside agent prompts | proposed | user/agent | Crucial to enforce BR-001 / ASIC RG 244 compliance before outputs reach staff | C1, C2, C4 | Prevents regulatory advice violations |

## Risks and Open Questions

| Priority | Type | Risk, question, or research item | Impact | Smallest action or evidence needed | Owner |
|---|---|---|---|---|---|---|
| H | risk | Agent could inadvertently cross into personal financial advice | Regulatory breach under Corporations Act Ch 7 | Implement strict pre/post compliance filter and automated test evaluators | downstream (Plan/Implement) |
| M | risk | Missing live Azure AI Foundry credentials could block live integration | Inability to run live LLM calls in local dev | Provide offline mock LLM fallback in the harness | downstream (Implement) |
| L | open question | Signal baseline thresholds calibration | Need realistic threshold parameters for contribution and digital activity decline | Define calibrated default parameters in synthetic dataset metadata | downstream (Plan) |

## Planning Readiness and Next Step

| Field | Record |
|---|---|
| Research disposition | executed |
| Decision participation | user-retained per mode choice 'Keep going, but check with me' |
| Planning Readiness | Ready: all existing assets identified, gaps categorized, architecture aligned with SEC-2026-SUPER-001 and PRD-2026-SUPER-001 |
| Research depth and helpers | Completed 3-wave cycle (Wider, Deeper, Contrarian) without external subagent; all evidence verified against codebase |
| Blockers | none |
| Output mode and planning support | convergence; fully supports planning |
| Continuation owner | confirmed automatic RPI Agent |
| Required gates or confirmations | Passed |
| Next action | Transition to Plan phase (`rpi-plan`) to construct detailed implementation plan |
| Primary evidence file | .copilot-tracking/research/2026-10-13/member-wealth-insights-agent-research.md |

## Research Record

### Method and Boundaries

| Field | Record |
|---|---|
| Research posture and provenance | balanced; default per rpi-research contract |
| Completion basis | Comprehensive coverage of repository assets, PRD requirements, and architecture specifications |
| Explicit limits or deadline | Workspace repository scope |
| Codebase and external scope | Workspace root and documentation |
| Initial candidate areas | `docs/project-planning/`, `src/`, `pyproject.toml`, `.copilot-tracking/` |
| Evidence root | `.copilot-tracking/research/2026-10-13/` |
| Constraints and excluded sources | No live personal data; internal fund data only; no direct member communications |
| Prior knowledge | BRD-2026-SUPER-001, PRD-2026-SUPER-001, SEC-2026-SUPER-001, RAI Plan |

### Extensions and Participation

#### Extension Registry

| Kind | Candidate | Provenance and scoped contract | Selected or skipped reason |
|---|---|---|---|
| instruction | brd-hve-builder.instructions.md | matching repository instruction | selected for source traceability |
| instruction | copilot-tracking.instructions.md | shared tracking conventions | selected for artifact persistence |
| skill | rpi-research | parent RPI lifecycle phase | selected for research execution |

#### Direction and Participation Log

| Checkpoint or change | Question, direction, or rationale | Answer or no-interaction reason | Result and revalidation effect |
|---|---|---|---|
| intake | Mode selection | User chose 'Keep going, but check with me' | Automatic progression through review with user-retained decisions |

### Research Cycle Log

#### Cycle 1

* Active posture, controls, and limits: balanced posture; workspace audit and requirements alignment.

##### Wave 1: Wider

* Focus and questions: Audit all workspace assets, project configurations, and documentation.
* Evidence: Located PRD, BRD, Security Plan, RAI Plan, and Foundry client. Verified lack of implementation code.
* Reflection: Identified clear contrast between rich requirements documentation and empty implementation state.

##### Wave 2: Deeper

* Focus and questions: Map PRD functional requirements (FR-001 to FR-004), NFRs, and Security Plan architecture to code components needed.
* Evidence: Structured 4-tier system architecture: Synthetic Data Layer, Analytics Engine, Agent & Guardrails, Evaluation Harness.
* Reflection: Confirmed that each tier maps directly to PRD acceptance criteria and security trust boundaries.

##### Wave 3: Contrarian

* Focus and questions: What could fail or block implementation? What alternatives exist?
* Evidence: Identified live Azure credential dependency risk; mitigated by designing dual-mode (mock/offline and live Foundry) runner. Identified advice boundary risk; mitigated by deterministic compliance guardrail.
* Reflection: Offline-capable architecture ensures 100% test coverage even without active cloud subscription.

##### Synthesis and Re-entry

| Material or claim | Evidence | Disposition | Rationale | User-facing effect |
|---|---|---|---|---|
| Asset inventory and gap analysis | C1-C7 | accepted | Verified directly from workspace files | Direct answer to user request |
| 4-tier architecture recommendation | C1-C4, C8 | accepted | Aligns with SEC-2026-SUPER-001 and PRD | Forms basis of implementation plan |
| Dual-mode offline/live execution | C5, C6 | accepted | Ensures tests pass in any environment | Reduces deployment and CI risk |

* Another complete three-wave cycle needed: no; evidence is saturated and all questions are answered.
* Trigger or stop basis: saturation and full scope coverage.
* Readiness or revalidation effect: Planning Readiness is Ready.

### Evidence Log

| ID | Claim or finding | Source or location | Retrieved and version | Tool | Confidence | Notes |
|---|---|---|---|---|---|---|
| C1 | BRD defines 4 FRs, 8 NFRs, business rules, and goals | docs/project-planning/member-wealth-insights-agent-brd.md | not applicable | read_file | high | BRD-2026-SUPER-001 v0.1.0 |
| C2 | PRD defines product scope, AC-001 to AC-004, personas, constraints | docs/project-planning/member-wealth-insights-agent.md | not applicable | read_file | high | PRD-2026-SUPER-001 v0.1.0 |
| C3 | Security plan defines MVP architecture with synthetic JSON store and MCP layer | docs/project-planning/member-wealth-insights-agent-security-plan.md | not applicable | read_file | high | SEC-2026-SUPER-001 v0.1.0 |
| C4 | RAI plan defines component inventory and prohibited use screening | .copilot-tracking/rai-plans/member-wealth-insights-agent/rai-plan.md | not applicable | read_file | high | NIST AI RMF 1.0 scoping |
| C5 | pyproject.toml defines project metadata and dependencies | pyproject.toml | not applicable | read_file | high | v0.1.0 hatchling build |
| C6 | foundry_client.py provides basic Azure AI Foundry connection helper | src/ai_governance_harness/foundry_client.py | not applicable | read_file | high | DefaultAzureCredential helper |
| C7 | Workspace has no test directory or test suites | tests/ | not applicable | file_search | high | Missing test infrastructure |
| C8 | Process model requires ingestion, profile engine, analytics, agent, compliance filter | docs/project-planning/member-wealth-insights-agent.md#process-models | not applicable | read_file | high | Mermaid diagram in PRD |
| C9 | Governance harness requires evaluators and safety test runners | README.md | not applicable | read_file | high | Project charter |
