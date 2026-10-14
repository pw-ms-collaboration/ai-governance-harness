<!-- markdownlint-disable-file -->
# RPI Changes: Semantic Personal-Advice Policy Classification

## Metadata

* Task ID: `semantic-advice-policy-2026-10-14`
* Related plan: [.copilot-tracking/plans/2026-10-14/semantic-advice-policy-plan.md](../../plans/2026-10-14/semantic-advice-policy-plan.md)
* Implementation date: `2026-10-14`

## Execution Status

* Status: Complete
* Declared invocation scope: full plan
* Completed scope markers: `P01`, `P01-T01`, `P01-T02`, `P02`, `P02-T01`, `P02-T02`, `P03`, `P03-T01`, `P03-T02`
* All remaining active-plan markers: none
* Status basis: all planned behavior, documentation, and validation requirements are complete.

## Execution Summary

Regex-based input advice detection is replaced by a strict semantic Foundry classifier. YAML policy evaluates only typed facts, technical classifier failures stop distinctly, split-turn context no longer depends on member-ID regex, and existing output guardrails remain intact.

## Completed Work

### Added a closed semantic policy-fact contract

* Related phase or task: `P01-T01`
* Files:
  * [src/ai_governance_harness/guardrails/advice_classifier.py](../../../src/ai_governance_harness/guardrails/advice_classifier.py)
* Behavior or functionality changed: chat input can now be represented by strict enums for intent, subject, financial action, product scope, confidence, and classification status. The classifier emits no copied prompt, identifier, rationale, or free-form field.
* Validation: Passed in focused classifier tests and the full suite.

### Governed semantic classification before primary chat

* Related phase or task: `P01-T02`
* Files:
  * [src/ai_governance_harness/chat/service.py](../../../src/ai_governance_harness/chat/service.py)
  * [src/ai_governance_harness/chat/config.py](../../../src/ai_governance_harness/chat/config.py)
* Behavior or functionality changed: a tool-free, no-store, schema-constrained Foundry call runs under its own lifecycle decisions and reliability circuit before `chat.input`. The current and preceding user turns provide regex-independent context. Invalid, filtered, unavailable, unknown, and low-confidence outcomes stop before MCP or the primary model and return `classification_unavailable`.
* Validation: Passed orchestration, split-turn, provider-stop, timeout, cleanup, and privacy tests.

### Policy now decides on semantic facts

* Related phase or task: `P02-T01`
* Files:
  * [src/ai_governance_harness/governance/policies/default.yaml](../../../src/ai_governance_harness/governance/policies/default.yaml)
  * [tests/test_governance.py](../../../tests/test_governance.py)
* Behavior or functionality changed: YAML rules deny identified-member recommendations, external-security recommendations, unsafe classifier outcomes, unknown intent, and low confidence while explicitly allowing classified safe intents and classifier lifecycle actions.
* Validation: Strict policy lint passed with zero errors and warnings; semantic rule tests passed.

### Removed request regex without weakening output checks

* Related phase or task: `P02-T02`
* Files:
  * [src/ai_governance_harness/guardrails/advice_filter.py](../../../src/ai_governance_harness/guardrails/advice_filter.py)
  * [src/ai_governance_harness/chat/service.py](../../../src/ai_governance_harness/chat/service.py)
* Behavior or functionality changed: `PERSONAL_ADVICE_REQUEST_PATTERNS`, `advice_request_policy_data`, and `_active_advice_request_text` are removed. Deterministic post-tool/output advice scanning, sanitization, and disclosures are unchanged.
* Validation: Legacy output-guardrail tests and the full suite passed.

### Added semantic, failure, and privacy regression coverage

* Related phase or task: `P03-T01`
* Files:
  * [tests/test_advice_classifier.py](../../../tests/test_advice_classifier.py)
  * [tests/test_chat_service.py](../../../tests/test_chat_service.py)
  * [tests/test_chat_app.py](../../../tests/test_chat_app.py)
  * [tests/test_chat_config.py](../../../tests/test_chat_config.py)
  * [tests/test_guardrails.py](../../../tests/test_guardrails.py)
* Behavior or functionality changed: deterministic tests cover strict schema, mixed advice, external securities, split-turn context, safe requests, invalid and filtered responses, timeout/unavailability, low confidence, no primary model after denial, client cleanup, and absence of prompt/member identifiers from governance snapshots.
* Validation: Focused tests passed; final full suite passed with 226 tests.

### Documented the classifier and operational trade-off

* Related phase or task: `P03-T02`
* Files:
  * [README.md](../../../README.md)
  * [docs/configuration.md](../../../docs/configuration.md)
  * [docs/architecture-and-controls.md](../../../docs/architecture-and-controls.md)
* Behavior or functionality changed: operators can distinguish semantic classification from YAML enforcement and output scanning, configure the classifier budget, understand the extra model-call latency, and diagnose technical classification stops separately from policy denials.
* Validation: Documentation is consistent with tested runtime behavior.

## Implementation-Time Plan Updates

### Incorporated standard critique findings

* Affected plan area or markers: `FR-003`, `FR-005`, `P01-T01`, `P01-T02`, `P02-T02`, `P03-T01`
* What changed: the plan now requires regex-independent two-user-turn context and a distinct `classification_unavailable` technical stop.
* Why: prevent split-turn advice bypass and avoid presenting provider/classifier failures as intentional personal-advice denials.
* Triggering evidence: `PC-001` and `PC-002`.
* User answer or decision: no additional decision; the corrections preserve the authorized recommended architecture.
* Reconciliation performed: requirements, task details, test matrix, readiness, critique disposition, and removal list are current.
* Planning and critique state: Ready; both critique findings are resolved.

## Validation Record

| Check | Scope | Status | Evidence or reason |
|---|---|---|---|
| Focused pytest | Classifier, guardrails, governance, chat service, chat API, and config | Passed | 100 tests passed before final additions; final focused classifier/integration rerun passed 75 tests. |
| Full pytest | Repository | Passed | 226 tests passed. |
| Changed-area Ruff | Changed Python source and tests | Passed | All checks passed. |
| Strict policy lint | `default.yaml` | Passed | Zero errors and zero warnings. |
| Package build | Source distribution and wheel | Passed | Both artifacts built successfully. |
| JavaScript syntax | Browser assets | Skipped | This plan did not modify JavaScript; unrelated pre-existing browser changes were outside scope. |

## Pre-Review Reconciliation

* Plan markers and task-local context: current; all full-plan markers are checked.
* Completed-work entries and handoff prose: current and mapped to every task.
* Validation, blockers, remaining work, and follow-up items: current; no blockers or remaining active work.
* Review readiness: ready.

## Blockers

* None.

## Remaining Work

* None.

## Follow-Up Items

* Canonical plan list: [.copilot-tracking/plans/2026-10-14/semantic-advice-policy-plan.md](../../plans/2026-10-14/semantic-advice-policy-plan.md), `## Follow-Up Items`
* Optional durable versioned semantic-classifier evaluation dataset remains outside immediate scope.

## Return-to-Caller State

* Implementation execution status: Complete
* Declared scope and markers: full plan; all `P01` through `P03` markers complete
* Validation coverage: focused tests, 226-test full suite, Ruff, strict policy lint, and package build passed
* Blockers: none
* Current plan updates: critique corrections are current
* Planning and critique state: Ready
* Follow-up items: optional durable evaluation dataset
* Review readiness or no-handoff reason: ready for review
* Continuation owner: automatic RPI parent
