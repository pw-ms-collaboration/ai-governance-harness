<!-- markdownlint-disable-file -->
# Review: Right-side identity and question panel

## Executive Summary

* Assessment: The implemented right rail satisfies the original plan and validation boundary, but the user refined two layout requirements during Review: System health must be collapsible, and prompt ideas must move from the rail to immediately above the message composer.
* Why this matters: The current result is sound but no longer represents the latest desired interaction pattern.
* Review execution: Complete
* Assessed outcome: Defects found
* Validation coverage: 17 targeted tests passed; rendered desktop, 375px, 320px, keyboard-order, target-size, identity, shortcut, sign-in, and clear-chat checks passed.
* Confidence and limitations: High confidence in both findings and the accepted routes. Visual polish of the revised composer pattern remains implementation-time evidence.

The assessment above is the reviewer's proposal. Parent Decision Record contains the final decisions and next actions.

## What You May Not Know

The prompt buttons already use parent-independent `.example` handlers, so they can move from the rail to the composer without changing their behavior. System health already sits beside disclosure-based Observability sections, so it can adopt the same native `<details>` pattern while preserving its existing status IDs.

## Findings and Proposed Routes

<!-- rpi:review id=RV-001 -->
### RV-001 [Medium]: System health is not collapsible

System health remains permanently expanded even though the surrounding Observability sections use collapsible disclosures.

* Related scope: User direction added during Review; Observability System health.
* Expected behavior: System health can be expanded and collapsed like the other Observability sections.
* Observed behavior and evidence: src/ai_governance_harness/chat/static/index.html renders System health as `<section class="runtime-summary">`, while Recent decisions and Active policy rules use `<details>` and `<summary>`.
* Impact: The dense health content cannot be reduced when users want to focus on other Observability evidence.
* Resolution condition: System health uses a keyboard-accessible native disclosure that retains `#runtime-title`, `#circuit-health-summary`, `#service-statuses`, `#circuit-statuses`, and all current runtime content.
* Proposed destination: `rpi-implement`
* Smallest useful next action: Convert the System health container to the existing disclosure pattern and extend the static UI contract test.

<!-- rpi:review id=RV-002 -->
### RV-002 [Medium]: Prompt ideas are separated from message composition

The example prompts are currently the third step in the right rail, but the latest user direction places prompt ideas immediately above the message input in the familiar Copilot/Teams composer pattern.

* Related scope: User direction added during Review; P01-T01/P01-T02 presentation boundary.
* Expected behavior: Compact prompt-idea buttons appear directly above the chat textbox and are removed from the right rail.
* Observed behavior and evidence: src/ai_governance_harness/chat/static/index.html renders `.examples` inside the rail’s Ask section; rendered evidence confirms the shortcuts work but are spatially separated from `#chat-input`.
* Impact: Suggested prompts feel like setup content instead of contextual composer affordances, and the right rail is longer than necessary.
* Resolution condition: The existing `.example` buttons appear in a compact prompt-ideas group immediately before the message field, retain their `data-question` behavior, and no longer appear in the rail.
* Proposed destination: `rpi-implement`
* Smallest useful next action: Move the existing group into `#chat-form`, restyle it as compact prompt ideas, and revalidate focus, reflow, and shortcut behavior.

## Parent Decision Record

### Current Disposition

* Based on events: RD-001 through RD-006
* Review execution: Complete
* Final outcome: Defects found; the original plan is implemented correctly, but the two latest user-required refinements remain.
* Finding decisions and next actions: RV-001 and RV-002 accepted for automatic implementation in one bounded follow-up.
* Decisions still needed: None.

This summary is derived from Decision History, not a second decision record. The latest event for each subject governs.

### Decision History

| Event | Subject | Decision source | Status or value | Proposed destination | Final destination | Owner | More information needed | Smallest next action | Rationale |
|-------|---------|-----------------|-----------------|----------------------|-------------------|-------|-------------------------|----------------------|-----------|
| RD-001 | Participation | Agent | Agent-owned | None | None | Review parent | None | Complete comparison | User selected automatic end-to-end RPI mode |
| RD-002 | Walkthrough | Agent | Skipped-auto | None | None | Review parent | None | Decide findings from evidence | Review participation is agent-owned |
| RD-003 | Execution | Agent | Complete | None | None | Review parent | None | Decide routes and outcome | Full supplied boundary was compared |
| RD-004 | RV-001 | Agent | Accepted | `rpi-implement` | `rpi-implement` | Automatic follow-up | None | Make System health collapsible | Latest user direction is explicit and compatible with existing native disclosures |
| RD-005 | RV-002 | Agent | Accepted | `rpi-implement` | `rpi-implement` | Automatic follow-up | None | Move prompt ideas to the composer | Latest user direction is explicit and existing handlers are location-independent |
| RD-006 | Outcome | Agent | Defects found | None | None | Automatic RPI parent | None | Start one bounded follow-up for RV-001 and RV-002 | Accepted findings prevent a conformant outcome |

## Validation Evidence

| Command | Scope | Status | Summary |
|---------|-------|--------|---------|
| `.venv\Scripts\python.exe -m pytest tests\test_chat_app.py -q` | Chat UI and API tests | Passed | 17 passed |
| `uv run pytest tests\test_chat_app.py -q` | Preferred environment path | Unavailable | Package-index TLS handshake failed; existing `.venv` provided a successful local fallback |
| Integrated browser checks | Chat workflow | Passed | Role preview, shortcut focus, mock sign-in, send availability, clear-chat focus, and role comparison verified |
| Integrated browser checks | 1440px, 375px, and 320px | Passed | Desktop rail, narrow stacking, 44px minimum controls, and no horizontal overflow verified |

## Risks, Blockers, and Residual Work

* Blockers: None.
* Remaining active work: None in the completed parent plan.
* Residual work: RV-001 and RV-002 are required follow-up work under the latest user direction.

## Review Record

### Scope and Evidence

* Task ID: `right-side-identity-question-panel`
* Review date: 2026-10-15
* Review scope: Full task plus explicit requirement refinements received during Review.
* Assessed boundary: FR-001 through FR-005, NFR-001 through NFR-003, P01/P02 and all five tasks, critique PC-001, role semantics, implementation validation, and the two latest user refinements.
* Review depth and provenance: Standard; default.
* Candidate identity: `right-side-identity-question-panel`, full scope, current uncommitted implementation.
* Review execution: Complete
* Helper use: None.
* Plan: .copilot-tracking/plans/2026-10-15/right-side-identity-question-panel-plan.md
* Plan critique: .copilot-tracking/reviews/plans/2026-10-15/right-side-identity-question-panel-plan-critique.md
* Changes: .copilot-tracking/changes/2026-10-15/right-side-identity-question-panel-changes.md
* Other evidence considered: .copilot-tracking/research/2026-10-15/right-side-identity-question-panel-research.md, current source diff, reported test results, browser snapshots, and the user’s Review refinements.

### Opening Review State

* Interpreted review goal: Determine whether the completed implementation satisfies the requested workflow, role-access accuracy, preserved behavior, and adaptive usability, including direction received during Review.
* Review scope: Full task.
* Evidence readiness: Complete artifact set, source diff, tests, and rendered evidence were available.
* Acceptance basis: Confirmed user direction, FR-001 through FR-005, NFR-001 through NFR-003, task requirements, resolved critique PC-001, and latest user refinements.
* First comparison boundary: Uncommitted source and test diff against the reconciled plan and changes record.
* Active read-only boundaries: Review wrote only this review record.
* Authority: the review parent compares evidence and writes findings; final outcome, route dispositions, and continuation are recorded in Parent Decision Record.
* Initial blockers: None.

### Acceptance and Change Coverage

| Requirement or scope | Implementation and validation evidence | Assessment | Finding or rationale |
|----------------------|----------------------------------------|------------|----------------------|
| FR-001, FR-002, P01-T01, P01-T02 | src/ai_governance_harness/chat/static/index.html and app.css; desktop/narrow browser evidence | Met for original plan | Conversation is primary and the rail reflows correctly |
| FR-003, P01-T03, PC-001 | index.html disclaimer, app.js presentation map, tests/test_chat_app.py, browser role preview | Met | Access is a preview, Reporting stays app-only, and sign-in status remains authoritative |
| FR-004, NFR-001 | Stable IDs and handlers, 17 tests, browser sign-in/shortcut/clear checks | Met | Existing behavior and safety constraints were preserved |
| FR-005, NFR-002, NFR-003 | 375px/320px no-overflow checks, focus order, 44px minimum controls | Met | Adaptive and keyboard evidence covers the planned boundary |
| P01/P02 completion claims | Completed markers and changes-record entries | Met | Every original task has implementation and validation evidence |
| Latest System health direction | Current `<section class="runtime-summary">` | Gap | RV-001 |
| Latest prompt-ideas direction | `.examples` remains inside the rail | Gap | RV-002 |

### Critique and Follow-Up Assessment

* Latest critique dispositions: PC-001 was resolved before implementation by distinguishing selected-role preview from authenticated state.
* Material revisions: No implementation-time plan changes occurred; the two new requirements arrived during Review and are routed as one follow-up.
* Dependent-work pause assessment: Not applicable; original implementation completed before the new direction arrived.
* Justification assessment: Original design decisions remain supported, except the prompt-idea placement superseded by the latest user direction.

| Follow-up item | Why outside immediate scope | Owner or next action | Assessment and route |
|----------------|-----------------------------|----------------------|----------------------|
| RV-001 and RV-002 | Added after parent implementation completed | Automatic RPI follow-up | Required and accepted; implement together |

### Reviewer Self-Check

* [x] Every supplied requirement, in-scope marker, critique disposition, validation result, blocker, remaining item, and follow-up has an assessment.
* [x] Findings are substantive, evidence-grounded, severity-graded, and include expected/observed behavior, resolution conditions, and one route each.
* [x] Execution status, assessed outcome, validation coverage, limitations, and proposed routes are explicit.
* [x] Parent Decision Record contains append-only participation, walkthrough, execution, finding, and outcome events.
* [x] Current Disposition reflects the latest events.
