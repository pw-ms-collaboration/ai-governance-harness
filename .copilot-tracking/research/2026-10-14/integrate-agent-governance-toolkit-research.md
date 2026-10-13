<!-- markdownlint-disable-file -->
# Task Research: integrate-agent-governance-toolkit

| Field              | Value       |
|--------------------|-------------|
| Date               | 2026-10-14  |
| Researcher / agent | RPI Research |
| Output mode        | convergence |

## Executive Summary

* Bottom line: Adopt the released 4.1 toolkit line as a pinned governance layer
  around the existing MCP/chat boundaries, map every applicable toolkit
  capability to code and validation evidence, and explicitly defer controls that
  require Azure, privileged runtimes, or capabilities this harness does not
  execute. Do not copy the repository or follow unreleased 5.0 `main`.
* Why this matters: This delivers real policy, identity, audit, reliability,
  compliance, and sandbox-readiness controls without replacing the working MCP
  server or making false "10/10" claims.
* Research status: Complete. Wider, deeper, and contrarian waves converged on a
  planning-ready integration boundary.
* Confidence and uncertainty: High confidence in licensing, release maturity,
  package availability, architecture, current harness gaps, and upstream
  limitations. Exact 4.1 Python APIs still require an implementation proof spike
  because upstream `main` documents the in-progress 5.0 ACS migration.

## What You May Not Know

The current harness already implements several foundations a governance toolkit
would otherwise need to add: typed closed-world tools, bounded model/tool loops,
request-size and protocol validation, hosted tenant/audience/scope checks,
privacy-safe telemetry, and sanitized errors. The integration therefore needs a
policy and assurance layer around these boundaries rather than a replacement for
the MCP server.

The largest verified local gaps are runtime policy decisions before model and
tool execution, execution isolation, end-to-end workload identity propagation,
resilience controls around Foundry and MCP calls, and supply-chain evidence
beyond dependency audit and package build.

The toolkit's own `[full]` extra is a distribution bundle, not proof that every
component or deployment control is active. The 4.1 meta-package installs core,
integrations, CLI, and protocol packages; sandboxing is a separate `agt-sandbox`
package and operational backends still require Docker, virtualization, native
binaries, or Azure.

## Findings

### The existing harness has strong bounded-tool foundations but no general policy engine

The MCP server exposes four typed read-only tools with closed-world annotations,
sanitized failures, synthetic provenance, and bounded inputs. The chat loop
rejects unknown tools, limits tool rounds and result size, disables parallel tool
calls, and does not persist model requests. These controls are useful enforcement
points, but authorization remains coarse and there is no per-request policy
decision that evaluates caller, tool, arguments, context, or risk before model
and tool execution.

* Questions: Q3, Q4, Q5
* Evidence state: evidence-backed finding
* Evidence: C2-C5 establish the current dependency, chat-loop, MCP-tool, and
  request-security boundaries.
* Confidence and limits: High confidence for the current source. The upstream
  policy interfaces still need verification before selecting the integration.

### Identity exists at the HTTP edge but is not propagated into tool policy

Hosted MCP requests validate trusted platform identity headers, tenant, audience,
and scope, then hash the principal ID for rate limiting. Local mode intentionally
uses a shared development principal. The chat service does not propagate an
end-user or workload identity into MCP tool context, and tool handlers do not
make subject/resource/action authorization decisions.

* Questions: Q3, Q4, Q6
* Evidence state: evidence-backed finding
* Evidence: C3-C5.
* Confidence and limits: High confidence for current source; deployment identity
  remains intentionally deferred and upstream identity requirements are pending.

### Telemetry is privacy-safe but not yet a governance evidence ledger

The MCP service emits allowlisted structured audit events, traces, counters, and
duration histograms while excluding tool arguments and results. This is a strong
privacy baseline. It does not yet record policy bundle version, decision ID,
decision outcome, enforcement point, or resilience/sandbox outcomes needed for a
complete governance evidence chain.

* Questions: Q3, Q4, Q5
* Evidence state: evidence-backed finding
* Evidence: C6.
* Confidence and limits: High confidence for the current telemetry module. The
  correct upstream event vocabulary is pending verification.

### Current CI has quality gates but limited supply-chain assurance

CI runs tests on Python 3.11-3.13 and separately runs Ruff, package build, and
`pip-audit` with read-only workflow permissions. It does not currently generate
an SBOM, attest build provenance, pin actions to immutable SHAs, sign artifacts,
or run OpenSSF Scorecard-style checks.

* Questions: Q2, Q3, Q5
* Evidence state: evidence-backed finding
* Evidence: C7.
* Confidence and limits: High confidence for the current workflow; the toolkit's
  own distribution and integrity guarantees are still pending.

### A legacy direct-call path could bypass future MCP enforcement

The older `MemberWealthInsightsAgent` invokes gateway functions directly when a
gateway is not injected. If policy enforcement is added only at the MCP
transport, that path would remain outside the enforcement boundary. Planning
must either route governed execution through one shared policy-enforced service
or apply the same policy decision point beneath both callers.

* Questions: Q3, Q4
* Evidence state: evidence-backed finding
* Evidence: C8.
* Confidence and limits: High confidence for the direct call path; its intended
  long-term role remains a planning decision.

### The released 4.1 line is the only portable team baseline today

GitHub's latest release is `v4.1.0`, published with CycloneDX and SPDX SBOM
assets. PyPI labels the meta-package Beta/Public Preview, and both public PyPI
and Microsoft CFS carry the 4.1 toolkit, core, integrations, CLI, protocols, and
sandbox packages. The unreleased 5.0 core depends on
`agent-control-specification>=0.4.0b0`, while CFS currently exposes only
`0.3.1b0` and `0.3.1b1`. Selecting 5.0 would therefore break the repository's
confirmed feed-neutral teammate requirement.

* Questions: Q1, Q2, Q4, Q6
* Evidence state: evidence-backed finding
* Evidence: W2, W3, W7-W10.
* Confidence and limits: High confidence from exact release, package metadata,
  and both index APIs as retrieved on 2026-10-14. Feed contents can change and
  should be rechecked during future upgrades.

### Toolkit coverage is broad but explicitly incomplete

The upstream self-assessment reports seven OWASP Agentic risks as Full and three
as Partial: supply chain, memory/context poisoning, and human-agent trust. It
also states that package availability is not proof of effective deployment.
Known limitations include action-not-reasoning governance, attempt-not-outcome
audit, policy-initialization bypass risk, credential persistence, opt-in memory
guards, no universal approval UI, streaming assurance gaps, and cross-SDK DID
and kill-switch inconsistencies.

* Questions: Q1, Q5, Q6
* Evidence state: evidence-backed finding
* Evidence: W5 and W6; C9 supplies the independent OWASP risk taxonomy used to
  avoid treating the upstream self-assessment as certification.
* Confidence and limits: High confidence in what upstream claims and discloses;
  no independent test execution or third-party certification was found.

### The toolkit provides the right enforcement model for this architecture

The policy architecture defines lifecycle intervention points for input,
pre/post model, pre/post tool, output, startup, and shutdown. Its newer ACS path
returns allow, deny, or transform decisions and documents deterministic,
stateless, fail-closed evaluation. The released 4.1 line also exposes the
`agentmesh.governance.govern` wrapper and includes core identity/trust, audit,
CLI, protocol, and integrations packages. These boundaries align with the
current chat and MCP seams without requiring a rewrite.

* Questions: Q1, Q3, Q4, Q5
* Evidence state: evidence-backed finding
* Evidence: W2, W4, W8.
* Confidence and limits: Architecture fit is high confidence. The exact 4.1
  wrapper behavior must be proved under the repository's tests before broad
  wiring because upstream `main` is already documenting 5.0 migration.

### Sandboxing is capability-dependent, not universally applicable

The current remote tools are read-only deterministic Python data lookups and do
not execute generated code, shell commands, or untrusted files. Running them
inside a code-execution sandbox would add operational complexity without
containing a current execution primitive. The correct "full" treatment is to
install and validate the toolkit's sandbox contract, define a fail-closed rule
that any future executable tool requires an approved provider, and keep Docker,
HyperLight, native, and Azure providers opt-in until their host prerequisites
are explicitly authorized.

* Questions: Q1, Q3, Q4, Q6
* Evidence state: evidence-backed finding
* Evidence: C4, W9, W11.
* Confidence and limits: High confidence for current tools and provider
  prerequisites. A real sandbox execution test requires Docker or another
  supported host runtime and is not an automatic research prerequisite.

## Recommendation and Alternatives

* Recommendation or decision state: Select a pinned 4.1 dependency integration
  with a repository-owned governance adapter, fail-closed policies, SRE
  boundaries, identity context, audit evidence, compliance CI, and a complete
  capability disposition matrix.
* Rationale: This direction uses supported packages available through both
  feeds, preserves the current architecture, contains preview churn behind one
  adapter, and distinguishes implemented controls from deferred infrastructure
  or inapplicable execution modes (C2-C8, W2-W11).
* What could change this result: CFS publishing the complete 5.0 dependency
  graph, a GA release, a breaking 4.1 API issue found by the proof spike, or a
  user decision to authorize privileged/cloud sandbox and identity services.

| Option | Benefits | Costs and risks | Evidence | Disposition |
|--------|----------|-----------------|----------|-------------|
| Pinned 4.1 packages plus repository adapter and capability map | Feed-portable, upstream-aligned, testable, contains preview churn | Adds dependencies and requires explicit lifecycle wiring | C2-C8, W2-W11 | selected |
| Follow unreleased 5.0 `main` | New ACS model and latest features | Not a release; alpha core dependency unavailable in CFS; breaking churn | W4, W7-W10 | rejected |
| Wholesale source copy | Maximum apparent surface | Severe drift, maintenance, attribution, and update risk | W1-W3, W11 | rejected |
| Toolkit CLI and documentation only | Low runtime risk | Does not enforce policy in the application | W2, W6 | rejected |
| Delay until GA | Lowest preview risk | Leaves known enforcement and resilience gaps open | C3-C8, W2 | viable but not selected |

## Scope and Questions

* Goal: Determine and execute an evidence-based integration of the applicable
  Agent Governance Toolkit capabilities into this local MCP and Foundry chat
  harness.
* Audience and use: Repository developers and reviewers will use the evidence
  to plan, implement, validate, and review the integration.
* In scope: Current repository architecture and controls; the toolkit's official
  repository, documentation, license, releases, supported interfaces, policy,
  identity, sandboxing, observability, reliability, and OWASP Agentic coverage.
* Out of scope: Creating Azure resources, deploying to Azure, copying
  unsupported source wholesale, weakening existing advice or sovereignty
  controls, and using unverified third-party summaries as authority.
* Decision and evidence criteria: Prefer supported, maintained interfaces;
  preserve local startup; avoid secret exposure; retain type safety and test
  coverage; identify each applicable toolkit capability and validation method;
  respect licensing and supply-chain boundaries.
* Requested output: A convergence recommendation that can automatically proceed
  into planning, implementation, and review.

| ID | Question | Source | Status |
|----|----------|--------|--------|
| Q1 | What capabilities and deployment models does the toolkit currently support? | User request and official upstream repository | answered |
| Q2 | What license, release, language, and dependency constraints apply? | Official upstream repository and package metadata | answered |
| Q3 | Which capabilities overlap, complement, or conflict with the current harness? | Upstream evidence and workspace code | answered |
| Q4 | What is the smallest maintainable integration architecture that delivers broad coverage? | Comparative synthesis | answered |
| Q5 | How should the integration be validated against toolkit and OWASP Agentic claims? | Official upstream tests/docs and standards guidance | answered |
| Q6 | What should be deferred because it requires cloud infrastructure or unsupported maturity? | Upstream requirements and current local-first boundary | answered |

## Decisions and Feedback

| Group | Decision or feedback item | Status | Owner | Rationale or input needed | Evidence | Impact of answer |
|-------|---------------------------|--------|-------|---------------------------|----------|------------------|
| D1 | Run end-to-end RPI automatically through Review | confirmed | user | Selected in the RPI mode prompt | User direction | Enables automatic phase transitions |
| D2 | Keep Azure deployment and privileged sandbox backends outside the current implementation boundary | confirmed | agent | Existing local-first direction plus W11 provider prerequisites | C1, W11 | Prevents unapproved external infrastructure and host changes |
| D3 | Use pinned released 4.1 packages through public PyPI or CFS, not unreleased 5.0 | confirmed | agent | Only 4.1 has a complete portable feed path today | W3, W7-W10 | Establishes dependency baseline |
| D4 | Interpret "full" as complete applicable-capability coverage with evidence and explicit dispositions | confirmed | agent | Package presence cannot prove enforcement; some components are inapplicable or require external infrastructure | C2-C8, W5-W11 | Prevents false assurance while preserving broad scope |
| D5 | Contain preview APIs behind a repository-owned adapter | confirmed | agent | Public Preview and active breaking migrations require an anti-corruption boundary | W2, W4, W5 | Reduces upgrade and rollback risk |

## Risks and Open Questions

| Priority | Type | Risk, question, or research item | Impact | Smallest action or evidence needed | Owner |
|----------|------|---------------------------------|--------|------------------------------------|-------|
| H | risk | Public Preview APIs and a one-way v4-to-v5 migration can break direct coupling | Upgrade churn and regressions | Isolate toolkit calls behind typed repository interfaces and contract tests | planning |
| H | risk | Policy configuration can default to effective allow or permissive behavior | False governed status | Fail startup when required policy cannot load; add deny-path tests | planning |
| H | risk | Existing legacy direct calls can bypass MCP-only enforcement | Uneven policy application | Place shared policy below both callers or remove the bypass | planning |
| H | risk | Identity and sandboxing can require cloud or privileged infrastructure | Local portability and safety impact | Implement interfaces and fail-closed readiness now; defer provider activation | planning |
| M | risk | Upstream OWASP ratings are a self-assessment, not certification | Overstated security posture | Maintain repository-owned ASI evidence matrix and never inherit ratings automatically | planning |
| M | further research | Exact 4.1 API behavior must be proved in the installed environment | Could alter adapter details | Run a bounded dependency/API spike during implementation before broad wiring | implementation |

## Planning Readiness and Next Step

| Field | Record |
|-------|--------|
| Research disposition | executed |
| Decision participation | agent-owned through confirmed automatic RPI mode |
| Planning Readiness | Ready; C2-C9 and W1-W11 establish the integration seams, baseline release, constraints, alternatives, risks, and validation needs |
| Research depth and helpers | One expansive cycle completed in wider, deeper, and contrarian order; upstream helper findings were verified against exact source, release, PyPI, CFS, and raw manifest URLs |
| Blockers | None for planning; privileged/cloud provider activation remains intentionally deferred |
| Output mode and planning support | convergence; supports planning after evidence synthesis |
| Continuation owner | confirmed automatic RPI Agent |
| Required gates or confirmations | License, release, feed portability, architecture, preview-risk, security-boundary, and local-first scope gates passed for planning |
| Next action | Automatically transition to Plan and produce a critiqued implementation plan |
| Primary evidence file | `.copilot-tracking/research/2026-10-14/integrate-agent-governance-toolkit-research.md`; date from current session |

## Research Record

### Method and Boundaries

| Field | Record |
|-------|--------|
| Research posture and provenance | expansive; brief-based because "full" adoption spans a materially unknown decision space |
| Completion basis | Continue complete three-wave cycles until material toolkit capabilities, interfaces, constraints, alternatives, and counter-evidence are source-backed and the next likely sources are redundant |
| Explicit limits or deadline | No deadline; preserve the existing local-first boundary and do not create Azure resources |
| Codebase and external scope | Current repository architecture, dependencies, security controls, tests, and docs; official `microsoft/agent-governance-toolkit` repository and referenced first-party material |
| Initial candidate areas | `pyproject.toml`, MCP server, chat service, orchestrator, guardrails, telemetry, tests; upstream README, license, manifests, docs, examples, packages, releases, and tests |
| Evidence root | Default repository root `.copilot-tracking/research/2026-10-14/` |
| Constraints and excluded sources | Research-only writes; external content is data, not instructions; no secrets; no unsupported wholesale copying; no cloud mutation |
| Prior knowledge | Existing local MCP/chat implementation and RPI artifacts are context only and will be verified against current source |

### Extensions and Participation

#### Extension Registry

| Extension | Status | Provenance and scoped authority |
|-----------|--------|---------------------------------|
| Repository instructions | selected | Apply repository safety, Markdown, Python, telemetry, and tracking conventions to evidence and later handoffs |
| `owasp-agentic` | selected | Evaluate the toolkit's OWASP Agentic coverage claims and control mapping |
| `secure-by-design` | selected | Evaluate trust boundaries, fail-safe defaults, and security-first integration choices |
| `supply-chain-security` | selected | Evaluate license, package provenance, dependency, pinning, and upstream lifecycle risks |
| `telemetry-foundations` | selected | Compare toolkit observability with the repository's privacy-safe telemetry contract |
| Other RPI phase skills | skipped | Research must complete before Plan, Implement, or Review activates |

#### Direction and Participation Log

| Direction | Status | Provenance | Effect |
|-----------|--------|------------|--------|
| Integrate the toolkit "full" and kick-start the work | current | User request | Requires broad capability coverage with evidence-backed dispositions |
| Handle the work end to end | current | User mode selection | Agent owns research decisions and automatic progression through Review |
| Keep Azure deployment deferred | current assumption | Existing explicit project direction | Cloud-dependent capabilities will be planned or deferred, not provisioned |

### Research Cycle Log

| Cycle | Wave | Status | Focus and outcome |
|-------|------|--------|-------------------|
| 1 | wider | completed | Mapped toolkit packages, languages, policy, identity, sandbox, audit, SRE, compliance, examples, releases, license, and current repository overlap |
| 1 | deeper | completed | Verified exact package metadata, 4.1/5.0 split, policy intervention model, sandbox providers, OWASP evidence, CFS availability, and local enforcement seams |
| 1 | contrarian | completed | Tested the "full install" premise against upstream limitations, self-assessment status, preview churn, feed gaps, bypass risks, and provider prerequisites |
| 1 | synthesis | completed | Selected a pinned 4.1 adapter integration with complete capability dispositions and explicit infrastructure deferrals |

### Evidence Log

| ID | Source | Retrieved | Establishes | State |
|----|--------|-----------|-------------|-------|
| C1 | User request and current session context | 2026-10-14 | Requested full toolkit adoption and automatic end-to-end execution | verified |
| C2 | `pyproject.toml` project metadata and dependencies | 2026-10-14 | Python 3.11-3.13 package with MCP, Foundry, OpenTelemetry, Starlette, and no existing Agent Governance Toolkit dependency | verified |
| C3 | `src/ai_governance_harness/chat/service.py::ChatService.complete` | 2026-10-14 | Bounded Foundry/MCP loop, runtime tool discovery, unknown-tool rejection, serial tool calls, result-size limit, and no persistence | verified |
| C4 | `src/ai_governance_harness/mcp_server/server.py` | 2026-10-14 | Four typed closed-world read-only tools, sanitized failures, telemetry, and provenance | verified |
| C5 | `src/ai_governance_harness/mcp_server/security.py` and `config.py` | 2026-10-14 | Hosted tenant/audience/scope validation, bounded requests, protocol validation, origin checks, and process-local rate limiting | verified |
| C6 | `src/ai_governance_harness/mcp_server/telemetry.py` | 2026-10-14 | Allowlisted privacy-safe logs, traces, metrics, and audit events without arguments or results | verified |
| C7 | `.github/workflows/ci.yml` | 2026-10-14 | Multi-version tests, lint, build, and dependency audit with read-only workflow permissions | verified |
| C8 | `src/ai_governance_harness/agent/orchestrator.py::MemberWealthInsightsAgent` | 2026-10-14 | Legacy orchestration can call gateway functions directly without crossing MCP | verified |
| C9 | OWASP Agentic Top 10 skill vulnerability index | 2026-10-14 | Independent risk taxonomy for ASI01-ASI10; does not certify an implementation | verified |
| W1 | https://github.com/microsoft/agent-governance-toolkit/blob/47abed7446d47e74cfa76d01a5913bb873ffcad9/LICENSE | 2026-10-14 | Toolkit source is MIT licensed with notice retention obligations for copied portions | verified |
| W2 | https://github.com/microsoft/agent-governance-toolkit/blob/47abed7446d47e74cfa76d01a5913bb873ffcad9/README.md | 2026-10-14 | Public Preview status, Python 3.11+, `[full]` install, governance wrapper, CLI, package map, and migration notice | verified |
| W3 | https://api.github.com/repos/microsoft/agent-governance-toolkit/releases/latest | 2026-10-14 | Latest release is non-prerelease v4.1.0 with CycloneDX and SPDX SBOM assets | verified |
| W4 | https://github.com/microsoft/agent-governance-toolkit/blob/47abed7446d47e74cfa76d01a5913bb873ffcad9/policy-engine/README.md | 2026-10-14 | ACS lifecycle intervention points and stateless, deterministic, fail-closed decision contract on current main | verified |
| W5 | https://github.com/microsoft/agent-governance-toolkit/blob/47abed7446d47e74cfa76d01a5913bb873ffcad9/docs/LIMITATIONS.md | 2026-10-14 | Reasoning, outcome, credential, initialization, knowledge, streaming, DID, and kill-switch boundaries | verified |
| W6 | https://github.com/microsoft/agent-governance-toolkit/blob/47abed7446d47e74cfa76d01a5913bb873ffcad9/docs/compliance/owasp-agentic-top10-architecture.md | 2026-10-14 | Upstream internal self-assessment is 7 Full, 3 Partial and explicitly not certification | verified |
| W7 | https://pypi.org/pypi/agent-governance-toolkit/json | 2026-10-14 | Released meta-package is 4.1.0 Beta; `[full]` adds core, integrations, CLI, and protocols under `<5` | verified |
| W8 | https://raw.githubusercontent.com/microsoft/agent-governance-toolkit/v4.1.0/agent-governance-python/agent-governance-toolkit-core/pyproject.toml | 2026-10-14 | Released 4.1 core packages Python 3.11-3.13 runtime, trust, identity, hypervisor, and optional operational extras | verified |
| W9 | https://raw.githubusercontent.com/microsoft/agent-governance-toolkit/v4.1.0/agent-governance-python/agent-sandbox/pyproject.toml | 2026-10-14 | Sandbox is separate `agt-sandbox` package with policy, Docker, HyperLight, and Azure extras | verified |
| W10 | https://packagefeedproxy.microsoft.io/pypi/simple/agent-governance-toolkit/ | 2026-10-14 | CFS carries 4.1 meta-package and related 4.1 components, while the 5.0 core's required ACS 0.4 line is not yet present | verified |
| W11 | https://github.com/microsoft/agent-governance-toolkit/blob/47abed7446d47e74cfa76d01a5913bb873ffcad9/agent-governance-python/agent-sandbox/README.md | 2026-10-14 | Sandbox providers require Docker, virtualization, native OS primitives, or Azure and are not universally portable | verified through upstream helper and manifest cross-check |

### Research Self-Check

| Check | Status |
|-------|--------|
| Opening scope, boundaries, posture, extensions, and participation persisted | passed |
| Wider, deeper, and contrarian waves completed in order | passed |
| Material findings use stable evidence IDs | passed |
| Alternatives and counter-evidence recorded | passed |
| Planning readiness is evidence-backed | passed |
