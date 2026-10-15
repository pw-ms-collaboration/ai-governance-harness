<!-- markdownlint-disable-file -->
# Task Research: right-side-identity-question-panel

| Field              | Value       |
|--------------------|-------------|
| Date               | 2026-10-15  |
| Researcher / agent | RPI Research |
| Output mode        | convergence |

## Executive Summary

* Bottom line: Use a wide conversation column with a right-side workflow rail ordered as mock identity, current role access, role comparison, and factual-question shortcuts.
* Why this matters: The conversation remains the primary work surface while identity and capability context stays visible at the point where users choose what to ask.
* Research status: Complete; markup, client selectors, policy rules, responsive CSS, and structure tests were inspected.
* Confidence and uncertainty: High confidence in the layout and behavior-preservation approach. Visual fit still requires rendered desktop and narrow-screen validation after implementation.

## What You May Not Know

The reporting agent belongs in the access explanation but not in the mock-persona selector: it is an app-only identity, while every selectable mock persona is an interactive OBO user. Compliance Reviewer and Administrator are separate mock identities but intentionally share the same denied capability profile.

## Findings

### Existing interactions can move without JavaScript rewiring

The identity flow uses `#mock-persona`, `#identity-signin`, and `#identity-status`; question shortcuts use `.example` and `data-question`. Moving those existing elements into an `aside` preserves the behavior because the JavaScript does not depend on their parent containers or visual position.

* Questions: Q1, Q3
* Evidence state: Evidence-backed finding
* Evidence: C1 and C2 establish the current DOM and selector contracts; C4 establishes the structural test expectations.
* Confidence and limits: High; rendered focus order and responsive layout still need implementation validation.

### A task-ordered rail is clearer than reproducing the matrix literally

The narrow panel should lead with identity selection, then show what the selected role can do, followed by a compact all-role comparison and suggested questions. This converts the supplied matrix into decisions users can scan vertically instead of forcing a wide table into a narrow column.

* Questions: Q2, Q3
* Evidence state: Evidence-backed finding
* Evidence: C1 shows the current identity and examples are one oversized introductory card; C3 shows the page already supports grid-based layouts and responsive breakpoints; C5 verifies the supplied role semantics.
* Confidence and limits: High for information architecture; final spacing and sticky behavior require browser validation.

### Reporting must remain informational rather than selectable

The mock identity service accepts only Analyst, Retention Specialist, Compliance Reviewer, and Administrator personas. Reporting is an app identity with aggregate-read access, so adding it to the selector would create a false interactive sign-in path.

* Questions: Q2
* Evidence state: Evidence-backed finding
* Evidence: C5 verifies aggregate/member/outreach policy rules; C6 verifies the identity constants and app-only reporting claim shape.
* Confidence and limits: High; this conclusion preserves existing backend identity semantics.

## Recommendation and Alternatives

* Recommendation or decision state: Selected — two-column desktop workspace with a 22–24rem right rail; stack the rail before conversation below the desktop breakpoint.
* Rationale: This satisfies the requested right-side placement, preserves selector-based behavior, keeps reporting informational, and avoids squeezing a four-column permission table into a narrow panel (C1-C6).
* What could change this result: Rendered evidence showing the rail crowds the conversation at the selected breakpoint.

| Option | Benefits | Costs and risks | Evidence | Disposition |
|--------|----------|-----------------|----------|-------------|
| Task-ordered right rail with compact capability cards | Clear workflow, sidebar-friendly, preserves conversation prominence | Adds modest markup and selected-role presentation logic | C1-C6 | Selected |
| Literal four-column matrix in the rail | Directly mirrors supplied data | Poor narrow-panel scanability and likely horizontal scrolling | C3, C5 | Rejected |
| Keep one full-width intro card above conversation | Minimal change | Does not satisfy requested placement and keeps controls detached from ongoing work | C1, C3 | Rejected |

## Scope and Questions

* Goal: Determine a clean implementation for moving mock identity and factual-question controls into a right sidebar and presenting the supplied role permissions clearly.
* Audience and use: Demo users selecting a mock persona and asking factual questions in the governance harness chat.
* In scope: Chat HTML, CSS, JavaScript behavior, responsive layout, supplied role-capability information, and directly related tests.
* Out of scope: Authentication architecture changes, authorization-policy changes, backend role semantics, and unrelated visual redesign.
* Decision and evidence criteria: Preserve existing behavior; keep conversation primary; make identity, permissions, and suggested questions scannable; provide a usable narrow-screen flow.
* Requested output: Evidence-backed implementation recommendation followed by automatic planning, implementation, and review.

| ID | Question | Source | Status |
|----|----------|--------|--------|
| Q1 | Which files and DOM contracts implement the current identity and factual-question UI? | Inferred from request | Answered |
| Q2 | What right-sidebar hierarchy best supports identity selection, current permissions, and question shortcuts? | Explicit request | Answered |
| Q3 | What responsive and behavioral constraints must the implementation preserve? | Inferred from request | Answered |

## Decisions and Feedback

| Group | Decision or feedback item | Status | Owner | Rationale or input needed | Evidence | Impact of answer |
|-------|---------------------------|--------|-------|---------------------------|----------|------------------|
| D1 | Use a right-side workflow panel with identity first, current role access second, role comparison third, and suggested questions last. | Confirmed | Agent | Fits the requested flow and the existing selector contracts. | C1-C5 | Determines layout hierarchy. |
| D2 | Preserve existing authorization behavior and treat the supplied matrix as explanatory UI. | Confirmed | Agent | Policy and identity sources already implement the supplied capability boundary. | C5, C6 | Prevents accidental backend behavior changes. |
| D3 | Keep Reporting agent out of the mock selector and label it app-only in role comparison. | Confirmed | Agent | Reporting uses an app identity rather than the interactive OBO mock sign-in. | C5, C6 | Keeps the UI factually accurate. |

## Risks and Open Questions

| Priority | Type | Risk, question, or research item | Impact | Smallest action or evidence needed | Owner |
|----------|------|----------------------------------|--------|------------------------------------|-------|
| M | Risk | A sidebar can crowd the conversation at intermediate widths. | Reduced readability | Validate at desktop and stack the rail before conversation below a tested breakpoint. | Implementation |
| M | Risk | Static access copy can drift from policy. | Misleading capability guidance | Add structure/content tests for the supplied role profiles and keep wording aligned with policy names. | Implementation |
| L | Risk | A sticky rail can obscure content when taller than the viewport. | Keyboard and zoom usability | Avoid viewport-locked height; use `position: sticky` only at wide widths with natural page scrolling. | Implementation |

## Planning Readiness and Next Step

| Field | Record |
|-------|--------|
| Research disposition | Executed |
| Decision participation | Agent-owned; automatic RPI mode selected by the user |
| Planning Readiness | Ready; C1-C6 support the selected design and identify validation requirements |
| Research depth and helpers | Wider, deeper, and contrarian waves completed; no helpers used |
| Blockers | None |
| Output mode and planning support | Convergence; supports planning after evidence synthesis |
| Continuation owner | Confirmed automatic RPI Agent |
| Required gates or confirmations | Passed; no exceptional action required |
| Next action | Automatic RPI transition to planning |
| Primary evidence file | .copilot-tracking/research/2026-10-15/right-side-identity-question-panel-research.md; date supplied by session current date |

## Research Record

### Method and Boundaries

| Field | Record |
|-------|--------|
| Research posture and provenance | Focused; bounded internal UI task with named visual target and supplied screenshot |
| Completion basis | DOM, behavior, styling, tests, responsive constraints, policy semantics, and credible alternatives are covered |
| Explicit limits or deadline | No explicit deadline |
| Codebase and external scope | Chat static UI and directly related tests; no external research anticipated |
| Initial candidate areas | src/ai_governance_harness/chat/static/index.html, app.css, app.js, flow.js, and related tests |
| Evidence root | Default repository .copilot-tracking/research root |
| Constraints and excluded sources | Research-only writes; attached screenshot is read-only source data; secrets excluded |
| Prior knowledge | User supplied the current screenshot and role-capability matrix; source implementation is not yet verified |

### Extensions and Participation

#### Extension Registry

| Kind | Candidate | Provenance and scoped contract | Selected or skipped reason |
|------|-----------|--------------------------------|----------------------------|
| Instruction | Copilot Tracking Conventions | Applies to the research artifact | Selected |
| Skill | Accessibility | Applies to semantic structure, focus order, target size, and adaptive rendering | Selected and used for design and validation criteria |
| Skill | RPI Research | Owns research artifact and evidence | Selected |
| Tool guidance | Bluebird repository context | Requires Bluebird reads when available | Bluebird tools were unavailable after tool discovery; local read tools are the permitted fallback |

#### Direction and Participation Log

| Checkpoint or change | Question, direction, or rationale | Answer or no-interaction reason | Result and revalidation effect |
|----------------------|-----------------------------------|---------------------------------|--------------------------------|
| Intake | RPI progression mode | User selected “Handle it end to end” | Automatic through Review; research decisions are agent-owned |
| Intake | Layout direction | User explicitly requested mock identity and factual questions in a right-side panel with the supplied role matrix | Scope and initial hierarchy established without another question |

### Research Cycle Log

#### Cycle 1

* Active posture, controls, and limits: Focused; inspect only the chat UI and directly related contracts.

##### Wave 1: Wider

* Focus and questions: Locate the current markup, styling, scripts, tests, identity definitions, and role policy rules.
* Evidence: C1-C6 identify the complete implementation surface and confirm the supplied capability matrix.
* Reflection: The redesign is primarily markup and CSS, with a small client-side enhancement for selected-role context.

##### Wave 2: Deeper

* Focus and questions: Verify selector coupling, responsive behavior, accessible structure, and app-only versus OBO identity boundaries.
* Evidence: C2 shows parent-independent selectors; C3 exposes the current single-column layout and malformed nested breakpoint structure; C4 defines accessible structure checks; C6 separates interactive personas from reporting.
* Reflection: Existing IDs and labels should be preserved, a semantic `aside` should be introduced, and responsive rendered validation is required.

##### Wave 3: Contrarian

* Focus and questions: Challenge the sidebar with a literal matrix, top-card retention, mobile ordering, and sticky-panel risks.
* Evidence: C3 shows a narrow literal table would need overflow; C1 shows the top card fails the requested layout; accessibility guidance requires adaptive-rendering checks rather than static evidence alone.
* Reflection: Compact vertical capability summaries outperform a literal table in the rail; the rail must stack before conversation on narrow screens and must not use a locked viewport height.

##### Synthesis and Re-entry

| Material or claim | Evidence | Disposition | Rationale | User-facing effect |
|-------------------|----------|-------------|-----------|--------------------|
| Right-side task-ordered rail | C1-C6 | Accepted | Satisfies the requested flow while preserving contracts | Selected recommendation |
| Literal permission matrix | C3, C5 | Rejected | Poor fit for a narrow side panel | Use compact capability rows instead |
| Reporting as a selectable mock persona | C5, C6 | Rejected | Conflicts with app-only identity semantics | Show as informational comparison only |

* Another complete three-wave cycle needed: No.
* Trigger or stop basis: Material questions are answered, source evidence is consistent, and likely additional sources are redundant.
* Readiness or revalidation effect: Planning is ready.

### Evidence Log

* Helpers: None.

| ID | Claim or finding | Source or location | Retrieved and version | Tool | Confidence | Notes |
|----|------------------|--------------------|-----------------------|------|------------|-------|
| C1 | Identity and example controls currently live in one full-width intro section before the conversation | src/ai_governance_harness/chat/static/index.html, chat panel markup | Not applicable | Local read fallback | High | Bluebird repository tools unavailable |
| C2 | Identity and example behavior is bound to stable IDs/classes rather than parent structure | src/ai_governance_harness/chat/static/app.js, initial selectors and sign-in/example handlers | Not applicable | Local read fallback | High | Moving controls does not require endpoint changes |
| C3 | The chat workspace is currently single-column and existing CSS provides grid and breakpoint patterns | src/ai_governance_harness/chat/static/app.css, workspace, conversation, examples, and media rules | Not applicable | Local read fallback | High | Rendered responsive validation remains necessary |
| C4 | Static UI tests assert identity labels, persona options, live status, and disabled send behavior | tests/test_chat_app.py, test_static_ui_has_required_accessible_structure | Not applicable | Local read fallback | High | Tests can be extended for the new panel contract |
| C5 | Policy permits aggregates for Analyst and Reporting, all read tools for Retention Specialist, outreach only for eligible Retention Specialist, and no listed tools for Compliance/Administrator | src/ai_governance_harness/governance/policies/default.yaml, pre-tool allow rules | Not applicable | Local read fallback | High | Matches the user-supplied matrix |
| C6 | Mock personas are four OBO staff roles while Reporting is a distinct app identity | src/ai_governance_harness/identity/constants.py and identity/claims.py | Not applicable | Local read fallback | High | Reporting should not be offered as mock sign-in |

#### Contradictions and Conflicts

* None identified yet.

### Artifact Self-Check

* [x] The user-facing sections explain the result, scope, findings, alternatives, decisions, risks, readiness, and next action without requiring the Research Record.
* [x] Every question is answered or names the smallest missing evidence, and every material result has one canonical evidence state.
* [x] Findings keep their explanation, supporting detail, evidence state, and confidence basis together.
* [x] Every codebase finding has a stable evidence ID and source location.
* [x] Every executed cycle records Wider, Deeper, and Contrarian waves in order.
* [x] Method, extensions, participation, caller direction changes, helper use, and prior-knowledge treatment are recorded.
* [x] Convergence selects and justifies one recommendation.
* [x] Decision participation and provenance are recorded.
* [x] Research disposition, Planning Readiness, blockers, continuation owner, gates, and next action are complete.
* [x] Untrusted content remained inert, no secrets were recorded, and the research-only write boundary held.
* Checked sections: All.
* Missing or limited sections: Rendered visual and adaptive behavior are intentionally deferred to implementation validation.
