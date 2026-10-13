<!-- markdownlint-disable-file -->
# RPI Changes: Deployable MCP Server

## Metadata

* Task ID: RPI-REAL-MCP-SERVER-2026-10-14
* Related plan: [.copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md](../../plans/2026-10-14/real-mcp-server-plan.md)
* Implementation date: 2026-10-14

## Execution Status

* Status: Partial
* Declared invocation scope: Full plan
* Completed scope markers: `P01`, `P01-T01`, `P01-T02`, `P02`, `P02-T01`, `P02-T02`, `P02-T03`, `P06`, `P06-T01`, `P06-T02`, `P06-T03`
* All remaining active-plan markers: `P03` through `P05`, `P07`, and their task markers
* Status basis: The local runtime, MCP protocol, Foundry chat UI, launchers, and local validation are complete. The user deferred Azure deployment work.

## Execution Summary

The repository now provides a real MCP server over stdio and stateless Streamable HTTP, privacy-safe local security and telemetry controls, a Foundry-powered browser chat that calls data tools through MCP, separate service entry points, and one convenience launcher. Azure Container Apps deployment remains planned but intentionally deferred.

## Completed Work

### Established the Python and CI foundation

* Related phase or task: `P01`, `P01-T01`, `P01-T02`
* Files:
  * [pyproject.toml](../../../pyproject.toml)
  * [.github/workflows/ci.yml](../../../.github/workflows/ci.yml)
  * [README.md](../../../README.md)
* Behavior or functionality changed: Raised the Python floor to 3.11, made `pyproject.toml` authoritative, added bounded runtime and development dependencies, documented public PyPI and CFS usage without repository-bound feed configuration, and added Python 3.11-3.13 CI.
* Validation: Passed locally on Python 3.13; Python 3.11 and 3.12 are represented by CI because those interpreters are not installed locally.

### Added the MCP protocol and local transports

* Related phase or task: `P02`, `P02-T01`, `P02-T02`, `P02-T03`
* Files:
  * [src/ai_governance_harness/mcp_server/server.py](../../../src/ai_governance_harness/mcp_server/server.py)
  * [src/ai_governance_harness/mcp_server/config.py](../../../src/ai_governance_harness/mcp_server/config.py)
  * [src/ai_governance_harness/mcp_server/http_app.py](../../../src/ai_governance_harness/mcp_server/http_app.py)
  * [src/ai_governance_harness/mcp_server/__main__.py](../../../src/ai_governance_harness/mcp_server/__main__.py)
  * [tests/test_mcp_server.py](../../../tests/test_mcp_server.py)
  * [tests/test_mcp_transports.py](../../../tests/test_mcp_transports.py)
* Behavior or functionality changed: Registered exactly four typed read-only tools, added explicit gateway startup, sanitized protocol errors, provenance, stdio, configurable HTTP, and package entry points.
* Validation: Passed in-memory protocol, stdio subprocess, and real localhost HTTP client tests.

### Added local security and telemetry controls

* Related phase or task: Partial implementation toward `P03`
* Files:
  * [src/ai_governance_harness/mcp_server/security.py](../../../src/ai_governance_harness/mcp_server/security.py)
  * [src/ai_governance_harness/mcp_server/telemetry.py](../../../src/ai_governance_harness/mcp_server/telemetry.py)
  * [tests/test_mcp_http.py](../../../tests/test_mcp_http.py)
* Behavior or functionality changed: Added origin, media type, body size, protocol revision, trusted hosted principal, tenant, audience, scope, correlation, rate-limit, health, OAuth metadata, and privacy-safe telemetry behavior. Azure platform configuration remains deferred.
* Validation: Passed local middleware and negative-path tests; actual Container Apps authentication remains unvalidated.

### Added the Foundry chat UI

* Related phase or task: `P06`, `P06-T01`, `P06-T02`, `P06-T03`
* Files:
  * [src/ai_governance_harness/chat/](../../../src/ai_governance_harness/chat/)
  * [src/ai_governance_harness/dev_launcher.py](../../../src/ai_governance_harness/dev_launcher.py)
  * [tests/test_chat_app.py](../../../tests/test_chat_app.py)
  * [tests/test_chat_config.py](../../../tests/test_chat_config.py)
  * [tests/test_chat_service.py](../../../tests/test_chat_service.py)
* Behavior or functionality changed: Added a dependency-free accessible browser UI, a bounded Foundry tool-calling loop that discovers and invokes tools through MCP, separate MCP/chat entry points, and a combined launcher that opens the UI and owns both processes.
* Validation: Passed focused tests and one live Foundry acceptance turn that selected `get_member_disengagement_signals`, returned a response, and attached the governance disclosure.

## Implementation-Time Plan Updates

### Expanded the active plan for local chat

* Affected plan area or markers: Added `P06`, `P07`, `FR-009` through `FR-011`, `NFR-015`, and decisions `D5` through `D7`
* What changed: Added a Foundry-powered chat UI, separate service topology, combined local launcher, and future two-app deployment scope.
* Why: The user requested a simple UI that works with the MCP service.
* Triggering evidence: User selected Foundry, dependency-free HTML/CSS/JavaScript, and two services with one convenience launcher.
* User answer or decision: Confirmed during implementation.
* Reconciliation performed: Phase markers, tasks, decisions, requirements, scope, and follow-up items updated.
* Planning and critique state: Original MCP plan critique remains passed; the user-approved UI expansion is implemented locally and Azure deployment is deferred.

### Deferred Azure deployment

* Affected plan area or markers: `P03`, `P04`, `P05`, `P07`
* What changed: Kept Azure Container Apps, platform authentication, infrastructure, deployment, and deployed acceptance work unchecked.
* Why: The user explicitly requested continued local work and no Azure move yet.
* Triggering evidence: User direction during implementation.
* User answer or decision: Confirmed.
* Reconciliation performed: Remaining markers and follow-up items identify the deferred scope.
* Planning and critique state: Local work is validated; deployment review is not yet eligible.

## Validation Record

| Check | Scope | Status | Evidence or reason |
|-------|-------|--------|--------------------|
| Initial worktree inspection | Full plan | Passed | Existing user and planning artifacts were preserved; no unrelated tracked modifications were present |
| Unit and integration tests | Local runtime and UI | Passed | 61 tests passed |
| Ruff | Repository | Passed | No lint findings |
| Package build | Distribution | Passed | Source and wheel artifacts built |
| Dependency audit | Installed environment | Passed | No known third-party vulnerabilities; the local project itself is not published on PyPI |
| Live Foundry chat | MCP and UI | Passed | Foundry selected one MCP tool and returned a disclosure-bearing response |
| Combined launcher | Local process lifecycle | Passed | Both readiness endpoints and UI loaded; launcher shutdown removed both child listeners |

## Pre-Review Reconciliation

* Plan markers and task-local context: Current for completed local scope and deferred Azure scope.
* Completed-work entries and handoff prose: Current.
* Validation, blockers, remaining work, and follow-up items: Current.
* Review readiness: Local implementation is ready for review; full-plan deployment review is deferred.

## Blockers

* Azure work is not technically blocked, but is paused by explicit user direction.

## Remaining Work

* Complete hosted security and telemetry configuration in `P03`.
* Complete Container Apps packaging and deployment in `P04`.
* Complete deployed validation and operator guidance in `P05`.
* Complete chat deployment and acceptance in `P07`.

## Follow-Up Items

* Canonical plan list: [.copilot-tracking/plans/2026-10-14/real-mcp-server-plan.md](../../plans/2026-10-14/real-mcp-server-plan.md), `## Follow-Up Items`
* Resume the code walkthrough only if requested.
* Resume Azure phases only after the user confirms deployment work should begin.

## Return-to-Caller State

* Implementation execution status: Partial
* Declared scope and markers: Full plan; `P01`, `P02`, and `P06` complete, with `P03` through `P05` and `P07` remaining
* Validation coverage: Full local tests, lint, build, audit, live Foundry turn, and launcher lifecycle
* Blockers: Azure work paused by user direction
* Current plan updates: Foundry chat UI and deployment phases added
* Planning and critique state: Original plan passed critique; implementation-time UI scope recorded and validated locally
* Follow-up items: Azure phases and optional walkthrough
* Review readiness or no-handoff reason: Local implementation is ready; deployed acceptance is not yet in scope
* Continuation owner: User
