<!-- markdownlint-disable-file -->
# RPI Plan Critique: Member Whole-of-Wealth Insights & Interaction Advisory Agent

## Metadata

* Task ID: PRD-2026-SUPER-001
* Critique date: 2026-10-13
* Plan: .copilot-tracking/plans/2026-10-13/member-wealth-insights-agent-plan.md
* Critique execution: Complete
* Critique depth: standard
* Depth provenance: default
* Critique type: initial
* Earlier critique: not_applicable

## Inputs and Criterion Boundary

* Task context and caller requirements: Assess existing workspace assets (BRD, PRD, Security Plan, RAI Plan) and implement missing components for Member Whole-of-Wealth Insights Agent and AI Governance Harness.
* Research and evidence considered: `.copilot-tracking/research/2026-10-13/member-wealth-insights-agent-research.md`, `docs/project-planning/member-wealth-insights-agent-brd.md`, `docs/project-planning/member-wealth-insights-agent.md`, `docs/project-planning/member-wealth-insights-agent-security-plan.md`, `.copilot-tracking/rai-plans/member-wealth-insights-agent/rai-plan.md`, `pyproject.toml`, `src/ai_governance_harness/foundry_client.py`.
* Decisions, dependencies, task Goals, and task Requirements considered: 4-tier architecture (Synthetic Data, Analytics Engine, Advisory Agent & Guardrails, Evaluation Harness), offline and live dual execution, ASIC RG 244 advice boundary enforcement.
* Assessment boundary: Workspace repository implementation and testing. Does not evaluate cloud infrastructure provisioning or live superannuation registry integration.

## Coverage Assessment

| Requirement, research, phase, or task ID | Coverage | Evidence or concern |
|---|---|---|
| FR-001 (Profile Aggregation) | Covered | Handled in P01-T01 (Pydantic models), P01-T02 (synthetic dataset), and P01-T03 (repository). |
| FR-002 (Movement & Churn Analytics) | Covered | Handled in P02-T01 with explicit baseline deviation algorithms and observation vs inference distinction. |
| FR-003 (FUM Outflow Diagnostics) | Covered | Handled in P02-T02 with cohort leakage breakdown and risk sizing models. |
| FR-004 (Interaction Advisory Agent) | Covered | Handled in P03-T02 with talking points generator and context synthesis for staff. |
| BR-001 / DD-001 (Advice Boundary) | Covered | Handled in P03-T01 with deterministic rule-based pre/post filters enforcing General Advice only. |
| CON-001 / CON-004 (Australian Regulation & Scope) | Covered | Enforced by compliance guardrail and staff-only co-pilot boundary. |
| CON-003 / SEC-2026-SUPER-001 (Data Minimisation) | Covered | Enforced by local synthetic JSON data store with no real PII. |
| NFR-001 to NFR-007 (Performance, Explainability, Governance) | Covered | Model explainability built into analytics schemas; governance evaluators in P04. |
| Evaluation & Governance Harness Charter | Covered | Handled in P04-T01 (benchmarks) and P04-T02 (custom evaluators and pytest suite). |

## Verdict

* Verdict: Pass
* Rationale: The plan addresses all 4 core PRD functional requirements, regulatory constraints, and security plan specifications. The 4 phases are sequenced logically with explicit dependencies, contracts, and testable acceptance criteria. Dual-mode execution ensures tests run deterministically offline while remaining integrated with Azure AI Foundry.

## Findings

* No blocking findings identified. The plan is complete and implementation-ready.

## Strengths and Residual Risk

* **Strengths:**
  1. Clear separation of concerns across 4 tiers: data, analytics, agent/guardrail, evaluation.
  2. Contractual Pydantic schemas specified up front for member profiles, churn assessments, and FUM reports.
  3. Strict, deterministic compliance filter to enforce ASIC RG 244 advice boundaries independently of LLM non-determinism.
  4. 100% offline testability via local synthetic JSON fixture and mock LLM, while keeping Foundry client integration functional.
* **Residual Risk:**
  1. Synthetic data generator must generate sufficiently varied edge cases (closure inquiry only, contribution reduction >20%, digital inactivity) to exercise all branches of Churn and FUM analytics. Accepted; task P01-T02 explicitly includes these cohort requirements.

## Questions or Blocking Evidence Gaps

* None.

## Limitations

* Assessment does not cover live production data access or external registry APIs, which are explicitly out of scope for this MVP per PRD `CON-003` and Security Plan `SEC-2026-SUPER-001`.

## Recommended Next Action

* Highest-impact finding: None
* Action owner: confirmed automatic RPI Agent
* Smallest next action: Transition to Implementation phase (`rpi-implement`)
* User response required: No
