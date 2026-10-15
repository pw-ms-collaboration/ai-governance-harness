<!-- markdownlint-disable-file -->
# RPI Plan Critique: Local MVP of agent identity (mock Entra Agent ID)

## Metadata

* Task ID: entra-agent-id-mvp
* Critique date: 2026-10-14
* Plan: .copilot-tracking/plans/2026-10-14/entra-agent-id-mvp-plan.md (revision 1, seven phases P01 to P07)
* Critique execution status: Complete
* Critique depth: standard
* Depth provenance: default
* Invocation consumed: yes

## Inputs and Criterion Boundary

* Task context and caller requirements: local MVP of ADR 0009 (four closed-enum governance fields, staff role matrix as MCP-boundary pre-tool rules) and ADR 0010 (guarded local mock issuer on 127.0.0.1:8002, MCP `jwt` source, chat Bearer plus OBO forwarding, UI persona switcher, D14 guard, D15 local persona, reporting command, launcher). ADR 0008 is target only. Constraints ADR 0001, 0002, 0003 amendment, 0005, 0006. Governance context and policy must land and pass before mock, chat, and UI work. User decisions G1 to G3 are authoritative.
* Research and evidence considered: .copilot-tracking/research/2026-10-14/entra-agent-id-architecture-research.md (targeted lookups only); docs/planning/adrs/0009-enforce-agent-and-staff-identity-through-governance-policy-context.md; docs/planning/adrs/0010-use-a-local-only-mock-entra-agent-id-issuer-for-the-mvp.md; docs/planning/adrs/0003-minimize-identity-and-governance-telemetry.md (2026-10-14 amendment); source seams src/ai_governance_harness/governance/{context.py,engine.py,config.py,policies/default.yaml}, src/ai_governance_harness/mcp_server/{security.py,config.py,__main__.py,server.py,tools.py,telemetry.py,http_app.py}, src/ai_governance_harness/chat/{app.py,service.py,config.py,__main__.py}, src/ai_governance_harness/{cli.py,dev_launcher.py,security_audit.py}, security/vex/audit-policy.yaml, pyproject.toml, .github/workflows/ci.yml, tests/*.py; installed MCP SDK 2.3.0 (`mcp/client/streamable_http.py`, `mcp/server/runner.py`).
* Decisions, dependencies, task Goals, and task Requirements considered: G1 to G3 (user), A1 to A5 (agent), F1; locked inputs (test ownership per task, exact removals none, max nine new test modules, generated target `uv.lock`, validation = P07-T03 command set); all P01 to P07 task Goals, Requirements, Details, and Dependencies; FR-001 to FR-012, NFR-001 to NFR-008.
* Assessment boundary: the critique judges implementability and consistency of the plan against the supplied ADRs, research, and current source. It does not re-open G1 to G3, does not verify live Entra behaviour, and does not execute code.
* Preflight note: the plan's Critique Disposition records `Critique execution: started` and a `Pending` row awaiting this critique; no critique artifact existed at the output path. That record is treated as the caller's marker for this single invocation, not a prior run.

## Coverage Assessment

| Requirement, research, phase, or task ID | Coverage | Evidence or concern |
|------------------------------------------|----------|---------------------|
| FR-001, FR-002, NFR-002, NFR-003; P01-T01, P01-T02, P01-T07 import boundary | Covered | Contracts match ADR 0009 field table and ADR 0003 amendment; `to_policy_context()` omission pattern exists in context.py |
| FR-003; P01-T05, P01-T07 | Partial | Policy-level matrix is correct, but runtime allow for aggregate tools is broken by nested governed calls (PC-001) |
| FR-004, R19; P01-T03, P03-T01, P04-T01 | Partial | Loopback-bind condition not applied to MCP `jwt` or chat (PC-003); guard exception type does not map to exit code 2 (PC-004) |
| FR-005, D15, G2; P01-T04, P03-T01 | Partial | P03-T01 `jwt` default and validation are not scoped to HTTP transport, so stdio would be forced through `jwt` (PC-002) |
| NFR-007, R20; P01-T06, P03-T05, P04-T04 | Partial | Migration inventory misses test_telemetry.py and direct `ChatSettings`/`ServerSettings` constructions (PC-005) |
| FR-006, NFR-006, NFR-008; P02-T01 to P02-T05 | Covered | Claim, misuse, key-hygiene and guard tests specified; PyJWT 2.15.1 already locked via mcp[crypto] and msal[crypto] |
| FR-007; P03-T02 to P03-T05 | Covered with risk | ContextVar propagation verified as a risk with a fallback that is not yet executable (PC-009) |
| FR-008; P04-T01 to P04-T04 | Partial | Identity failure mapping through the MCP circuit breaker is unspecified (PC-006); chat has no elicitation callback (PC-008) |
| FR-009, NFR-004; P05-T01 to P05-T03 | Covered | Same-origin, storage, and CSP assertions specified |
| FR-010; P06-T01, P06-T03 | Partial | Depends on PC-001; report command configuration contract unspecified (PC-010) |
| FR-011, FR-012; P06-T02, P07-T01, P07-T02 | Covered | Launcher already has ordered `Service` start; evidence keeps `deferred` and `partial` |
| NFR-005, NFR-007; P07-T03 | Partial | Six commands omit two CI steps (PC-007) |

## Verdict

* Verdict: Revise
* Rationale: The plan is well grounded and its contracts match ADRs 0009, 0010, and 0003. However, one implementation blocker (PC-001) would make the analyst, reporting-agent, and local-analyst aggregate allows fail at runtime even though the policy-level matrix passes, and the P03-T04/T05/P06 acceptance tests would fail with no planned remedy. Two High findings (PC-002, PC-003) affect stdio usability and the R19 bypass guard. All findings are direct planner corrections; none requires a user decision or reverses G1 to G3.

## Findings

<!-- rpi:critique id=PC-001 -->
### PC-001 [High]: Aggregate tools call the governed member-signals method, so analyst, reporting, and local-analyst aggregate allows are denied at runtime

* Related IDs: FR-003, FR-010, NFR-001; P01-T05, P01-T06, P01-T07, P03-T05, P05-T03, P06-T01, P06-T03; ADR 0009 matrix
* Evidence: src/ai_governance_harness/mcp_server/tools.py `SuperannuationDataGateway.get_cohort_churn_analytics` and `get_fum_outflow_summary` loop over every member and call `self.get_member_disengagement_signals(m_id)`, which is decorated with `@governed_read_only_tool("get_member_disengagement_signals")` and evaluates PRE_TOOL and POST_TOOL under the caller's context. src/ai_governance_harness/mcp_server/server.py `_call_gateway` converts the resulting `GovernanceDeniedError` into `ToolError`. P01-T05 Details only notes the outreach case's nested member-signals call.
* Concern: Under the P01-T05 matrix, analyst (`mcp`), reporting (`mcp`, app), and local analyst are denied `get_member_disengagement_signals`, so the nested call denies the whole aggregate tool. The pure-policy matrix test in P01-T07 passes, but the P03-T05 end-to-end assertion "analyst gets an allowed `get_cohort_churn_analytics`", the P06-T01/T03 reporting allow, the CLI `fum-outflows` under an analyst persona, and the P05-T03 manual demo all fail. It also emits one deny event per member per aggregate call.
* Impact: Core matrix outcome (aggregate allow for analyst and reporting agent) cannot be demonstrated; implementers may be tempted to widen rules, which ADR 0002 and ADR 0009 Rollback forbid.
* Smallest useful change: Add to P01 (P01-T05 Details or a new task before P01-T06) a refactor in tools.py that moves signal computation into an ungoverned private helper (for example `_compute_disengagement_signals`) used by the two aggregate methods, while the public `get_member_disengagement_signals` and the outreach `build_case` path stay governed. Add a gateway-level test in P01-T07 that a local analyst (and a context with `boundary=mcp`, `actor=reporting`, `token_type=app`) gets allowed aggregate results and a denied member-signals call, without changing any policy rule.
* Action owner: planning parent
* Exact resolving evidence: plan revision naming the tools.py refactor target and a P01-T07 gateway-level test asserting aggregate allow and member deny for analyst and reporting contexts.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-002 -->
### PC-002 [High]: The `jwt` principal-source default and validation are not scoped to HTTP, but stdio is the default transport

* Related IDs: FR-005, FR-007, D15, G2, A3, R20; P01-T04, P01-T06, P03-T01, P03-T05
* Evidence: src/ai_governance_harness/mcp_server/config.py `ServerSettings.transport` defaults to `"stdio"` and `from_environment` defaults `MCP_TRANSPORT` to `stdio`. P03-T01 sets `MCP_PRINCIPAL_SOURCE` default to `jwt` whenever not hosted and says "`jwt` requires every value above" plus the guard, with no transport condition. Existing constructions that would fail: tests/test_telemetry.py line 197 `ServerSettings(environment="test")`, tests/test_mcp_http.py line 144 `ServerSettings(transport="streamable-http", hosted=False)`, tests/test_mcp_config.py default assertions, and the stdio subprocess in tests/test_mcp_transports.py.
* Concern: As written, stdio MCP (the D15/G2 token-less local path) would refuse to start unless all `jwt` variables and `MOCK_IDENTITY_ENABLED` are set, contradicting the README stdio flow and the plan's own "unset persona means deny" behaviour. The plan also does not say whether the requirement is a model validator (breaks every direct construction) or a `from_environment` rule.
* Impact: P03 cannot leave the suite green as claimed; stdio and legacy flows regress.
* Smallest useful change: In P03-T01, state that the principal source applies only when `transport == "streamable-http"`; stdio ignores it and keeps `boundary=local` from P01-T04. State where the requirement is enforced (model validator on HTTP transport only), and list the affected existing tests above in P03-T05's migration scope.
* Action owner: planning parent
* Exact resolving evidence: P03-T01 contract text with the transport condition, and P03-T05 naming tests/test_mcp_http.py local snapshot test, tests/test_telemetry.py MCP settings test, and the tests/test_mcp_transports.py stdio test as migrated.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-003 -->
### PC-003 [High]: The loopback-bind guard condition is not applied to MCP `jwt` trust or to chat's mock routes

* Related IDs: FR-004, R19, D14; P01-T03, P03-T01, P03-T05, P04-T01, P04-T04; ADR 0010 Guard
* Evidence: P03-T01 calls `require_mock_identity_allowed("mcp-jwt")` and P04-T01 calls `require_mock_identity_allowed("chat")`, both without `bind_host`. src/ai_governance_harness/mcp_server/config.py `validate_host` only rejects empty values, and chat/config.py accepts any `CHAT_HOST`. FR-004 and the plan's What You May Not Know require "the bind address is loopback" for all four mock components. Guard tests in P03-T05 and P04-T04 omit a non-loopback host case.
* Concern: With `MCP_HOST=0.0.0.0` or `CHAT_HOST=0.0.0.0` in a local environment, chat exposes `/api/mock-identity/signin` (persona minting) and MCP trusts mock-signed tokens on a network interface.
* Impact: The R19 authentication-bypass mitigation is incomplete for two of four components.
* Smallest useful change: Require `bind_host=settings.host` in both calls, and add a non-loopback host case to the P03-T05 and P04-T04 guard tests.
* Action owner: planning parent
* Exact resolving evidence: P03-T01 and P04-T01 contracts passing `bind_host`; guard test lists including a non-loopback `MCP_HOST` and `CHAT_HOST`.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-004 -->
### PC-004 [Medium]: `MockIdentityGuardError(RuntimeError)` does not reach the existing exit-code-2 handlers

* Related IDs: FR-004, R19; P01-T03, P01-T04, P02-T02, P03-T01, P04-T01, P06-T01
* Evidence: src/ai_governance_harness/mcp_server/__main__.py `main` and src/ai_governance_harness/chat/__main__.py `main` catch only `ValidationError` and `ValueError` for code 2. Pydantic wraps only `ValueError` and `AssertionError` raised inside validators, so a `RuntimeError` from a guard call in `ServerSettings` validation propagates unwrapped. src/ai_governance_harness/cli.py has no configuration exit code; its `2` already means `MemberNotFoundError`. P03-T01 says configuration errors exit "through the existing main handling".
* Concern: Guard failures would exit with a traceback and code 1 (or be reported as an unexpected CLI error, code 3). The P02-T05 and P03-T05 tests assert only "non-zero", so they would not catch it.
* Impact: Inconsistent fail-closed signalling, possible non-sanitized tracebacks, and an untested contract.
* Smallest useful change: Make `MockIdentityGuardError` subclass `ValueError` (or require explicit handlers in each `main`), have guard tests assert exit code `2` exactly, and state the CLI's guard exit code (and that it differs from, or is documented alongside, member-not-found).
* Action owner: planning parent
* Exact resolving evidence: P01-T03 contract showing the base class, and guard tests asserting exit code `2`.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-005 -->
### PC-005 [Medium]: The test-migration inventory misses suites that the plan's own changes break

* Related IDs: NFR-007, R20; P01-T06, P04-T04; locked input "exact test removals: none"
* Evidence: tests/test_telemetry.py `test_given_sensitive_inputs_when_evaluating_then_export_is_metadata_only` evaluates PRE_TOOL `get_member_profile` with the default context and asserts decisions `{"allow", "deny"}`; after P01-T05 both are deny. It is not in P01-T06's list. P04-T01 makes `AGENT_ID_SIDECAR_URL` and `AGENT_ID_INTERACTIVE_ID` required on `ChatSettings`, which breaks direct `ChatSettings(model_deployment=...)` constructions in tests/test_chat_app.py, tests/test_chat_service.py, and tests/test_chat_config.py; P04-T04 does not list them. (PC-002 lists the MCP settings cases.)
* Concern: P01 and P04 cannot "leave the suite green" with the stated assertion-change scope ("limited to rule names and the interim HTTP denial").
* Impact: Implementers either expand assertion changes without plan authority or stall.
* Smallest useful change: Add the telemetry test to P01-T06 (run it under an explicit allowed context such as the chat interactive fixture) and add a `ChatSettings` fixture or defaults migration to P04-T04; widen the "assertion changes limited to" sentence accordingly.
* Action owner: planning parent
* Exact resolving evidence: P01-T06 and P04-T04 migration lists naming these tests.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-006 -->
### PC-006 [Medium]: Identity failures inside the MCP client path are not mapped or isolated from the shared MCP circuit breaker

* Related IDs: FR-008, NFR-001; P04-T03, P04-T04
* Evidence: src/ai_governance_harness/chat/service.py routes `list_tools` and `call_tool` through `self._mcp_reliability.call(...)`, a process-wide `ReliabilityGuard` with `circuit_failure_threshold` default 3, and maps errors via `_known_service_error`, which only recognises `ChatServiceError` and `GovernanceDeniedError` (including inside exception groups). P04-T03 places OBO acquisition in an `httpx2` auth hook inside the MCP transport.
* Concern: An OBO failure or an MCP `401` raised inside the transport surfaces through the task group and reliability guard. The plan does not say it must surface as `identity_unavailable` or `authentication_required`, nor whether it counts toward the shared circuit. One persona's expired token could open the MCP circuit for every caller, or be reported as `upstream_failure`.
* Impact: Wrong error contract and a cross-user availability failure in the demo.
* Smallest useful change: In P04-T03, require the hook to raise the specific `ChatServiceError` codes (found by `_known_service_error`), fetch and check the first OBO before opening the MCP client, and state that identity failures don't count toward the MCP circuit (or explicitly accept that they do). Add a P04-T04 test that repeated identity failures don't open the MCP circuit.
* Action owner: planning parent
* Exact resolving evidence: P04-T03 requirement text on error mapping and circuit behaviour, plus the matching P04-T04 test.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-007 -->
### PC-007 [Medium]: P07-T03 validation does not fully mirror CI

* Related IDs: NFR-005, NFR-007; P07-T03; user direction "Validation mirrors CI"; locked input "validation = six CI commands"
* Evidence: .github/workflows/ci.yml also runs `uv run agt --json doctor` (with `PYTHONUTF8=1`) and `uv run cyclonedx-py environment --pyproject pyproject.toml --output-reproducible --output-file dist/sbom.cdx.json`. P07-T03 lists six commands without them. P02-T01 adds a direct dependency and two console scripts, which the SBOM step covers.
* Concern: The locked validation set is narrower than the confirmed user direction.
* Impact: A CI failure in the quality job could pass local validation.
* Smallest useful change: Add both commands to P07-T03 and update the locked validation input to eight commands (or record why they are excluded).
* Action owner: planning parent
* Exact resolving evidence: P07-T03 command list and the Critique Disposition locked input matching ci.yml.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-008 -->
### PC-008 [Low]: Chat has no elicitation callback, so chat-side elicitation forwarding and the UI outreach demo are not achievable as specified

* Related IDs: FR-008; P03-T04, P04-T03, P04-T04, P05-T03
* Evidence: src/ai_governance_harness/chat/service.py opens `Client(self._settings.mcp_url)` without `elicitation_callback`. P04-T03 says the auth hook covers "elicitation responses", and P04-T04 asserts elicitation requests carry an OBO bearer. Separately, src/ai_governance_harness/mcp_server/server.py resolves the outreach approval before the PRE_TOOL check, so a denied persona is prompted before denial (pre-existing).
* Concern: The chat-side elicitation assertion has nothing to test, and a retention specialist cannot complete outreach through the UI.
* Impact: Unclear acceptance and a manual demo step that can't pass.
* Smallest useful change: State that chat outreach elicitation remains unsupported in the UI, move the "elicitation carries the bearer" assertion to the P03-T05 end-to-end harness, and limit the P05-T03 manual check to the four non-elicitation tools. Record the approval-before-PRE_TOOL ordering as residual risk or a follow-up.
* Action owner: planning parent
* Exact resolving evidence: revised P04-T03, P04-T04, and P05-T03 text.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-009 -->
### PC-009 [Low]: The ContextVar-propagation fallback can't be carried out as described

* Related IDs: FR-007; P03-T04, P03-T05; plan risk "Middleware ContextVar may not reach session-based MCP tool handlers"
* Evidence: src/ai_governance_harness/mcp_server/server.py tool functions take no request-context parameter, and src/ai_governance_harness/mcp_server/security.py stores identity only in the ContextVar. The fallback reads "identity from `ctx.request_context.request`", but nothing on the request carries the normalized identity.
* Concern: If propagation fails, the fallback needs a design change in the middleware and every tool signature.
* Impact: Re-planning during implementation of the riskiest P03 item.
* Smallest useful change: In P03-T04, also store the normalized enums and `principal_hash` (never claims or token) in `request.state`, so the fallback becomes a local change in the tool wrappers.
* Action owner: planning parent
* Exact resolving evidence: P03-T04 requirement text naming `request.state` storage limited to the four enums and the hash.
* Decision route: direct planner correction

<!-- rpi:critique id=PC-010 -->
### PC-010 [Low]: The reporting command's configuration contract is unspecified

* Related IDs: FR-010, FR-012, G3; P06-T01, P07-T02
* Evidence: P06-T01 reuses the P04 sidecar client but doesn't name the variables for sidecar URL, reporting agent ID, and MCP URL, or their defaults. P06-T02 sets environment only for launched services. P07-T02 documents variables from P01-T03, P03-T01, and P04-T01 only.
* Concern: `uv run ai-governance-report` run in a separate terminal may have no configuration, and the README wouldn't explain it.
* Impact: Demo friction; implementer invents names.
* Smallest useful change: In P06-T01, bind the inputs (for example `AGENT_ID_SIDECAR_URL`, `AGENT_ID_REPORTING_ID`, `MCP_SERVER_URL`, with mock-constant loopback defaults that apply only when the guard passes) and add P06-T01 to P07-T02's `.env.example` list.
* Action owner: planning parent
* Exact resolving evidence: P06-T01 contract and P07-T02 variable list.
* Decision route: direct planner correction

## Strengths and Residual Risk

* Contracts for the context fields, policy matrix, mock claims, normalizer, and the ADR 0003 privacy boundary match ADR 0009, ADR 0010, and the amendment. Seams cited (MCP SDK `httpx2` client hook, `_sender_context`, `configure_azure_export(manual_only=True)`, `_validate_platform_principal`, launcher `Service`) exist as described.
* PyJWT 2.15.1 is already locked through `mcp[crypto]` and `msal[crypto]`, and `pyjwt` is already in `scan_distributions`, so P02-T01 is low risk for ADR 0006.
* Residual risk the parent may accept: Easy Auth claim-type aliases (for example the long-form `oid` URI) are fixture-tested only under G1; real-token verification stays post-MVP (R4, R7).

## Questions or Blocking Evidence Gaps

* None. No finding needs a user decision.

## Limitations

* Standard depth. The research document was consulted by targeted lookup, not read in full. No code was executed. Windows subprocess timing and `agt lint-policy --strict` acceptance of `in [...]` (R13) were not verified.

## Recommended Next Action

* Highest-impact finding: PC-001
* Action owner: planning parent
* Smallest next action: Revise P01 to add the tools.py aggregate refactor and gateway-level test, then apply PC-002 to PC-010 as direct corrections and finalize without another critique.
* User response required: no
