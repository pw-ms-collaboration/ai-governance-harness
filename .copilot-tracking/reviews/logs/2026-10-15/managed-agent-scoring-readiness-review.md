<!-- markdownlint-disable-file -->
# Review: Managed agent response scoring readiness

## Executive Summary

* Assessment: the proposed architecture is supported, but the current
  implementation is not ready for reliable managed end-to-end acceptance.
  Definition and adapter development can proceed after their explicit contract
  is recorded; capture correction must precede trustworthy live scoring.
* Review execution: Complete for this bounded readiness comparison.
* Assessed outcome: Not accepted as implementation-ready without qualifications.
* Findings: one High prerequisite defect and one Medium planning gap.
* Validation coverage: supplied historical results, current source, installed SDK
  introspection, and official documentation; no tests or cloud operations run.
* Limitations: no managed response implementation exists, actual registration and
  result transport are unverified, and current model-service access is unknown.

The user-owned Parent Decision Record accepts both proposed routes and records
the final readiness outcome. This is not a completed-implementation acceptance
review. Managed definition/adapter development need not wait for capture
correction, which gates trustworthy live acceptance.

## What You May Not Know

The existing managed evaluator grades deterministic stdio enforcement evidence,
not agent responses. The installed Foundry client uses HTTPX 2 while the observer
recognizes HTTPX 1. Also, the current production denial performs an authorized
semantic classification call before input enforcement. "Zero blocked executions"
must mean zero prohibited primary-agent/tool/backend executions after denial,
not zero model requests over the entire turn. The older agent plan and changes
record still describe the pre-classifier zero-target-request behavior.

Moving the response judge removes the need to repair the old local judge as a
managed-mode prerequisite. It does not resolve target/classifier service access
or prove that the managed judge deployment works.

## Findings and Proposed Routes

<!-- rpi:review id=RV-001 -->
### RV-001 [High]: The collector does not observe the actual Foundry transport

Complete execution evidence cannot currently be certified for the default
installed client. Moving the judge does not repair this local prerequisite.

* Related scope: real local execution, complete observation, deterministic
  enforcement; existing P02-T01/P03-T02 and FR-002/FR-004.
* Expected behavior: observe the actual SDK transport and retries, with required
  probes healthy and complete, while preserving production execution.
* Observed behavior and evidence: agent_worker.py:82 and :133-141 recognize only
  httpx.Client.send and httpx.Request. Installed azure-ai-projects 2.8.0 creates
  openai.DefaultHttpxClient whose MRO contains httpx2.Client; its send is not the
  observed send. The existing integration simulation explicitly supplies an
  HTTPX 1 client in tests/test_agent_evaluation_collection.py:35-111. The agent
  changes record already reopens these tasks after the failed live attempt.
  agent_contracts.py:329 policy_score requires HTTP attempts to cover logical
  requests, so the current gate rejects missing attempts rather than treating
  their zero count as valid proof.
* Impact: correctly executed cases cannot establish the required enforcement
  pass with default transport. Weakening the gate to permit that gap would
  produce unsound evidence.
* Resolution condition: end-to-end local-route capture observes the actual
  installed transport, its retry attempts and causal policy sequence, and rejects
  unsupported/unhealthy observation. Denial retains an allowed classifier call,
  the exact deny rule, and zero prohibited primary/tool/backend activity.
  Reconcile the older zero-target-call prose with the current semantic policy.
* Proposed destination: rpi-implement, existing capture/regression prerequisite.
* Smallest useful next action: reproduce using the default SDK transport at a
  controlled external HTTP boundary and correct capture before managed live
  acceptance. A further live network run requires explicit permission.

The changed semantic rule is already reflected in current policy_score and
collection tests: deny-identified-member-financial-recommendation, with
foundry.advice_classifier pre/post events followed by chat.input denial.
The stale plan prose is not evidence that the current oracle requires zero
classifier calls.

<!-- rpi:review id=RV-002 -->
### RV-002 [Medium]: Define a response-specific managed contract before reuse

The current managed adapter offers useful transport patterns, but cannot be
reused unchanged for four independent response criteria, explanations, and
cross-run definition reuse. This is a planning gap for the proposed increment,
not a defect against the older enforcement-only adapter's accepted scope.

* Related scope: versioned definitions, binary rubric preservation, managed-only
  response scoring, approved records, per-case scores/explanations/errors.
* Expected behavior: preserve all four applicable criterion IDs and conditions,
  pin reusable definitions, retain each criterion's outcome and explanation,
  and combine response acceptance with independent local enforcement.
* Observed behavior and evidence: foundry.py:127 creates a code-based single
  governance_enforcement metric. Its _result at :229 expects one numeric metric
  and drops reason; run_managed at :432 calls create_version on each invocation
  rather than selecting a previously pinned definition. agent_runner.py:286
  requires a local judge and invokes _judge for baselines and controls.
  CaseOutcome.accepted is coupled to JudgeEvaluation, whose result includes
  literal response evidence and an exact four-criterion schema. Official prompt
  evaluators document a single result/reason output; arbitrary JudgeResult JSON
  is not an established managed prompt output contract. No managed-response
  task-centered plan or adapter changes record was supplied.
* Impact: directly swapping APIs can lose individual failures and explanations,
  silently change provenance across runs, or run both response judges. A
  weighted score or aggregate pass rate would violate the user's all-pass rule.
* Resolution condition: record and implement an explicit response export,
  definition-registry, applicability, result-normalization, and acceptance
  contract. Validate it with managed good/bad controls and service-shape evidence.
* Proposed destination: rpi-plan, distinct managed-agent-response increment.
* Smallest useful next action: record the contract below in a task-centered plan
  before implementing it; do not mutate the old enforcement evaluator contract.

Recommended contract, not an approved implementation decision:

* Define eight prompt evaluators from the existing eight criterion IDs and
  pass conditions, one binary result plus reason per evaluator. Partition allow
  and deny records so only the four applicable definitions run. Do not generate
  a new weighted rubric or assign pass to irrelevant dimensions.
* Keep authoritative rubric conditions in versioned definitions. Bound and
  delimit prompt/response/reference data as untrusted inputs; preserve the
  existing anti-injection instruction boundary. Use the documented deployment
  and threshold parameters, then verify actual binary result types in the
  service rather than coercing arbitrary truthy values.
* Persist a reusable registry containing evaluator names, exact service versions
  and definition digests. Check digest/definition identity on reuse, create new
  versions only for intentional definition changes, and never bind "latest".
  Record rubric, instruction, dataset and policy digests and judge deployment
  provenance with each run.
* Export an allowlisted JSONL record containing row/case/run identity, category,
  synthetic prompt, expected behavior, actual public response or legitimate
  public policy-denial message, minimal trusted requested facts, approved
  execution metadata, and digests. Keep full profiles, intermediate transcripts,
  credentials, HTTP headers/bodies and unrestricted telemetry out. Reuse
  private_text and private non-overwriting writers; they are bounded preflight,
  not comprehensive DLP. Keep local enforcement evidence authoritative rather
  than asking the response judge to infer execution or override policy_score.
* Managed mode selects one response backend before execution, requires inference
  and submission consent, and never invokes judge_response or falls back to it.
  Retain the existing local mode and enforcement-only managed command.
* Normalize each case's four unique applicable criterion results, including
  score/verdict, reason, status, sanitized error, evaluator identity and row
  identity. Retrieve all pages; reject missing, duplicate, unknown, mismatched,
  malformed, skipped, errored and incomplete results. Do not reuse _result
  unchanged or claim managed reasons satisfy literal-excerpt checks without
  verifying that contract. Bound deadlines; retain IDs and partial outcomes for
  failed/cancelled runs and permit result retrieval without rerunning the agent.
* Case acceptance is complete healthy local capture AND policy_score == 1.0
  AND all four applicable completed error-free response criteria pass. No
  averages. Run acceptance also requires every expected baseline and calibration
  control outcome; a judge service error is not a successful negative control.
  Carry forward the two good and six bad controls, including injection.
* Acceptance evidence must cover zero local-judge invocation in managed mode,
  definition reuse/version mismatch, exact criterion applicability, privacy
  rejection before submission, enforcement failure despite favorable managed
  scores, missing/duplicate paginated results, provider errors, and cancellation.
  Separately authorized live evidence must establish target/classifier access,
  prompt evaluator registration, binary score/reason/error shapes and calibration.

## Parent Decision Record

### Current Disposition

* Based on events: RD-001 through RD-007.
* Decision participation: user-owned.
* Walkthrough: completed; RV-001 and RV-002 decided.
* Review execution: Complete for readiness.
* Final outcome: Defects found in the existing capture prerequisite. The proposed
  architecture is viable and ready for focused planning, followed by independent
  definition/adapter development. It is not accepted for live end-to-end
  acceptance until actual transport capture is corrected and remote behavior is
  established.
* Finding decisions and next actions: RV-001 accepted for later rpi-implement as
  a live-acceptance prerequisite; RV-002 accepted for a distinct focused
  rpi-plan managed-response contract. Capture correction does not
  block independent evaluator-definition or managed-adapter development.
* Decisions still needed: none for this review. No
  implementation, registration or submission is authorized by route discussion.

### Decision History

| Event | Subject | Decision source | Status or value | Proposed destination | Final destination | Owner | More information needed | Smallest next action | Rationale |
|-------|---------|-----------------|-----------------|----------------------|-------------------|-------|-------------------------|----------------------|-----------|
| RD-001 | participation | user request, standalone context | user-owned | none | none | User | none | Review readiness without implementation | No automatic RPI continuation was requested |
| RD-002 | RV-001 clarification | User question | pending; timing clarified | rpi-implement | pending | User / reviewer | Route decision remains open | Distinguish development start from trustworthy live acceptance | User asked whether this is needed from day one or merely defensive. Installed transport mismatch is demonstrated, but correction need not precede independent definition/adapter development; it must precede live acceptance. No implementation permission inferred. |
| RD-003 | RV-001 | User selected suggested action | accepted; gate live acceptance, not development start | rpi-implement | rpi-implement | Later implementer | Actual-transport capture and regressions | Correct capture before live acceptance; allow independent managed development | User explicitly approved the timing and route, not implementation execution or cloud operations. |
| RD-004 | RV-002 | User selected suggested action | accepted | rpi-plan | rpi-plan | Later planning parent | Focused managed-response contract | Plan the distinct managed increment without replacing the enforcement evaluator | User explicitly accepted focused planning as the route; no planning or implementation was started by this review. |
| RD-005 | walkthrough | Reviewer, derived from user answers | completed | none | none | Review parent | none | Close review | Both actionable findings have explicit user-owned dispositions. |
| RD-006 | execution | Review parent | Complete | none | none | Review parent | none | Return readiness assessment | Every material proposal item and qualification was assessed once within the bounded readiness evidence. |
| RD-007 | outcome | Review parent, reflecting evidence and approved routes | Defects found; ready for focused planning and independent managed development, not live acceptance | none | rpi-plan first; rpi-implement capture before live acceptance | User / later stage owners | Actual transport and authorized live managed evidence | Advise the accepted routes; do not invoke them | Capture defect remains real; the user explicitly chose not to make its correction a prerequisite for development start. |

## Validation Evidence

| Evidence | Scope | Status | Summary |
|----------|-------|--------|---------|
| Existing agent changes record | Historical local implementation | Supplied passed results | Reports 231 combined checks plus two focused checks; not rerun and not evidence of default HTTPX 2 coverage |
| Existing agent changes record, live attempt | Historical target/local judge | Failed as supplied | Factual baseline HTTP 502 and judge service errors; exact provider cause unknown |
| Current collection tests and policy_score | Semantic-classifier oracle | Source inspected | Authorized classifier activity is retained while primary/tool/backend execution after denial is zero |
| Installed SDK introspection | Default transport | Confirmed | Projects 2.8.0, OpenAI 3.29.0; default client uses HTTPX 2 and its send differs from the observed HTTPX 1 send |
| Installed SDK model introspection | Model metadata | Initial attempt failed, source inspection recovered | Private _fields attribute was absent; public signatures and transport factory source were then inspected; no application failure inferred |
| Official custom evaluator and JSONL/result docs | API feasibility | Documentation verified | Prompt result/reason, binary scoring, precomputed JSONL and paginated output retrieval supported |
| Tests, lint, package build | Current worktree | Not run | Read-only review; supplied validation assessed, not re-executed |
| Authentication, model calls, registration, managed submission | Remote acceptance | Not run | Review request does not authorize cloud writes or inference |

## Risks, Blockers, and Residual Work

* Blocker to trustworthy live acceptance: actual-transport observation, RV-001.
* Planning gap before the managed increment: response-specific contract, RV-002.
* Remote acceptance remains unverified: target and classifier access, evaluator
  registration permissions, managed judge deployment and actual result shapes.
  The prior local judge failure is not independently a managed-mode blocker.
* No source fix, plan mutation, remote registration or submission occurred.
* Direct Application Insights evaluation is not selected: current GenAI spans
  intentionally omit content. Keep that privacy boundary unchanged.
* MAF/container capture and unrelated formatting remain distinct follow-ups,
  not requirements of this local-agent managed scoring increment.

## Review Record

### Scope and Evidence

* Task ID: managed-agent-scoring-readiness.
* Review date: 2026-10-15.
* Review scope: readiness for the user's two implementation items and two qualifications.
* Assessed boundary: existing rubric, collector, runner, deterministic gate,
  managed adapter, CLI, telemetry, and official managed evaluator contracts.
* Review depth and provenance: standard; default.
* Candidate identity: user proposal plus current uncommitted evaluation implementation.
* Review execution: Complete.
* Helper use: none.
* Existing prerequisite plan: .copilot-tracking/plans/2026-10-14/agent-level-evaluation-plan.md.
* Existing prerequisite critique: .copilot-tracking/reviews/plans/2026-10-14/agent-level-evaluation-plan-critique.md.
* Existing prerequisite changes: .copilot-tracking/changes/2026-10-14/agent-level-evaluation-changes.md.
* Research: .copilot-tracking/research/2026-10-14/agent-level-evaluation-research.md
  and .copilot-tracking/research/2026-10-14/custom-governance-evaluation-research.md.
* Additional evidence: .copilot-tracking/changes/2026-10-14/semantic-advice-policy-changes.md,
  current evaluation modules, tests/test_agent_evaluation_collection.py,
  tests/test_agent_evaluation_contracts.py, tests/test_agent_evaluation_runner.py,
  chat/service.py, chat/genai_telemetry.py and governance/telemetry.py.
* No task-centered managed-response implementation plan or changes record was supplied.
* Official sources checked 2026-10-15:
  https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/custom-evaluators;
  https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/cloud-evaluation-datasets;
  https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/cloud-evaluation-results;
  https://learn.microsoft.com/en-us/python/api/azure-ai-projects/azure.ai.projects.models.promptbasedevaluatordefinition;
  Azure/azure-sdk-for-python sample_eval_catalog_prompt_based_evaluators.py.
  The fetched sample is illustrative: do not copy its unpinned version,
  unbounded polling, inconsistent parameter naming, or deletion of evaluators.

### Opening Review State

* Interpreted review goal: determine whether the proposed implementation has
  adequate contracts and prerequisites, and identify material gaps.
* Evidence readiness: existing local implementation and historical validation
  are available; managed response implementation and live acceptance are absent.
* Acceptance basis: preserve individual applicable binary criteria, version and
  reuse registered definitions, capture the real local chat/policy/MCP path,
  export only approved evaluation records, retrieve scores/explanations/errors,
  bypass the local judge in managed mode, and retain independent enforcement.
* First comparison boundary: source and supplied evidence establish readiness
  only, not a successful managed response run.
* Active read-only boundaries: write only this review record; preserve source,
  plan, critique, research, changes, and existing dirty worktree.
* Authority: reviewer owns evidence and proposed routes; user owns route decisions.
* Initial blockers: the existing changes record reopens capture/regression work
  and reports unsuccessful live target/judge access.

### Acceptance and Change Coverage

| Requirement or scope | Implementation and evidence | Assessment | Finding or rationale |
|----------------------|-----------------------------|------------|----------------------|
| Reuse rubric and preserve individual binary criteria | agent-rubric.json, AgentRubric, JudgeResult.checked_score; official prompt evaluator contract | Basis available; managed mapping needs definition | RV-002; four applicable IDs must remain independently visible |
| Version definitions for reuse | foundry.testing_criterion pins versions; run_managed always creates a version | Pattern reusable; registry/reuse missing for proposed mode | RV-002 |
| Real local chat/policy/MCP execution | collect_case, production chat builders, ExecutionObserver, current simulated HTTP integration | Actual transport coverage gap | RV-001 |
| Capture approved responses, facts and evidence | AgentEvidence, ReferenceFacts, private_text and collector isolation | Reusable local boundary; explicit managed projection needed | RV-002 |
| Submit JSONL and retrieve scores/explanations/errors | foundry._run and _result; official precomputed dataset/results docs | Transport pattern available; single-metric parser unsuitable unchanged | RV-002 |
| Do not invoke local response judge in managed mode | run_agent currently invokes _judge for baselines and controls | Required new backend selection and result acceptance contract | RV-002; absence is expected in existing local-only path |
| Export records, not all traffic | GenAI metadata-only spans and bounded governance telemetry | Qualification supported | Keep content instrumentation off; explicit preflighted dataset submission |
| Keep matched policy, complete observation, zero prohibited execution | policy_score and CaseOutcome.accepted | Correct logical separation; physical coverage incomplete | RV-001; classifier call is permitted, not blocked primary execution |
| Overall acceptance combines enforcement and response | accepted_outcomes and controls | Reusable semantics | RV-002 must preserve conjunction, completeness and calibration |
| Historical completion claims and failed live attempt | Agent plan/changes and semantic policy changes | Historical only; full-plan acceptance not established | Do not require old local judge success for new managed mode |

### Critique and Follow-Up Assessment

* Latest prerequisite critique PC-001 added before-inference/before-persistence
  private preflight; load_inputs, safe text validators and runner preflight
  implement the corresponding boundary. Managed export must preserve it.
* Material revision: semantic policy now allows classifier inference before
  denial. Current oracle/tests track it, but the older agent plan and changes
  prose do not. Reconcile those artifacts during prerequisite continuation.
* Dependent-work pause: this review makes no claim of completed dependent
  managed work. Definition design can progress independently of live capture;
  reliable end-to-end acceptance cannot.
* Justification: Foundry supports precomputed response grading and prompt
  evaluators. Nothing requires hosting the local agent in Foundry or exporting
  ordinary application content telemetry.

| Follow-up item | Why outside immediate scope | Owner or next action | Assessment and route |
|----------------|-----------------------------|----------------------|----------------------|
| MAF/Azure Container Apps capture | User specifies real local execution | Future adapter owner | Preserve distinct follow-up |
| Original managed response mapping follow-up | Previously excluded from local-only increment | Managed-scoring planner | Now the user's proposed increment, RV-002 |
| Unrelated repository formatting | Not a managed scoring readiness condition | Repository owners | Preserve existing separate follow-up |
| Live acceptance | Requires service access and explicit external-action consent | User and implementer | Acceptance prerequisite, not demonstrated implementation defect |

### Reviewer Self-Check

* [x] Every material item in the user's proposal and both qualifications has an
  assessment or explicit gap.
* [x] Findings distinguish prerequisite defect from new-increment planning gap.
* [x] Assessed execution and outcome, proposed routes and limits are explicit.
* [x] Source was inspected directly; no helper was used.
* [x] Standard comparison remained within readiness scope.
* [x] Only this review record was written; no tests, source edits, plan mutation,
  authentication, inference, registration or managed submission occurred.
* Checked boundary: user's two implementation items, two qualifications, local
  capture, semantic oracle, rubric, managed transport/results, privacy and consent.
* Missing evidence: managed-response task-centered plan/implementation and actual
  default-transport/live managed acceptance.
