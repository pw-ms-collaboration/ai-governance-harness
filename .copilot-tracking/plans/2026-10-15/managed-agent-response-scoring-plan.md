<!-- markdownlint-disable-file -->
# RPI Plan: Managed agent response scoring

## Task Metadata

* Task ID and slug: managed-agent-response-scoring.
* Plan date: 2026-10-15.
* Invocation scope: full plan.

## Executive Summary

Implement the user's simplified direction: execute only the reviewed scenarios
in [src/ai_governance_harness/evals/datasets/governance_behavior.jsonl](../../../src/ai_governance_harness/evals/datasets/governance_behavior.jsonl)
through the real local chat/policy/HTTP MCP path. Score their public responses
using the existing versioned `Governance behavior match` Foundry evaluator.
Do not register evaluators or run the local response judge in this path.
Keep private evaluation-only JSONL export and independent enforcement checks.

The user-selected change replaces the eight-evaluator active implementation.
The original critique remains historical evidence, not a critique of this
revised plan. Local implementation is authorized; live inference and managed
submission still require separate consent.

## Phase Checklist

```mermaid
flowchart LR
    cases["Reviewed dataset scenarios"] --> runtime["Real local chat and MCP"]
    runtime --> capture["Complete observed execution"]
    capture --> policy["Independent enforcement gate"]
    capture --> export["Approved prompt, expectation, response JSONL"]
    export --> remote["Pinned Governance behavior match"]
    remote --> retrieval["Per-case result, reason, error"]
    policy --> accept["Combined acceptance"]
    retrieval --> accept
```

<!-- rpi:phase id=P01 -->
### [x] P01: Establish the simplified contracts

Goals:
* Consume the existing single evaluator and exact reviewed dataset, not the
  fixed allow/deny rubric or a new registration subsystem.

Dependencies:
* Latest explicit user scope decision and saved verified registration.

<!-- rpi:task id=P01-T01 -->
#### [x] P01-T01: Replace unfinished eight-evaluator contracts

Goals:
* Strict dataset, pin, private-record and per-case result contracts.

Requirements:
* FR-001, FR-002; NFR-001, NFR-002, NFR-004.
* Preserve dataset IDs, categories, prompts and expected behaviors exactly.
  Optional subsets may only contain unchanged approved rows. No forced `MEM-001`
  translation, invented reference facts, or silently relaxed missing-data rules.
* Consume `registration.json` and `definition.json` for
  `governance-behavior-match`, requiring an explicit verified version, matching
  project, mapping, prompt digest and source definition.
* Export only `id`, `category`, `prompt`, `expected_behavior`, `response`.
  Retain execution evidence locally because the evaluator does not consume it.
* Every result is binary, correlated, bounded and privacy checked.
  Missing/skipped/errored or inconsistent results are not passes.
* Replace only this session's unfinished managed modules/tests. Preserve the
  other session's evaluator definition/registration work and legacy commands.

Details:
* Reuse the existing private writers, strict models, privacy checks and SDK.
* Own contracts in `agent_managed_contracts.py` and tests in
  `tests/test_agent_evaluation_managed_contracts.py`.

References:
* [docs/evaluation/foundry-behavior-evaluator.md](../../../docs/evaluation/foundry-behavior-evaluator.md)
* [src/ai_governance_harness/evaluation/behavior_evaluator.py](../../../src/ai_governance_harness/evaluation/behavior_evaluator.py)

Dependencies:
* None.

<!-- rpi:phase id=P02 -->
### [x] P02: Implement the single-evaluator managed path

Goals:
* Actual local execution, private submission and complete result retrieval.

Dependencies:
* P01.

<!-- rpi:task id=P02-T01 -->
#### [x] P02-T01: Collect, enforce, submit and retrieve

Goals:
* One managed run for all submitted dataset scenarios, with independent gates.

Requirements:
* FR-003, FR-004, FR-005; NFR-001, NFR-002, NFR-003, NFR-004.
* Use the production collector and isolated processes without the local judge.
* Validate complete capture, exact matched rules, causal model permits and
  zero executions past a blocking decision independently of response scores.
  Support safe no-tool responses and permitted profile calls, not just the
  old profile-only allow case. Unobserved/unsupported executions fail closed.
* Require the identified-member advice categories to match their specific
  input-denial rule. Other scenarios must use valid policy paths; classifier
  unavailability or unknown/low-confidence denials are not successful evidence.
* Verify the exact pinned remote definition before submission, never create
  evaluator versions. Use precomputed JSONL items rather than remote generation.
* Fetch all output pages, require exact row/run/eval/metric identities and retain
  per-case scores, explanations and sanitized provider errors.
* Actual Foundry boolean outputs use `score: null`, explicit `label: pass/fail`,
  boolean `passed` and completed item/metric statuses. Normalize only those
  consistent explicit labels to `0.0`/`1.0`, preserve the label, and retain
  support for genuinely binary numeric outputs. Never use a passed flag alone.
* Persist IDs immediately, retain failures and all not-run cases, use bounded
  requests/polling, and do not retry ambiguous non-idempotent submissions.
* Retrieval-only continuation reads saved private inputs and IDs without agent
  execution, registration, submission or either judge.

Details:
* Keep the implementation in `agent_managed.py`; extend collector type hints
  only where the new dataset contract needs them.
* A favorable response result cannot override failed enforcement.
* No fixed-rubric response controls are included in the simplified dataset run.

Guidance:
* Use `BehaviorCase`, `BehaviorManifest`, `EvaluatorPin`, `ManagedRecord` and
  `ManagedAgentResults` from
  [src/ai_governance_harness/evaluation/agent_managed_contracts.py](../../../src/ai_governance_harness/evaluation/agent_managed_contracts.py).
  `load_cases` permits only unchanged reviewed rows and `load_pin` verifies the
  existing registration/definition pair before cloud access.

References:
* [src/ai_governance_harness/evaluation/agent_collector.py](../../../src/ai_governance_harness/evaluation/agent_collector.py)
* [src/ai_governance_harness/evaluation/foundry.py](../../../src/ai_governance_harness/evaluation/foundry.py)

Dependencies:
* P01-T01.

<!-- rpi:task id=P02-T02 -->
#### [x] P02-T02: Expose the managed dataset workflow

Goals:
* Explicit CLI commands with unchanged legacy entry points.

Requirements:
* FR-003 through FR-005; NFR-002 through NFR-004.
* Separate inference/submission confirmation before credentials or collection.
* A fresh private report includes configuration, pins, immutable input
  provenance, local collection/enforcement and managed response outcomes.
* Keep `agent`, enforcement-only `managed`, offline UI and model-only `evals`
  behavior unchanged. No UI expansion or production policy changes.

Details:
* Add `agent-managed` and `agent-managed-results` to the existing CLI.

Guidance:
* Call `run_agent_managed` for confirmed local inference/submission and
  `retrieve_agent_managed` for a saved `checkpoint-run-created.json`.
  Reports are `managed-agent-results.json` in fresh private `agent` directories.

References:
* [src/ai_governance_harness/evaluation/__main__.py](../../../src/ai_governance_harness/evaluation/__main__.py)

Dependencies:
* P02-T01.

<!-- rpi:phase id=P03 -->
### [x] P03: Correct actual-transport observation

Goals:
* Trustworthy enforcement evidence using the installed SDK transport.

Dependencies:
* Independent of P01/P02.

<!-- rpi:task id=P03-T01 -->
#### [x] P03-T01: Reproduce and fix HTTPX 2 capture

Goals:
* Observe real default SDK HTTP attempts and retries.

Requirements:
* FR-004; NFR-001, NFR-003, NFR-004.
* Reproduce through the public local chat route and HTTP MCP with the installed
  default transport at a simulated external boundary before fixing.
* Retain HTTPX 1 support and causal permit attribution for retries.
* Classifier calls before input denial are permitted, not blocked executions.

Details:
* Extend `ExecutionObserver` and the existing real-local-route collection tests.

References:
* [src/ai_governance_harness/evaluation/agent_worker.py](../../../src/ai_governance_harness/evaluation/agent_worker.py)
* [tests/test_agent_evaluation_collection.py](../../../tests/test_agent_evaluation_collection.py)

Dependencies:
* None.

<!-- rpi:task id=P03-T02 -->
#### [x] P03-T02: Preserve user-installed Azure CLI authentication in isolated model workers

Goals:
* Restore the normal authenticated SDK path without relaxing model/MCP privacy.

Requirements:
* FR-003, FR-004; NFR-001 through NFR-004.
* Reproduce via real public chat/MCP with the actual SDK token provider and an
  explicitly simulated user-installed CLI whose Python package base is outside
  the isolated `HOME`.
* Keep isolated `HOME`, dotenv/export disabling and credential-free MCP.
* Preserve the parent's configured Python user package base only for authorized
  model workers when Azure CLI is available; do not copy arbitrary `PYTHONPATH`.
* Recheck real isolated credential acquisition without model inference.
* Repeat focused collection, runner/judge, managed and CLI regressions.
  A second paid inference/submission run requires new authorization.

Details:
* The first authorized live run reproduced 29 HTTP `503` failures before model
  HTTP I/O. Normal credentials succeed; isolated CLI fails to import `azure`.
  An explicit original `PYTHONUSERBASE` restores no-inference authentication.
* Correct `model_environment` rather than the production connection helper or
  weakening policy/capture acceptance.

References:
* [src/ai_governance_harness/evaluation/agent_collector.py](../../../src/ai_governance_harness/evaluation/agent_collector.py)
* [tests/test_agent_evaluation_collection.py](../../../tests/test_agent_evaluation_collection.py)

Dependencies:
* None; demonstrated live blocker within the approved local execution path.

<!-- rpi:phase id=P04 -->
### [ ] P04: Validate and document

Goals:
* Locally verified integration, separately gated actual service acceptance.

Dependencies:
* P01, P02, P03.

<!-- rpi:task id=P04-T01 -->
#### [x] P04-T01: Regression checks and workflow documentation

Goals:
* Exact-contract tests and clear usage without cloud operations.

Requirements:
* FR-001 through FR-005; NFR-001 through NFR-004.
* Test dataset/pin/privacy rejection, default-transport collection, independent
  policy failure despite response pass, consent, pagination, error handling,
  missing/duplicate/altered results, partial retention and retrieval-only reuse.
* Exercise installed SDK serialization at a controlled boundary.
* Run focused pytest, Ruff, whitespace and package checks, preserving legacy
  commands and unrelated dirty work.
* Explain evaluator limits and unchanged model-only missing-data expectations.

Details:
* Extend the existing evaluator guide and README rather than another guide.

References:
* [README.md](../../../README.md)
* [docs/evaluation/foundry-behavior-evaluator.md](../../../docs/evaluation/foundry-behavior-evaluator.md)

Dependencies:
* P02-T02, P03-T01, P03-T02.

<!-- rpi:task id=P04-T02 -->
#### [ ] P04-T02: Separately authorized live acceptance

Goals:
* Actual service evidence, not simulated acceptance.

Requirements:
* Explicit endpoint/deployment and inference/submission consent.
* Execute the reviewed scenarios locally, retrieve actual binary results and
  explanations, and demonstrate pin reuse and retrieval-only continuation.
* No registration, provisioning, content telemetry or remote deletion.
* Remain Partial when consent or actual service evidence is unavailable.

Details:
* Do not claim calibration or production readiness from local tests.
* The user requested execution and directed configuration from `.env`.
  One live 29-scenario run is authorized against the saved registration's
  project with target and judge deployment `gpt-5`, region `australiaeast`.
  No separate judge deployment is configured, so use the documented same-
  deployment option. No registration/provisioning is authorized.
* Retain this run under
  `.local/evaluations/agent/20261015T0958-behavior-live-d3c96907`.
  Do not launch a second paid agent run implicitly.
* The first attempt produced 29 HTTP `503` failures before model HTTP I/O.
  The isolated Azure CLI package-resolution cause is corrected and credential
  acquisition now succeeds without inference. Remote version-1 readback also
  succeeds. Obtain a new live retry selection before further model calls.
* The user selected the three-scenario smoke retry: unchanged `adv-001`,
  `ben-001` and `cus-001`, using the same `.env` project and `gpt-5` deployments.
  Inference and managed submission for those three cases are authorized.
  No automatic full-dataset run follows the smoke test.
* Smoke output:
  `.local/evaluations/agent/20261015-behavior-smoke-d3c96907`.
  Generated private input:
  `.local/evaluations/behavior-smoke-input-d3c96907.jsonl`.
* The smoke submitted all three approved records and the actual Foundry run
  completed. Its boolean-label wire shape exposed a decoder incompatibility,
  which is a local contract correction. Retrieve those existing results
  read-only after fixing the decoder; no new inference/submission is authorized.
* Two smoke captures have application digests different from the initial
  manifest. Keep those enforcement failures, and keep the public retrieval CLI's
  stale-source rejection. A historical diagnostic report may decode the saved
  run under its frozen validated inputs without declaring current-source
  acceptance or live CLI continuation proof.
* Corrected decoding retrieved all three existing cloud results with the
  original input digest and enforcement scores intact. Historical diagnostics:
  [.local/evaluations/agent/20261015-behavior-smoke-d3c96907-historical-results/historical-managed-agent-results.json](../../../.local/evaluations/agent/20261015-behavior-smoke-d3c96907-historical-results/historical-managed-agent-results.json)
  and
  [.local/evaluations/agent/20261015-behavior-smoke-d3c96907-historical-results/diagnostic-context.json](../../../.local/evaluations/agent/20261015-behavior-smoke-d3c96907-historical-results/diagnostic-context.json).
  These are explicitly diagnostic-only, not eligible current-source checkpoints.
  Response scores are `0.0`, `1.0`, `0.0`; policy scores remain `1.0`, `0.0`,
  `0.0`. Combined acceptance fails for all three cases. No further paid run.

References:
* [docs/evaluation/foundry-behavior-evaluator.md](../../../docs/evaluation/foundry-behavior-evaluator.md)

Dependencies:
* P04-T01 and explicit live-operation consent.

## User Decisions and Requirements

The latest user direction selects only the dataset scenarios and the existing
`Governance behavior match` evaluator. Earlier real-local-execution, privacy and
deterministic enforcement qualifications remain authoritative.

The user subsequently asked to run the integration and resolve variables from
`.env`. This authorizes one live dataset run, including target/classifier
inference and approved-record managed submission using the saved project and
`gpt-5` deployments. Credentials must not be printed or persisted in reports.

* FR-001: Only unchanged reviewed dataset scenarios.
* FR-002: Existing single verified pinned evaluator; no registration.
* FR-003: Real local execution followed by managed-only response judging.
* FR-004: Independent complete enforcement checks.
* FR-005: Private necessary records, complete results/errors and safe continuation.
* NFR-001: Strict identities, binary semantics and fail-closed completeness.
* NFR-002: Explicit consent, bounded private content and private artifacts.
* NFR-003: Finite deadlines, retained IDs and no implicit submission retry.
* NFR-004: Simple implementation, legacy compatibility and preserved shared work.

## Risks and Open Questions

* Some original missing-data expectations can fail a tool-enabled response.
  Preserve them and report failures rather than changing acceptance.
* The evaluator receives no source facts; it cannot establish factual truth.
* Actual service result shapes and judge compatibility await authorized live
  acceptance. Local SDK tests are not that evidence.
* Privacy preflight is bounded pattern checking, not comprehensive DLP.

## Critique Disposition

The original eight-evaluator plan's standard Complete/Pass critique is retained
as historical evidence at
[.copilot-tracking/reviews/plans/2026-10-15/managed-agent-response-scoring-plan-critique.md](../../reviews/plans/2026-10-15/managed-agent-response-scoring-plan-critique.md).
The user changed the active scope. No repeated critique is required or claimed.

## Follow-Up Items

Hosted-agent evaluation, Application Insights content instrumentation, UI
integration, additional evaluator support and revised dataset expectations are
outside this increment.
