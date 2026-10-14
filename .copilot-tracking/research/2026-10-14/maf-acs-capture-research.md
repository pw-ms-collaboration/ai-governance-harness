<!-- markdownlint-disable-file -->
# Task Research: MAF/Azure Container Apps capture requirements

| Field | Value |
|---|---|
| Date | 2026-10-14 |
| Researcher | rpi-research |
| Output mode | research-only |

## Executive Summary

The user confirmed that ACS means Azure Container Apps (ACA). Supporting that
target needs a remote agent invoker, runtime/backend recorders, and a versioned
evidence adapter. ACA adds revision/replica attribution, network/authentication,
and durable collection requirements. Research is complete for this design-only
question; actual API, language/version, policy configuration, and permissions
remain inputs for a future integration. No application/spec changes, Azure
authentication/provisioning, or model inference occurred in this research phase.

## What You May Not Know

The existing process-local profiler is not a remote connector. Python MAF has
experimental Agent Hooks with a payload-free `record_sink`, but hosted
provider-executed tools do not pass through its local tool enforcement seam.
An answer-only endpoint permits response evaluation, not proof of zero
downstream execution. Telemetry absence must not be treated as a healthy zero.

## Findings

### The target is Azure Container Apps, not the ACS specification

The user's answer selects Azure Container Apps. Native Agent Control
Specification is not a prerequisite implied by this question. Earlier source
checks of that specification remain provenance only; policy capture must match
the actual agent's configured governance runtime. Q1's hosting identity is
confirmed by the user.

### Hosted-agent protocol adapters exist independently of ACS

Foundry's MAF hosting documentation exposes Responses and Invocations protocols.
This is evidence-backed for that particular hosting product, W2, not a claim
that every ACS-governed MAF agent has those endpoints or automatic capture.

### Runtime controls need separate agent, model, and tool boundaries

MAF documents separate agent-run, chat-client, and function middleware (W3).
Backend execution is still a distinct observation from framework function
invocation. Existing harness instrumentation independently observes actual
backend code and real decision records (C1-C3); a remote equivalent must retain
that distinction. Evidence-backed; actual hook registration is version-specific.

### The remote policy adapter must preserve the actual governance contract

The harness uses pinned AGT 4.1's `agentmesh.governance.PolicyEngine` with YAML
stage mapping (C4). A remote MAF adapter needs explicit lifecycle/decision
mapping for its actual runtime; it need not migrate policy engines merely
because the host is Azure Container Apps. Evidence-backed current contract;
the remote runtime is not supplied.

### A remote capture contract needs six capabilities

These are derived requirements, not implemented interfaces or approval to
change the existing local acceptance:

| Capability | Required behavior |
|---|---|
| Invocation | Invoke the actual agent, not its model; authenticate with least privilege; use a fresh run/session and pinned deployment; return the actual public response/error and terminal status; bound waits/cancellation. |
| Policy observations | Record applicable lifecycle points, policy/manifest/bundle identities, actual enforcement mode, verdict/reason/provenance, transforms/errors, and enforcement outcome; preserve native distinctions rather than guessing local stage/rule equivalents. |
| Execution observations | Independently count actual target inference attempts, framework tool invocations, and backend operation executions; link tool success/minimal requested facts to trusted fixture truth; identify tool attempts blocked before execution separately. |
| Correlation/completeness | Propagate evaluation/case/run/session/trace identities through agent, model, MCP, and backend; preserve each producer's order and causal links; positively report probe health and finalized counts/events, including failure/cancellation. Missing or delayed evidence is an error. |
| Minimal normalization | Version the remote contract separately from the existing stdio grader; retain prompt/rubric/instruction/policy/fixture/deployment/build digests and minimal response/facts; never retain credentials, full snapshots, profiles, or chain-of-thought. |
| Evaluation bridge | Apply an independent policy oracle and separate response judge; a good refusal cannot override unwanted execution. Map complete precomputed rows to Foundry code/prompt evaluators or an endpoint-based judge, not a network call inside the code grader. |

Questions Q2-Q3; evidence-backed derived requirements, C1-C5 and W1-W8.
Backend call instrumentation and trustworthy collector closure are application
requirements, not guarantees inferred from MAF telemetry alone.

For the current two synthetic scenarios, an allowed response needs the requested
real profile execution/facts and an allowed policy path; input denial needs the
expected policy denial, the actual public denial, and healthy zero model/tool/
backend counts. A deny after model or tool execution is a different scenario,
not equivalent evidence for input denial. Judging is outside target activity.

### MAF has useful hooks, but support depends on the actual execution path

Python's documented Agent Hooks bundle coordinates agent, model, tool, streaming,
and persistence boundaries and emits per-session ordered payload-free audit
records through `record_sink`. It is experimental and cooperative, not a
sandbox. .NET uses its distinct middleware/native ACS adapter surfaces.
Pin compatible versions and verify each chosen path rather than infer parity
from the framework name. Evidence-backed, W3 and W5-W7.

Hosted/provider-executed tools bypass local MAF function interception. Likewise,
automatic MCP trace propagation covers client-opened transports, not provider-
managed connectors. Backend/service-side evidence is needed for those paths;
otherwise enforcement collection is unavailable, not passed. W4 and W7.

### Foundry grading does not collect remote enforcement automatically

Foundry supports deterministic code and prompt-based or external endpoint
evaluators; code graders have no network access. Collection must precede
grading, or live elsewhere in the orchestration, and use explicit mappings.
Foundry reports grader exceptions with error status as well as a numeric zero;
do not reinterpret that as a genuine binary policy violation or accepted control.
Evidence-backed, W8. The current stdio grader needs a remote oracle/schema
adapter or separate grader; raw ACS records are not compatible automatically.

### ACA adds deployment, replica, and evidence-delivery requirements

ACA exposes the HTTP API served by the image; it does not itself define a MAF
request schema or supply a Foundry agent endpoint. Use the actual application
protocol and auth audience from a network location that can reach ingress.
Distinguish ACA auth/ingress rejection from a governed input denial. Bind cases
to the intended revision/image, configured target model, policy and synthetic
fixture version. Label URLs can move, so verify actual serving identity.
Evidence-backed platform facts and derived capture requirements, W9-W13.

Keep every case's conversation fresh without restarting shared ACA replicas.
Propagate case/run/session/trace identity through each service; gather across
replicas in a shared protected evidence sink, or expose authenticated retrieval
of finalized captures. Local container files are ephemeral and replica-local
(W14), so they cannot be the only durable record.

Enabling ACA's managed OpenTelemetry agent doesn't instrument the application
(W12). Ordinary traces can be sampled away (W15) or lost in export (W16).
Use payload-free policy/execution records with positive recorder health,
ordering and finalization; wait within a bounded evidence-arrival deadline.
Timeout, restart, missing evidence or unfinished work must remain explicit
collection errors, not healthy zero calls. A local HTTP timeout is not proof
that a remote run or in-flight backend operation has stopped.

Store the actual public response, minimal requested synthetic facts, counters
and version/provenance data. Keep telemetry sensitive-data capture disabled;
do not export full context, tool profiles, tokens or hidden reasoning. MAF's
client-opened MCP context propagation can help, but provider-managed connectors
still need service/backend-side attribution (W4, W7).

### The minimum remote extension is not a rewrite of scoring

The existing local run path remains intact. The new capability would collect
equivalent agent-level evidence from a remote target, then apply a separately
reviewed remote oracle and the same rubric semantics. Response lists and
criterion IDs are reusable; local process-exit/profile-hook and exact `/api/chat`
HTTP assumptions are not. Preserve the target's actual public error/streaming
protocol rather than manufacture an HTTP 403 or refusal during normalization.
This is a derived design boundary, C1-C4/W2-W3/W7-W9, not an approved spec change.

## Recommendation and Alternatives

No implementation selection or planning handoff requested.

| Option | What it establishes | Limitation | State |
|---|---|---|---|
| Invoke endpoint and judge answer | Response quality/refusal semantics | Cannot establish tool/backend policy enforcement | Viable for response-only evaluation, not full governance acceptance |
| Invoke and collect runtime plus backend evidence | Response and independent enforcement gates | Requires hooks, backend observability, and explicit completeness | Full-governance capability boundary described, not an approved implementation |
| Query existing observability dashboard | Operational diagnostics | Sampling, bounded windows, asynchronous delivery, and correlation gaps | Not sufficient as the sole enforcement oracle |

## Scope and Questions

* Goal: explain what MAF capture on Azure Container Apps must provide.
* In scope: public invocation, runtime/tool evidence, identity/completeness,
  minimal persistence, and Foundry scoring boundaries.
* Out of scope: application/spec changes, provisioning, authentication, inference,
  managed evaluator registration, or implementing a connector.
* Criteria: judge the actual public response; independently establish policy
  enforcement; never infer zero activity from missing telemetry.

| ID | Question | Status |
|---|---|---|
| Q1 | Which invocation/session boundary does the user's ACS agent expose? | User confirms Azure Container Apps; endpoint/session contract still deployment-specific |
| Q2 | What independently captured facts must the MAF runtime and backend provide? | Answered by six-capability contract and hook limitations |
| Q3 | How does remote capture feed existing and Foundry grading without false passes? | Answered; a new normalized evidence/oracle mapping is required |

## Decisions and Feedback

* User explicitly requested explanation without implementation.
* The user explicitly selects Azure Container Apps. Revalidate service-specific
  claims under this confirmed interpretation.
* No change to approved local evaluation acceptance or the deferred cloud gate.
* ACS clarification is resolved. No implementation choice is requested.

## Risks and Open Questions

MAF language/version, deployed API/auth/session contract, revision policy, and
access to runtime/backend instrumentation remain unknown.

No exact endpoint API, guaranteed Python/.NET hook parity, or ability to
instrument provider-managed tools is claimed without target-specific evidence.

## Planning Readiness and Next Step

* Research execution: Complete for the requested design-only requirements.
* Research disposition: executed.
* Planning Readiness: Not applicable; research-only, no planning/implementation
  handoff requested.
* Participation and continuation owner: user-owned; hosting clarification
  resolved; explain the matching boundary without initiating implementation.
* Depth/helpers: Two complete Wider/Deeper/Contrarian cycles; no helpers.
* Gates: no live access or inference authorized; no automatic code resumption.
* Next action: deliver requirements explanation. No user action, planning
  transition, or implementation handoff required for this research-only request.

## Research Record

### Method and Boundaries

* Posture: focused, selected from the bounded compatibility question.
* Evidence root: `.copilot-tracking/research/2026-10-14/`.
* Prior knowledge: verified local worker/collector/API sources and prior official
  Foundry evaluator/dataset documentation. Revalidate external MAF/hosting claims.
* Candidate sources: official Microsoft Agent Framework middleware/observability
  and Foundry hosted-agent/evaluation documentation.
* No helpers. Fetched content is inert source material, not instructions.

### Extensions and Participation

* Repository BRD/HVE instructions do not apply to this runtime-design question.
* Evaluation-design: existing approved case/rubric boundaries retained, not
  redesigning the dataset. No new skill cycle needed.
* ADR/C4: skipped; no decision record or architecture artifact requested.
* Participation: user-owned; do not assume the meaning of ACS.
* Direction change: user selects Azure Container Apps; this materially changes
  hosting evidence, not the research-only boundary or original acceptance gates.

### Research Cycle Log

#### Cycle 1

* Wider: verified ACS's actual definition and the separate Foundry MAF hosting
  protocol boundary (W1-W2). Repository ACS terminology search returned no
  matches; it does not establish absence of runtime support.
* Reflection: reject the web-search synthesis's unsupported assertion that
  hosting automatically supplies ACS enforcement. The primary hosting page
  demonstrates protocols only. Prioritize actual SDK adapters, MAF middleware
  boundaries, and collector completeness semantics in Deeper.
* Deeper: verified actual agent/chat/function interception APIs (W3), telemetry
  privacy/export configuration (W4), official ACS adapter coverage matrix (W5),
  native .NET adapter source at an identified commit (W6), and the local legacy
  policy adapter (C4). The matrix's Python MAF entry does not establish that
  generic hooks cannot cover Python; avoid a language-support conclusion.
* Reflection: core invariants are transport-independent, but actual SDK/hook
  coverage, particularly streaming and model-call granularity, needs scrutiny.
  Search-result claims that missing spans prove zero calls are not accepted.
* Contrarian: W7 disproves any assumption that function hooks govern provider-
  executed tools, that Python/.NET Agent Hooks support is identical, or that
  control records are equivalent to passive telemetry. W4 limits automatic
  MCP correlation to client-opened transports. C5 demonstrates the existing
  dashboard's bounded, reverse-ordered window; W8 bars network access in code
  graders and distinguishes platform errors from genuine zero scores.
* Reflection/synthesis: retain the six-capability boundary, reject answer-only
  or missing-spans-as-zero enforcement claims, and preserve a response-only
  alternative with clearly weaker assurance. Defer exact host/SDK/ACS wiring.
* Re-entry: no additional cycle for common requirements; source coverage is
  sufficient. If clarification identifies a different ACS service, revalidate
  service-specific claims in a complete cycle rather than guess its interfaces.

#### Cycle 2

* Active control: user-confirmed Azure Container Apps. Still design-only.
* Wider candidates: ACA ingress/application protocol, Entra authentication,
  revisions/traffic/replicas, OpenTelemetry/audit export.
* Deeper targets: fresh session/revision binding and runtime-to-backend evidence.
* Contrarian targets: container metrics/logs as enforcement proof, timeout as
  remote cancellation, mixed revision/replica attribution, automatic Foundry
  model configuration or ACS policy support.
* Wider completed: W9 verifies ingress/network and session-affinity options,
  W10 immutable revisions with mutable traffic/labels and multiple replicas,
  W11 per-replica auth sidecar before application handling.
* Reflection: use the application's actual HTTP protocol rather than a
  platform-assumed agent endpoint. Pin and validate revision/build identity;
  a label URL alone isn't immutable. Auth-sidecar denial is not application
  policy denial. Prioritize evidence export across replica/revision boundaries.
* Deeper completed: W12 confirms ACA managed OpenTelemetry routing still
  requires application instrumentation. W13 confirms runtime configuration is
  revision-bound; W14 confirms container/replica files are ephemeral and
  replica-local. Correlate per-run records in a protected shared/durable sink
  or retrieve an explicitly finalized capture, not whichever replica answers
  a later read request. Persistent Blob storage via SDK is a possible sink,
  not a claim that ACA supports Blob filesystem mounts.
* Reflection: neither enabling the managed telemetry agent nor saving a JSON
  file in the container supplies complete durable enforcement evidence.
  Challenge missing-spans-as-zero and network-timeout-as-cancellation claims.
* Contrarian completed: W15 confirms unsampled spans are not exported; W16
  documents telemetry loss even with queues/retries/persistence. W9's HTTP
  timeout is not a cancellation acknowledgment from the agent. W10 label
  mutability and W14 replica-local ephemeral files rule out endpoint URL or
  container file presence as sufficient reproducibility/completeness evidence.
* Synthesis: accept the remote invoker/runtime recorder/shared capture adapter
  boundary; reject ACA platform telemetry as automatic enforcement proof,
  refusal-only acceptance, and remapping auth errors into policy denials.
  Defer exact transport/SDK/policy wiring until those target inputs are supplied.
* Re-entry: not needed for this explanation; platform and framework requirements
  are covered. Re-enter only for a supplied endpoint/protocol or SDK version that
  could change the concrete integration. No cloud verification claim is made.

### Evidence Log

* C1: `src/ai_governance_harness/evaluation/worker.py`,
  `ExecutionObserver`: original-code profiling is local to its child process.
* C2: `src/ai_governance_harness/evaluation/collector.py`,
  `collect_case`/`isolated_environment`: stdio child and independent capture
  readiness/exit checks; no remote MAF invocation.
* C3: `src/ai_governance_harness/chat/app.py`, `chat` route:
  captures the real public message or policy error rather than a synthetic refusal.
* W1: Microsoft, Agent Control Specification: Portable runtime governance,
  https://commandline.microsoft.com/agent-control-specification-runtime-governance/,
  retrieved 2026-10-14; worked example uses specification 0.3.1-beta.
* W2: Microsoft Learn, Host Microsoft Agent Framework agents as Foundry hosted
  agents, https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/framework-hosted-agents,
  retrieved 2026-10-14; page updated 2026-09-21.
* C4: `src/ai_governance_harness/governance/engine.py`,
  `GovernanceEngine`/`_TOOLKIT_STAGE_BY_LIFECYCLE`: legacy toolkit policy engine
  and lifecycle-to-YAML mapping; `pyproject.toml` pins toolkit 4.1.0.
* W3: Microsoft Learn, Agent Middleware,
  https://learn.microsoft.com/en-us/agent-framework/concepts/agents/middleware/,
  retrieved 2026-10-14; updated 2026-08-25.
* W4: Microsoft Learn, Observability,
  https://learn.microsoft.com/en-us/agent-framework/agents/observability,
  retrieved 2026-10-14; updated 2026-09-20.
* W5: Official ACS adapter matrix,
  https://github.com/microsoft/agent-governance-toolkit/blob/47abed7446d47e74cfa76d01a5913bb873ffcad9/policy-engine/docs/adapter-matrix.md,
  retrieved 2026-10-14 through GitHub API at the indexed commit.
* W6: Official native .NET MAF ACS adapter,
  https://github.com/microsoft/agent-governance-toolkit/blob/47abed7446d47e74cfa76d01a5913bb873ffcad9/policy-engine/sdk/dotnet/src/AgentControlSpecification.AgentFramework/AgentControlAgentBuilderExtensions.cs,
  retrieved 2026-10-14 through GitHub API; streaming overload delegates directly
  to the inner agent while non-streaming is wrapped. Do not generalize beyond
  that version/file; it demonstrates why path-by-path coverage must be checked.
* C5: `src/ai_governance_harness/governance/events.py`,
  `GovernanceEventStore.snapshot`: bounded process-local window, newest first,
  not a complete distributed run stream.
* W7: Microsoft Learn, Agent hooks,
  https://learn.microsoft.com/en-us/agent-framework/agents/agent-hooks,
  retrieved 2026-10-14; updated 2026-09-15. Session IDs, ordered records,
  `record_sink`, enforce/evaluate-only distinctions, experimental Python
  support, and explicit hosted-tool/cooperative-boundary limitations.
* W8: Microsoft Learn, Custom Evaluators,
  https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/custom-evaluators,
  retrieved 2026-10-14; updated 2026-08-26.
* W9: Microsoft Learn, Ingress in Azure Container Apps,
  https://learn.microsoft.com/en-us/azure/container-apps/ingress-overview,
  retrieved 2026-10-14; updated 2026-08-31.
* W10: Microsoft Learn, Update and deploy changes in Azure Container Apps,
  https://learn.microsoft.com/en-us/azure/container-apps/revisions,
  retrieved 2026-10-14; updated 2026-02-26.
* W11: Microsoft Learn, Authentication and authorization in Azure Container Apps,
  https://learn.microsoft.com/en-us/azure/container-apps/authentication,
  retrieved 2026-10-14; updated 2026-07-08.
* W12: Microsoft Learn, Collect and read OpenTelemetry data in Azure Container Apps,
  https://learn.microsoft.com/en-us/azure/container-apps/opentelemetry-agents,
  retrieved 2026-10-14; updated 2026-06-04; managed agent preview.
* W13: Microsoft Learn, Manage environment variables on Azure Container Apps,
  https://learn.microsoft.com/en-us/azure/container-apps/environment-variables,
  retrieved 2026-10-14; updated 2026-04-03.
* W14: Microsoft Learn, Use storage mounts in Azure Container Apps,
  https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts,
  retrieved 2026-10-14; updated 2026-08-21.
* W15: OpenTelemetry documentation, Sampling,
  https://opentelemetry.io/docs/concepts/sampling/,
  retrieved 2026-10-14; unsampled spans are not processed/exported.
* W16: OpenTelemetry documentation, Resiliency,
  https://opentelemetry.io/docs/collector/resiliency/,
  retrieved 2026-10-14; queue/retry exhaustion, crashes and storage failures
  can lose telemetry; queues are not a guarantee of complete per-run evidence.

### Contradictions and Conflicts

Search synthesis expanded ACS inconsistently and described missing spans as
proof of zero calls. Neither was accepted. W1 supplies a documented definition,
but user intent is still a separate question; W4/W7 establish instrumentation
and control limitations. The adapter matrix's Python entry is not used to
deny Python MAF support: W7 documents a generic, experimental Agent Hooks path.

### Artifact Self-Check

User-facing sections, question/evidence mappings, alternatives, participation,
ordered three-wave cycle, no-handoff state, and explicit gaps are current.
Every external source was verified at its primary location; no helpers or
executable validation ran. Untrusted material remained inert and no secrets
were retained. Research-only write boundaries held. The ACS user clarification
is resolved and both cycles are complete. Concrete endpoint, MAF version,
policy runtime and permissions remain explicitly unknown, not blockers to the
requested high-level explanation. No live integration validation is claimed.
