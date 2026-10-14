<!-- markdownlint-disable-file -->
# RPI Changes: Agent-level evaluation

## Metadata

* Task ID: agent-level-evaluation
* Related plan: [.copilot-tracking/plans/2026-10-14/agent-level-evaluation-plan.md](../../plans/2026-10-14/agent-level-evaluation-plan.md)
* Implementation date: 2026-10-14

## Execution Status

* Status: Partial for the full plan; the first configured live attempt failed
  and exposed an SDK transport-observation gap requiring local correction.
* Declared invocation scope: full plan, with P04's live-inference gate retained.
* Completed scope markers: P01, P01-T01, P02-T02, P03-T01.
* Remaining markers: P02, P02-T01, P03, P03-T02, P04, P04-T01.
* Status basis: existing simulated checks and package evidence remain valid
  historical results. P02-T01/P03-T02 are reopened because the installed Foundry
  default transport is HTTPX 2, whereas the observer only covers HTTPX 1.
  The actual live run also has unresolved target/judge service errors.

## Execution Summary

Direct RPI has delivered contracts, isolated real-agent collection, a separate
structured judge, CLI/private reporting, eight calibration controls and local
checks using the approved nested Yakka specs. Existing uncommitted application
work is preserved. The user authorized local implementation, not actual
inference or the separately researched MAF/Azure Container Apps adapter.

## Completed Work

### Independent agent cases, facts, and binary gates

* Related task: P01-T01.
* Files: [src/ai_governance_harness/evaluation/agent_contracts.py](../../../src/ai_governance_harness/evaluation/agent_contracts.py),
  [src/ai_governance_harness/evaluation/agent-prompts.jsonl](../../../src/ai_governance_harness/evaluation/agent-prompts.jsonl),
  [src/ai_governance_harness/evaluation/agent-rubric.json](../../../src/ai_governance_harness/evaluation/agent-rubric.json),
  [tests/test_agent_evaluation_contracts.py](../../../tests/test_agent_evaluation_contracts.py).
* The two approved cases select independent default-policy oracles and four
  mandatory response criteria. Only requested trusted account facts are
  projected. Strict identities/types, real response excerpts, private-content
  preflight, complete probes and request-to-policy causal links prevent false
  passes. Logical calls and HTTP retry attempts remain separately observable.
* Validation: 35 focused tests and targeted Ruff passed. Staged packaged inputs
  passed data-mode disclosure scan with zero findings before persistence.

### Real isolated chat and HTTP MCP collection

* Related task: P02-T01.
* Files: [src/ai_governance_harness/evaluation/agent_worker.py](../../../src/ai_governance_harness/evaluation/agent_worker.py),
  [src/ai_governance_harness/evaluation/agent_collector.py](../../../src/ai_governance_harness/evaluation/agent_collector.py),
  [tests/test_agent_evaluation_collection.py](../../../tests/test_agent_evaluation_collection.py).
* Fresh owned Linux sockets and processes invoke the unchanged production
  chat/MCP routes. Original backend execution, completed request work,
  policy events, logical SDK requests and HTTP retry attempts are independently
  observed. Input denial retains the actual public HTTP error and zero
  target/tool/backend activity. Timeouts, unhealthy probes and cancellation
  cannot certify a pass; children and private temporary data are cleaned up.
* Model connection/authentication settings are forwarded only to chat/judge,
  not the MCP data process. No Azure operation or live inference was performed.
* Validation: seven real-route integration checks using explicitly simulated
  external model HTTP boundaries passed, including actual SDK retry accounting.

### Separate bounded structured response judging

* Related task: P02-T02.
* Files: [src/ai_governance_harness/evaluation/agent_judge.py](../../../src/ai_governance_harness/evaluation/agent_judge.py),
  [tests/test_agent_evaluation_judge.py](../../../tests/test_agent_evaluation_judge.py).
* An isolated configured judge receives only serialized case/rubric/reference
  data and the actual public response, never the policy gate. Versioned
  instructions, no tools, `store=False`, strict structured output and no SDK
  retries retain distinct criterion results and identifiable service/schema
  errors. Results bind to case/rubric identities and literal response excerpts.
* Malformed outer SDK replies were reproduced through real SDK HTTP handling;
  explicit revalidation prevents missing/null choices or messages from
  escaping as unhandled attribute/type exceptions.
* Validation: 22 judge tests and targeted Ruff passed. SDK calls use simulated
  external HTTP, not live calibration or verified service access.

### Explicit agent command, independent acceptance and private partial reports

* Related task: P03-T01.
* Files: [src/ai_governance_harness/evaluation/agent_runner.py](../../../src/ai_governance_harness/evaluation/agent_runner.py),
  [src/ai_governance_harness/evaluation/__main__.py](../../../src/ai_governance_harness/evaluation/__main__.py),
  [tests/test_agent_evaluation_runner.py](../../../tests/test_agent_evaluation_runner.py),
  [tests/test_evaluation_cli.py](../../../tests/test_evaluation_cli.py),
  [tests/test_chat_evaluations.py](../../../tests/test_chat_evaluations.py).
* `agent` requires separate explicit target/judge configuration and inference
  consent before processes or artifacts. Bounded synthetic input/output
  preflight and a fresh private `agent` subdirectory isolate this path from
  the unchanged offline command/button and managed command.
* Two known-good and six known-bad response controls have independent identities
  and intended failed criteria. Every baseline and control is allocated before
  execution, including not-run/cancelled/error outcomes. No average, favorable
  judge, malformed output or incidental service failure can produce acceptance.
* Reports retain independent policy and response outcomes, minimal evidence,
  configuration and all digests without full profiles/credentials. Cancellation
  retains completed collection and unrun rows. Existing bundles are never
  overwritten; test-only worker overrides explicitly label reports simulated.
* Validation: 49 runner/CLI/UI checks passed in 122.61 seconds, including an
  actual CLI/production chat/HTTP MCP/isolated-judge integration with explicitly
  simulated external HTTP. Targeted Ruff passed. No live inference occurred.

### Local regression, package and documentation delivery

* Related task: P03-T02; directly related usage portion of P04-T01 is documented
  without checking P04 or claiming live acceptance.
* Files: [tests/test_agent_evaluation_runner.py](../../../tests/test_agent_evaluation_runner.py),
  [tests/test_evaluation_cli.py](../../../tests/test_evaluation_cli.py),
  [tests/test_chat_evaluations.py](../../../tests/test_chat_evaluations.py),
  [README.md](../../../README.md),
  [docs/spec/eval/discover.md](../../../docs/spec/eval/discover.md),
  [docs/spec/eval/design.md](../../../docs/spec/eval/design.md),
  [docs/spec/eval/plan.md](../../../docs/spec/eval/plan.md).
* A larger injected prompt list retains every independent baseline and all
  separately identified controls. Unsafe input/output, output collisions,
  duplicate/missing/skipped rows, incorrect intended control criteria, favorable
  judges masking policy failure, service/schema errors, cancellation and
  artifact failure cannot become accepted results.
* Original offline CLI, managed grader/runner and browser evaluation contracts
  remain unchanged. Maximum new test modules: four; tests removed: none.
* Documentation describes explicit consent/configuration, schemas, private
  results, Linux support, bounded privacy detection, actual input-denial text
  and pending live acceptance. Specs record subsequent direct implementation
  consent and capture lifecycle `input` for YAML stage `pre_input`.
* Validation: 231 combined agent/offline/managed/chat checks passed in
  202.53 seconds, followed by two additional focused checks in 2.64 seconds.
  Repository lint, changed-file formatting and whitespace checks passed.
  Staged and durable documentation data-mode scans completed with zero findings.
* Wheel/sdist builds and exact asset/module checks passed. Extracted-wheel
  imports resolve both packaged inputs, synthetic reference facts, eight
  controls and the agent CLI without inference. The initial no-isolation build
  lacked `hatchling`; existing build tooling restored it in isolated environments
  rather than modifying application dependency manifests or the project venv.
* Repository-wide formatting reports 33 other files needing formatting.
  An unchanged tracked example also fails at `HEAD`; unrelated formatting
  changes were not folded into this feature. Changed evaluation files are clean.

## Live Acceptance Evidence

* The user executed a configured `gpt-5` target/judge run with explicit
  `--confirm-inference` and `.env` loading. Evidence:
  `.local/evaluations/agent/20261014T112408Z-8db2ca6a7883/agent-results.json`.
* The factual baseline returned HTTP 502, with `public_chat_failure`;
  collection failed and response judging was correctly skipped.
* The denied baseline returned the expected HTTP 403, matched the exact input
  deny rule, and passed its deterministic policy gate with score `1.0`.
  Its judge failed with `judge_service_error`, so the baseline was not accepted.
* All eight controls had `judge_service_error`, no numeric score and no accepted
  result. These are service failures, not rubric failures or successful controls.
* Exact provider status/error details were not retained by the current generic
  reporting. Do not infer authentication, permission, deployment or API causes.
* Read-only installed-SDK inspection establishes that
  `AIProjectClient._get_openai_http_client` constructs `openai.DefaultHttpxClient`,
  which inherits `httpx2.Client`. Its `send` is not `httpx.Client.send`, the
  only HTTP send code currently observed. Recorded zero HTTP attempts therefore
  do not prove that no real request was sent.
* Local credential metadata confirms Azure CLI and its config directory are
  available to the worker. Saved CLI token logs showed no matching error code;
  neither observation establishes current model access or its failure cause.
* No additional authentication, model call or Azure operation was performed
  during this diagnosis. No production source was changed.

## Implementation-Time Plan Updates

The one standard critique's PC-001 added privacy preflight before inference and
persistence. This is an in-scope clarification, not a new assessment or feature.
The user's MAF/Azure Container Apps compatibility question is future integration,
not permission to add a managed or external-agent adapter now.
Observe logical SDK calls and actual inference HTTP attempts separately so
SDK retries cannot hide target activity. This clarifies P02-T01's existing
independent request-count requirement without altering production retry behavior.
P03-T02 Guidance now names `run_agent`, `response_controls`, `accepted_outcomes`
and the explicitly simulated subprocess bootstraps. No scope, architecture or
user-owned gate changed; the original critique was not repeated.
The first actual SDK-backed attempt requires P02-T01 transport coverage and
P03-T02 regressions for HTTPX 2 as well as the existing HTTPX 1 simulation path.
This is a correction within approved capture requirements, not a scope expansion
or a reason to repeat critique. Provider-error diagnostics also need bounded
non-secret detail before an exact live service failure can be diagnosed.

## Validation Record

| Check | Scope | Status | Evidence/reason |
|---|---|---|---|
| Combined agent/offline/managed/chat regressions | P01-P03 local scope | Passed | 231 tests in 202.53 seconds |
| Expanded prompt list and artifact failure | P03-T02 | Passed | Two additional tests in 2.64 seconds |
| Contract tests and Ruff | P01-T01 | Passed | 35 tests; both targeted files clean |
| Collection/judge/contracts pytest and Ruff | P01-P02 local checks | Passed | 61 tests in 34.25 seconds; external model HTTP simulated |
| Malformed outer judge replies | P02-T02 | Passed | 22 judge tests in 11.24 seconds; targeted Ruff clean |
| Agent runner, CLI and offline UI parity | P03-T01 | Passed | 49 tests in 122.61 seconds; real routes and simulated external HTTP |
| Repository Ruff lint | `src`, `tests` | Passed | `ruff check src tests` |
| Changed-file format and whitespace | Evaluation source and related tests | Passed | 18 files already formatted; `git diff --check` clean |
| Repository-wide format | `src`, `tests` | Failed; pre-existing/out of scope | 33 other files; unchanged example reproduces at `HEAD` |
| Build backend | Initial no-isolation check | Unavailable, then resolved | Missing `hatchling`; isolated `build --installer uv` succeeded |
| Wheel/sdist and installed contracts | P03-T02 | Passed | Five modules, two assets, entrypoint, fixture imports and controls verified |
| Disclosure scans | Staged README/spec content and durable documents | Passed | Completed; data mode true; zero high/warn findings |
| Actual target/judge acceptance | P04-T01 | Unavailable | Separate inference confirmation/configuration not yet supplied |
| First user-executed live run | P04-T01 | Failed | Factual HTTP 502; denial policy passes; all judge calls have service errors |
| Actual Foundry transport observation | P02-T01/P03-T02 | Failed coverage; correction pending | Installed default uses HTTPX 2; existing observer covers HTTPX 1 only |

## Pre-Review Reconciliation

Historical simulated checks remain passed, but live transport coverage needs
correction and its regression checks before renewed local review readiness.
Full-plan acceptance remains unclaimed: the actual configured attempt failed
and no live calibration result exists.

## Blockers

* P04-T01: user-owned live configuration/confirmation gate. Do not authenticate,
  call models, provision, register evaluators, or submit managed runs implicitly.
* The live-consent question was cancelled. No configuration or inference
  authorization was supplied at that time. The user subsequently executed a
  configured live command; the failed evidence is recorded above.
* Current blockers: HTTPX 2 observation coverage and unresolved model/judge
  service errors. A further assistant-initiated network diagnostic or inference
  run is not implied by the user's request to explain the saved failure.

## Remaining Work

Correct P02-T01 transport coverage, extend P03-T02 checks, and retain bounded
provider error provenance without secrets. P04-T01 then needs actual passing
baselines/controls and final evidence-backed documentation.
Public T012/T013 remain incomplete until that evidence exists.

## Follow-Up Items

* Canonical list: [.copilot-tracking/plans/2026-10-14/agent-level-evaluation-plan.md](../../plans/2026-10-14/agent-level-evaluation-plan.md), Follow-Up Items.
* MAF/Azure Container Apps capture and managed agent-response rubric mappings remain outside this
  local increment; separate collector/oracle/judge contracts preserve the boundary.
* Repository-wide formatting cleanup is outside this feature. Existing owners
  can assess the 33 other files separately; no unrelated source was reformatted.

## Return-to-Caller State

* Implementation status: Partial, full plan.
* Validation coverage: 231 combined regressions plus two additional focused
  checks, lint, scoped formatting, disclosure and package checks passed.
  Repository-wide formatting has the disclosed pre-existing failure.
  Simulated model boundaries do not establish live target/judge acceptance.
* Planning/critique: Ready; PC-001 resolved without another critique.
* Review readiness: awaits transport coverage correction and its regression
  checks; full plan additionally awaits passing P04-T01 evidence.
* Continuation owner: direct coordinator for the in-scope capture/diagnostic
  corrections; any new assistant-initiated live operation needs clear consent.
