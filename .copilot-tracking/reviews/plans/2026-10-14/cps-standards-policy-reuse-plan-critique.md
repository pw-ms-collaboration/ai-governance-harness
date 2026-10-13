<!-- markdownlint-disable-file -->
# RPI Plan Critique: CPS 234 policy reuse pilot

## Metadata

* Task ID: cps-standards-policy-reuse
* Critique date: 2026-10-14
* Plan: .copilot-tracking/plans/2026-10-14/cps-standards-policy-reuse-plan.md
* Critique execution: Complete
* Critique depth: Standard
* Depth provenance: Default
* Critique type: Initial
* Earlier critique: Not applicable

## Inputs and Criterion Boundary

* Task context and caller requirements: Research and plan a CPS 234 pilot without implementation, using separate source, control-profile, and runtime-enforcement layers and stopping before Implementation.
* Research and evidence considered: .copilot-tracking/research/2026-10-14/cps-standards-policy-reuse-research.md; CPS 234 CSV; default policy; governance adapter, context, evidence profile, tests, README, BRD, and ADRs named by the plan.
* Decisions, dependencies, task Goals, and task Requirements considered: Confirmed CPS 234 pilot scope, deferred CPS 230 extension, FR-001 through FR-006, NFR-001 through NFR-005, P01 through P03, and P01-T01 through P03-T02.
* Assessment boundary: Implementation credibility, requirement coverage, dependencies, validation ownership, source-to-control traceability, and overclaim prevention. The critique cannot determine legal applicability or source authority.

## Coverage Assessment

| Requirement, research, phase, or task ID | Coverage | Evidence or concern |
|------------------------------------------|----------|---------------------|
| FR-001, FR-002, NFR-001, NFR-002, NFR-005, P01-T01 | Partial | The model fields are bounded, but the repository-reference contract that FR-004 later validates is not defined. |
| FR-003, NFR-004, P01-T02 | Partial | The plan alternates between every substantive clause and every non-empty `Item-*`, leaving the exact coverage denominator unclear. |
| FR-004, FR-005, P02-T01, P02-T02 | Partial | Validation outcomes are strong, but canonical reference syntax and generated-target ownership are not locked. |
| NFR-003, P03-T01 | Covered | Existing semantic tests, strict policy lint, no removals, and no runtime semantic change by default provide a credible regression boundary. |
| FR-006, P03-T02 | Covered | The documentation task names the layer model, approval boundary, source refresh, derived controls, and future CPS 230 work. |
| P01-P03 sequencing and dependencies | Covered | Contract, profile, cross-layer validation, tests, and guidance are ordered coherently. |

## Verdict

* Verdict: Revise
* Rationale: The architecture and validation strategy are credible, but two contract ambiguities would force implementers to invent behavior that determines traceability completeness and reference validation.

## Findings

<!-- rpi:critique id=PC-001 -->
### PC-001 [Medium]: Cross-layer reference syntax is not contractual

* Related IDs: FR-004, FR-005, P01-T01, P02-T01, P02-T02
* Evidence: .copilot-tracking/plans/2026-10-14/cps-standards-policy-reuse-plan.md
* Concern: The plan requires references to runtime rules, repository symbols, paths, and assurance evidence, but does not define how those reference types are encoded or what resolution means.
* Impact: Two implementations could both claim compliance with the plan while validating different things, and unsafe or stale symbol references could pass.
* Smallest useful change: Add a compact contractual reference shape with explicit kinds, repository-relative path rules, optional symbol or record ID fields, and kind-specific resolution behavior.
* Action owner: Planning parent
* Exact resolving evidence: P01-T01 and P02-T02 contain one reference contract used by FR-004 and the test matrix includes each reference kind.
* Decision route: Direct planner correction

<!-- rpi:critique id=PC-002 -->
### PC-002 [Medium]: CPS 234 coverage denominator is ambiguous

* Related IDs: FR-003, NFR-004, P01-T02, P02-T02, P03-T01
* Evidence: .copilot-tracking/plans/2026-10-14/cps-standards-policy-reuse-plan.md and src/ai_governance_harness/governance/policies/CPS_Standards/cps_234_information_security _2026-10-14.csv
* Concern: The plan uses both "substantive clause" and "every non-empty `Item-*`". The source also contains `Item-a`, an objective fragment, heading rows, parent clauses, and child clauses.
* Impact: The 100 percent coverage requirement has no reproducible denominator, so completion could omit child clauses or incorrectly treat determination metadata as a control obligation.
* Smallest useful change: Define the pilot denominator as all clause fragments from `Item-13` through `Item-36`, including lettered children; classify `Item-a`, objective text, and heading rows as catalogued source context outside the control denominator.
* Action owner: Planning parent
* Exact resolving evidence: FR-003, NFR-004, P01-T02, P02-T02, and P03-T01 use the same explicit denominator and test it.
* Decision route: Direct planner correction

## Strengths and Residual Risk

* The plan credibly separates source, interpretation, implementation, evidence, and approval.
* No runtime semantic change by default, exact removals of none, bounded additions, and explicit regression ownership substantially reduce pilot risk.
* Legal applicability and source authority remain appropriate human-owned residual risks rather than technical assertions.

## Questions or Blocking Evidence Gaps

* None. Both findings are direct planner corrections and do not require a user decision or new research.

## Limitations

* The critique did not independently validate APRA source authority, legal applicability, or Toolkit expression capabilities because those are outside the supplied implementation boundary.

## Recommended Next Action

* Highest-impact finding: PC-001
* Action owner: Planning parent
* Smallest next action: Add the cross-layer reference contract and align the clause coverage denominator throughout the plan.
* User response required: No
