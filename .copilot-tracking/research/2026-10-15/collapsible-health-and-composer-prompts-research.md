<!-- markdownlint-disable-file -->
# Task Research: collapsible-health-and-composer-prompts

| Field | Value |
|-------|-------|
| Date | 2026-10-15 |
| Researcher / agent | RPI Research |
| Output mode | Convergence |

## Executive Summary

* Bottom line: Reuse the existing native Observability disclosure pattern for System health and move the existing `.example` group intact into the chat form immediately above the message label.
* Why this matters: Both refinements match current repository behavior, require no new interaction model, and reduce visual distance between prompt ideas and message composition.
* Research status: Complete through reuse of verified parent Review evidence.
* Confidence and uncertainty: High; final chip spacing and disclosure defaults require rendered validation.

## What You May Not Know

The existing prompt handlers are location-independent: they query `.example`, copy `data-question` into `#chat-input`, update the counter, and focus the input. System health IDs are also independent of their parent container, so a semantic wrapper change does not affect runtime rendering.

## Findings

### Native details is the consistent health disclosure

System health should use `<details>` and `<summary>` because adjacent Observability sections already use that keyboard-accessible pattern. Existing runtime IDs can remain unchanged inside the disclosure.

* Questions: Q1
* Evidence state: Evidence-backed finding
* Evidence: C1 and C2.
* Confidence and limits: High; default open/closed state is a presentation choice resolved from the user’s “collapsible like others” direction.

### Prompt ideas can move without behavior changes

The three `.example` buttons can move directly above the textbox inside `#chat-form`. Their event handlers do not depend on the right rail or current parent section.

* Questions: Q2
* Evidence state: Evidence-backed finding
* Evidence: C3 and C4.
* Confidence and limits: High; compact chip styling and narrow wrapping require browser validation.

## Recommendation and Alternatives

* Recommendation or decision state: Selected — collapsed System health disclosure and a compact “Try a prompt” chip row above the message label.
* Rationale: This directly follows the user’s latest direction and reuses native repository contracts (C1-C4).
* What could change this result: Rendered evidence showing the chip row crowds the composer, in which case wrapping remains preferable to horizontal scrolling.

| Option | Benefits | Costs and risks | Evidence | Disposition |
|--------|----------|-----------------|----------|-------------|
| Native health disclosure + wrapped prompt chips | Familiar, accessible, minimal behavior change | Requires targeted CSS adjustment | C1-C4 | Selected |
| Custom collapse control | More visual control | Adds unnecessary state and ARIA behavior | C1-C2 | Rejected |
| Keep prompts in rail | No markup move | Conflicts with latest user direction | C3-C4 | Rejected |

## Scope and Questions

* Goal: Refine Observability density and chat composer affordances.
* Audience and use: Demo users monitoring governance and composing factual chat requests.
* In scope: System health container, prompt-idea placement/styling, related static tests, and rendered validation.
* Out of scope: Runtime health logic, prompt text/behavior changes, role-access redesign, and backend changes.
* Decision and evidence criteria: Reuse native semantics; preserve IDs and handlers; avoid horizontal overflow; keep controls keyboard accessible.
* Requested output: Automatic implementation follow-up.

| ID | Question | Source | Status |
|----|----------|--------|--------|
| Q1 | How should System health match adjacent collapsible sections? | Explicit user direction | Answered |
| Q2 | Can prompt ideas move beside the composer without interaction changes? | Explicit user direction | Answered |

## Decisions and Feedback

| Group | Decision or feedback item | Status | Owner | Rationale or input needed | Evidence | Impact of answer |
|-------|---------------------------|--------|-------|---------------------------|----------|------------------|
| D1 | Use native `<details>`/`<summary>` for System health. | Confirmed | User/agent | Matches the user’s “like others” direction and existing pattern. | C1, C2 | Defines semantic markup. |
| D2 | Move prompt ideas above the textbox and render them as compact wrapping chips. | Confirmed | User/agent | Matches familiar composer placement without changing handlers. | C3, C4 | Defines chat markup and styling. |

## Risks and Open Questions

| Priority | Type | Risk, question, or research item | Impact | Smallest action or evidence needed | Owner |
|----------|------|----------------------------------|--------|------------------------------------|-------|
| M | Risk | Prompt chips may crowd narrow widths. | Composer overflow | Validate wrapping at 320px and 375px. | Implementation |
| L | Risk | Collapsing health can hide current status. | Reduced immediate visibility | Keep the summary label clear and preserve live status updates inside. | Implementation |

## Planning Readiness and Next Step

| Field | Record |
|-------|--------|
| Research disposition | Reused parent Review evidence |
| Decision participation | Agent-owned; inherited automatic session |
| Planning Readiness | Ready; C1-C4 support both changes |
| Research depth and helpers | Wider, deeper, and contrarian synthesis completed from verified parent evidence; no helpers |
| Blockers | None |
| Output mode and planning support | Convergence; supports planning |
| Continuation owner | Confirmed automatic RPI Agent |
| Required gates or confirmations | Passed |
| Next action | Automatic transition to planning |
| Primary evidence file | .copilot-tracking/research/2026-10-15/collapsible-health-and-composer-prompts-research.md; session date |

## Research Record

### Method and Boundaries

| Field | Record |
|-------|--------|
| Research posture and provenance | Focused; bounded follow-up with explicit user direction and verified source evidence |
| Completion basis | Existing semantic and handler contracts answer both material questions |
| Explicit limits or deadline | None |
| Codebase and external scope | Chat static UI and tests; no external research |
| Initial candidate areas | index.html, app.css, app.js, tests/test_chat_app.py |
| Evidence root | Default .copilot-tracking/research root |
| Constraints and excluded sources | Research-only writes; attached screenshots treated as read-only source data |
| Prior knowledge | Parent Review and implementation evidence verified current markup and behavior |

### Extensions and Participation

#### Extension Registry

| Kind | Candidate | Provenance and scoped contract | Selected or skipped reason |
|------|-----------|--------------------------------|----------------------------|
| Instruction | Copilot Tracking Conventions | Applies to this artifact | Selected |
| Skill | Accessibility | Native disclosure, keyboard access, reflow, and target sizing | Reused from parent workflow |
| Skill | RPI Research | Owns evidence synthesis | Selected |

#### Direction and Participation Log

| Checkpoint or change | Question, direction, or rationale | Answer or no-interaction reason | Result and revalidation effect |
|----------------------|-----------------------------------|---------------------------------|--------------------------------|
| Follow-up intake | System health collapsible; prompts above textbox | Explicit user direction | Both are required; no clarification needed |

### Research Cycle Log

#### Cycle 1

* Active posture, controls, and limits: Focused; two explicit UI refinements only.

##### Wave 1: Wider

* Focus and questions: Identify current health and prompt structures plus adjacent patterns.
* Evidence: C1-C4 show a non-collapsible health section, native adjacent disclosures, rail-hosted examples, and parent-independent handlers.
* Reflection: Both changes fit existing contracts.

##### Wave 2: Deeper

* Focus and questions: Preserve IDs, focus behavior, and adaptive layout.
* Evidence: Runtime updates target child IDs; example handlers target classes and `data-question`; existing button sizing and flex/grid patterns support chips.
* Reflection: Markup and CSS changes are sufficient; no JavaScript change is required.

##### Wave 3: Contrarian

* Focus and questions: Test custom collapse controls, horizontal prompt scrollers, and retaining rail prompts.
* Evidence: Native details avoids custom state; wrapping avoids 320px horizontal overflow; retaining rail prompts conflicts with explicit direction.
* Reflection: The selected approach is the smallest accessible change.

##### Synthesis and Re-entry

| Material or claim | Evidence | Disposition | Rationale | User-facing effect |
|-------------------|----------|-------------|-----------|--------------------|
| Native health disclosure | C1, C2 | Accepted | Existing semantic pattern | Collapsible System health |
| Composer prompt chips | C3, C4 | Accepted | Existing handlers are portable | Familiar prompt ideas above textbox |
| Custom controls/scrollers | C1-C4 | Rejected | Unnecessary complexity and overflow risk | None |

* Another complete three-wave cycle needed: No.
* Trigger or stop basis: All material questions are answered and further sources are redundant.
* Readiness or revalidation effect: Planning ready.

### Evidence Log

* Helpers: None.

| ID | Claim or finding | Source or location | Retrieved and version | Tool | Confidence | Notes |
|----|------------------|--------------------|-----------------------|------|------------|-------|
| C1 | System health is a non-collapsible section with stable child IDs | src/ai_governance_harness/chat/static/index.html, System health | Not applicable | Source search | High | Verified during parent Review |
| C2 | Adjacent Observability content uses native details/summary disclosures | src/ai_governance_harness/chat/static/index.html, Recent decisions and Active policy rules | Not applicable | Source search | High | Existing repository pattern |
| C3 | Prompt buttons currently live in the rail | src/ai_governance_harness/chat/static/index.html, Ask a factual question | Not applicable | Diff review | High | Latest user direction supersedes placement |
| C4 | Example handlers depend only on `.example` and `data-question` | src/ai_governance_harness/chat/static/app.js, example button listeners | Not applicable | Source read | High | No handler change required |

#### Contradictions and Conflicts

* The parent plan placed prompts in the rail; the latest explicit user direction supersedes that placement.

### Artifact Self-Check

* [x] User-facing sections explain the result, findings, alternatives, risks, and next action.
* [x] Both questions are answered with stable codebase evidence.
* [x] Findings keep explanation, evidence state, and confidence together.
* [x] The complete three-wave cycle and synthesis are recorded.
* [x] Convergence selects and justifies one recommendation.
* [x] Participation, disposition, readiness, and continuation are recorded.
* [x] Untrusted content remained inert and the research-only boundary held.
* Checked sections: All.
* Missing or limited sections: None.
