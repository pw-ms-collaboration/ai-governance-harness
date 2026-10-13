<!-- markdownlint-disable-file -->
# RPI Plan Critique: Deployable MCP Server

## Metadata

* Task ID: RPI-REAL-MCP-SERVER-2026-10-14
* Critique date: 2026-10-14
* Plan: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md
* Critique execution: Complete
* Critique depth: standard
* Depth provenance: default (caller specified standard depth)
* Critique type: follow-up
* Earlier critique: Not a durable artifact. Earlier informal findings B1-B4, N1-N6, S1-S4 were returned in conversation before the plan revision and are reconciled below.

## Inputs and Criterion Boundary

* Task context and caller requirements: Plan a protocol-compatible, deployable Streamable HTTP MCP server over the existing read-only superannuation gateway, with local stdio support, Azure deployment, and a thorough rather than demo-grade implementation. Assess the full revised plan boundary once and reconcile every earlier finding.
* Research and evidence considered: .copilot-tracking/research/2026-10-14/real-mcp-server-research.md; src/ai_governance_harness/mcp_server/tools.py; src/ai_governance_harness/mcp_server/__init__.py; src/ai_governance_harness/guardrails/sovereignty.py; src/ai_governance_harness/agent/orchestrator.py; tests/test_mcp_tools.py; pyproject.toml; requirements.txt; repository tree including the absence of .github/workflows, Dockerfile, and infra.
* Decisions, dependencies, task Goals, and task Requirements considered: D1 Azure Container Apps, D2 Python 3.11 floor, D3 Container Apps built-in Entra authentication, D4 stateless Streamable HTTP (all Confirmed, user-owned); FR-001 through FR-008; NFR-001 through NFR-014; phases P01 through P05 and tasks P01-T01 through P05-T02 with their declared dependency edges.
* Assessment boundary: The critique evaluates the plan text, the supplied research artifact, and the current repository state. It can conclude on internal consistency, coverage, dependency ordering, test ownership, and whether the declared requirements are implementable against the observed code. It cannot verify live Azure Container Apps behavior, MCP SDK API surface details, or Microsoft Learn content, because no research artifact in the supplied evidence covers hosting, identity, or ingress, and this critique does not perform research.

## Coverage Assessment

| Requirement, research, phase, or task ID | Coverage | Evidence or concern |
|------------------------------------------|----------|---------------------|
| FR-001, FR-002, FR-003, FR-007; NFR-001, NFR-005, NFR-007, NFR-009, NFR-013 | Covered | P01-T01, P02-T01, P02-T02, P02-T03, and P05-T02 give each a named artifact, an owning task, and regression boundaries. |
| P01, P02 (all tasks) | Covered | Dependency edges are acyclic and each task names concrete files and the existing code it preserves. |
| FR-006 | Partial | P04-T01 places health endpoints outside the MCP path and P04-T02 enables platform authentication, but no requirement excludes probe paths from the authentication boundary. See PC-001. |
| NFR-014 | Partial | P02-T01 and P03-T01 reference a protocol revision, but no task implements or tests the authorization discovery surface standard MCP clients use. See PC-002. |
| NFR-012; P03-T01, P03-T03 | Partial | Rate limiting is required and tested but its enforcement point is undefined and is in tension with stateless multi-replica scaling. See PC-003. |
| NFR-006; P02-T03, P03-T03 | Partial | P03-T03 extends a test file that no task creates. See PC-004. |
| D4; P04-T02; Risks table | Partial | A residual risk row recommends `minReplicas: 1` and externalized session state, contradicting the confirmed stateless decision and the planned `minReplicas: 0`. See PC-005. |
| Plan Goals; NFR-002, NFR-010; P02-T02 | Partial | The advice-boundary goal and the compliance risk row were not reconciled with the raw-tool exemption recorded in P02-T01, and the fail-open behavior of the existing sovereignty guardrail is unaddressed. See PC-006 and PC-007. |
| Supplied research artifact | Partial | The research explicitly scopes out deployment, authentication redesign, and production hardening, so P03 through P05 rest on user decisions and task-level links rather than recorded evidence. See PC-008. |
| NFR-011; P03-T02 | Covered with residual gap | Audit content and exclusions are explicit; retention, alerting, and environment ownership remain unassigned. See PC-009. |
| FR-004, FR-005, FR-008; NFR-003, NFR-004, NFR-008; P04-T03, P05-T01, P05-T02 | Covered | Immutable digest deploys, workload identity, what-if, rollback, smoke verification, and secret-free documentation are each owned by a named task. |

## Verdict

* Verdict: Revise
* Rationale: The revision closed the material decision, dependency, CI, and test-ownership gaps and is structurally implementation-ready. Two High findings remain that would surface as deployment failures rather than code defects: the platform authentication boundary is likely to reject the Container Apps health probes that P04-T02 configures, and no task delivers the authorization discovery surface that standard MCP clients require, which leaves NFR-014 unverifiable under D3. Four Medium findings record internal contradictions and an undeliverable test reference that would mislead an implementer.

## Earlier Finding Reconciliation

| Earlier finding | Status | Evidence |
|-----------------|--------|----------|
| B1 Deployment and security requirements rest on research that excluded them | Superseded in part, still open in part | D1, D3, and D4 are now Confirmed user decisions and outrank critique advice, so the decision-openness concern is superseded. The evidence-traceability residue is re-recorded as PC-008. |
| B2 Guardrails are not on the MCP path and the plan does not say where they go | Resolved in part, still open in part | P02-T01 Details now classifies raw factual tools as exempt from the narrative advice filter. The unreconciled plan Goal and the still-Planning-owned compliance risk row are re-recorded as PC-006. |
| B3 Sovereignty guardrail fails open, contradicting NFR-002 | Resolved in part, still open in part | NFR-010 and P02-T02 add hosted-mode region validation. Whether the shared guardrail itself changes, and the NFR-007 consequence, remain unstated; re-recorded as PC-007. |
| B4 Missing stateless versus stateful decision | Resolved | D4 Confirmed; P02-T02 and P04-T02 carry stateless requirements. A contradictory residual risk row is re-recorded as PC-005. |
| N1 Test ownership entirely unassigned | Resolved in part, still open in part | P02-T03, P03-T03, and P05-T01 assign client strategy, files, and merge-versus-environment gating. The dangling file reference is re-recorded as PC-004. |
| N2 No CI exists and D2's test matrix references nothing | Resolved | P01-T02 owns the initial CI baseline across Python 3.11 through 3.13 and states it is a new baseline. |
| N3 Dependency contract under-specified | Resolved | P01-T01 names pyproject.toml as source of truth; NFR-013 adds pinning and scanning; P04-T01 adds SBOM and image scanning. |
| N4 D1 framed as open while scope pre-decided Azure | Resolved | D1 is Confirmed and recorded in Confirmed User Direction. |
| N5 Operations requirements name categories but no decisions | Resolved in part, still open in part | FR-008, NFR-011, NFR-012, and P03-T02 decide audit content, telemetry backend, and exclusions. Retention, alerting, and environment ownership remain open; re-recorded as PC-009. |
| N6 Import-time singleton is a hosted-mode hazard | Resolved | FR-007, P02-T02, and the matching risk row move data loading into an explicit startup lifecycle with readiness ownership. |
| S1 Pin the MCP protocol revision | Resolved | NFR-014 and P03-T01 require revision validation; the depth of client compatibility work is re-recorded as PC-002. |
| S2 MCP authorization spec imposes a floor regardless of platform | Still open | P03-T01 asserts platform authentication does not replace protocol authorization requirements, but no task implements the discovery surface; escalated to PC-002. |
| S3 NFR-001 versus the gateway `data_directory` constructor | Resolved | P02-T02 Details separates the direct gateway API from the remote tool surface. |
| S4 `MCP_TOOL_DEFINITIONS` is consumed and must be retained | Resolved | P01-T01 Details requires retention until a separate task removes the Foundry role. |

## Findings

<!-- rpi:critique id=PC-001 -->
### PC-001 [High]: Platform authentication is likely to reject the health probes the deployment depends on

* Related IDs: FR-006, NFR-003, P04-T01, P04-T02, P04-T03
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P04-T01 ("Provide liveness and readiness endpoints outside the MCP protocol path"), P04-T02 ("Configure built-in Entra authentication and deny unauthenticated requests" and "Configure startup, readiness, and liveness probes"), P04-T03 ("Verify health ... after deployment").
* Concern: The plan enables a deny-by-default authentication boundary across the application and separately configures platform health probes against unauthenticated application paths. No requirement excludes the probe paths from the authentication boundary or states how the platform probe authenticates.
* Impact: The first deployment can fail at revision activation rather than at test time. Probes returning an authentication challenge mark the revision unhealthy, and the P04-T03 post-deployment health check fails before any authentication or tool-call verification runs, making the failure hard to attribute.
* Smallest useful change: Add a requirement to P04-T02 that the authentication configuration explicitly excludes the liveness and readiness paths, and a matching assertion in the P05-T01 Bicep policy tests that probe paths are unauthenticated while `/mcp` is not.
* Action owner: planning parent
* Exact resolving evidence: P04-T02 Requirements name the excluded probe paths and the unauthenticated-request behavior for them; P05-T01 asserts both the exclusion and the continued protection of the MCP path.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-002 -->
### PC-002 [High]: No task delivers the authorization discovery surface that standard MCP clients require

* Related IDs: NFR-003, NFR-014, FR-004, P03-T01, P03-T03, P05-T02
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P03-T01 Details ("It does not grant unrestricted tool authorization or replace protocol authorization requirements") and Requirements ("Return standards-compatible authorization failures"); NFR-014 ("The selected MCP protocol revision and supported client compatibility are documented and tested").
* Concern: P03-T01 correctly states that platform authentication does not satisfy protocol authorization, but no task in P02 through P05 owns the resource-metadata discovery document or the challenge response an unauthenticated MCP client needs in order to discover where to obtain a token. The plan also does not record how the platform boundary responds to a non-interactive client that presents no token, which determines whether a client receives a usable challenge or a browser-oriented response.
* Impact: NFR-014 cannot be satisfied or tested as written. A deployment can be fully secured yet unusable by conforming MCP clients, which defeats the stated purpose of exposing a shared remote endpoint and would be discovered only after P04 completes.
* Smallest useful change: Add one task under P03 that owns the protocol authorization surface, naming the discovery document, the unauthenticated challenge contract, the token audience, and the explicit client set the first deployment must support; extend P03-T03 to assert the challenge and discovery responses.
* Action owner: planning parent, escalating to the user only if satisfying the contract requires an ingress component beyond the Container Apps boundary confirmed in D3
* Exact resolving evidence: A P03 task exists whose Requirements name the discovery endpoint and challenge contract, and P03-T03 asserts both for an unauthenticated request; or the plan records a user-accepted limitation that the first deployment supports only a named non-standard client configuration.
* Decision route: direct planner correction unless it changes D3, in which case a significant user decision is required

<!-- rpi:critique id=PC-003 -->
### PC-003 [Medium]: Rate limiting has no enforcement point and conflicts with stateless multi-replica scaling

* Related IDs: NFR-012, D4, P03-T01, P03-T03, P04-T02
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P03-T01 ("Add bounded per-client or per-principal rate limiting suitable for the first deployment"), P03-T03 ("rate limiting" assertions), P04-T02 ("stateless HTTP with no sticky sessions ... bounded maximum replicas").
* Concern: Per-principal counters held in an application process are per-replica. With stateless routing and a replica range that starts at zero, the effective limit varies with replica count and resets on scale events. The plan neither selects an enforcement point nor states the accepted approximation.
* Impact: P03-T03 would assert a limit that holds only in a single-replica test and not in the deployed topology, producing false assurance for the only abuse control on a public endpoint.
* Smallest useful change: State in P03-T01 whether the limit is best-effort per-replica or enforced at ingress, record the accepted error margin for the per-replica choice, and scope the P03-T03 assertion to the chosen semantics.
* Action owner: planning parent
* Exact resolving evidence: P03-T01 names the enforcement point and accepted semantics, and P03-T03 asserts only behavior that holds under the chosen topology.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-004 -->
### PC-004 [Medium]: P03-T03 extends a test file that no task creates

* Related IDs: NFR-006, P02-T03, P03-T03
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P03-T03 ("Extend `tests/test_mcp_http.py` ..."); P02-T03 creates `tests/test_mcp_server.py` and `tests/test_mcp_transports.py` only; the repository currently contains four test files and no `tests/test_mcp_http.py`.
* Concern: The security test task depends on an artifact that neither exists nor is produced by its declared dependencies.
* Impact: An implementer either creates an unplanned file with no stated ownership boundary or duplicates HTTP coverage already assigned to P02-T03, weakening the otherwise explicit test-ownership model.
* Smallest useful change: Rename the P03-T03 target to the file P02-T03 creates, or add the HTTP test file to P02-T03's created artifacts and state the split between transport behavior and security behavior.
* Action owner: planning parent
* Exact resolving evidence: Every test file named in P03-T03 is either created by a declared dependency task or listed as created by P03-T03 itself.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-005 -->
### PC-005 [Medium]: A residual risk row contradicts the confirmed stateless decision and the planned replica floor

* Related IDs: D4, P02-T02, P04-T02, Risks and Open Questions
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, risk row "Stateful scale-to-zero loses in-memory MCP sessions ... Use `minReplicas: 1` or externalize resumable session state | Planning" against D4 ("Use stateless Streamable HTTP") and P04-T02 ("`minReplicas: 0` for development").
* Concern: The risk row describes a stateful topology that D4 removed and prescribes a replica floor the plan contradicts, while still carrying an unresolved Planning owner.
* Impact: An implementer reading the risks table may set a replica floor or add session storage that the deployment requirements do not call for, raising cost and contradicting P04-T02.
* Smallest useful change: Replace the row with the stateless-specific residual risk already captured as cold-start latency, or mark it explicitly as not applicable under D4.
* Action owner: planning parent
* Exact resolving evidence: No risk row prescribes behavior that contradicts a Confirmed decision, and no residual risk retains a Planning owner at handoff.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-006 -->
### PC-006 [Medium]: The advice-boundary goal and compliance risk were not reconciled with the raw-tool exemption

* Related IDs: Plan Goals, P02-T01, Risks and Open Questions
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, Goals ("Keep Australian-region and financial-advice boundaries enforceable across the remote tool surface") against P02-T01 Details ("the narrative advice filter remains in the orchestrator"); risk row "Raw MCP tools bypass the narrative guardrails in the orchestrator ... | Planning". Source evidence: src/ai_governance_harness/agent/orchestrator.py lines 87, 141, and 229 apply `AdviceClassificationGuardrail`; src/ai_governance_harness/mcp_server/tools.py applies no guardrail.
* Concern: P02-T01 resolves the question by exempting raw factual tools, but the plan Goal still asserts advice-boundary enforcement across the remote surface and the risk row still carries an open Planning owner for the same question.
* Impact: A governance-focused deliverable carries a documented claim its implementation does not make true. The contradiction is most likely to be discovered during review or demonstration rather than implementation.
* Smallest useful change: Reword the Goal to state that the remote surface carries region and read-only boundaries while narrative advice filtering remains an orchestrator responsibility, and close the risk row against the P02-T01 decision.
* Action owner: planning parent
* Exact resolving evidence: The Goal and the risk row both reflect the P02-T01 exemption, and P05-T02 documentation states the same boundary for operators.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-007 -->
### PC-007 [Medium]: The fail-open behavior of the existing sovereignty guardrail is unaddressed

* Related IDs: NFR-002, NFR-007, NFR-010, P02-T02, P03-T03
* Evidence: src/ai_governance_harness/guardrails/sovereignty.py, `validate_region` returns `True` when no region is configured ("In mock or offline environments, default is approved"); .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P03-T03 References cite "Existing fail-closed region examples" in tests/test_guardrails.py.
* Concern: NFR-010 and P02-T02 add hosted-mode region validation, but no task states whether the shared guardrail is modified or whether hosted configuration performs an independent check. The P03-T03 reference describes the existing guardrail as fail-closed, which is true only when a region or endpoint value is present.
* Impact: An implementer who satisfies NFR-010 by delegating to the existing guardrail inherits the permissive default and silently fails NFR-002. Conversely, changing the shared guardrail affects the orchestrator and existing guardrail tests, which NFR-007 requires to remain compatible.
* Smallest useful change: Add one sentence to P02-T02 stating that hosted-mode validation rejects an absent region independently of the shared guardrail default, and whether the shared guardrail is left unchanged.
* Action owner: planning parent
* Exact resolving evidence: P02-T02 names the enforcement location for absent-region rejection and the intended effect, if any, on src/ai_governance_harness/guardrails/sovereignty.py and the existing guardrail tests.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-008 -->
### PC-008 [Low]: Deployment and identity requirements have no corresponding research evidence record

* Related IDs: FR-005, NFR-003, NFR-008, NFR-012, P03, P04, Sources
* Evidence: .copilot-tracking/research/2026-10-14/real-mcp-server-research.md, Scope ("Out of scope: Source changes, deployment, authentication redesign, and production hardening") and an Evidence Log containing no hosting or identity sources; .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, Sources lists five Azure Container Apps pages that appear in no evidence log.
* Concern: The hosting, authentication, scaling, and probe requirements are grounded in task-level links and Confirmed user decisions rather than recorded, dated evidence. Confirmed direction settles the choice of platform, but it does not establish platform behavior, which is what PC-001 and PC-002 turn on.
* Impact: Platform-behavior assumptions cannot be audited or revisited during implementation, and review cannot distinguish a verified capability from an assumed one.
* Smallest useful change: Record the Container Apps authentication, probe, ingress, and scaling pages as dated evidence entries supporting the specific P03 and P04 requirements, or state in the plan that these are unverified platform assumptions to be confirmed during P04.
* Action owner: planning parent
* Exact resolving evidence: Each platform-behavior requirement in P03 and P04 maps to a dated evidence entry, or the plan records the assumption status explicitly.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-009 -->
### PC-009 [Low]: Operational ownership beyond telemetry emission is unassigned

* Related IDs: FR-006, NFR-011, P03-T02, P04-T02
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P03-T02 ("Define retention and access ownership in deployment documentation"); no task defines alerting, failure thresholds, or the environment count.
* Concern: Audit content and exclusions are well specified, but retention values, alerting on authentication-failure or probe-failure rates, and whether more than one deployed environment exists are left to documentation without an owner or acceptance condition.
* Impact: The first deployment can be observable yet unmonitored, and the deployment automation in P04-T03 has no stated environment topology to target beyond development parameters.
* Smallest useful change: Name the environment count in P04-T02 parameters and add one alerting condition with its threshold to P03-T02.
* Action owner: planning parent
* Exact resolving evidence: P04-T02 states the environments provisioned and P03-T02 names at least one alert condition and its owner.
* Decision route: direct planner correction

## Strengths and Residual Risk

* The four previously blocking decisions are Confirmed with rationale and explicit planning impact, and each unblocked downstream phase requirement traces to one of them.
* Test ownership is now concrete: protocol semantics, transport framing, security behavior, container smoke, infrastructure policy assertions, and deployed verification are each assigned to a named task with stated regression boundaries against the existing 22-test baseline.
* The adapter boundary is correctly scoped. Retaining `MCP_TOOL_DEFINITIONS`, preserving the direct gateway API with `data_directory`, and keeping risk scoring in tools.py protect NFR-007 against the most likely implementer overreach.
* P04-T03 is unusually strong for a first deployment: workload identity, digest deploys, what-if, post-deployment authentication and tool-call verification, and documented rollback.
* Residual risk accepted by the plan and not re-raised here: cold-start latency under scale-to-zero, and contributor disruption from the Python 3.11 floor. Both have named mitigations and Implementation owners.

## Questions or Blocking Evidence Gaps

* None blocking. PC-002 may become a user decision if the protocol authorization contract cannot be satisfied within the Container Apps boundary confirmed by D3; the planning parent should determine that before escalating.

## Limitations

* No research artifact in the supplied evidence covers Azure Container Apps authentication, probe, ingress, or scaling behavior, and this critique performs no research. PC-001, PC-002, and PC-003 are raised as evidence gaps and internal contradictions in the plan, not as verified assertions about platform behavior.
* MCP SDK API specifics, including stateless Streamable HTTP configuration and in-memory client ergonomics, were not verified against the SDK and are accepted as stated.
* The earlier findings reconciled above came from a conversational pre-revision review rather than a durable critique artifact, so reconciliation maps informal identifiers rather than prior `PC-xxx` identifiers.

## Recommended Next Action

* Highest-impact finding: PC-001
* Action owner: planning parent
* Smallest next action: Revise P04-T02 and P05-T01 to exclude the health probe paths from the authentication boundary and assert that exclusion, then address PC-002 by adding a P03 task that owns the protocol authorization discovery surface.
* User response required: no, unless PC-002 cannot be satisfied within the Container Apps authentication boundary confirmed in D3
