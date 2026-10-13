<!-- markdownlint-disable-file -->
# RPI Plan Critique: Deployable MCP Server (Follow-Up 2)

## Metadata

* Task ID: RPI-REAL-MCP-SERVER-2026-10-14
* Critique date: 2026-10-14
* Plan: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md
* Critique execution: Complete
* Critique depth: standard
* Depth provenance: explicit caller direction for standard depth
* Critique type: follow-up
* Earlier critique: .copilot-tracking/reviews/plans/2026-10-14/real-mcp-server-plan-critique.md

## Inputs and Criterion Boundary

* Task context and caller requirements: Reconcile PC-001 through PC-009 against the revised plan and identify only material new gaps the revision introduced. One assessment, standard depth, no plan or source edits.
* Research and evidence considered: .copilot-tracking/research/2026-10-14/real-mcp-server-research.md, including the new Cycle 2 log and Evidence Log entries W6 through W11; .copilot-tracking/reviews/plans/2026-10-14/real-mcp-server-plan-critique.md; repository state previously reviewed, including src/ai_governance_harness/mcp_server/tools.py, src/ai_governance_harness/guardrails/sovereignty.py, src/ai_governance_harness/agent/orchestrator.py, tests/, and pyproject.toml.
* Decisions, dependencies, task Goals, and task Requirements considered: D1 through D4 (all Confirmed and unchanged); FR-001 through FR-008; NFR-001 through NFR-014; phases P01 through P05 with the renumbered P03 task set (P03-T01 security, new P03-T02 authorization discovery, P03-T03 telemetry, P03-T04 security tests) and the revised P04 and P05 dependency edges.
* Assessment boundary: The critique evaluates internal consistency, coverage, sequencing, and whether the applied fixes actually close the earlier findings. It cannot verify live Azure Container Apps behavior, Microsoft Entra token issuance, or MCP SDK API details; the new research entries record sources but this critique does not re-derive their content.

## Coverage Assessment

| Requirement, research, phase, or task ID | Coverage | Evidence or concern |
|------------------------------------------|----------|---------------------|
| FR-001 through FR-008; NFR-001 through NFR-013; P01, P02, P04, P05 | Covered | Each requirement has an owning task with named artifacts, and the P02 to P05 dependency edges remain acyclic after the P03 renumbering. P04-T01 correctly re-points to P03-T03 for telemetry. |
| NFR-014; P03-T02, P03-T04, P05-T01, P05-T02 | Partial | The authorization discovery contract, 401 behavior, and metadata assertions are now owned and tested, but no acceptance step verifies that a named standards-compatible client completes the discovery flow end to end. See PC-011. |
| FR-006; P04-T01, P04-T02, P05-T01 | Partial | P04-T02 excludes exact health paths and P05-T01 asserts the exclusion set, but P04-T01 does not pin the health path names it implements. See PC-010. |
| NFR-006; P02-T03, P03-T04 | Partial | The dangling test file is resolved, but P02-T03 is now asked to cover authentication-boundary behavior that P03-T01 implements later. See PC-012. |
| Research evidence; Sources | Partial | Cycle 2 and W6 through W11 close the hosting evidence gap, but the MCP authorization specification that P03-T02 now depends on appears in neither the Evidence Log nor the plan Sources. See PC-013. |
| NFR-012; P03-T01, P03-T04 | Covered | Best-effort per-principal limiting, the documented replica-multiplied upper bound, and the explicit instruction not to present it as a global quota make the control and its limits honest and testable. |
| NFR-002, NFR-007, NFR-010; P02-T02 | Covered | Hosted configuration rejects an absent region independently of the shared guardrail, and the preserved offline default protects existing CLI and guardrail tests. |
| D4; P04-T02; Risks and Open Questions | Covered | The stateful-session risk row is removed; production `minReplicas: 1` is a reviewed parameter with no session affinity, consistent with the stateless decision. |

## Verdict

* Verdict: Pass
* Rationale: All nine earlier findings are resolved in the plan text, and the two High findings are closed with substantive contracts rather than restatement: a dedicated authorization discovery task with an explicit bounded fallback and a named authentication-exclusion set asserted by infrastructure policy tests. The revision introduced no blocking gaps. One Medium and three Low findings remain; each is a precision or verification improvement that an implementer or the planning parent can absorb without re-planning, and PC-011 is a residual risk the plan already acknowledges through its documented return-to-planning trigger.

## Earlier Finding Reconciliation

| Earlier finding | Status | Evidence |
|-----------------|--------|----------|
| PC-001 Platform authentication likely to reject health probes | Resolved | P04-T02 excludes `/health/live`, `/health/ready`, and both protected-resource metadata paths and nothing else; P05-T01 asserts that exclusion set and that `/mcp` remains protected. Residual path-naming precision is re-recorded as PC-010. |
| PC-002 No authorization discovery surface for MCP clients | Resolved | New P03-T02 owns OAuth 2.0 Protected Resource Metadata at `/.well-known/oauth-protected-resource/mcp` and the root fallback, the Entra issuer and audience, the HTTP 401 unauthenticated response, and the supported-client documentation, with an explicit return-to-planning trigger if a required client cannot complete discovery. The remaining verification gap is re-recorded as PC-011. |
| PC-003 Rate limiting had no enforcement point and conflicted with stateless scaling | Resolved | P03-T01 selects a process-local token bucket keyed by authenticated principal, states the deployed upper bound as the per-replica limit multiplied by maximum replicas, and forbids presenting it as a strict global quota; P03-T04 tests per-replica semantics only. |
| PC-004 P03-T03 extended a test file no task created | Resolved | P02-T03 now creates `tests/test_mcp_http.py` and P03-T04 extends it. A sequencing consequence of this fix is re-recorded as PC-012. |
| PC-005 Residual risk row contradicted D4 and the replica floor | Resolved | The stateful scale-to-zero row is removed; P04-T02 Details separates development `minReplicas: 0` from production `minReplicas: 1` as reviewed parameters without session affinity. |
| PC-006 Advice-boundary goal and compliance risk unreconciled | Resolved | The plan Goal now scopes the remote surface to region, read-only, provenance, authentication, and privacy boundaries and places narrative filtering in the orchestrator; the risk row is reframed as a Low documentation risk with an Implementation owner. |
| PC-007 Sovereignty guardrail fail-open unaddressed | Resolved | P02-T02 Details states that hosted configuration rejects an absent region before calling `SovereigntyGuardrail` and that the shared permissive offline default is deliberately preserved for NFR-007. The P03-T04 reference describing tests/test_guardrails.py as fail-closed examples remains loosely worded but is no longer misleading given this explicit statement. |
| PC-008 Deployment and identity requirements lacked research evidence | Resolved | The research artifact records a Cycle 2 wider, deeper, and contrarian pass over Azure hosting alternatives and a finding supported by W6 through W11 covering ingress, authentication, managed identity, probes, scaling, and sticky sessions. The newly introduced authorization dependency is re-recorded as PC-013. |
| PC-009 Operational ownership beyond telemetry emission unassigned | Resolved | P03-T03 sets 30-day development and 90-day production retention with operations-role access and two parameterized alert conditions; P04-T02 provisions separate development and production parameter sets; P05-T01 adds alerting to the Bicep policy assertions. |

## Findings

<!-- rpi:critique id=PC-010 -->
### PC-010 [Low]: The health endpoint paths are fixed in infrastructure but not in the task that implements them

* Related IDs: FR-006, P04-T01, P04-T02, P05-T01
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P04-T01 ("Provide liveness and readiness endpoints outside the MCP protocol path") against P04-T02 ("Exclude only `/health/live`, `/health/ready`, ...").
* Concern: The exact paths are asserted by infrastructure and by P05-T01 policy tests, but the application task that creates them does not name them, so the contract exists only on the consuming side.
* Impact: An implementer who chooses different path names produces probes and authentication exclusions that do not match the application, recreating the PC-001 failure mode at a later and more expensive point.
* Smallest useful change: Name `/health/live` and `/health/ready` in the P04-T01 Requirements so the application and infrastructure share one stated contract.
* Action owner: planning parent
* Exact resolving evidence: P04-T01 Requirements contain the same literal health paths that P04-T02 excludes and P05-T01 asserts.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-011 -->
### PC-011 [Medium]: No acceptance step proves a named client completes the authorization discovery flow

* Related IDs: NFR-014, FR-004, P03-T02, P03-T04, P05-T01, P05-T02
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P03-T02 Details ("The application does not claim to customize the platform-generated `WWW-Authenticate` header" and "If a required client cannot complete Entra discovery through this contract, return to planning"); P03-T04 tests metadata and 401 behavior; P05-T01 acquires a token directly and calls one tool.
* Concern: Every planned test exercises the server side of the contract. The deployed smoke test supplies its own token and therefore never traverses the unauthenticated-discovery path that the design depends on. The plan's own escape hatch is conditioned on a client failing to complete discovery, but nothing in P03 through P05 would detect that condition.
* Impact: NFR-014's client-compatibility clause is satisfied by documentation and server-side assertions only. If the platform 401 does not carry a usable challenge, the gap surfaces when a real consumer first connects, after the full deployment path is built, which is exactly when the return-to-planning branch is most costly.
* Smallest useful change: Add one acceptance step to P05-T01 or P05-T02 that connects one named standards-compatible MCP client with no pre-supplied token and records whether discovery and authorization complete, with that result as the explicit trigger for the P03-T02 fallback.
* Action owner: planning parent
* Exact resolving evidence: A P05 task names the client, the no-token starting condition, and the pass or fail criterion that activates the P03-T02 return-to-planning branch.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-012 -->
### PC-012 [Low]: P02-T03 is scoped to authentication behavior that P03-T01 has not yet implemented

* Related IDs: NFR-006, P02-T03, P03-T01, P03-T04
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P02-T03 ("Add `tests/test_mcp_http.py` for HTTP configuration, middleware, authentication-boundary, and hosted-mode behavior that P03 extends") with Dependencies limited to P02-T01 and P02-T02; the hosted request security middleware is created by P03-T01.
* Concern: The PC-004 fix moved file creation earlier but carried authentication-boundary scope with it, so P02-T03 names coverage whose implementation does not exist at that point in the sequence.
* Impact: An implementer either stalls at P02-T03, writes placeholder tests, or pulls P03-T01 work forward, blurring the otherwise clean phase boundary.
* Smallest useful change: Limit the P02-T03 description of the new file to HTTP configuration and hosted-mode startup behavior and state that P03-T04 adds the authentication cases.
* Action owner: planning parent
* Exact resolving evidence: P02-T03 describes only coverage implementable from its declared dependencies, with authentication cases attributed to P03-T04.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-013 -->
### PC-013 [Low]: The authorization specification underpinning P03-T02 is absent from evidence and Sources

* Related IDs: NFR-003, NFR-014, P03-T02, Sources
* Evidence: .copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md, P03-T02 References cite the MCP authorization specification, but the plan Sources list and the research Evidence Log (W1 through W11) contain only the transports specification.
* Concern: The normative basis for the new discovery task, including the metadata path convention and required fields, is cited at task level only and has no dated evidence record, unlike the Container Apps sources added for PC-008.
* Impact: The specific metadata path and field set cannot be audited or revisited against a recorded retrieval during implementation, which is the same traceability weakness PC-008 addressed for hosting.
* Smallest useful change: Add the MCP authorization specification to the plan Sources and record it as a dated evidence entry supporting the P03-T02 requirements.
* Action owner: planning parent
* Exact resolving evidence: The authorization specification appears in the plan Sources and in the research Evidence Log with a retrieval date and a supports statement referencing P03-T02.
* Decision route: direct planner correction

## Strengths and Residual Risk

* The PC-002 fix is substantive rather than cosmetic. P03-T02 separates what the platform owns from what the application owns, states the discovery mechanism it relies on, declines to claim control over the platform challenge header, and pre-registers the escalation path if the contract proves insufficient. That is the correct shape for a bounded first deployment under D3.
* PC-003 is resolved with an honest control rather than an overstated one. Documenting the deployed bound as per-replica multiplied by maximum replicas, and forbidding its presentation as a global quota, prevents a false assurance that would otherwise have reached operator documentation.
* The authentication exclusion set is now closed rather than open ended: P04-T02 enumerates four paths, and P05-T01 asserts that these are the only exclusions. This converts the highest-severity earlier finding into a testable invariant.
* The P03 renumbering was applied consistently. P04-T01 re-points to P03-T03, P03-T04 depends on all three preceding P03 tasks, and no stale task identifier remains.
* Residual risks explicitly carried by the plan and not re-raised here: cold-start latency under scale-to-zero, contributor disruption from the Python 3.11 floor, best-effort rather than strict rate limiting, and operator misreading of the raw-tool advice-filter boundary. Each has a named owner and mitigation.
* Residual risk recorded but not accepted by a test gate: PC-011. The plan anticipates the failure mode but has no step that would detect it.

## Questions or Blocking Evidence Gaps

* None. No finding requires evidence the plan or research cannot supply, and no finding requires a user decision.

## Limitations

* Platform behavior remains unverified by this critique. Whether Container Apps authentication can exclude the exact four paths named in P04-T02, and what its unauthenticated 401 response contains, are accepted as planned assumptions backed by W7 rather than confirmed here. PC-011 exists precisely because the plan currently has no step that would surface an error in those assumptions.
* MCP SDK specifics for stateless Streamable HTTP and the in-memory test client were not verified against the SDK.
* The applied-fix table in the plan's Critique Disposition section was treated as a claim and checked against the plan body and research artifact rather than accepted at face value; all nine claims were confirmed.

## Recommended Next Action

* Highest-impact finding: PC-011
* Action owner: planning parent
* Smallest next action: Add a single named-client, no-token discovery acceptance step to P05 and apply the three Low precision corrections (PC-010, PC-012, PC-013) directly; no further critique is warranted for these.
* User response required: no
