<!-- markdownlint-disable-file -->
# Changes: Integrate Microsoft Agent Governance Toolkit

## Execution

| Field | Record |
|-------|--------|
| Task | `integrate-agent-governance-toolkit` |
| Scope | Full approved plan P01-P06, including user-added P06-T03 |
| Status | Implemented and validated |
| Plan | `.copilot-tracking/plans/2026-10-14/integrate-agent-governance-toolkit-plan.md` |
| Research | `.copilot-tracking/research/2026-10-14/integrate-agent-governance-toolkit-research.md` |
| Critique | `.copilot-tracking/reviews/plans/2026-10-14/integrate-agent-governance-toolkit-plan-critique.md` |

## Completed Work

### P01-T01: Released Toolkit Boundary Proven

* Added mandatory `>=4.1,<5` toolkit and sandbox policy dependencies through
  the repository package contract and resolved them through Microsoft CFS.
* Proved released policy allow/default-deny behavior, exact-agent matching,
  toolkit CLI behavior, Agent SRE async circuit breaking, and Agent Sandbox
  provider contracts on Python 3.13.
* Confirmed 4.1 lifecycle stages require repository adapter mapping and that
  `load_yaml` must be followed by `load_policy`.

### P01-T02: Stable Fail-Closed Adapter Added

* Added typed configuration, context, lifecycle, decision, error, reliability,
  sandbox, event, telemetry, and snapshot contracts behind one repository
  package.
* Policy load and evaluation failures deny with sanitized errors. Governance
  can be disabled only in the explicit test environment.

### P02-T01 and P02-T02: Default-Deny Enforcement Made Load-Bearing

* Added an exact-workload packaged policy that permits only the current
  read-only lifecycle and tool operations.
* Enforced input, model, tool, output, startup, and shutdown decisions across
  chat, MCP, the shared gateway, and legacy callers. Unknown tools evaluate
  against default deny before execution.

### P03-T01 and P03-T02: Bounded Identity and Evidence Added

* Propagated request-scoped workload, environment, correlation, authentication,
  and opaque principal context without raw identity claims.
* Added privacy-safe structured logs, OpenTelemetry decision metrics and spans,
  and a bounded process-local event store that excludes request and member
  content.

### P04-T01 and P04-T02: Reliability and Sandbox Boundaries Added

* Protected Foundry, MCP, and MCP observability operations with toolkit circuit
  breakers and total operation timeouts.
* Added a fail-closed execution classification. Current read-only tools require
  no privileged provider; future code, shell, write, or unrestricted-network
  execution requires an approved healthy sandbox.

### P05-T01: Repository OWASP Agentic Evidence Added

* Added a repository-owned ASI01-ASI10 evidence matrix with explicit
  implemented, partial, and not-applicable states, tests, limitations, and
  Public Preview/non-certification caveats.
* Added a toolkit-compatible runtime evidence manifest; strict toolkit
  verification reports all ten package controls and six evidence checks.

### P06-T01: Governance Readiness and Diagnostics Added

* Expanded chat and MCP readiness with governance enforcement, policy digest,
  and sandbox status.
* Added authenticated-hosted/local-public MCP snapshot routing and merged
  same-origin chat snapshots with strict remote event validation.

### P06-T03: Governance Observability Panel Completed

* Added a responsive complementary panel with allow/deny totals, bounded recent
  decisions, service and circuit state, sandbox posture, active policy rules,
  OWASP evidence, and privacy/retention guarantees.
* Added visible refresh and pause controls with polling only while visible.
  The default-deny demonstration evaluates a fixed prohibited action and always
  reports `executed: false`.
* Browser validation proved semantic names and structure, logical keyboard
  order with visible focus, pause state, inert deny behavior, and 320 CSS-pixel
  reflow without page overflow. Axe reported no violations and 50 passes; its
  remaining gradient/overlap contrast checks were inconclusive. Manual contrast
  calculations ranged from 5.50:1 to 13.89:1 for the affected text/status pairs.

### P05-T02 and P06-T02: Supply-Chain Gate and Team Documentation Completed

* Added an expiring OpenVEX exception for `PYSEC-2026-3552`,
  `PYSEC-2026-3553`, and `PYSEC-2026-3554`, backed by exact package versions
  and a source-reachability check for the affected APIs.
* Added `ai-governance-audit`, which fails closed on expiry, dependency drift,
  VEX mismatch, affected API reachability, or any unrelated vulnerability.
* Exact-pinned Toolkit and sandbox packages to 4.1.0 and documented the
  supported public PyPI and Microsoft CFS single-index workflows.
* Added seven proposed MADR records covering the Toolkit adapter, default-deny
  enforcement, privacy-safe telemetry, local reliability and sandbox
  boundaries, same-origin observability, the temporary dependency exception,
  and feed-neutral team setup.

## Validation

| Check | Result | Evidence |
|-------|--------|----------|
| Toolkit API proof | passed | Policy, CLI, circuit-breaker, and sandbox contracts exercised |
| Dependency resolution | passed | 143 packages synchronized through Microsoft CFS; public PyPI attempt was unavailable because of a TLS handshake failure |
| Automated tests | passed | 80 tests in 51.99 seconds |
| Ruff | passed | Repository-wide check |
| JavaScript syntax | passed | `node --check` for the panel client |
| Package build | passed | Source distribution and wheel |
| Distribution content | passed | Policy and evidence YAML present in source distribution and wheel |
| Dependency audit | passed with reviewed exception | VEX gate validated three inherited advisories; no unreviewed findings |
| Governance policy lint | passed | Strict mode, zero errors and warnings |
| Governance evidence verification | passed | 10/10 package controls and 6/6 evidence checks |
| CycloneDX SBOM | passed | `dist/sbom.cdx.json` generated |
| Local service acceptance | passed | Chat/MCP ready; inert deny recorded; live merged panel rendered |
| Accessibility automation | partial | Axe: zero violations, 50 passes, contrast indeterminate; rendered keyboard and reflow probes passed |

## Governed Residual Risk

* Agent Governance Toolkit core 4.1.0 requires
  `cryptography>=46.0.7,<49.0`, while clearing the three inherited advisories
  requires `cryptography>=50.0.0`.
* The temporary exception expires on 13 November 2026. It is valid only for the
  exact reviewed dependency versions and while the affected APIs remain absent
  from the scanned execution path.
* Repository maintainers remain responsible for reviewing the proposed ADRs
  and replacing the exception when a compatible Toolkit release is available.

## Follow-Up Items

* Hosted Entra/APIM identity and privileged/cloud sandbox providers remain
  deferred under the approved local-first scope.
* Upgrade the Toolkit, remove the exception, revise the VEX statements, and
  supersede ADR 0006 when the upstream dependency constraint is resolved.
