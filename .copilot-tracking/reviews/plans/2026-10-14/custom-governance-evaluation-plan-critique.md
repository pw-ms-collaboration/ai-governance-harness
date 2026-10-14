<!-- markdownlint-disable-file -->
# RPI Plan Critique: Custom Governance Evaluation

## Metadata

* Task ID: custom-governance-evaluation
* Critique date: 2026-10-14
* Plan: .copilot-tracking/plans/2026-10-14/custom-governance-evaluation-plan.md
* Critique execution status: Complete
* Critique depth: standard
* Depth provenance: default
* Invocation consumed: yes
* Attempt ID and kind: 55ab3cbf-e649-4190-bb4a-79172cb329cc; initial
* Candidate identity and saved hash boundary: v1; a4d9ffa9a7ed811deb89552120e8fbee17fef727c0fb2afcc7f0edd888c719df; saved-content boundary excludes only the metadata between `## Critique Disposition` and the line beginning `Test/change boundary locked for the candidate:`
* Current-run provenance: uninterrupted planner reservation, saved-hash verification, and immediate synchronous fresh-context activation
* Original attempt and recovery approval: not applicable; initial attempt with no recovery authorized

## Inputs and Criterion Boundary

* Task context and caller requirements: Assess the complete seven-task/four-phase implementation plan for the approved two-variant synthetic member-profile evaluation. Preserve production enforcement, use isolated stdio children and independent evidence, support local and managed Foundry grading, keep the managed task unfinished when access or execution fails, and do not widen scope to Yakka routing, MAF, HTTP, or production assurance.
* Research and evidence considered: `.copilot-tracking/research/2026-10-14/custom-governance-evaluation-research.md`; `docs/spec/eval/discover.md`; `docs/spec/eval/design.md`; `docs/spec/eval/plan.md`; `src/ai_governance_harness/mcp_server/tools.py`; `src/ai_governance_harness/mcp_server/server.py`; `src/ai_governance_harness/mcp_server/__main__.py`; `src/ai_governance_harness/mcp_server/config.py`; `src/ai_governance_harness/mcp_server/telemetry.py`; `src/ai_governance_harness/governance/config.py`; `src/ai_governance_harness/governance/engine.py`; `src/ai_governance_harness/governance/events.py`; `src/ai_governance_harness/foundry_client.py`; `src/ai_governance_harness/governance/policies/default.yaml`; `tests/test_mcp_transports.py`; `tests/test_governance.py`; `tests/test_mcp_tools.py`; `pyproject.toml`.
* Decisions, dependencies, task Goals, and task Requirements considered: Confirmed direct repository implementation; no Yakka routing change; child-only profiling; independent manifest; pinned managed evaluator; no production governance/gateway/chat/telemetry edits; locked test/change boundary; P01-T01 through P04-T02 dependencies; FR-001 through FR-007; NFR-001 through NFR-003; T001 through T007.
* Assessment boundary: The supplied evidence supports local runtime feasibility and SDK-shape analysis, but not authenticated managed execution. This critique evaluates whether the plan can implement and report both the local deliverable and a truthful managed blocker; it does not infer service success or perform validation/research.

## Coverage Assessment

| Requirement, research, phase, or task ID | Coverage | Evidence or concern |
|------------------------------------------|----------|---------------------|
| Q1 / FR-001 / FR-002 / P01-T01 / P02-T01 | Covered | The child-only profiler, policy fixture, request-level event boundary, response-state capture, observer health, and lifecycle bounds are grounded in the research and the existing MCP/gateway seams. |
| Q2 / FR-005 / P03-T01 | Partial | The research supports direct Projects 2.8 evaluator APIs and paginated result models, but the repository's connection helper still calls a connection-string constructor that the research records as unavailable in the verified SDK. |
| Q3 / FR-003 / FR-004 / NFR-002 / P01-T02 / P02-T02 | Covered | Independent manifest checks, strict types, explicit error-versus-0.0 handling, immutable baselines, and regression controls are materially specified. |
| NFR-001 / NFR-003 / P02-T01 / P03-T01 | Covered | Synthetic/minimal artifacts, no production observer changes, dotenv/telemetry isolation, finite subprocess/API bounds, child cleanup, and retained failure metadata are assigned. |
| FR-006 / P04-T01 | Covered with downstream limitation | The plan correctly keeps real managed access and externally visible action approval as a later gate and forbids client-construction claims. |
| FR-007 / P04-T02 / T007 | Partial | The task requires truthful partial handoff, but its dependency on blocked P04-T01 prevents the final documentation/review path from executing when managed access fails. |
| Full dependency and validation boundary | Partial | Phase/task dependencies and the locked four-test/seven-module maximum are explicit; the finalization dependency contradicts the required partial-delivery behavior. |

## Verdict

* Verdict: Revise
* Rationale: The local collection/grading design is credible and aligned with the approved scope, but two substantive plan gaps remain. The final handoff is structurally blocked by a managed prerequisite even though the requirements explicitly call for delivering and reviewing the local subset with an honest managed blocker. In addition, the verified SDK/API floor conflicts with an existing connection path and the plan does not make the supported connection contract executable and testable before the managed gate.

## Findings

<!-- rpi:critique id=PC-001 -->
### PC-001 [High]: Managed prerequisite blocks the required truthful partial handoff

* Related IDs: `FR-006`, `FR-007`, `NFR-002`, `P04-T01`, `P04-T02`, `T006`, `T007`
* Evidence: `.copilot-tracking/plans/2026-10-14/custom-governance-evaluation-plan.md` under P04-T01/P04-T02 and the phase dependencies: P04-T02 depends on P04-T01, while P04-T02 also says to review the delivered subset if P04-T01 blocks and the user requires the full managed task to remain unfinished when cloud access fails.
* Concern: The dependency graph makes the final documentation/RPI-review task ineligible whenever the managed demonstration is blocked. That conflicts with the plan's own requirement to complete local delivery and review it as a partial outcome, and leaves no executable owner/path for recording the exact managed blocker, local evidence, and unfinished managed acceptance.
* Impact: A normal downstream access failure can prevent the plan from producing the required local handoff, retained blocker evidence, truthful task states, and documentation without incorrectly waiving `E005`/`E008` or claiming managed completion.
* Smallest useful change: Split local finalization from managed acceptance: make the documentation/review portion of P04-T02 depend on P02-T02 and P03-T01 (or add an explicit conditional dependency), and gate only the managed-evidence subsection and managed completion claims on P04-T01. State the exact blocker artifact and leave T006 and its managed acceptance claims unfinished when P04-T01 is blocked.
* Action owner: planning parent
* Exact resolving evidence: The revised plan's dependency graph and Done criteria permit P04-T02 to record local commands, local results, review status, and the concrete P04-T01 blocker after T006 fails, while retained managed baseline/control evidence and managed completion remain explicitly incomplete; a later changes/review record shows those states from actual results.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-002 -->
### PC-002 [High]: Verified managed SDK floor conflicts with the existing connection helper

* Related IDs: `FR-005`, `FR-006`, `NFR-003`, `P03-T01`, `P04-T01`, Q2, D4
* Evidence: `.copilot-tracking/research/2026-10-14/custom-governance-evaluation-research.md` Evidence C3 records the verified Projects 2.8 client surface and that `from_connection_string` is absent; `src/ai_governance_harness/foundry_client.py` still calls `AIProjectClient.from_connection_string`; `pyproject.toml` permits `azure-ai-projects>=1.0.0b1`; P03-T01 only says to tighten floors “as needed” and reuse the helper “when compatible.”
* Concern: The plan does not identify which supported connection mode the managed runner will actually use or how the known incompatible branch is handled. A fresh installation can resolve a lower SDK that lacks the evaluator APIs, while the verified 2.8 implementation can fail on the existing connection-string path. The locked canonical targets also omit `foundry_client.py`, so the stated compatibility requirement has no clearly authorized implementation target.
* Impact: T004 may appear implemented through mocked endpoint calls while the real authorized command cannot construct its client, or may silently drop an existing connection mode at T006. That undermines managed registration/submission and makes the cloud blocker indistinguishable from an unresolved packaging/API contract.
* Smallest useful change: Make T004 specify an exact supported SDK floor/pin and a tested connection contract: either preserve and test every documented helper path with compatible APIs, or explicitly use the endpoint/coordinate path for the runner and document the supported prerequisite without altering existing application behavior. Add the necessary helper target and compatibility tests to the locked boundary only if preserving the connection-string path requires a code change.
* Action owner: planning parent; user only if preserving or dropping the existing connection-string behavior becomes a material compatibility decision
* Exact resolving evidence: A declared dependency floor and runner contract, plus focused tests against the installed declared SDK, demonstrate client construction and evaluator registration for the chosen connection modes; no managed task starts until this contract is green, and no unsupported `from_connection_string` branch is treated as evidence of access.
* Decision route: direct planner correction; significant/divergent user decision only if the supported application connection contract must be changed

## Strengths and Residual Risk

* The plan preserves the approved two-row scope, distinguishes request-level evidence from startup/shutdown noise, requires independent original-operation observation, keeps malformed evidence separate from completed 0.0 violations, and explicitly rejects score-only or SDK-construction claims.
* Residual managed access, service error-shape, and externally visible-action approval risk is appropriately retained as a downstream gate rather than used to block local implementation.

## Questions or Blocking Evidence Gaps

* None requiring additional research for the local plan. The managed service remains unverified by design; the plan must report that as a blocker when encountered, not as a successful or waived result.

## Limitations

* No authenticated Foundry run, generated evaluation package, or new test output was supplied; this critique therefore assesses feasibility and plan contracts, not implementation correctness.
* No parent state file was supplied; reservation/current-run verification was based on the plan's saved Critique Disposition and the resolved planning reference.

## Recommended Next Action

* Highest-impact finding: `PC-001`
* Action owner: planning parent
* Smallest next action: Revise P04-T02 so local documentation/review can complete with a recorded P04-T01 managed blocker while T006 and managed acceptance remain unfinished; also make the T004 SDK/connection contract explicit before finalizing the plan.
* User response required: no for the dependency correction; yes only if the SDK-compatible resolution would change the existing supported connection behavior.
