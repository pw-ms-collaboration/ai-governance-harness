<!-- markdownlint-disable-file -->
# RPI Plan Critique: Semantic Personal-Advice Policy Classification

## Metadata

* Task ID: `semantic-advice-policy-2026-10-14`
* Critique date: `2026-10-14`
* Plan: `.copilot-tracking/plans/2026-10-14/semantic-advice-policy-plan.md`
* Critique execution: Complete
* Critique depth: standard
* Depth provenance: default
* Critique type: initial
* Earlier critique: not applicable

## Inputs and Criterion Boundary

* Task context and caller requirements: replace regex input classification with policy-level semantic facts, retain policy authority, produce a thorough plan, implement, and test before acceptance.
* Research and evidence considered: `.copilot-tracking/plans/2026-10-14/semantic-advice-policy-plan.md`, `src/ai_governance_harness/chat/service.py`, `src/ai_governance_harness/guardrails/advice_filter.py`, `src/ai_governance_harness/governance/policies/default.yaml`, `src/ai_governance_harness/governance/reliability.py`, and `pyproject.toml`.
* Decisions, dependencies, task Goals, and task Requirements considered: all `FR-001` through `FR-005`, `NFR-001` through `NFR-004`, `P01` through `P03`, decisions `D1` through `D4`, and risks `R1` through `R5`.
* Assessment boundary: implementation credibility, lifecycle sequencing, failure behavior, privacy, multi-turn classification, policy ownership, removal boundary, test ownership, and operational validation. The critique does not assess live model accuracy.

## Coverage Assessment

| Requirement, research, phase, or task ID | Coverage | Evidence or concern |
|---|---|---|
| `FR-001`, `FR-002`, `P01`, `P02` | Covered | The plan separates semantic fact production from YAML enforcement and sequences classification before the primary assistant. |
| `FR-003`, `P01-T02`, `P02-T01` | Partial | Fail-closed statuses are listed, but the public behavior for technical classifier failures is not distinguished from an intentional personal-advice policy denial. |
| `FR-004`, `NFR-003` | Covered | Prompt text and free-form rationale are excluded from policy, telemetry, logs, and public errors. |
| `FR-005`, `P02-T02` | Partial | The removal list covers advice regex patterns but does not explicitly replace the regex-dependent multi-turn context helper in `chat/service.py`. |
| `NFR-001`, `NFR-002` | Covered | Strict schema, no tools, no storage, bounded completion, timeout, independent circuit, and cleanup are binding. |
| `NFR-004`, `P03` | Covered | Focused, full, lint, policy-lint, privacy, and build validation are owned. |

## Verdict

* Verdict: Revise
* Rationale: The architecture is credible, but two direct corrections are needed to prevent a regression in multi-turn advice detection and to preserve the product's explicit distinction between governance denials and technical classifier stops.

## Findings

<!-- rpi:critique id=PC-001 -->
### PC-001 [High]: Multi-turn classifier input contract is unspecified

* Related IDs: `FR-001`, `FR-005`, `P01-T01`, `P02-T02`, `P03-T01`
* Evidence: `src/ai_governance_harness/chat/service.py` currently uses `_active_advice_request_text` to combine prior user intent when a short member-ID follow-up arrives, and that helper itself uses a member-ID regex.
* Concern: Removing request regex without defining the replacement context window can regress the existing requirement that a short member-ID follow-up inherits prior personal-advice intent. It can also leave regex in the semantic-classification path contrary to the requested architecture.
* Impact: A user could split a prohibited recommendation request across turns and bypass semantic denial, or implementation could retain hidden regex routing.
* Smallest useful change: Require the classifier input to use the current user turn plus the immediately preceding user turn as separately labelled context, independent of member-ID pattern matching, and add split-turn denial tests.
* Action owner: planning parent
* Exact resolving evidence: plan requirements explicitly define the bounded context window, remove `_active_advice_request_text`, and assign a split-turn semantic regression test.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-002 -->
### PC-002 [Medium]: Technical classifier failures lack an explicit public error contract

* Related IDs: `FR-003`, `P01-T02`, `P02-T01`, `P03-T01`
* Evidence: the plan maps timeout, unavailable, filtered, malformed, and empty classifier outcomes to policy-consumed statuses, while current chat behavior already distinguishes model stops and policy denials with structured errors.
* Concern: Treating every technical classification failure as an ordinary personal-advice denial would obscure whether policy rejected the user's request or the classifier could not establish a safe decision.
* Impact: Operators and users would receive misleading denial semantics, repeating the error-clarity problem that earlier changes addressed.
* Smallest useful change: Keep fail-closed policy evidence, but require a dedicated `classification_unavailable` structured chat error for operational/invalid classifier outcomes, with bounded reason metadata and correlation ID; reserve personal-advice denial messaging for successfully classified unsafe intent.
* Action owner: planning parent
* Exact resolving evidence: plan requirements define the structured error code/status and tests distinguish semantic denial from classifier technical stop without exposing raw content.
* Decision route: direct planner correction

## Strengths and Residual Risk

* The plan correctly keeps YAML policy as the decision authority rather than embedding allow/deny logic in model instructions.
* Strict schema, fixed enums, no tools, no storage, bounded output, and privacy-safe policy projection form a credible classifier boundary.
* The removal boundary correctly preserves deterministic post-tool output scanning.
* Residual model-accuracy risk remains and is appropriately described as evaluation risk rather than deterministic correctness.

## Questions or Blocking Evidence Gaps

* None. Both findings are planner-owned corrections supported by existing behavior and user direction.

## Limitations

* No live Foundry call was assessed; the critique covers contract and integration credibility only.

## Recommended Next Action

* Highest-impact finding: `PC-001`
* Action owner: planning parent
* Smallest next action: revise the plan to define bounded multi-turn semantic context and structured technical-stop behavior, then proceed without a follow-up critique because the architecture is unchanged.
* User response required: no
