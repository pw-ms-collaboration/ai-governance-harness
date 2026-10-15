<!-- markdownlint-disable-file -->
# RPI Plan Critique: Right-side identity and question panel

## Metadata

* Task ID: `right-side-identity-question-panel`
* Critique date: 2026-10-15
* Plan: .copilot-tracking/plans/2026-10-15/right-side-identity-question-panel-plan.md
* Critique execution: Complete
* Critique depth: Standard
* Depth provenance: Default
* Critique type: Initial
* Earlier critique: Not applicable

## Inputs and Criterion Boundary

* Task context and caller requirements: Move mock identity and factual-question controls into a clean right-side panel and include the supplied role-capability matrix without changing enforcement.
* Research and evidence considered: .copilot-tracking/research/2026-10-15/right-side-identity-question-panel-research.md, src/ai_governance_harness/chat/static/index.html, src/ai_governance_harness/chat/static/app.css, src/ai_governance_harness/chat/static/app.js, tests/test_chat_app.py, src/ai_governance_harness/governance/policies/default.yaml, and src/ai_governance_harness/identity/constants.py.
* Decisions, dependencies, task Goals, and task Requirements considered: D1-D4, FR-001 through FR-005, NFR-001 through NFR-003, P01/P02, and P01-T01 through P02-T02.
* Assessment boundary: The supplied plan and research support assessment of markup, presentation behavior, role semantics, tests, and validation. The critique cannot decide rendered visual quality before implementation.

## Coverage Assessment

| Requirement, research, phase, or task ID | Coverage | Evidence or concern |
|------------------------------------------|----------|---------------------|
| FR-001, FR-002, FR-005, NFR-002, NFR-003 | Covered | P01-T01/P01-T02 define the layout and reflow; P02-T02 owns rendered and keyboard validation. |
| FR-003, Research C5-C6 | Partial | The role matrix is covered, but “current-role access” can inaccurately imply authorization before mock sign-in succeeds. |
| FR-004, NFR-001 | Covered | Stable selectors, reset behavior, CSP/storage constraints, and targeted regression tests are explicitly preserved. |
| P01-T01 through P02-T02 | Covered | Tasks have bounded outcomes, requirements, references, dependencies, and validation ownership. |
| Test and change boundary | Covered | Existing test file owns regressions; no removals, files, dependencies, or backend changes are permitted. |

## Verdict

* Verdict: Revise
* Rationale: The plan is otherwise credible, but it needs one direct correction so explanatory access copy cannot be mistaken for an authenticated authorization state.

## Findings

<!-- rpi:critique id=PC-001 -->
### PC-001 [Medium]: Distinguish selected-role preview from signed-in identity

* Related IDs: FR-002, FR-003, FR-004, P01-T01, P01-T03, P02-T01
* Evidence: The plan names a “current role access” summary that updates immediately on persona selection, while src/ai_governance_harness/chat/static/app.js clears the access token on change and establishes identity only after a successful sign-in response.
* Concern: A user could select a persona and see “current access” before authentication succeeds, making explanatory policy copy look like active authorization.
* Impact: The UI could misrepresent identity and governance state, undermining the panel’s factual purpose even though backend enforcement remains correct.
* Smallest useful change: Rename the pre-sign-in content to a selected-role access preview, keep `#identity-status` as the authoritative sign-in state, and require the preview to state that access is enforced only after sign-in and policy evaluation.
* Action owner: Planning parent
* Exact resolving evidence: The plan’s D1, FR-002/FR-003, P01-T01, P01-T03, and P02-T01 explicitly distinguish preview from authenticated state and test the disclaimer.
* Decision route: Direct planner correction

## Strengths and Residual Risk

* The plan correctly keeps Reporting app-only, preserves enforcement boundaries, limits changes to four existing files, and separates static regression coverage from rendered accessibility evidence.
* Residual visual-fit risk is appropriately owned by implementation-time desktop and narrow-screen validation.

## Questions or Blocking Evidence Gaps

* None.

## Limitations

* Rendered visual quality and adaptive behavior cannot be assessed until implementation.

## Recommended Next Action

* Highest-impact finding: PC-001
* Action owner: Planning parent
* Smallest next action: Apply the direct terminology and test-contract correction, then finalize without a follow-up critique because scope and architecture do not change.
* User response required: No
