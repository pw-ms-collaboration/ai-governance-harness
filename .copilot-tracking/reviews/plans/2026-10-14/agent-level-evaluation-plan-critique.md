<!-- markdownlint-disable-file -->
# RPI Plan Critique: Agent-level evaluation

## Metadata

* Task ID: agent-level-evaluation
* Critique date: 2026-10-14
* Plan: .copilot-tracking/plans/2026-10-14/agent-level-evaluation-plan.md
* Critique execution status: Complete
* Critique depth: standard
* Depth provenance: default
* Invocation consumed: yes
* Attempt ID/kind: agent-level-evaluation-initial-20261014 / initial
* Candidate hash: 60c67b95bee371a661c90ab7d26ce081f936e71a0ae98f16382f3749ebfa3921,
  before reservation-only metadata.
* Current-run provenance: immediate uninterrupted planner activation in session
  056fe23f-8ad3-4ae6-8253-3bf6d116a7cb; saved reservation read back and verified.
* Recovery approval: not applicable.

## Inputs and Criterion Boundary

Assessed the supplied final candidate, approved docs/spec/eval/ specifications,
the completed research C1-C9, and current implementation boundaries already read.
Coverage includes FR-001-FR-006, NFR-001-NFR-004, P01-P04, all task requirements,
dependencies, consent, process control, observer readiness, error separation,
artifact isolation, judge calibration, and preservation of original work.
This assessment is planning evidence, not implementation or service-access proof.

## Coverage Assessment

| IDs | Coverage | Evidence or concern |
|---|---|---|
| FR-001, FR-004, NFR-001, P01 | Covered | Strict independent cases/rubric/references and binary no-average gates |
| FR-002, NFR-002, P02-T01 | Covered | Real apps, owned sockets, independent probes and explicit cleanup/errors |
| FR-003, P02-T02 | Covered | Separate structured judge, validated IDs/excerpts, bounded no-retry calls |
| FR-005, NFR-003, P01-T01/P03-T01 | Partial | Caller-supplied prompt/rubric text needs a defined pre-inference privacy gate |
| FR-006, NFR-004, P03/P04 | Covered | Regression controls, offline parity, and separately gated real acceptance |

## Verdict

* Verdict: Revise.
* Rationale: The implementation boundaries are credible, but injectable input
  needs an explicit privacy/content preflight before it can be exported to a
  target or judge or retained in artifacts.

## Findings

<!-- rpi:critique id=PC-001 -->
### PC-001 [Medium]: Define the private synthetic-input gate before inference

* Related IDs: FR-001, FR-005, NFR-003, P01-T01, P03-T01.
* Evidence: The plan supports caller-supplied prompts/rubrics and validates
  schemas/identity, while the approved scope requires synthetic content and no
  credentials. It explicitly bounds public responses but does not identify
  the text preflight required before model calls or artifact persistence.
* Concern: Valid JSON can still carry accidental credentials, personal contact
  information, or full-profile data, and instruction-like text must remain
  case data rather than trusted rubric/system instructions.
* Impact: Schema validity alone does not preserve the agreed privacy boundary.
* Smallest useful change: Require a bounded synthetic/private-content preflight
  for supplied prompt/rubric and retained public/criterion text before inference
  and writes; reject unsafe content explicitly without echoing it.
* Action owner: Planning parent.
* Exact resolving evidence: P01-T01/P03-T01 require this gate, and P03-T02
  tests rejection before model/client creation and private persistence.
* Decision route: Direct planner correction within the confirmed scope.

## Strengths and Residual Risk

The plan separates deterministic enforcement from semantic grading, preserves
the real public denial, prevents unready zero-count proof, and keeps offline
artifacts/UI intact. Live deployment compatibility and actual judge calibration
remain explicitly gated, not claimed as established.

## Questions or Blocking Evidence Gaps

No additional user scope decision is required. Actual inference configuration
and authorization remain an implementation acceptance gate.

## Limitations

No model call, authentication, remote service test, rendered diagram preview,
or application implementation was performed by this assessment.

## Recommended Next Action

* Highest-impact finding: PC-001.
* Action owner: Planning parent.
* Smallest next action: Add the private-input preflight and its failure tests,
  then finalize from this consumed assessment without a closure critique.
* User response required: no.
