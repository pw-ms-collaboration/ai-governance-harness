<!-- markdownlint-disable-file -->
# RPI Changes: Custom Governance Evaluation

## Metadata

* Task ID: custom-governance-evaluation
* Related plan: [.copilot-tracking/plans/2026-10-14/custom-governance-evaluation-plan.md](../../plans/2026-10-14/custom-governance-evaluation-plan.md)
* Implementation date: 2026-10-14

## Execution Status

* Status: Partial overall; local delivery and final local handoff complete.
* Declared invocation scope: Full plan.
* Completed scope markers: P01, P02, P03, P01-T01, P01-T02, P02-T01, P02-T02,
  P03-T01, P04-T02.
* Remaining markers: P04, P04-T01, deferred by user.
* Basis: Local implementation, real stdio acceptance, and managed runner tests
  are complete. User explicitly deferred actual Azure execution for now.

## Execution Summary

User approved direct implementation from the retained small specification and
automatic RPI. P04-T01 is user-deferred; P04-T02 local handoff and Review
are complete. One independent
standard plan critique completed with both planner-owned findings resolved.
The evaluation package, installed commands, regression controls, and related
documentation are implemented. No managed resource has changed.
The user reaffirmed finishing this original plan before the separate live-agent
evaluation. Existing unrelated chat source/test changes are preserved.

## Completed Work

### Version-pinned managed runner and complete failure reporting

* Related task: P03-T01; evaluation T004.
* Files: Evaluation `foundry.py`, managed CLI, dependency floors, README, and
  `tests/test_evaluation_foundry.py`.
* Behavior: Endpoint-only real SDK construction, deployment access preflight,
  trusted-bundle validation, evaluator registration/readback and explicit version
  pinning, typed nested evidence transport, separate baseline/control runs,
  bounded polling/pagination, exact row/metric/error reconciliation, and private
  retained reports. No local-success fallback or cloud resource deletion.
* Validation: 37 managed tests and all 87 evaluation tests passed; real SDK
  wire serialization is verified with mock HTTP, not authenticated service
  execution. The workflow reproduced four malformed-result crashes; SDK field
  and page guards now report explicit sanitized errors instead of escaping with
  `AttributeError`/`TypeError`. Queue deadline, deployment mismatch, invalid
  eval/run IDs, wrong recognized control-error category, and result pages are covered.

### Final local evidence and package regression acceptance

* Related tasks: P02-T02/P03-T01; final P04-T02 validation inputs.
* Behavior: Fresh installed local run preserves both actual `1.0` baselines,
  zero child exits, eleven completed `0.0` controls, and seven intended explicit
  evidence errors. All eighteen controls are accepted independently.
* Evidence: `.local/evaluations/20261014T023344Z-54be5b9885b2/local-results.json`;
  manifest digest `3897f9dacd2ea6fff3fb7d796f8c40057bdcccc1b06897d817cf9ab122a9419b`.
* Validation: Final full repository suite passed 180 tests; full Ruff, all eleven
  new Python-file formatting checks, and `git diff --check` passed. Rebuilt wheel
  contains all seven evaluation modules, packaged policy/synthetic data, and the
  installed entrypoint, with no private evaluation/environment/tracking artifacts.
* Supporting cleanup: Removed only the existing unused `typing.Optional` import;
  no member-model behavior changed. Unrelated existing chat changes are preserved.

### Local-only handoff with explicit managed deferral

* Related task: P04-T02; local handoff complete.
* Behavior: README explicitly distinguishes independent local execution from
  deferred managed grading. The existing confirmation gate produces only a
  local blocked report when `--confirm-submit` is omitted.
* Evidence: `.local/evaluations/20261014T023344Z-54be5b9885b2/managed-deferred/managed-results.json`;
  `submission_confirmation_required`, zero runs, no evaluator/evaluation IDs.
* Validation: Installed managed command without confirmation exited with the
  expected non-success status; retained report was verified. Unit coverage
  proves this path never obtains credentials or uploads. This is evidence of
  intentional no-submission, not an attempted Azure access failure.

### One standard RPI outcome review and local closeout

* Related task: P04-T02.
* Record:
  [.copilot-tracking/reviews/logs/2026-10-14/custom-governance-evaluation-review.md](../../reviews/logs/2026-10-14/custom-governance-evaluation-review.md).
* Review execution: Complete for supplied state/delivered local boundary.
* Outcome: Residual work. No substantive implementation finding in delivered
  local collection/grading or managed runner implementation; actual managed
  acceptance remains explicitly deferred, not passed.
* Decisions: Agent-owned automatic Review; walkthrough skipped automatically.
  Deferred managed proof, one live-agent case, and pre-existing legacy helper
  work remain distinct. No second plan critique or outcome Review occurred.
* Current delivery: Complete locally. Original full P04/T006/T007 managed
  acceptance remains unfinished under the user deferral.

### Installed local command and independent regression controls

* Related task: P02-T02; evaluation T005.
* Files: CLI, artifacts/collector, pyproject, ignore rule, README, CLI tests.
* Behavior: New private immutable run directory; distinct baseline/control
  JSONL, manifest/grader/policy and minimal results. Both baselines must pass;
  all 18 known controls require the exact declared violation/evidence-error
  outcomes. Failures exit nonzero, and incomplete baselines do not run controls.
* Validation: 50 focused tests and Ruff passed after syncing the changed
  manifest. Installed CLI passed with both 1.0 baselines and all 18 controls in
  `.local/evaluations/20261014T014817Z-f89f4571a536`. Cloud remains unexecuted.

### Actual isolated stdio enforcement evidence

* Related task: P02-T01; evaluation T002.
* Files: evaluation `worker.py`, `collector.py`, and collection tests.
* Behavior: Unchanged real server/tool; original-code/event-return observation
  installed for main/future threads. A transparent supervisor records actual
  child exit. SDK teardown bounds/reaps its process tree. Explicit environment
  blocks dotenv, Azure secrets/export and inherited governance configuration.
  Responses are inspected in memory and reduced to data/error states.
* Validation: 46 focused tests and Ruff passed, including both actual stdio
  variants, startup/deadline failure rejection, and original-body thread counting.
  The first real deny run exposed the SDK's exact sanitized error prefix; the
  response observer now explicitly recognizes it without permissive text matching.

### Shared deterministic grading and portable definition

* Related task: P01-T02; evaluation T003.
* Files: evaluation `evaluator.py`, `artifacts.py`, and `tests/test_evaluation.py`.
* Behavior: Bound independent manifest; exact event/identity/digest/version and
  operation/response checks. Valid violations return 0.0; unsupported, malformed,
  unhealthy, and failed evidence raises sanitized `EvidenceValidationError`.
  Generated managed adapter packages the same source and manifest, not input code.
* Validation: 36 focused tests and Ruff passed, including executed trusted
  generated-code parity, size/import boundaries, and altered expectation defense.

### Independent strict evidence and isolated policy fixtures

* Related task: P01-T01; evaluation T001.
* Files: [src/ai_governance_harness/evaluation/evaluator.py](../../../src/ai_governance_harness/evaluation/evaluator.py),
  [src/ai_governance_harness/evaluation/artifacts.py](../../../src/ai_governance_harness/evaluation/artifacts.py),
  [tests/test_evaluation.py](../../../tests/test_evaluation.py).
* Behavior: Strict minimal models reject coercion/extra profile fields and bind
  evidence to source/fixture/toolkit/grader versions plus an independent manifest.
  Isolated allow policy bytes match the package, while the named deny fixture
  blocks only the profile pre-tool stage and preserves startup/shutdown.
* Validation: Eight focused tests and Ruff passed. Actual stdio collection is
  not yet implemented and is not claimed by these tests.

## Implementation-Time Plan Updates

### Finish original scope before the single live-agent follow-up

* Affected areas: Current execution state and follow-up ownership.
* User decision: Finish the initial governance evaluation first; subsequently
  evaluate one real agent-level scenario through the existing `/api/chat` flow.
* Reconciliation: Preserve original scope, IDs, completed local work, and the
  one historical plan critique. Agent-level work is not an active plan task.
* Validation refinement: Complete queued-run deadline and malformed SDK-result
  coverage before accepting P03-T01. Full-suite execution found one pre-existing
  unused `typing.Optional` import in the member model; remove only that import
  as validation cleanup, without changing the model contract.

### Deliver locally for now without Azure operations

* Affected areas: P04-T01 execution permission, P04-T02 local handoff, and
  canonical T006/T007 outcome status.
* User decision: "can we keep things local for now without deploying to azure?"
  means retain completed local delivery and defer actual managed execution.
* Effect: No Azure authentication, deployment access check, evaluator
  registration, evaluation submission, or resource provisioning. Managed code
  remains available but unexecuted.
* Reconciliation: Preserve P01-P03 completion and original future managed
  acceptance; leave P04-T01/T006 and full P04 unfinished. Final local review can
  proceed through the already approved independent P04-T02 handoff contract.
  This is an execution deferral, not a claim of local/cloud parity or a second
  plan critique.

### Defer live-agent follow-up under the fully offline boundary

* User decision: Selected `fully_offline_defer_live` after the local handoff.
* Effect: No existing Foundry model inference, new Azure deployment, or
  hosted grading. The selected `/api/chat` target stays a future one-case
  workstream; no agent dataset, mock substitute, or live-agent result is claimed.
* Reconciliation: Parent Review decision RD-008 records the deferral; current
  plan/follow-up and session state match it. Local delivery remains complete.

### Critique-driven SDK and partial-handoff contracts

* Affected areas: P03-T01/P04-T02, dependency/SDK/readiness records.
* Change: Endpoint-only runner with verified dependency floors and separate
  partial handoff/review eligibility even if managed demonstration blocks.
* Reason/evidence: PC-001/PC-002 in the one completed plan critique.
* User direction: Direct implementation and automatic RPI; no application
  connection-mode change authorized.
* Reconciliation: Tasks, dependencies, requirements, summary, decisions, and
  critique dispositions are current. No closure critique ran.

## Validation Record

| Check | Scope | Status | Evidence/reason |
|---|---|---|---|
| Read-only instrumentation feasibility | Research | Passed | Original backend entries and real events observed across main/future threads; not stdio acceptance. |
| SDK contract/model serialization | Research | Passed | Projects 2.8/OpenAI 3.29 APIs and preserved extra error fields; no authenticated request. |
| Candidate structure/reference checks | Plan | Passed | Current task blocks, local references, markers, and single consumed critique gate. |
| Schema/policy fixture tests | P01-T01 | Passed | 8 tests; strict counts/extra fields, framed digests, and real toolkit named denial. |
| Ruff | Initial evaluation source/tests | Passed | No findings. |
| Shared/portable grader tests | P01-T02 | Passed | 36 tests including local/generated-code baseline, violation, and error parity. |
| Actual stdio/observer tests | P02-T01 | Passed | 46 tests including both subprocess baselines and startup/deadline failure rejection. |
| Actual local baseline/controls | P02-T02 | Passed | Installed command, two baseline 1.0 grades, 18 accepted controls; 50 tests. |
| Managed runner contracts/failure boundaries | P03-T01 | Passed | 37 tests; fake service/real SDK serialization only, not authenticated cloud evidence. |
| All evaluation tests | Implementation | Passed | 87 tests, including real isolated stdio collection and complete managed failure-boundary coverage. |
| Full repository tests | Implementation | Passed | Final 180 tests, including existing application behavior. |
| Full repository Ruff | Implementation | Passed | Pre-existing unused import removed without behavior change. |
| Package build/contents | Implementation | Passed | Rebuilt wheel; seven evaluation modules, policy/synthetic data and CLI entrypoint; no private artifacts. |
| Evaluation formatting/diff whitespace | Implementation | Passed | All eleven new Python files formatted; `git diff --check` clean. |
| Fresh installed local run | Final evidence | Passed | `.local/evaluations/20261014T023344Z-54be5b9885b2`; both 1.0 baselines and all 18 controls accepted. |
| Actual managed baseline/control runs | Managed | Skipped | User explicitly requested local-only delivery for now; no authentication or Azure operation performed. |
| Local no-submission report | P04-T02 | Passed | Installed confirmation gate retained `blocked` / `submission_confirmation_required`, zero runs and no cloud IDs. |
| Standard RPI outcome Review | P04-T02 | Complete | Delivered local scope conforms; outcome Residual work; actual managed acceptance deferred. |

## Pre-Review Reconciliation

* Plan/context: P01/P02/P03 and P04-T02 are accepted; P04-T01 is deferred.
* Work entries/handoff: Local/runner delivery and final validation are recorded;
  no-submission report and one completed scoped Review are retained.
* Validation/blockers/remaining work: Above and below.
* Review status: Local delivered subset reviewed. Actual managed acceptance is
  explicitly outside current delivery and remains unverified.

## Blockers

* No local implementation blocker.
* P04-T01: User-deferred local-only execution. Managed access/deployment remain
  unverified; future actual cloud execution needs a separate user decision.

## Remaining Work

* Current local delivery: No remaining implementation/review work.
* Deferred P04-T01: Actual authorized cloud baseline/control acceptance and
  dependent final managed documentation, only when separately resumed.

## Follow-Up Items

* Existing application helper's legacy connection-string/coordinate branches
  remain outside the endpoint-only evaluation runner and unchanged; a separate
  application-connection migration owns them.
* User-selected subsequent work: One agent-level end-to-end case through
  `/api/chat`, grading the final answer/task outcome rather than MCP enforcement.
  User subsequently deferred the live case to remain fully offline; scenario
  and rubric are not yet confirmed. Resume only when real model execution is authorized.
* Actual Foundry evaluation execution is deferred by the local-only decision.

## Return-to-Caller State

* Implementation: Local delivered scope complete; original full plan partial
  with actual managed work intentionally deferred.
* Validation: Accepted local/runner implementation and fresh real local evidence;
  180 repository tests, Ruff/formatting/whitespace checks, and rebuilt package
  contents passed. One RPI outcome Review complete; actual cloud proof deferred.
* Planning/critique: Ready, single completed critique, both findings resolved.
* Review status: Complete for supplied state/delivered local boundary; Residual
  work outcome. Full managed acceptance is not claimed.
* Continuation owner: Confirmed automatic RPI parent.
* Next action: None under current fully offline choice. Managed proof and
  live-agent work are separately deferred; no active implementation remains.
