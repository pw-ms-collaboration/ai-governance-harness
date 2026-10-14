<!-- markdownlint-disable-file -->
# Review: Custom Governance Evaluation

## Executive Summary

* Assessment: Delivered local collection/grading and managed runner implementation
  conform to their accepted contracts. The original full managed spike remains partial.
* Review execution: Complete, for the supplied comparison boundary.
* Assessed outcome: Residual work; actual managed acceptance is user-deferred.
* Validation supplied: 180 repository tests, 87 evaluation tests, Ruff,
  formatting, whitespace, rebuilt wheel contents, and fresh installed local run.
* Limit: Actual managed service execution is user-deferred; no Azure operation
  or local/cloud parity is claimed.

The assessment is a proposal. Parent Decision Record owns final decisions.

## What You May Not Know

Local collection and grading require no Azure deployment or authentication.
The retained no-submission report records intentional user deferral, not an
attempted service failure. The original full managed acceptance remains unfinished.

## Findings and Proposed Routes

No substantive implementation finding was identified within the delivered
boundary. Deferred actual cloud execution is an explicit unassessed limitation,
not a demonstrated defect or a passing managed result.

## Parent Decision Record

### Current Disposition

* Based on events: RD-001 through RD-008.
* Decision participation: agent-owned, from confirmed automatic RPI.
* Walkthrough: skipped-auto.
* Review execution: Complete.
* Final outcome: Residual work. Local delivered scope conforms; actual managed
  evidence is deferred, so full-plan managed completion is not accepted.
* Finding decisions: None; no substantive `RV-xxx` finding.
* Next actions: Local P04-T02 handoff is complete. Preserve P04-T01/T006/T007
  and the separate live-agent case as deferred; no Azure inference is permitted
  under the latest fully offline choice.
* Decisions still needed: None for current local delivery. Resuming actual
  managed scoring or live-agent model execution requires new authorization.

### Decision History

| Event | Subject | Decision source | Status or value | Proposed destination | Final destination | Owner | More information needed | Smallest next action | Rationale |
|---|---|---|---|---|---|---|---|---|---|
| RD-001 | participation | User-confirmed automatic RPI | agent-owned | None | None | Review parent | None | Compare delivered evidence once | User approved automatic RPI and did not retain Review decisions; external-action deferral remains authoritative. |
| RD-002 | walkthrough | Automatic parent | skipped-auto | None | None | Review parent | None | Decide from evidence | No user-retained Review decisions and no substantive finding to walk through. |
| RD-003 | execution | Review parent | Complete | None | None | Review parent | None | Close local handoff | Every supplied material contract is assessed once or explicitly recorded as unverified/deferred. |
| RD-004 | outcome | Review parent | Residual work | None | None | Automatic parent | Actual managed service evidence is deferred | Preserve partial overall status | Local work conforms; the original full managed acceptance cannot be claimed from local results or SDK mocks. |
| RD-005 | managed-execution | Latest user decision | Deferred | P04-T01 | Future authorized P04-T01 | User / implementer | Separate permission and actual service results | Do not authenticate or submit now | User requested keeping things local for now; no technical service failure is asserted. |
| RD-006 | agent-follow-up | Prior confirmed user target | Accepted distinct follow-up | Separate agent-level evaluation | One `/api/chat` scenario | User / implementer | Concrete prompt/rubric and permissible model execution | Confirm whether the existing cloud model is allowed with local runtime/scoring | Agent final-answer/task-outcome evaluation is different from scripted MCP enforcement; local runtime does not necessarily mean offline inference. |
| RD-007 | legacy-helper-follow-up | Review parent | Preserve distinct follow-up | Application connection migration | Separate application work if needed | Future implementer | Reproduce through the live user-facing path when applicable | Do not change it in this evaluation | Known legacy constructor incompatibility is outside this endpoint-only runner and did not cause the local deliverable to fail. |
| RD-008 | agent-follow-up | Explicit user selection after local closeout | Deferred: fully offline | One live `/api/chat` case | Future separately authorized live-agent case | User / implementer | Permission for real model execution | Stop live-agent work; retain completed local evaluation | User selected fully offline and deferred the live case; mock mode cannot substitute for live reasoning evidence. |

## Validation Evidence

Review assessed these supplied results and executed no validation itself.

| Command or evidence | Scope | Status | Summary |
|---|---|---|---|
| `.venv/bin/python -m pytest -q` | Repository | Passed | 180 tests; existing application behavior preserved. |
| Four focused evaluation test selectors | Evaluation | Passed | 87 tests: strict contracts, portable parity, real stdio, private CLI artifacts, and 37 managed SDK/failure tests. |
| `.venv/bin/ruff check .` | Repository | Passed | Only supporting change outside evaluation is removal of an unused member-model import. |
| Ruff format check and `git diff --check` | Evaluation / worktree whitespace | Passed | Eleven new Python files formatted; no whitespace errors. |
| `uv build --quiet` and wheel inspection | Packaging | Passed | Seven evaluation modules, default policy, synthetic data, installed entrypoint, and no private environment/tracking/evaluation files. |
| Installed `ai-governance-eval local` | Actual local workflow | Passed | Two baseline grades of 1.0, zero child exits, eleven completed 0.0 controls, seven intended errors; all 18 controls accepted. |
| Installed managed command without confirmation | Local no-submission gate | Passed | Explicit blocked report, zero runs and no cloud IDs; unit test forbids obtaining credentials on this path. |
| Actual Azure access / registration / evaluation | Managed acceptance | Skipped | Explicit local-only user decision; no Azure operation performed. |
| Python 3.12/3.13 and actual managed sandbox | Additional runtime coverage | Unavailable | Only current Python 3.11 environment and generated-code execution supplied; not a multi-runtime/service certification. |

## Risks, Blockers, and Residual Work

* Deferred active work: P04-T01/T006 and dependent managed T007 acceptance.
* Review blocker: None for delivered local scope.
* Follow-ups: One user-selected live-agent case; existing legacy connection
  helper compatibility; authorized managed proof only when separately resumed.

## Review Record

### Scope and Evidence

* Task ID: custom-governance-evaluation.
* Review date: 2026-10-14.
* Review scope: Full supplied task state, assessing delivered P01-P03 and
  P04-T02 local handoff; explicitly exclude acceptance of deferred P04-T01.
* Assessed boundary: FR-001 through FR-007, NFR-001 through NFR-003 and
  T001-T007, with actual managed FR-006/T006 unverified.
* Review depth and provenance: standard; default.
* Candidate identity: Current saved plan/changes and source-bound local manifest
  `3897f9dacd2ea6fff3fb7d796f8c40057bdcccc1b06897d817cf9ab122a9419b`.
* Review execution: Complete.
* Helper use: None; parent-owned direct comparison.
* Plan: .copilot-tracking/plans/2026-10-14/custom-governance-evaluation-plan.md.
* Plan critique: .copilot-tracking/reviews/plans/2026-10-14/custom-governance-evaluation-plan-critique.md.
* Changes: .copilot-tracking/changes/2026-10-14/custom-governance-evaluation-changes.md.
* Research: .copilot-tracking/research/2026-10-14/custom-governance-evaluation-research.md.
* Specification: docs/spec/eval/discover.md, design.md, plan.md.
* Implementation: src/ai_governance_harness/evaluation/, four evaluation test
  files, pyproject.toml, .gitignore, README.md, member-model import cleanup.
* Local evidence: .local/evaluations/20261014T023344Z-54be5b9885b2/local-results.json.
* Deferral evidence: .local/evaluations/20261014T023344Z-54be5b9885b2/managed-deferred/managed-results.json.

### Opening Review State

* Interpreted goal: Assess the completed local delivery and managed runner
  implementation without converting mocks or user deferral into cloud acceptance.
* Evidence readiness: Reconciled plan markers, completed-work entries, actual
  validation, local results, explicit no-submission report, and follow-up ownership.
* Acceptance basis: Current marker Requirements, original stable specification,
  PC-001/PC-002 dispositions, and latest local-only user decision.
* Comparison boundary: One direct comparison of all material delivered
  contracts and deferred acceptance; no live service operation or second Review.
* Active read-only boundaries: Only this canonical review record may change
  during Review; source, plan, critique, research, and changes are read-only.
* Authority: Parent compares evidence, records findings, and owns outcome/routes.
* Initial blockers: No local review blocker; managed execution deliberately deferred.

### Acceptance and Change Coverage

| Requirement or scope | Implementation and validation evidence | Assessment | Finding or rationale |
|---|---|---|---|
| P01-T01 / T001 / FR-002 / E002 / NFR-001 | `evaluator.py`, `artifacts.py`, schema/fixture tests | Met | Strict minimal models; two independent oracle variants; framed source/fixture hashes; isolated deny fixture preserves live policy and startup/shutdown. |
| P01-T02 / T003 / FR-003 / E004/E006 | Shared grader, generated adapter and executed parity/control tests | Met for delivered portable definition | Exact identity/rule/sequence/digest/count/response comparisons; edited expectations cannot self-certify; malformed/unhealthy evidence raises sanitized errors; same trusted code below size limit. Actual sandbox remains unverified. |
| P02-T01 / T002 / FR-001 / E001/E003 / NFR-003 | `worker.py`, `collector.py`, actual stdio and thread/failure tests, fresh local results | Met | Original operation entries observed independently; both real request variants, expected rule sequences, response states and zero exits accepted. Hook health, lifecycle completeness, deadlines and SDK process teardown are explicit. |
| P02-T02 / T005 / FR-004 / E008 local portion | CLI, regression controls, installed local results and private-artifact tests | Met | Every baseline must pass separately. Eleven valid violations grade 0.0 and seven malformed/unhealthy rows raise the exact intended errors; controls never replace baseline acceptance. |
| P03-T01 / T004 / FR-005 / E005 implementation portion | `foundry.py`, 37 managed tests, actual installed SDK serialization and explicit floors | Met for runner implementation | Endpoint-only client avoids unchanged legacy helper; verified deployment precedes registration; returned version/readback, nested transport, deadlines/pages, exact row/metric/error identities and minimal reports are covered by SDK mocks, not service claims. |
| P04-T01 / T006 / FR-006 / E005/E008 managed portions | User decision; no-submission report | Deferred / not assessed | No cloud authentication, access check, registration or run. Do not infer managed parity or permissions from local/SDK tests. |
| P04-T02 / FR-007 / T007 local handoff portion | README, reconciled source plan/changes and retained evidence | Met for local handoff; Review supplies final input | Commands and limitations match delivered behavior. P04-T01 and full T007 managed documentation remain unfinished; parent may close local handoff without marking full P04 complete. |
| NFR-001/NFR-002 cross-cutting | Environment allowlist, strict evidence, minimal private artifacts, response observer, trusted bundle and CLI/error tests | Met within supplied local boundary | Dotenv and credential/export inheritance blocked before child import; profiles inspected only in memory; failures never become passing baselines or incidental accepted controls. |
| Dependency floors / preserved application / supporting lint cleanup | `pyproject.toml`, 180 repository tests, wheel and member import diff | Met | Declared APIs and isolation support are intentional; production enforcement/chat/telemetry were not changed by this evaluation. Existing unrelated chat changes were preserved. |
| Implementation-time decisions / direct RPI / local-only deferral | Current plan, changes and user history | Reconciled | No native Yakka dispatch or root-spec recreation; historical critique preserved; no approval implied for cloud operations; subsequent live-agent work remains separate. |

### Critique and Follow-Up Assessment

* PC-001: Resolved. P04-T02 local handoff/review depends on delivered local work
  and the runner, not successful cloud execution. The current deferred state
  retains no-submission evidence without checking P04-T01/T006 or full P04.
* PC-002: Resolved within runner scope. Explicit SDK floors, endpoint-only
  construction, credential-helper-only reuse, and installed-SDK serialization
  tests avoid the known legacy constructor branch without removing it.
* Later refinements: SDK schema guards and deadline/error tests preserve intent;
  the single unused import cleanup is nonfunctional and recorded.
* Current user decision: Local-only execution defers future managed proof;
  it does not redefine an unexecuted cloud run as accepted evidence.
* Pause/resumption: No deferred cloud-dependent work was executed. The existing
  independent local handoff path remains eligible; no second critique was run.

| Follow-up | Why outside current delivered scope | Owner / next action | Assessment and route |
|---|---|---|---|
| Actual managed acceptance | User explicitly deferred Azure execution | User / implementer; separately authorize P04-T01 | Keep original active task unchecked; preserve future managed acceptance. |
| One live-agent scenario through `/api/chat` | Measures final-answer/task outcome, not toolkit enforcement | User / implementer; confirm execution mode and prompt/rubric | Accepted distinct next workstream; no large dataset or new hosting surface implied. |
| Legacy application connection helper | Not used by endpoint-only evaluation runner | Future application implementer; reproduce user-facing need first | Distinct follow-up, not a demonstrated evaluation defect. |

### Reviewer Self-Check

* [x] Every supplied requirement, marker, material update, critique disposition,
  validation, blocker and follow-up has an assessment or explicit limitation.
* [x] No substantive finding was invented from intentionally unassessed cloud work.
* [x] Review execution and outcome are separate; local conformance does not imply
  original full managed completion.
* [x] Parent decisions are append-only, with explicit local-only deferral and
  distinct follow-up ownership.
* [x] Standard depth covered the material boundary once without cosmetic findings,
  broad research, optional helpers, or a second comparison.
* [x] Review changed only this canonical record; it ran no tests or cloud calls.
* Checked boundary: P01-P03 delivery, P04-T02 local handoff, recorded P04-T01
  deferral, E001-E008/FR-001-FR-007/NFR-001-NFR-003, critique and follow-ups.
* Limited evidence: Actual managed API/sandbox/permissions and multi-Python
  execution are not established; live agent reasoning is outside this suite.
