<!-- markdownlint-disable-file -->
# Review: Semantic Personal-Advice Policy Classification

## Executive Summary

* Assessment: The full implementation conforms to the approved semantic-classification plan. Input advice detection is no longer regex-driven, YAML policy remains the enforcement authority, technical classifier stops are distinct from unsafe-intent denials, and existing output controls remain intact.
* Why this matters: Mixed, pronoun-based, and split-turn personal-advice requests now reach policy as typed facts without placing raw prompts or member identifiers in governance evidence.
* Review execution: Complete
* Assessed outcome: Conformant
* Validation coverage: 226-test full suite, focused classifier and orchestration tests, changed-area Ruff, strict policy lint, and package build all passed.
* Confidence and limitations: High confidence in contract, policy, orchestration, privacy, failure, and regression behavior. Live semantic accuracy remains model-dependent and was not claimed or required as deterministic evidence.

The assessment above is the reviewer's proposal. Parent Decision Record contains the final decisions and next actions.

## What You May Not Know

The classifier lifecycle allow rules do not allow the user's request. They authorize only the constrained classification call and result; `chat.input` is evaluated separately from the resulting typed facts. Operational failures still create fail-closed policy evidence but surface to the user as `classification_unavailable`, not as a personal-advice denial.

## Findings and Proposed Routes

No substantive findings were identified within the assessed boundary.

## Parent Decision Record

### Current Disposition

* Based on events: `RD-001`, `RD-002`, `RD-003`, `RD-004`
* Review execution: Complete
* Final outcome: Conformant; all active requirements and plan markers have implementation and validation evidence.
* Finding decisions and next actions: none
* Decisions still needed: none

This summary is derived from Decision History, not a second decision record. The latest event for each subject governs.

### Decision History

| Event | Subject | Decision source | Status or value | Proposed destination | Final destination | Owner | More information needed | Smallest next action | Rationale |
|---|---|---|---|---|---|---|---|---|---|
| `RD-001` | Review participation | agent | `agent-owned` | none | none | RPI parent | none | Complete the standard evidence comparison | Automatic end-to-end progression was authorized by the user. |
| `RD-002` | Finding walkthrough | agent | `skipped-auto` | none | none | RPI parent | none | Decide findings from evidence | Agent-owned review has no per-finding user walkthrough. |
| `RD-003` | Review execution | agent | Complete | none | none | RPI parent | none | Decide outcome | The complete acceptance boundary was assessed once. |
| `RD-004` | Review outcome | agent | Conformant | none | none | RPI parent | none | Stop automatic session | No material findings, blockers, or required residual work remain. |

## Validation Evidence

| Command | Scope | Status | Summary |
|---|---|---|---|
| `.venv\Scripts\pytest.exe tests\test_advice_classifier.py tests\test_chat_service.py tests\test_governance.py -q` | Classifier contract, orchestration, and policy | Passed | 75 tests passed after final classifier/provider changes. |
| `.venv\Scripts\pytest.exe -q` | Full repository | Passed | 226 tests passed. |
| `.venv\Scripts\ruff.exe check ...` | Changed Python source and tests | Passed | All checks passed. |
| `.venv\Scripts\agt.exe --json lint-policy --strict ...\default.yaml` | Governance policy | Passed | Zero errors and zero warnings. |
| `.venv\Scripts\python.exe -m build` | Source distribution and wheel | Passed | Both package artifacts built successfully. |

## Risks, Blockers, and Residual Work

* Blockers: none
* Remaining active work: none
* Residual work: the plan records an optional future versioned semantic-classifier evaluation dataset. It is outside current acceptance because model accuracy is not represented as deterministic.

## Review Record

### Scope and Evidence

* Task ID: `semantic-advice-policy-2026-10-14`
* Review date: `2026-10-14`
* Review scope: full task, `P01` through `P03`
* Assessed boundary: `FR-001` through `FR-005`, `NFR-001` through `NFR-004`, semantic contract, Foundry lifecycle, reliability, privacy, YAML policy authority, regex removal, output-control preservation, documentation, and validation.
* Review depth and provenance: standard; default
* Candidate identity: `semantic-advice-policy-2026-10-14`, full-plan completed revision
* Review execution: Complete
* Helper use: none
* Plan: `.copilot-tracking/plans/2026-10-14/semantic-advice-policy-plan.md`
* Plan critique: `.copilot-tracking/reviews/plans/2026-10-14/semantic-advice-policy-plan-critique.md`
* Changes: `.copilot-tracking/changes/2026-10-14/semantic-advice-policy-changes.md`
* Other evidence considered: task-specific source and test changes, `.copilot-tracking/pr/pr-reference.xml`, and recorded validation outputs.

### Opening Review State

* Interpreted review goal: verify that the implemented semantic classifier replaces input regex safely while preserving policy ownership and existing workflows.
* Review scope: full task
* Evidence readiness: plan, critique, changes record, completed markers, source/tests, and final validation are available and reconciled.
* Acceptance basis: plan functional and non-functional requirements plus resolved `PC-001` and `PC-002`.
* First comparison boundary: typed classifier contract through `chat.input` enforcement and primary-model/MCP stop behavior.
* Active read-only boundaries: review record and evidence only.
* Authority: the review parent compares evidence and writes findings; final outcome, route dispositions, and continuation are recorded in Parent Decision Record.
* Initial blockers: none

### Acceptance and Change Coverage

| Requirement or scope | Implementation and validation evidence | Assessment | Finding or rationale |
|---|---|---|---|
| `FR-001`, `P01-T01` | `src/ai_governance_harness/guardrails/advice_classifier.py`; `tests/test_advice_classifier.py` | Met | Strict closed schema, no free-form output, and bounded projection are tested. |
| `FR-001`, `P01-T02` | `src/ai_governance_harness/chat/service.py`; `tests/test_chat_service.py` | Met | Classification occurs before `chat.input`, MCP discovery, and primary assistant calls under a distinct lifecycle and circuit. |
| `FR-002`, `P02-T01` | `src/ai_governance_harness/governance/policies/default.yaml`; `tests/test_governance.py` | Met | YAML policy owns semantic denials and safe-intent allow decisions. |
| `FR-003`, resolved `PC-002` | `classification_unavailable` orchestration and timeout/invalid/filter/low-confidence tests | Met | Unsafe intent remains a governance denial; technical and uncertain stops are explicit and fail closed. |
| `FR-004`, `NFR-003` | Policy projections and governance snapshot assertions | Met | Prompt text, Microsoft stock wording, and `MEM-003` are absent from governance snapshots and public details. |
| `FR-005`, resolved `PC-001`, `P02-T02` | Removed request regex and `_active_advice_request_text`; split-turn test; retained output tests | Met | Context uses two user turns without regex and output scanning remains active. |
| `NFR-001`, `NFR-002` | Classifier call options, settings, reliability circuit, and cleanup tests | Met | Strict schema, no tools, no storage, bounded tokens, minimal reasoning, timeout/circuit, and cleanup hold. |
| `NFR-004`, `P03` | Final validation record and documentation | Met | Full suite, lint, policy lint, package build, and directly related docs are complete. |
| Implementation-time critique corrections | Plan and changes record critique dispositions | Met | Both corrections were applied before dependent implementation completed; no architecture divergence occurred. |

### Critique and Follow-Up Assessment

* Latest critique dispositions: `PC-001` and `PC-002` are resolved in requirements, implementation, tests, and documentation.
* Material revisions: no material implementation divergence; task guidance was updated with created contract/test ownership pointers.
* Dependent-work pause assessment: implementation proceeded only after the plan incorporated both critique corrections.
* Justification assessment: supported by existing product behavior, the user's recommended-change authorization, and final tests.

| Follow-up item | Why outside immediate scope | Owner or next action | Assessment and route |
|---|---|---|---|
| Versioned semantic-classifier evaluation dataset | Ongoing model-quality management exceeds the current contract/enforcement migration | Product/compliance owner may plan later | Optional distinct follow-up; not required for acceptance |

### Reviewer Self-Check

* [x] Every supplied requirement, acceptance criterion, in-scope marker, material update, critique disposition, validation result, blocker, remaining item, and plan follow-up has an assessment or explicit gap.
* [x] No unsupported or cosmetic finding was manufactured.
* [x] Execution status, assessed outcome, validation coverage, limitations, and proposed continuation are explicit.
* [x] Parent participation, walkthrough, execution, and outcome events are append-only and reflected in Current Disposition.
