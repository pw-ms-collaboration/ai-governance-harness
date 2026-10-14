<!-- markdownlint-disable-file -->
# Task Research: agent-level-evaluation

| Field | Value |
|---|---|
| Date | 2026-10-14 |
| Researcher / agent | Direct RPI coordinator using rpi-research |
| Output mode | convergence |

## Executive Summary

Current sources support implementing the approved suite with separate strict
agent contracts, evaluation-only original-code observation in isolated local
chat/MCP subprocesses, and a separately configured structured-output judge.
The user explicitly selected direct RPI from docs/spec/eval/; native Yakka is not
being dispatched or modified. Research is complete and planning is ready for
local implementation. Actual live target/judge acceptance remains gated on
inference confirmation and deployment access.

## What You May Not Know

The approved denial occurs before target-model inference. Its public error
message must still be judged by the live judge, independently of policy evidence.
The policy YAML stage `pre_input` becomes an `input` lifecycle event in captured
application evidence. Checking for a literal `pre_input` event would falsely
reject correct enforcement.

## Findings

### Preserve the real application and observe original execution

The existing collector/worker establishes a transparent profile-observer
pattern, isolated configuration, and private writers. Real chat and HTTP MCP
builders can run in fresh subprocesses with dedicated observers and normal
governed tool execution. Questions Q1 and Q4 are answered by C1-C5 and C8-C9.
Evidence state: evidence-backed finding. Confidence is high for local integration
boundaries; complete capture and cleanup still need implementation tests.

### Separate the oracle, public response, and judge

Trusted fixture bytes provide the minimal requested reference independently of
model output. Strict prompt cases can select allow/deny expectations while the
bundled rubric remains authoritative. The judge sees public answer/error text,
not an intermediate model draft or the deterministic gate verdict. Questions Q2
and Q4 are answered by C1, C4, C6, and C8-C9. Evidence state: evidence-backed
finding. Caller-provided prompts must remain synthetic, bounded, and consistent
with reviewed expectations.

### Client support is not deployment readiness

OpenAI 3.29.0 provides JSON-schema response formatting, explicit request timeout,
and retry configuration. A local judge can validate identity, four criterion
labels, brief rationale, and actual response excerpts. Q3 is answered for client
implementation by C7. Evidence state: evidence-backed finding for the installed
SDK; actual deployment support is unresolved until an authorized live request.

## Recommendation and Alternatives

Select separate agent contracts, production app builders in isolated processes,
independent original-code probes, a local structured judge, and private agent-only
artifacts. This follows the approved design without altering normal chat/MCP
behavior. A materially different deployment/API contract could require re-entry.

| Option | Benefits | Risks | Evidence | Disposition |
|---|---|---|---|---|
| Real isolated chat/MCP with independent probes | Measures actual user-visible policy path and tool selection | Needs careful coroutine observation and process cleanup | C2-C9 | Selected |
| Direct model response evaluation | Existing payload examples | Skips tools, chat policy, and real denial | C4 and approved design | Rejected |
| In-process mocked agent as completion evidence | Fast contract tests | Cannot establish real target/judge acceptance | C8-C9 | Tests only |
| Dashboard snapshots as evidence | Already available | Bounded, reverse-ordered, incomplete request attribution | C2-C3 | Rejected |

## Scope and Questions

Goal: establish sufficient current evidence to implement E009-E016 and
T008-T013 without weakening enforcement or changing offline evaluation.
Audience: implementers and reviewers of this synthetic-data demonstration.
In scope: chat/MCP execution, isolated collection, case/rubric contracts, judge
SDK output, independent evidence gates, private artifacts, CLI, and tests.
Out of scope: native Yakka changes, moving specs, UI work, managed submission,
resource provisioning, live member data, and unauthorized inference.
Criteria: real user-visible response; independent complete policy/operation
evidence; strict binary rubric validation; explicit errors and consent.

| ID | Question | Source | Status |
|---|---|---|---|
| Q1 | Which current execution and observer boundaries can collect real agent behavior without altering production telemetry? | Approved E009-E010 and E015 | Answered: C1-C5, C7 |
| Q2 | How can prompt/rubric/reference contracts remain strict and independent while permitting caller-supplied prompt lists? | Approved E011-E014 | Answered: C1, C4, C6 |
| Q3 | Which installed client contract supports structured local LLM judging and explicit failure reporting? | Approved E012-E013 | Answered for implementation: C7; live deployment remains gated |
| Q4 | Which regressions and contrary paths must prevent false passes and preserve offline behavior? | Approved E013-E016 | Answered: C4, C8-C9 |

## Decisions and Feedback

| Group | Decision | Status | Owner | Rationale | Evidence | Impact |
|---|---|---|---|---|---|---|
| D1 | Preserve docs/spec/eval/ and use direct RPI, not native Yakka | Confirmed | User | User selected direct_rpi after routing review | Current conversation | Authorizes direct implementation |
| D2 | Default-policy profile allow and advice input deny; binary criteria; CLI only | Confirmed | User | Approved refinement scope | docs/spec/eval/ | Fixes behavior boundary |
| D3 | No managed work or live inference now | Confirmed boundary | User | Live acceptance needs separate confirmation and configuration | docs/spec/eval/plan.md, Execution | Gates remote acceptance |
| D4 | Use evaluation-only profiling, independent fixture projection, and structured local judging | Selected | Coordinator | Existing contracts support the approved runtime without changing production telemetry | C1-C9 | Ready for bounded planning |

## Risks and Open Questions

Live deployment access and structured-output support need verification before
actual model acceptance. They need not block local contract/integration work.
Implementation must not confuse unhealthy zero-count probes with enforcement or
an API error with a legitimate refusal.

## Planning Readiness and Next Step

| Field | Record |
|---|---|
| Research disposition | executed |
| Decision participation | Agent-owned ordinary technical choices within the user's approved direct implementation; user retains scope and inference decisions |
| Planning Readiness | Ready for local implementation planning; C1-C9 cover material boundaries |
| Research depth and helpers | Wider, Deeper, and Contrarian completed in order; no helpers |
| Blockers | None for local implementation; live access/consent remain acceptance prerequisites |
| Output mode and planning support | convergence; supports planning only after Ready |
| Continuation owner | Direct RPI coordinator authorized by the user |
| Required gates or confirmations | Research complete; task-level plan/critique still required; live consent separately retained |
| Next action | Coordinator enters rpi-plan for the approved implementation |
| Primary evidence file | .copilot-tracking/research/2026-10-14/agent-level-evaluation-research.md |

## Research Record

### Method and Boundaries

| Field | Record |
|---|---|
| Research posture and provenance | Focused from the brief: bounded extension with named approved source targets and fixed behavior |
| Completion basis | Questions covered by current sources, counterexamples examined, and no material implementation gap remains |
| Explicit limits or deadline | None supplied; no artificial cycle ceiling |
| Codebase and external scope | Current repository and installed SDK signatures; official API documentation when needed |
| Initial candidate areas | evaluation collector/worker/artifacts, chat service/API, MCP tools/runtime, governance events/context, foundry client, tests |
| Evidence root | .copilot-tracking/research/ |
| Constraints and excluded sources | Read-only research; no .env contents, credentials, remote authentication, inference, or external code disclosure |
| Prior knowledge | Existing tool-enforcement research/history is retained but does not establish new agent/judge readiness |

### Extensions and Participation

#### Extension Registry

| Kind | Candidate | Provenance and scoped contract | Disposition |
|---|---|---|---|
| Skill | yakka | User request and route review | Selected for the spec/execute boundary; native execution declined in favor of direct RPI |
| Skill | evaluation-design | Prior spec refinement | Existing scope/rubric guidance; no full benchmark dataset is generated |
| Instruction | copilot-tracking | Matching evidence root | Selected for dated evidence and stable phase/task markers |
| Instruction | BRD/HVE Builder guidance | Artifact type does not match | Skipped; this is application evaluation work |
| Skill | Additional security/planner skills | No requested security assessment or new risk classification | Skipped; preserve implementation boundaries |

#### Direction and Participation Log

| Checkpoint | Direction | Answer or rationale | Effect |
|---|---|---|---|
| Intake | Start work with Yakka if no functional refinement remains | User request | Inspect execution readiness before dispatch |
| Routing | Keep nested evaluation specs | User selected direct_rpi | No file migration, extension modification, or native-dispatch claim |
| Technical decisions | Use current evidence within fixed scope | No unresolved product question at intake | Coordinator can select ordinary implementation details |

### Research Cycle Log

#### Cycle 1

Active posture: focused. Fixed two-case CLI suite; no live inference or managed
operations during research.

##### Wave 1: Wider

The existing collector has an explicit environment allowlist, fresh process
isolation, strict manifest/evidence models, and private non-overwriting writers.
The evaluation-only worker uses Python profiling hooks to observe original
operation entry and actual recorded event returns, without replacing policy
wrappers. C1-C3 establish reusable boundaries.

Reflection: retain the same observation strategy but require dedicated chat/MCP
request capture and separate schemas. The bounded dashboard is insufficient.
Inspect async-call resumption, HTTP process shutdown, model-client signatures,
and synthetic reference projection in the Deeper wave.

##### Wave 2: Deeper

ChatService enforces input before client construction and MCP connection. The
input-denied case therefore needs no target client but still needs the real chat
API error contract. The allowed path discovers tools, invokes the original
OpenAI completion method, chooses the profile tool, calls HTTP MCP, sanitizes the
answer, and enforces output. The requested fixture facts are balance 145000,
Accumulation phase, Growth allocation 0.7 and Australian Shares 0.3.

Installed OpenAI 3.29.0 accepts `response_format`, `store`, `timeout`, and
`max_completion_tokens`; MCP 2.3.0 `Client.call_tool` is a coroutine. A profile
observer must count a coroutine frame once rather than once per resumption.
The original synchronous operation can be counted and its minimal returned
account projection captured independently of the verdict.

Reflection: use the real application builders in evaluation-only subprocesses,
dedicated original-code observers, and bounded per-case reports. Structured JSON
judging is supported by the client interface, but deployment support remains a
live prerequisite. Examine false passes and privacy/isolation alternatives next.

##### Wave 3: Contrarian

The current UI reader requires exactly two stdio baselines and 18 controls; agent
bundles must live under a separate non-run-ID agent directory. Reusing that reader
or its schema would misreport results. A generic HTTP 403 or model content filter
cannot satisfy the expected input-deny oracle. Unready/failed probes cannot
prove zero calls. Production events use `input`, not the YAML `pre_input` stage.

The alternative direct-model runner misses the real agent path; test doubles
are legitimate contract evidence only. OpenAI SDK configuration does not prove
service access. These counterexamples support the selected boundaries rather
than widening scope. Reflection: retain explicit per-stage errors, strict
identity/completeness gates, and a separately authorized live acceptance step.

##### Synthesis and Re-entry

Accepted: separate schema, original-code observation, minimal independent
reference facts, public response/error grading, strict no-average gates.
Rejected: model-only baseline, fabricated refusal, dashboard-only trace,
unhealthy zero-count proof, and mixing agent bundles into the offline UI reader.
Deferred: actual remote inference/deployment compatibility until confirmation.
No second cycle is needed for local planning: the fixed questions are covered,
counterexamples examined, and further remote evidence requires retained consent.

### Evidence Log

Helpers: none.

Current repository sources will be recorded with stable C identifiers; any
external sources will use W identifiers and retrieval dates.

| ID | Claim | Source or location | Retrieved/version | Tool | Confidence | Notes |
|---|---|---|---|---|---|---|
| C1 | Strict independent manifests and minimal private artifacts already exist | src/ai_governance_harness/evaluation/evaluator.py, StrictModel and GovernanceEnforcementEvaluator; artifacts.py, write_json | Current worktree | view | High | Reuse helpers, not the stdio evidence schema |
| C2 | Original operation and event-return observation avoids replacing runtime enforcement | src/ai_governance_harness/evaluation/worker.py, ExecutionObserver | Current worktree | view | High | New agent capture needs additional probes |
| C3 | Current isolation excludes dotenv and credentials by default | src/ai_governance_harness/evaluation/collector.py, isolated_environment | Current worktree | view | High | Agent execution needs an explicit approved model-auth allowlist |
| C4 | Chat input denial precedes model-client creation; HTTP error text is the user-visible denial | src/ai_governance_harness/chat/service.py, ChatService.complete; chat/app.py, chat | Current worktree | view | High | No fabricated model refusal |
| C5 | Real HTTP MCP startup/cleanup and public apps exist | src/ai_governance_harness/mcp_server/__main__.py, run_server; chat/__main__.py, main; tests/test_mcp_transports.py | Current worktree | view | High | Reuse apps and policy lifecycle, not a model-only surrogate |
| C6 | Trusted account facts are independently available | src/ai_governance_harness/data/synthetic/accounts.json, MEM-001; mcp_server/tools.py, SuperannuationDataGateway.get_member_profile | Current worktree | view | High | Keep only the three requested fields |
| C7 | Installed SDK accepts structured response payloads and MCP calls can resume | OpenAI 3.29.0 Completions.create signature; MCP 2.3.0 Client.call_tool signature | Installed local environment; no service call | inspect.signature | High for client interface | Actual deployment compatibility unverified |
| C8 | Offline UI schema is deliberately fixed to stdio evidence | src/ai_governance_harness/chat/evaluations.py, LocalResults; tests/test_chat_evaluations.py | Current worktree | view | High | Separate agent artifact directory/schema required |
| C9 | Policy stage and captured lifecycle names differ | src/ai_governance_harness/governance/models.py, LifecyclePoint; governance/policies/default.yaml; advice_request_policy_data probe | Current worktree; no model call | view and local classification | High | Approved allow maps to passed; advice prompt maps to personal_advice_requested; captured denial is input |

#### Contradictions and Conflicts

Native Yakka cannot read the nested specs or accept the existing deferred task
table. The user explicitly selected a different direct RPI execution route.

### Artifact Self-Check

All template sections are present without unresolved placeholders. Questions,
findings, provenance, alternatives, confirmed decisions, all three waves,
counter-evidence, research disposition, and planning readiness are recorded.
No helper, native dispatch, authentication, inference, or managed run occurred.
The research-only write boundary held. No further user decision is needed for
the fixed local implementation; live acceptance remains explicitly gated.
