# Plan: Custom Governance Evaluation Spike

Status: Original local delivery and RPI review complete; managed execution
deferred by user. Agent-level implementation and local checks are delivered;
authorized live acceptance remains pending.
Sources: [Discover](discover.md), [Design](design.md).

## Goal

Deliver one deterministic evaluator that verifies allow/deny policy enforcement
for a synthetic member-profile request through an isolated stdio MCP subprocess
and the real shared gateway.
Collect evidence locally, prove local grading and regression detection, and
register/run the evaluator in Foundry with retained row-level results.
The original completion boundary includes both local collection and managed
scoring. The user's latest decision is to keep delivery local for now without
Azure deployment/execution; managed scoring remains deferred rather than waived.

Extend this retained scope with a CLI-only local agent smoke suite: inject the
two confirmed synthetic prompts through the real chat agent/MCP path, independently
verify default-policy allow/input-deny behavior, and use live LLM judging of the
actual public answer/denial against mandatory binary rubric criteria.
The new agent milestone does not require a managed evaluation run and does not
complete or waive the original deferred managed milestone.

## Tasks

Task IDs remain local to this evaluation Plan. Removing the separate top-level
MVP files does not renumber these tasks or establish any execution result.
Statuses below reflect accepted results from direct RPI implementation. Actual
managed execution remains separately gated by cloud-action confirmation.
T001-T007 retain their identity, scope, status, and accepted historical evidence.
T008-T013 are new work; no original Done result satisfies their new requirements.
Implementation and simulated local checks are distinguished from live acceptance.

| Task | Work | Depends on | Done when | Status |
|---|---|---|---|---|
| T001 | Define the versioned evidence schema, independent case manifest, allow/deny expectations, and isolated test-policy fixture. | None | Both `MEM-001` variants specify tool/member, exact gateway decisions/rules/event sequence, independently calculated policy-byte digest, operation count, MCP error flag, and returned-profile state; observer readiness/completeness and baseline/control identities are defined; the test policy denies only the intended profile stage while preserving unrelated rules; strict validation distinguishes violations from malformed evidence. | Done |
| T002 | Implement isolated stdio MCP execution capture and independent profile-operation/response instrumentation. | T001 | One real request per fresh subprocess produces complete case-linked evidence with healthy observers; allow executes the original operation once with the exact gateway allow sequence and a successful profile response; explicit test-rule denial executes zero times, emits no request-level post-tool event, and returns an MCP error without a profile; observers exclude wrapper entry/startup loading and inspect all response representations; waits are bounded, children are reaped, and normal application behavior/live policies remain unchanged. | Done |
| T003 | Implement the shared `governance_enforcement` grader and sandbox-compatible code definition. | T001 | Valid baseline evidence scores 1.0; schema-valid violations score 0.0; malformed/unsupported evidence or failed collection errors explicitly; the grader validates the row against its bundled independent manifest and checks strict types, observer health, rules, enforcement/digest/order/count/MCP/return states; altered expected values cannot redefine a pass; the same managed definition needs no local project import or network access and meets sandbox limits. | Done |
| T004 | Verify the managed SDK/API contract and implement versioned Foundry registration, precomputed-row submission, bounded polling, and persistent result reporting. | T001, T003 | SDK/API compatibility is recorded before runner implementation, preserving supported existing connection behavior or obtaining migration review; requests use explicit item schema/mappings and required initialization parameters; mocked API checks cover authentication/submission errors, timeout, cancellation, all result pages, and missing/duplicate/skipped/errored results; artifacts preserve row scores/statuses, evaluation/run/report IDs, and resolved evaluator version without a local-success fallback. | Done |
| T005 | Run the local integrated baseline and evaluator regression controls. | T002, T003 | Exactly both actual stdio MCP baseline variants pass locally; incorrect decisions/allowed flags, execution/data after denial, wrong digests/rules, disabled enforcement, missing/extra/reordered events, and altered expectations score 0.0; malformed evidence and incomplete/failed capture are explicit errors; unrelated tool/startup errors or absent probes cannot pass as policy denial; baseline/control artifacts are separately identified, minimal, versioned, and repeatable. | Done |
| T006 | Verify authorized Foundry access and execute retained managed baseline/control runs. | T004, T005 | Actual project permissions and deployment/API compatibility are verified rather than inferred from client construction; exactly both baseline rows score 1.0 remotely without item errors; schema-valid violation controls receive completed 0.0 grades and malformed controls have the intended item errors, not unrelated failures/timeouts; local/cloud score/error outcomes agree; every result page, row identity, evaluator version, and report URL is retained. | Deferred by user |
| T007 | Document the repeatable local and managed evaluation commands and limitations. | T006 | Documentation matches the implementation, explains prerequisites and error/pass separation, identifies retained cloud evidence, and states that the two variants measure tool enforcement rather than live agent reasoning or production assurance. | Pending |
| T008 | Define the independent agent case manifest, versioned prompt-list contract, case-specific binary rubric, judge instructions/output schema, and separate agent artifact schema for E009-E014. | None | The allowed profile and input-denied advice prompts match Discover; required facts and policy/tool expectations are grounded in the synthetic fixture/default policy; exactly four mandatory criteria apply per case; prompt/rubric/reference provenance and strict validation are defined; source links and no-full-profile privacy boundaries resolve; user review and implementation gates are recorded rather than inferred from T001-T005. | Done |
| T009 | Implement isolated collection through the real local chat API, live target tool-calling runtime, and loopback HTTP MCP with independent observers for E009-E010 and E015. | T008 | Fresh conversations/process pairs collect the actual public answer/error, complete chat/gateway policy evidence, target/tool/backend counts, and policy/fixture versions; target selects tools without scripted intervention; input denial matches the exact default rule with zero blocked work; readiness/incomplete capture and generic service failures cannot pass; waits/cleanup/configuration are bounded and the development server is untouched. | Implemented; simulated-model integration checked |
| T010 | Verify judge API compatibility and implement the separate versioned LLM response judge for E011-E013. | T008 | Existing supported client behavior is preserved; the configured real judge can consume bounded delimited case data and emit the required structured criteria; local validation rejects missing/duplicate/unknown criteria, mismatched IDs, invalid labels/types, and fabricated excerpts; pass scores are derived from all criteria, errors have no score, untrusted response instructions have no authority, and target/judge identities remain separate. | Implemented; SDK checked, live compatibility pending |
| T011 | Wire the explicit agent CLI mode, deterministic agent-evidence gate, private reporting, and inference confirmation for E009 and E013-E015. | T009, T010 | Prompt/rubric/configuration validation and `--confirm-inference` are required before model calls; each case retains separate policy/response/error outcomes in a fresh agent-only bundle; aggregate acceptance requires every baseline and declared control's intended outcome; missing/duplicate/skipped/error results exit nonzero; offline `local`, managed submission behavior, and the existing Run Eval reader/button remain unchanged. | Done |
| T012 | Run agent/judge contract tests, known-good/bad regression controls, and an explicitly authorized live two-case acceptance run for E016. | T011 | Target/judge access and output compatibility are verified without provisioning; both actual agent baselines pass independent policy and all rubric gates; input denial has zero target/tool/backend work; good controls pass and every bad control fails its intended criterion; favorable judge labels cannot mask enforcement failures; failure-boundary/cleanup/offline regression tests pass; artifacts distinguish actual live evidence from test doubles and retain all attempts. | Local checks passed; live acceptance pending |
| T013 | Document the implemented agent command, prompt/rubric contract, live-inference prerequisites, result interpretation, and limitations. | T012 | Documentation matches accepted behavior and retained live evidence; describes the input-denied public error rather than a model refusal, CLI-only scope, explicit target/judge configuration, no-average gate, error separation, synthetic/privacy limits, and unchanged offline UI; managed execution remains explicitly deferred and no two-case production/benchmark assurance is claimed. | Usage documented; live evidence pending |

## Execution

Document authoring does not start implementation. The user reviews the documents
and explicitly requests execution separately. Record outcomes, changed files,
checks and blockers only from actual results; a failed or blocked prerequisite
prevents its dependent work from starting.

**Recorded execution consent:** the user approved the evaluation specification,
selected direct repository implementation without `yakka-execute`, and confirmed
automatic RPI. Implementation may proceed through the reviewed task-level RPI
plan and its gates. Native dispatch, resource provisioning, role changes, and
unconfirmed externally visible managed operations are not authorized.
The latest user decision explicitly keeps the current delivery local; do not
authenticate or perform any Azure operation until separately authorized.

**Agent-extension consent boundary:** the user confirmed a local application
suite using live target and judge models, the default-policy factual/advice pair,
mandatory binary criteria, and CLI-only access. This supersedes the earlier
offline-only assumption for the new agent milestone, not the default offline
suite or deferred managed work. The user subsequently approved direct RPI
implementation and explicitly requested continuation. That new approval
authorizes local implementation and checks on T008-T013, not inference or Azure
operations. Actual live execution still requires separate configuration and
explicit inference confirmation.

**Path eligibility:** the user approved retaining `docs/spec/eval/` as a small,
focused specification and removing `docs/spec/{discover,design,plan}.md`.
Native `yakka-execute` currently reads only those project-root files. It cannot
dispatch this nested evaluation Plan as-is. A reviewed routing solution is
required before native execution. Do not recreate root specifications, invent
runtime support, or emulate a failed native dispatch with manual implementation.
The separately approved direct RPI route is not a native-dispatch fallback and
does not require changing this folder.

**SDK readiness:** T004's compatible runner and mocked registration, data-mapping,
polling, and item-result contracts are accepted below. These results do not prove
actual service access; dependency bounds and connection-helper construction
alone also do not establish it. Preserve existing supported connection paths.

**Cloud readiness:** Azure authentication and service access have not been
verified for this evaluation. T001-T005 describe work that does not require
authenticated cloud access, but T006 cannot start until
authorized credentials, evaluator permissions, and a valid deployment are
available. If verification fails, record the actual blocker without changing
the expected governance behavior or substituting local scores.

T002 and T003 are independent after T001. T004 can be implemented against mocked
API boundaries while T002 is developed; mocked checks are not a managed-run
completion claim. T005 joins actual local collection and grading, and T006 joins
that evidence with the managed runner.

Run test-policy cases in isolated evaluation processes, not against the active
development server. Use the confirmed stdio transport with one request per
subprocess; no hosted HTTP path or model inference is added. Retain managed
reports and keep credentials and full profiles out of artifacts.
Isolate inherited settings and automatic `.env` loading so local evaluation does
not export telemetry to an unapproved destination.
The earlier authoring request alone did not authorize code or Azure operations.
The subsequent direct implementation consent is recorded above; obtain separate
confirmation before externally visible managed registration/submission.

That stdio/no-inference constraint belongs to T001-T007. T008-T013 deliberately
exercise the existing local chat/loopback HTTP MCP agent with live inference,
not hosted HTTP assurance. With the subsequent implementation approval, new tasks
proceed independently of deferred T006/T007 through the reviewed direct RPI route.
Contract/unit integration uses test doubles without authenticated cloud access;
T012's live acceptance remains blocked until target/judge access and explicit
inference confirmation are available. No mocked response fulfills it.

Baseline and control acceptance are distinct. Both baseline rows must pass.
Controlled violations must receive the intended completed 0.0 grade; deliberately
malformed controls must produce the intended explicit error. A completed managed
run, an aggregate score, or an incidental tool/grader failure is not sufficient.

**Recorded results:** T001-T005 are accepted. The fresh installed local
command produced both actual stdio baseline grades of `1.0` and all 18 intended
control outcomes in `.local/evaluations/20261014T023344Z-54be5b9885b2`.
The version-pinned managed runner and its 37 contract/failure-boundary tests are
accepted. The final full repository suite passed 180 tests; Ruff, formatting,
whitespace checks, and package build/content checks passed.
Mocked SDK results are not actual cloud evidence.

The earlier retained bundle remains historical evidence; the new bundle binds
the current source and is the managed submission input. T006 and dependent T007 are
unfinished until actual authorized managed acceptance and its documentation.
The latest user direction confirms finishing this original plan before a
separate single-case live-agent evaluation, with actual managed execution now
deferred to keep things local for now. No Azure resource was deployed, no
evaluator registered, and no evaluation submitted.

The one standard RPI outcome review is complete for the delivered local scope.
It identified no substantive local implementation defect. The original managed
acceptance remains deferred, so this is local completion, not full managed-spike
completion. Repeat local collection/grading with `ai-governance-eval local`.
The user also selected fully offline execution and deferred the subsequent
live-agent case; no mock reasoning result is substituted for that future work.

**Refinement and implementation history:** the preceding offline/deferred-agent
decision remains the original delivery boundary. Agent-level refinement was
subsequently approved for direct RPI implementation and continuation.
The local agent command, independent collector/oracle, structured judge, eight
response controls, private partial reporting and usage documentation now exist.
Real chat/MCP routes and isolated judging were checked with explicitly simulated
external model HTTP boundaries. No live inference, live judge calibration or
managed run has occurred. No task IDs are retired or reused.

T009 and T010 are independent after T008. T011 joins their collectors/judge with
the deterministic agent gate and reporting. T012 joins the implemented CLI with
real live acceptance; T013 depends on that evidence, not on deferred cloud
registration. T007 remains the original pending managed documentation task and
does not block these new tasks.

## Done

**Original managed spike:**

All tasks have accepted actual results: exactly both real local stdio MCP variants
pass; controlled violations receive completed 0.0 grades and malformed evidence
receives explicit errors locally and remotely; the versioned custom evaluator
runs successfully in Foundry; complete baseline/control scores, item statuses,
identities, and report URLs are retained; and the documented demonstration is
repeatable.

Local-only grading or document readiness is not completion of the managed
evaluation spike. This result does not certify member-level authorization,
model behavior, financial-advice safety, or production compliance.

**Agent-level local milestone:** completion requires accepted actual results for
T008-T013, both named baselines run through the real isolated agent with live
configured target/judge models, passing deterministic enforcement and every
required binary criterion, known-good/bad controls with their declared outcomes,
and retained private versioned reports plus repeatable documentation. The denied
baseline's target-model count is zero by design; its public error is still judged
by the live judge.

Agent milestone completion does not imply T006/T007 completion, managed scoring,
hidden-reasoning correctness, a statistically representative benchmark, or
production certification. Revised documents, mock tests, or an aggregate judge
score alone do not complete either milestone.
