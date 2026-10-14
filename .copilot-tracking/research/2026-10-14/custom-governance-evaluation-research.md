<!-- markdownlint-disable-file -->
# Task Research: custom-governance-evaluation

| Field | Value |
|---|---|
| Date | 2026-10-14 |
| Researcher / agent | RPI Research, automatic RPI parent |
| Output mode | convergence |

## Executive Summary

* Bottom line: Keep production enforcement unchanged and observe the original
  operation/event-recording code only inside dedicated stdio children. Use the
  installed projects 2.8/OpenAI Evals APIs with explicit evaluator-version
  binding, complete item results, and score/error separation.
* Why this matters: The evaluation can prove actual local tool enforcement
  rather than trusting verdicts or error messages, and can send the same
  independently graded evidence to Foundry.
* Research status: Complete; Wider, Deeper, and Contrarian waves executed.
* Confidence and uncertainty: High for local observation and SDK request
  contracts. Managed permissions and actual service error shape remain runtime
  prerequisites, not claimed successes or blockers to local implementation.

## What You May Not Know

The project virtual environment contains `azure-ai-projects` 2.8.0, while system
Python contains 1.0.0. Use the project environment for compatibility evidence.
Client construction does not prove Azure access.

## Findings

### Original operation entry can be observed without bypassing governance

An evaluation-only profiler can identify the original wrapped profile method's
code object and the real event store's return events. The runtime probe observed
the main thread and a future worker thread while leaving the original decorator
and toolkit unchanged. Production execution does not need an observer hook.

* Questions: Q1, Q3.
* Evidence state: Evidence-backed finding.
* Evidence: C2, C5-C7; two real operation entries and four policy allow events.
* Confidence and limits: High for Python 3.11 feasibility; implementation must
  exercise the actual MCP subprocess path and verify healthy probes, teardown,
  no wrapper-entry counting, and complete capture. A missing probe cannot prove
  zero execution. Source-level observation is not tamper-proof attestation.

### Managed APIs support pinned graders and independently identifiable items

Projects 2.8.0 exposes direct evaluator registration. Explicit
`evaluator_version` avoids silently selecting the latest definition. OpenAI
output items contain the source row plus results and item status; its models
also preserve additional error metadata during serialization.

* Questions: Q2.
* Evidence state: Evidence-backed finding.
* Evidence: C3-C4, C7-C8, W1-W4.
* Confidence and limits: High for installed SDK contracts and official examples.
  A placeholder-client probe is not authentication, registration, or a managed
  run. Code grading consumes mapped `item` data and does not require an agent
  target. Real service errors still need retained managed verification.

### Example success patterns must not replace this spec's stricter gate

The SDK example omits version pinning, uses unbounded polling, and deletes
results. Those choices conflict with our requirements. Likewise a generic MCP
error or numeric 0.0 alone does not establish an enforced deny or expected
malformed-evidence error.

* Questions: Q3.
* Evidence state: Evidence-backed finding.
* Evidence: C2, C8, W1-W4 and approved E003/E006/E008.
* Confidence and limits: High. The application sanitizes denied gateway calls,
  so acceptance must combine explicit matched-rule/event evidence, independent
  operation counts, and observed response state. Preserve baseline/control
  identities and classify absent/error results explicitly.

## Recommendation and Alternatives

* Selected: Evaluation-only profiling in fresh stdio children; a portable shared
  schema/manifest/grader; direct, version-pinned SDK registration and bounded
  precomputed-dataset evaluation.
* Rationale: This uses existing runtime boundaries and supported installed APIs
  without introducing production observer hooks, hosted services, or model calls.
* Could change: A supported Python version failing the real subprocess
  observation check, or a managed API refusing the verified schema/error contract.

| Option | Benefit | Risk | Evidence | Disposition |
|---|---|---|---|---|
| Observe original code in evaluation-only children | Real operation entry; no production changes | Must cover future worker threads and verify hooks | C6-C7 | Selected |
| Count the governed wrapper | Easy count | Counts denied requests as execution | C2 | Rejected |
| Infer denial from MCP error text | No instrumentation | Sanitized errors are not policy evidence | C2 | Rejected |
| Add production telemetry/tool endpoints | Easier remote collection | Expands approved surface | E007 | Rejected |
| Register latest evaluator and check run status only | Short SDK example | Wrong version, missing rows, or errors can pass | W2-W4/C8 | Rejected |

## Scope and Questions

* Goal: Close concrete implementation-readiness gaps for the existing small spec.
* Audience and use: Automatic RPI planning and implementation in this repository.
* In scope: Existing gateway, governance event recording, stdio startup/tests,
  installed Python/Foundry SDK contracts, and official evaluation documentation.
* Out of scope: Product features, MAF/container deployment, hosted transport
  assurance, Yakka runtime modifications, live member data, and cloud provisioning.
* Criteria: Preserve real policy enforcement, independently observe operation
  entry, keep evidence minimal, and distinguish grades from errors end to end.
* Requested output: Bounded evidence-backed recommendation supporting planning.

| ID | Question | Source | Status |
|---|---|---|---|
| Q1 | How can an isolated stdio child observe original operation entry and all real policy events without modifying production enforcement? | Approved E001-E003/E007 | Answered: code-object profiling in main and future threads. |
| Q2 | Which installed SDK contracts register a code evaluator, map precomputed evidence, and retrieve complete score/error results? | Approved E004-E006 | Answered: direct evaluator versions, Evals API, explicit version/mappings, paginated item serialization. |
| Q3 | Which apparent successes could falsely certify denial or managed completion, and how can the contract reject them? | Approved E006/E008 | Answered: absent probes, generic errors, self-authored expectations, latest-version drift, incomplete rows, and score-only checks. |

## Decisions and Feedback

| Group | Decision | Status | Owner | Rationale | Evidence | Impact |
|---|---|---|---|---|---|---|
| D1 | Keep `docs/spec/eval/`; implement directly without `yakka-execute`. | Confirmed | User | Explicit next-step selection. | Conversation | No root specs or routing changes. |
| D2 | Retain local plus managed scoring and isolated stdio subprocesses. | Confirmed | User | Explicit refinement answers. | Evaluation Discover | Both delivery paths remain required. |
| D3 | Automatic RPI with evidence-based ordinary decisions and required gates. | Confirmed | User | Explicit automatic-continuation answer. | Conversation | Parent owns eligible phase continuation. |
| D4 | Use evaluation-only code profiling and explicit managed version binding. | Resolved | Agent | Verified runtime/API contracts; preserves user constraints. | C6-C8/W2-W4 | Ready for task-level planning. |

## Risks and Open Questions

| Priority | Type | Item | Impact | Smallest evidence needed | Owner |
|---|---|---|---|---|---|
| H | Risk | A counter outside the original operation or absent observer can falsely report zero executions. | Invalid enforcement claim | Required real stdio positive/negative tests and unhealthy-observer rejection. | Implementation |
| H | Open question | Managed service access is unverified. | Actual cloud runs may be blocked | Authorized service check during implementation, without exposing credentials. | Implementation |
| M | Risk | A score of 0.0 can mean a violation or an evaluator error. | False control acceptance | Preserve item error state and verify exact error controls in the service. | Implementation |

## Planning Readiness and Next Step

| Field | Record |
|---|---|
| Research disposition | Executed; complete |
| Decision participation | Agent-owned ordinary decisions; user confirmed automatic RPI. |
| Planning Readiness | Ready for task-level planning; Q1-Q3 have supported contracts and explicit runtime checks. |
| Research depth and helpers | Wider, Deeper, and Contrarian complete; no helper used. |
| Blockers | No planning blocker. Managed access is a downstream gate; confirm externally visible actions before retained cloud runs. |
| Output mode and planning support | Convergence; supports planning after readiness. |
| Continuation owner | Confirmed automatic RPI parent. |
| Required gates | Complete research cycle, task-level plan, one independent standard critique, implementation evidence, review. |
| Next action | Automatic parent resumes RPI Plan; no implementation during this research phase. |
| Primary evidence file | `.copilot-tracking/research/2026-10-14/custom-governance-evaluation-research.md` |

## Research Record

### Method and Boundaries

| Field | Record |
|---|---|
| Research posture and provenance | Focused; bounded internal implementation with named sources and established scope. |
| Completion basis | Questions supported by exact runtime/API evidence; complete all three waves before synthesis. |
| Explicit limits or deadline | None supplied; no invented ceiling. |
| Codebase and external scope | Active repository and installed dependencies under `.venv`; official Microsoft and Python sources. |
| Initial candidate areas | Gateway decorator/original method, event-store `record`, stdio entrypoint/tests, SDK evaluator models/operations, evaluation item results. |
| Evidence root | Repository `.copilot-tracking/research`. |
| Constraints and exclusions | Read-only source inspection/probes; write only this research artifact; no secrets, resource provisioning, or inference. |
| Prior knowledge | Existing eval documents and directly inspected runtime are current. Prior MCP/toolkit research is historical context, not proof that its pre-change gap descriptions remain current. |

### Extensions and Participation

#### Extension Registry

| Kind | Candidate | Provenance and scoped contract | Selection |
|---|---|---|---|
| Instruction | `.github/copilot-instructions.md` | PRD-specific clarification preferences. | Not applicable: no PRD authoring. |
| Skill | `python-foundational` | Python implementation standards already loaded. | Reused as design criteria; no Python source changes in Research. |
| Skill | `evaluation-design` | Conversational-agent dataset design. | Skipped: fixed deterministic tool-enforcement cases, not conversational quality dataset design. |
| Skill | Security and supply-chain assessors | Assessment-specific guidance. | Skipped: no security audit or new framework selection. |

#### Direction and Participation Log

| Checkpoint | Direction | Answer or rationale | Effect |
|---|---|---|---|
| Intake | Implement approved small evaluation spec directly. | User selected direct implementation. | Yakka execution-routing blocker is inapplicable to this separately authorized coding route. |
| Continuation | Still use RPI. | User selected automatic RPI. | Agent-owned ordinary decisions; stop for required approval or unsupported material choices. |
| Prior-knowledge gate | Reuse current specifications and prior source reads. | Real gaps remain in instrumentation and exact managed APIs. | Execute only bounded new research. |

### Research Cycle Log

#### Cycle 1

* Active posture: Focused; preserve approved scope and read-only boundaries.
* Wider: Inspected existing gateway/event/stdio seams, installed evaluator/run
  signatures, and the official custom-evaluator registration example.
  Reflection: The installed SDK exposes `client.evaluators.create_version` and
  OpenAI Evals APIs directly, whereas documentation also shows a `beta` alias.
  Exact model fields/version binding and output-item error preservation need
  deeper verification. Evaluation-only profiling is a candidate for observing
  original operation code without replacing the enforcement wrapper.
* Deeper: A read-only probe counted two entries into the original wrapped profile
  method, one on the main thread and one in a newly created worker thread,
  while recording exactly four real gateway allow events. No wrapper or toolkit
  was replaced. Installed SDK schemas include explicit `evaluator_version`
  binding, datasource-item identity, numeric scores, and additional item fields.
  Reflection: Profiling both main and future threads is viable; missing probes
  and implicit dotenv/export settings must remain hard errors. An initial SDK
  response-module import guess failed and was corrected to the actual nested
  `openai.types.evals.runs` path; use verified contracts rather than guessed ones.
* Contrarian: Challenged score-only acceptance using a serialized 0.0 SDK result
  carrying `status=error`; verified those additional fields survive. Compared
  the upstream sample's latest-version, unbounded-polling, and deletion behavior
  with this spec and rejected them. Profile readiness, dotenv isolation, and
  worker-thread coverage remain binding negative checks.
* Synthesis and re-entry: Accepted verified child-only observation and pinned
  managed dataset grading; rejected wrapper counters, generic-error inference,
  and run-status-only acceptance. No further cycle is needed for planning:
  current contracts answer all questions, and actual managed access is a
  separately authorized implementation check rather than a research claim.

### Evidence Log

* Helpers: None.

| ID | Claim | Source/location | Retrieved/version | Tool | Confidence | Notes |
|---|---|---|---|---|---|---|
| C1 | User-approved evaluation contract defines isolated stdio plus managed grading. | `docs/spec/eval/discover.md`, Requirements and confirmed decisions | Not applicable | View/conversation | High | Approval is for direct implementation, not native Yakka dispatch. |
| C2 | Gateway decorator retains an original wrapped operation; real policy events are recorded centrally. | `src/ai_governance_harness/mcp_server/tools.py`, `governed_read_only_tool`; `governance/engine.py`, `_record_decision`; `governance/events.py`, `record` | Not applicable | View | High | Exact observation strategy remains Q1. |
| C3 | Project SDK/runtime versions are available without installation. | `.venv`, package metadata and `AIProjectClient` feature probe | 2026-10-14; projects 2.8.0, OpenAI 3.29.0, MCP 2.3.0 | Read-only Python probe | High | `get_openai_client` exists; `from_connection_string` does not. No authenticated request performed. |
| C4 | Installed project client exposes evaluator version creation and OpenAI Evals create/run/retrieve/paginated output APIs. | `.venv` SDK operation signatures | 2026-10-14; projects 2.8.0 / OpenAI 3.29.0 | Read-only introspection | High | Placeholder endpoint; no network call. |
| C5 | Telemetry exporter is configured only when its connection setting is present; dotenv is loaded by server configuration. | `src/ai_governance_harness/mcp_server/telemetry.py`, `configure_telemetry`; `mcp_server/config.py` | Not applicable | View | High | Child environment must explicitly prevent export and dotenv loading. |
| W1 | Code evaluator uses `code_text`, schemas, metrics, required runtime parameters, and `grade(sample, item)`. | https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/custom-evaluators | 2026-10-14; current article | Web fetch | High | Local contract verification still required; no service success implied. |
| C6 | Evaluation-only profiling observes original method calls and real event-store returns across main and future worker threads. | `SuperannuationDataGateway.get_member_profile.__wrapped__`; `GovernanceEventStore.record`; runtime `sys.setprofile` / `threading.setprofile` | 2026-10-14; Python 3.11 project runtime | Read-only probe | High | Two real direct calls produced two backend entries/four allow events; this is observation feasibility, not the required stdio evaluation demonstration. |
| C7 | Dotenv 1.2.4 supports `PYTHON_DOTENV_DISABLED`; installed criteria support evaluator-version pinning. | `.venv` dotenv implementation and evaluator/output model annotations | 2026-10-14 | Introspection | High | Set the flag before importing the package in the child. |
| W2 | Evaluator version is latest unless explicitly specified. | https://learn.microsoft.com/en-us/python/api/azure-ai-projects/azure.ai.projects.models.testingcriterionazureaievaluator | 2026-10-14; current reference | Web fetch | High | Pin returned registration version. |
| W3 | Current SDK sample uses direct `.evaluators.create_version` with projects 2.8.0. | https://raw.githubusercontent.com/Azure/azure-sdk-for-python/main/sdk/ai/azure-ai-projects/samples/evaluations/sample_eval_catalog_code_based_evaluators.py | 2026-10-14; current main sample | Web fetch | High | Sample uses unbounded polling/deletes reports; those behaviors conflict with our specification and are not adopted. |
| C8 | SDK preserves extra result error fields and serializes required code/schema/metric fields. | `.venv` `Result.model_validate/model_dump`; `EvaluatorVersion` / `CodeBasedEvaluatorDefinition.as_dict` | 2026-10-14 | Read-only model probe | High | No service request. |
| W4 | Results must be retrieved across pages; run terminals include completed, failed, and canceled. | https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/cloud-evaluation-results | 2026-10-14; current article | Web fetch | High | Deadline and per-call bounds are required additions to examples. |

#### Contradictions and Conflicts

Documentation's `beta.evaluators` examples coexist with the current 2.8 direct
API; the installed SDK and current official sample settle the implementation
surface. Historical MCP/toolkit research describes pre-change gaps and is
retained only as context, not current runtime proof. The sample's cleanup and
polling are examples, not authority to weaken the approved contract.

### Artifact Self-Check

* User-facing summary, findings, decisions, alternatives, and readiness are
  synchronized; all questions have answers and explicit verification limits.
* One complete three-wave cycle and its distinct reflections are recorded.
* C1-C8/W1-W4 preserve source/version provenance; no helper was used.
* Agent-owned ordinary decisions follow user-approved automatic RPI.
* Only this primary research artifact was written. No source files, credentials,
  cloud resources, or application configuration changed.
* Actual stdio evaluation, dual-version support, and managed service execution
  are not research completion claims; they remain implementation checks.
