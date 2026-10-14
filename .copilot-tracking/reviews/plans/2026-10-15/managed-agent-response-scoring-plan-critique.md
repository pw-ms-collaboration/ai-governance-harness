<!-- markdownlint-disable-file -->
# RPI Plan Critique: Managed agent response scoring

## Metadata

* Task ID: managed-agent-response-scoring.
* Critique date: 2026-10-15.
* Plan: .copilot-tracking/plans/2026-10-15/managed-agent-response-scoring-plan.md.
* Critique execution status: Complete.
* Critique depth: standard.
* Depth provenance: default; no deep critique requested.
* Invocation consumed: yes.
* Attempt ID and kind: managed-agent-response-scoring-initial-20261015 / initial.
* Candidate identity and saved hash boundary:
  4b7a8a3cbf532487cd85055a5d3d03cd6305be198dce85efc5fe5f6704f56ffd,
  complete saved candidate before reservation-only metadata.
* Current-run provenance: direct planner session
  d3c96907-f418-4d49-90c4-3a6a7ad63dac; uninterrupted reservation, readback and
  immediate critique activation. Reconstructing the pre-reservation candidate
  verified the recorded hash. No prior same-task terminal critique exists.
* Original attempt and recovery approval: not applicable; initial attempt.
* Planning reservation/recovery contract: read from the parent's resolved
  rpi-plan references/planning.md; no recovery attempted.

## Inputs and Criterion Boundary

* Caller requirements: register reusable response definitions from the existing
  rubric, preserve independent binary criteria and all-pass acceptance, run
  through the real local chat/policy/MCP path, export only approved records,
  retrieve scores/explanations/errors and never run the local response judge in
  managed mode. Retain deterministic enforcement and content-free telemetry.
* Confirmed timing: RV-001 capture correction gates live acceptance, not the
  beginning of definition/adapter development; RV-002 routes focused planning.
* Supplied evidence: readiness review and its cited official evaluator,
  precomputed JSONL and result contracts; earlier agent and enforcement research;
  semantic-advice policy changes; current agent contracts, runner, collector,
  observer, enforcement-managed adapter, private writers and relevant tests.
* Decisions and dependencies: assessed D1-D8, P01-P04, all seven task Goals and
  Requirements, explicit module/test ownership, category applicability,
  definition reuse, checkpoint retrieval and live consent.
* Assessment boundary: local implementation credibility and downstream live
  acceptance gates, not current project access, successful registration,
  model calibration or completed implementation.

## Coverage Assessment

| Requirement, phase or task ID | Coverage | Evidence or concern |
|-------------------------------|----------|---------------------|
| FR-001, P01-T01/P01-T02 | Covered | Four applicable unique results per row; scalar prompt evaluators preserve the current eight criterion identities and reject weighted/aggregate substitution |
| FR-002, P01-T02 | Covered | Project-bound immutable registry, exact service versions, canonical definition equality and zero registration during normal scoring |
| FR-003, NFR-002, P01-T01/P02-T01 | Covered | Explicit category-specific field allowlists, preflight, minimal trusted facts, bounded execution metadata, returned-text/error checks and no full-report export |
| FR-004, P02-T02 | Covered | Existing local default retained; managed opt-in bypasses the local judge for baselines and controls with no fallback |
| FR-005, P02-T02/P03-T01 | Covered | Independent policy_score conjunction and exact matched-rule/causal evidence; permitted classifier activity is not confused with prohibited work |
| FR-006, P02-T01/P02-T02 | Covered | Exact row/criterion sets, explanations/errors, paginated results and explicit unsubmitted/partial states |
| FR-007, NFR-003, P02-T01 | Covered | Durable returned IDs, immutable checkpoints, retrieval-only continuation and no implicit retry after ambiguous submission |
| FR-008, P03-T01 | Covered | Real public-route reproduction at the actual default transport boundary before correction; old HTTPX 1 simulation alone is explicitly insufficient |
| NFR-001/NFR-004, P04-T01 | Covered | Strict completeness, test ownership and no-removal boundary; targeted checks plus packaging and existing mode/UI preservation |
| P04-T02 | Covered with explicit downstream evidence gate | Actual binary result shapes, registration/access, live baselines/controls, subsequent reuse and retrieval are required, but no cloud permission or current success is inferred |
| Phase/task dependency graph | Covered | P03 is independent of P01/P02 development; P04-T01 and P04-T02 require capture correction before trustworthy acceptance |
| Current material updates and scope separation | Covered | Classifier-before-denial is reconciled without weakening zero-prohibited-execution checks; hosted capture/content instrumentation remain separate |

## Verdict

* Verdict: Pass.
* Rationale: the plan gives a credible bounded implementation path for every
  supplied requirement, preserves existing behavior and specifies checkable
  privacy, identity, provenance and failure boundaries. Live service uncertainty
  is assigned to an explicit authorized acceptance task rather than presented
  as either an implementation prerequisite or a demonstrated success.

## Findings

No substantive implementation-blocking planning finding identified within the
supplied standard-depth boundary. No PC placeholder or second assessment is
needed.

## Strengths and Residual Risk

The plan avoids forcing managed scalar results into the existing local
four-criterion/excerpt schema and avoids reusing the single enforcement metric
parser unchanged. It preserves independence of response judgment and enforcement.

Residual risks are already recorded with owners and checkable gates: actual
service binary/error shape and judge access, ambiguous submission, four
judgments per scored row, bounded privacy detection and actual transport
compatibility. A service incompatibility cannot be accepted through an implicit
local fallback or broadened score coercion.

## Questions or Blocking Evidence Gaps

None for local implementation planning. Actual registration/model access and
live calibration remain P04-T02 prerequisites. Consent is not yet supplied.

## Limitations

No production changes, tests, inference, authentication, cloud writes or new
research occurred during critique. The plan was read in full and assessed
against supplied evidence once. Source-level documentation checks and saved
candidate hash verification do not prove rendered diagrams or runtime behavior.
Dual-theme Mermaid rendering is explicitly unavailable in the plan.

## Recommended Next Action

* Highest-impact finding: none.
* Action owner: planning parent.
* Smallest next action: record Complete/Pass and finalize implementation-ready
  planning with the existing live-operation gates unchanged.
* User response required: no.
