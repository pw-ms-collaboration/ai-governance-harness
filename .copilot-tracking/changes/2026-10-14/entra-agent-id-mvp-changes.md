<!-- markdownlint-disable-file -->
# RPI Changes: Local MVP of agent identity

## Metadata

* Task ID: entra-agent-id-mvp
* Implementation date: 2026-10-14
* Plan: [.copilot-tracking/plans/2026-10-14/entra-agent-id-mvp-plan.md](../../plans/2026-10-14/entra-agent-id-mvp-plan.md)

## Execution Status

* Status: Complete for the full implementation plan; Review not yet invoked.
* Declared scope: full plan, P01 through P07.
* Completed markers: P01-P07 and every task in those phases.
* Remaining active-plan markers: none.
* Phase gate: P01 full `uv run pytest` passed before P02.
* Approved write boundary: plan-named application, test, dependency, evidence, documentation and tracking files. No live Entra provisioning, deployment, pushes, or ADR status changes.
* Decisions: choose the simplest contract-preserving implementation; ask only for choices weakening default deny or privacy. Focus tests on the matrix, rejection, guard, privacy and import boundary.

## Implementation-Time Plan Updates

### Integrate main after implementation

* User explicitly selected preserving the approved MVP tool matrix while retaining main's compatible privacy and guardrail improvements.
* Rebased the three existing branch commits onto `origin/main` at `f6e494b`; the MVP remains local work, not a new commit.
* Recovery: original committed tip at `backup/entra-agent-id-before-main-20261014-1546`; full tracked/untracked MVP retained in stash `93e088b493502c0e961d37196ed5b5575e3a17a6`.
* Stash restoration conflicted in README, chat service, HTML and launcher; both new launcher test files were combined. Retained Foundry external-denial recording, scope-refusal policy notices, profile-field minimization, fixed UI disclosures, stronger share-advice detection, evaluations and team documentation. Retained the five-tool MVP surface, caller authentication, per-request OBO, module-local token and three-service guard.
* External provider-denial events now pass the current identity context to the updated event recorder. Incoming tests are migrated to explicit callers rather than an anonymous bypass.
* Integration validation: Complete. After environment repair, normal `uv run pytest` passed all 298 tests in 143.59 seconds; Ruff and the normal audit console command passed. Strict policy lint, evidence verification, JavaScript syntax, build and SBOM also passed on the integrated source.
* Windows environment repair: a running launcher locked its console executable during `uv` synchronization, leaving some scripts unavailable. With explicit user approval, stopped the identified launcher process tree, restored the package with `uv sync --all-extras`, and verified the report console script. The dev stack is intentionally stopped.
* Final Git state: committed branch tip `aac4888`, three commits ahead and zero behind `origin/main`; no conflicts or staged changes. All MVP and reconciliation work remains uncommitted. Recovery branch and already-restored stash are retained; do not apply that stash again.
* Conflict resolutions: [README.md](../../../README.md) keeps upstream metadata and both sets of instructions; [src/ai_governance_harness/chat/service.py](../../../src/ai_governance_harness/chat/service.py) combines role-aware tools/OBO with upstream profile filtering and denial reporting; [src/ai_governance_harness/chat/static/index.html](../../../src/ai_governance_harness/chat/static/index.html) keeps persona UI and persistent disclosures with one module script; [src/ai_governance_harness/dev_launcher.py](../../../src/ai_governance_harness/dev_launcher.py) combines the three-service loopback guard with upstream reusable-port probing. Launcher tests retain both upstream and MVP coverage.

### Reconcile the accepted handoff

* P07-T03: separated the changes-record sentence from the doctor/SBOM bullet as requested.
* Reconciled stale pending-critique metadata with the completed critique and user confirmation that PC-001 through PC-010 are incorporated. No new critique.

## Validation Record

| Check | Final result | Evidence |
|-------|--------------|----------|
| `uv run pytest` | Passed | Post-rebase: 298 tests, 143.59 seconds, Windows Python 3.13.15 |
| `uv run ruff check .` | Passed | No diagnostics |
| Strict policy lint | Passed | Zero errors and warnings |
| `agt --json verify --evidence` | Passed | Strict evidence checks and 10 toolkit component checks; hosted validation remains deferred |
| `uv build` | Passed | Wheel and source distribution in `dist` |
| CycloneDX CI command | Passed | Reproducible `dist/sbom.cdx.json` generated |
| `uv run ai-governance-audit` | Passed | Existing temporary VEX exceptions validated; `cryptography` 48.0.1; local project not found on PyPI |
| `uv run agt --json doctor` | Passed (exit 0) | Toolkit 4.1.0 found; legacy standalone distributions/config files reported absent |
| JavaScript syntax | Passed | `node --check` |
| Worktree hygiene | Passed | `git diff --check`; temporary service ports no longer listening after cleanup |

* The toolkit verifier emits an internal `toolkit_version: 3.2.2` while installed package metadata and doctor report 4.1.0. Its component-presence checks are not evidence that application code adopts toolkit identity APIs. The AST import-boundary test passes.
* P01: `uv run agt --json lint-policy --strict` passed with zero warnings/errors.
* P01: `uv run pytest` passed, 171 tests (53.41 seconds). Initial run: 170 passed, HTTP startup timeout. Isolated subprocess tests from developer App Insights configuration and increased the bounded Windows startup wait to 45 seconds; production export remains unchanged.

## Completed Work

### Evidence, documentation and final acceptance checks (P07)

* Updated [.env.example](../../../.env.example), [README.md](../../../README.md) and packaged evidence. ASI03 stays `partial`; `hosted_principal_validation` stays `deferred`. ADR statuses are unchanged.
* Real launcher smoke: three isolated loopback ports reached ready, including MCP JWKS loaded. The test disabled Azure export only in its environment; production manual span/metric export remains configured.
* The stdio subprocess test now verifies both unset persona denial and retention-specialist approval. The actual identity console command refused `GOVERNANCE_ENVIRONMENT=staging` with exit 2.
* Browser expiry check injected a structured 401 and confirmed send becomes disabled and reauthentication is requested. Real all-persona checks used actual authentication and MCP but deterministic inference, not live Foundry.
* Reporting distinguishes the known sanitized policy-denial result from unrelated MCP errors, which now produce failure rather than a successful denial summary.
* Final fixture correction: PyJWT refuses to generate HMAC signatures using asymmetric key bytes. The algorithm-confusion test therefore builds that invalid token using standard-library HMAC; verification still rejects it. The final full suite passes.
* Temporary browser verification source and all owned demo services were removed/stopped. No commits, pushes, or external provisioning.

### Reporting command and ordered launcher (P06)

* Added `ai-governance-report` and three-service startup with derived synthetic configuration and readiness ordering. Guard refusal is checked before processes start; all owned processes stop on failure.
* Validation: 13 report/launcher/transport tests passed, including the real subprocess report. Installed `uv run ai-governance-report --json` against the browser verification stack returned aggregate allowed, FUM allowed, member denied, exit 0, with no raw credentials or agent identifiers.
* A build-isolation PyPI TLS failure was resolved using the user-provided Microsoft feed proxy. No dependency upgrades.
* Bounded launcher readiness waits are 60 seconds to accommodate observed Windows cold starts.

### Persona UI and browser verification (P05)

* Added labelled native selector, explicit mock sign-in, page-memory-only token, disabled send until signed in, conversation clearing on persona changes and credential removal on 401.
* Snapshot and event table display mock mode and the four enums. Increased bounded policy-condition display to 1024 characters so the new allow rules are not truncated.
* Validation: 12 chat UI tests passed; JavaScript syntax passed. Integrated browser exercised all four personas against real local issuer, chat authentication/OBO and MCP. Only Foundry inference was replaced by a deterministic test double to avoid a cloud dependency.
* Browser evidence: analyst aggregate allowed/member denied; retention aggregate/member allowed; compliance and administrator both denied. Each change of persona cleared the visible conversation. Panel events matched all eight expected MCP decisions; the native control exposed the accessible name `Mock identity`.
* Live Foundry inference was not part of this browser test. No claim of a full accessibility conformance audit.

### Authenticated chat and OBO forwarding (P04)

* Added request-local `CallerIdentity` (hidden `SecretStr`, excluded from serialization), bounded `SidecarClient`, and per-request `AgentAuth` in [src/ai_governance_harness/identity/sidecar.py](../../../src/ai_governance_harness/identity/sidecar.py). Reporting reuses this client.
* Chat validates before policy/model work and preserves structured errors and same-origin headers. Identity exceptions never increment the shared MCP breaker.
* Local judgment: the toolkit breaker exposes no exception predicate. A private adapter subclass suppresses failure accounting only for explicitly classified caller-auth errors, scoped by `ContextVar`; toolkit admission and state transitions remain intact.
* Moved the existing error contract to [src/ai_governance_harness/errors.py](../../../src/ai_governance_harness/errors.py) to avoid a chat/sidecar import cycle; `chat.service.ChatServiceError` remains available.
* Validation: 63 chat/governance/export regression tests passed; 40 authenticated-chat and regression tests passed; Ruff passed. Foundry credential acquisition is unchanged.

### MCP authentication and privacy (P03)

* Added HTTP-only source configuration, pure shared normalization and RS256 JWKS validation with pinned issuer/audience/tenant, required lifetimes, bounded input and rate-limited key refresh.
* Easy Auth and JWT project identical identity enums. HTTP requests populate both request state and `ContextVar`; local stdio remains token-less.
* Real identity + MCP subprocess tests prove analyst aggregate allow/member deny and retention outreach elicitation. No propagation fallback was needed.
* MCP export now uses the existing manual-only exporter path: explicit spans and metrics still export; automatic HTTP/header instrumentation and root logs do not.
* Validation: 62 source/config/HTTP/export regression tests passed; 37 identity tests including middleware privacy passed; both subprocess transport tests passed; Ruff passed.

### Guarded mock issuer (P02)

* Added [src/ai_governance_harness/identity](../../../src/ai_governance_harness/identity) with synthetic constants, guarded configuration, bounded bearer parsing, ephemeral RS256 issuer and sidecar-compatible endpoints. No private key persistence or Azure export.
* Added the identity script and direct `PyJWT[crypto]>=2.15.1,<3` dependency; refreshed the lock without upgrades.
* Validation: 23 service tests passed. Dependency audit passed, validating the existing temporary VEX exceptions; the local project has no PyPI audit record. `cryptography` remains 48.0.1.
* P03/P04 consumers should reuse `identity.constants`, `identity.tokens.bearer_token`, `identity.config.require_loopback_url`, and the shared D14 guard.

### Identity-aware governance and local entry points (P01)

* Added closed enum aliases and telemetry projections in [src/ai_governance_harness/governance/context.py](../../../src/ai_governance_harness/governance/context.py), event fields, explicit evaluated-context logging/spans and boundary population.
* Added [src/ai_governance_harness/mock_identity_guard.py](../../../src/ai_governance_harness/mock_identity_guard.py) as the single D14 guard and D15 persona resolver. Later mock components must reuse these functions.
* Aggregate tools now use private signal computation; the member method and outreach path remain governed.
* The policy uses separate chat, staff, reporting and local rules; advice conditions are unchanged. Removed exception traceback logging in the policy failure branch so raw failure text cannot enter logs.
* Focused [tests/test_identity_policy.py](../../../tests/test_identity_policy.py) checks the full Cartesian matrix, malformed rule fields, all guard predicates, aggregate/member separation, enum validation and event privacy. AST import-boundary test passes. Existing tests use explicit fixtures, not an anonymous allow.

## Blockers

* None.

## Pre-Review Reconciliation

* Plan markers and task-local context: current; all full-plan markers checked with evidence above.
* Completed-work evidence, handoff, validation and remaining work: reconciled.
* Review readiness: Ready for `/rpi-review`; manual progression, awaiting user request.
* Task status: active until Review and maintainer acceptance; implementation execution is Complete.

## Follow-Up Items

* Retain the plan's post-MVP Entra integration and maintainer ADR acceptance items outside implementation scope.
