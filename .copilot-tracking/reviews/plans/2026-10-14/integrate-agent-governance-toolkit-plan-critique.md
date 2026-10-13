<!-- markdownlint-disable-file -->
# Plan Critique: Integrate Microsoft Agent Governance Toolkit

## Critique Metadata

| Field | Record |
|-------|--------|
| Task ID | `integrate-agent-governance-toolkit` |
| Plan | `.copilot-tracking/plans/2026-10-14/integrate-agent-governance-toolkit-plan.md` |
| Research | `.copilot-tracking/research/2026-10-14/integrate-agent-governance-toolkit-research.md` |
| Date | 2026-10-14 |
| Depth | standard |
| Depth provenance | RPI default; no user request for deep critique |
| Critique type | initial |
| Execution status | Complete |
| Verdict | Revise |

## Assessment Boundary

The critique assessed the supplied plan and research across user direction,
FR-001 through FR-009, NFR-001 through NFR-008, all phase/task goals and
requirements, dependency sequencing, test ownership, local-first constraints,
feed portability, Public Preview containment, and the upstream limitations
recorded as W1-W11. It did not perform additional research or test toolkit APIs.

## Coverage Assessment

The plan has a credible architecture and correctly rejects wholesale copying,
unreleased 5.0, automatic inheritance of upstream OWASP ratings, and unapproved
cloud/privileged providers. It also identifies the load-bearing boundaries and
locks semantic validation. Four contradictions or missing completion conditions
must be corrected before implementation can safely begin.

## Findings

### PC-001 — Policy-input minimization contradicts argument-aware enforcement

| Field | Record |
|-------|--------|
| Severity | High |
| Related IDs | FR-002, FR-004, NFR-004, P02-T01, P02-T02, P03-T01 |
| Evidence | FR-004 says decisions must not receive member IDs, prompts, arguments, or results, while P02 requires pre/post model and tool decisions, argument constraints, transforms, and revalidation. Those decisions cannot evaluate content-dependent policy if the snapshot never receives the relevant bounded value. |
| Impact | An implementer must either violate FR-004 or reduce policy enforcement to metadata-only decisions, undermining the stated lifecycle and tool controls. |
| Smallest useful change | Separate policy-evaluation data from telemetry/audit data. Permit the in-memory decision snapshot to receive the minimum validated content required by a rule, classify/redact sensitive fields before upstream evaluation where possible, prohibit persistence, and keep raw values out of logs, metrics, traces, and evidence. Name which lifecycle points are metadata-only versus content-aware. |
| Action owner | planner |
| Resolving evidence | Revised FR-004, NFR-004, P02 and P03 requirements with a consistent data-handling contract and semantic tests proving raw values are not emitted. |
| Decision need | Direct planner correction; no user response required. |

### PC-002 — Mandatory enforcement versus optional package installation is ambiguous

| Field | Record |
|-------|--------|
| Severity | High |
| Related IDs | FR-001, NFR-003, P01-T01, P01-T02, P06-T01 |
| Evidence | P01 requires adding toolkit packages but does not state whether they are mandatory runtime dependencies or an optional project extra. The rollback switch and provider deferrals further blur whether `ai-governance-dev` can start ungoverned. Upstream initialization bypass is a documented high risk. |
| Impact | The application could install or start without the governance runtime while still appearing operational, recreating the exact bypass the plan intends to prevent. |
| Smallest useful change | Declare core toolkit, CLI/protocol, and policy sandbox contract dependencies mandatory for ordinary project installation; keep only privileged provider extras optional. Require startup/readiness to fail when governance is enabled but unavailable, and restrict any bypass to tests with an explicit non-hosted development setting that is visibly degraded. |
| Action owner | planner |
| Resolving evidence | Revised dependency and startup requirements in P01/P06 plus acceptance tests for missing package, missing policy, forbidden hosted bypass, and visibly degraded local bypass. |
| Decision need | Direct planner correction; confirmed user direction favors broad active integration. |

### PC-003 — SRE phase has no completion route if the released API is absent

| Field | Record |
|-------|--------|
| Severity | Medium |
| Related IDs | FR-006, P01-T01, P04-T01, Planning Readiness |
| Evidence | P04 requires a toolkit-backed circuit breaker but permits recording the capability as blocked when the 4.1 API is unavailable. The plan nevertheless treats P04 as active required work and gives no replan/stop rule or alternative released package resolution. |
| Impact | Implementation could mark the plan complete without FR-006 or stall after broad wiring with no credible completion path. |
| Smallest useful change | Make the P01 proof spike a hard dependency decision: identify the released package/API that owns the circuit breaker and add it to the pinned set, or stop and revise the plan before P02. P04 cannot complete with the capability merely recorded as blocked. |
| Action owner | planner |
| Resolving evidence | P01/P04 requirements name the proof result as a gate and define `blocked -> return to Plan`, with no completion claim until FR-006 is implemented and semantically tested. |
| Decision need | Direct planner correction; no user response required. |

### PC-004 — Agent Goal Hijack validation is too indirect for the requested breadth

| Field | Record |
|-------|--------|
| Severity | Medium |
| Related IDs | FR-008, NFR-006, P05-T01, P05-T02, ASI01 |
| Evidence | P05 requires a complete evidence matrix and toolkit verification but the locked semantic test list covers allow/deny/transform/failure/circuit/sandbox behavior, not adversarial input, prompt-injection resistance, or goal integrity. Research explicitly records that the toolkit governs actions rather than reasoning and that upstream ratings are not certification. |
| Impact | The repository could label ASI01 implemented based on policy presence or toolkit CLI output without a test that challenges the actual chat boundary. |
| Smallest useful change | Add bounded adversarial prompt fixtures and assertions proving injected user/tool content cannot expand the tool catalog, bypass required tool use, alter system scope, or suppress final guardrails. Record ASI01 as partial unless those runtime outcomes are decided; never treat a static scan as proof of reasoning safety. |
| Action owner | planner |
| Resolving evidence | Revised P05/test contract naming adversarial semantic cases and the evidence-matrix rule that ASI01 remains partial where only action governance is proved. |
| Decision need | Direct planner correction; no user response required. |

## Severity Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 2 |
| Medium | 2 |
| Low | 0 |

## Highest-Impact Finding

PC-001 is highest impact because the current requirements simultaneously demand
content-aware enforcement and forbid the policy engine from receiving the values
needed to decide it. Correcting the in-memory decision versus emitted evidence
boundary removes that contradiction without weakening privacy.

## Limitations

* The critique did not execute the 4.1 packages; P01 intentionally owns that
  implementation proof.
* The critique did not assess cosmetic structure or diagram styling.
* No user decision is required for the findings; all are compatible with
  confirmed direction and are planner-owned corrections.

## Closeout

* Execution: Complete.
* Verdict: Revise.
* Action owner: planner.
* Smallest next action: revise the data-handling contract, mandatory enforcement
  posture, SRE proof gate, and ASI01 semantic validation, then reassess planning
  readiness.
* User response required: no.
