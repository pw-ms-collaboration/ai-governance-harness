<!-- markdownlint-disable-file -->
# Task Research: real-mcp-server

| Field              | Value        |
|--------------------|--------------|
| Date               | 2026-10-14   |
| Researcher / agent | rpi-research |
| Output mode        | analysis     |

## Executive Summary

* Bottom line: The repository needs a thin MCP protocol adapter around its existing data gateway. The adapter must create an `MCPServer`, register the four typed Python functions as tools, and start a stdio or Streamable HTTP transport.
* Why this matters: The current package works only through direct Python calls. No MCP host can discover or invoke its functions until the protocol and transport layers exist.
* Research status: Complete for the requested walkthrough depth.
* Confidence and uncertainty: High confidence from direct source review and current official MCP and VS Code documentation. The team still needs to choose local stdio or deployed HTTP before implementation.

## What You May Not Know

* The existing `MCP_TOOL_DEFINITIONS` list is not needed by the current MCP Python SDK. The SDK derives tool names, descriptions, and JSON Schema from decorated functions, type hints, and docstrings.
* A local stdio server does not listen on a port. VS Code launches it as a child process and owns its stdin and stdout.
* The current MCP Python SDK requires Python 3.11+, while this project declares Python 3.10+ support.
* The existing direct-call gateway remains useful for CLI execution and unit tests. MCP can be an adapter rather than a replacement.

## Findings

### The Current Gateway Has No MCP Protocol Boundary

The current module loads data and exposes ordinary Python functions. It has no MCP SDK dependency, server object, tool decorators, capability negotiation, JSON-RPC handling, or transport startup. An external host therefore has no process or URL to connect to.

* Questions: Q1
* Evidence state: Evidence-backed finding
* Evidence: C1 establishes the direct-call gateway and standalone function-schema list. C2 establishes the missing SDK dependency. C3 establishes the absence of server and transport code.
* Confidence and limits: High. All Python source and project dependencies were searched.

### A Thin Adapter Can Reuse the Existing Business Logic

The current SDK registers a typed function with `@mcp.tool()` and derives its input schema from Python annotations and its description from the docstring. The existing gateway methods already have typed signatures and deterministic return values, so an adapter can delegate to them without moving the data-loading or risk-calculation logic.

* Questions: Q2, Q4
* Evidence state: Evidence-backed finding
* Evidence: C1 establishes the reusable gateway functions. W1 and W2 establish current `MCPServer` construction and decorator-based tool registration.
* Confidence and limits: High. Return-content design and error mapping still require implementation choices.

### Startup Depends on the Transport

For local use, `mcp.run()` defaults to stdio and blocks while a host sends protocol messages through the child process pipes. VS Code needs a server entry in workspace MCP configuration containing the launch command and arguments. For deployment, the same server can use Streamable HTTP, which listens on an HTTP endpoint and adds authentication and transport-security obligations.

* Questions: Q3
* Evidence state: Evidence-backed finding
* Evidence: W2 defines stdio and Streamable HTTP startup. W3 explains host-launched subprocess behavior. W4 defines VS Code workspace MCP configuration. W5 defines protocol transport requirements.
* Confidence and limits: High. The deployment environment is outside this walkthrough.

### MCP Is Optional for the Existing CLI

The CLI can continue calling the gateway directly. Introducing MCP into the CLI process would add protocol overhead without changing the result. MCP becomes valuable when VS Code, another IDE, an agent host, or a remote client must discover and call these tools.

* Questions: Q4
* Evidence state: Evidence-backed finding
* Evidence: C1 and C3 establish the direct-call design. W1 documents an in-memory client option for protocol-level tests without a subprocess.
* Confidence and limits: High for this repository. Future product requirements could make MCP the primary boundary.

### Azure Container Apps Supports the Selected Deployment Boundary

Azure Container Apps provides managed HTTPS ingress, built-in Microsoft Entra authentication, managed identity, health probes, session-affinity controls, scaling, and Azure Monitor integration. These capabilities support the selected stateless Streamable HTTP architecture without requiring an AKS cluster.

* Questions: Q3
* Evidence state: Evidence-backed finding
* Evidence: W6 through W11 establish the relevant Container Apps ingress, authentication, identity, probe, scaling, and session behavior.
* Confidence and limits: High for documented platform behavior. Region-specific SKU availability must be verified immediately before deployment.

## Recommendation and Alternatives

* Recommendation or decision state: Keep the gateway and add a separate MCP adapter only if external hosts must call the tools. Prefer stdio for local VS Code use and Streamable HTTP only for a deployed shared service.
* Rationale: This preserves tested business logic and isolates protocol concerns. C1, W2, W3, and W4 support the boundary.
* What could change this result: A requirement that all CLI calls cross the MCP boundary, a shared remote service requirement, or continued Python 3.10 support.

| Option | Benefits | Costs and risks | Evidence | Disposition |
|--------|----------|-----------------|----------|-------------|
| Local stdio adapter | Simple host launch, no port, appropriate for VS Code workspace use | Requires a launch command and clean stdout; each host runs its own process | W2, W3, W4 | Recommended for local use |
| Streamable HTTP service | Shared URL and deployable service | Requires hosting, authentication, origin validation, and network controls | W2, W5 | Viable for deployment |
| Keep direct Python calls only | No new dependency or process boundary | External MCP hosts cannot discover or invoke tools | C1, C2, C3 | Viable when MCP interoperability is not required |

## Scope and Questions

* Goal: Explain what this repository needs to become a real MCP server and how it would start.
* Audience and use: A developer learning the current code and its intended MCP architecture.
* In scope: Existing gateway code, tool registration, MCP server lifecycle, transports, host configuration, and a bounded follow-up on Azure Container Apps capabilities used by the implementation plan.
* Out of scope: Source changes, live deployment, final SKU selection, and production execution.
* Decision and evidence criteria: Claims must match repository evidence and current official MCP documentation.
* Requested output: A deeper walkthrough segment.

| ID | Question | Source | Status |
|----|----------|--------|--------|
| Q1 | Why is the current package not a protocol-compatible MCP server? | User request and repository evidence | Answered internally |
| Q2 | Which components are required for a real Python MCP server? | Inferred from the walkthrough | Answered |
| Q3 | How would the server start and connect to a host? | User request | Answered |
| Q4 | Which existing code can remain unchanged? | Inferred from the walkthrough | Answered |

## Decisions and Feedback

| Group | Decision or feedback item | Status | Owner | Rationale or input needed | Evidence | Impact of answer |
|-------|---------------------------|--------|-------|---------------------------|----------|------------------|
| D1 | Explain the real MCP server boundary before continuing the application walkthrough | Confirmed | User | The user selected deeper MCP coverage | Conversation | Controls the next walkthrough segment |

## Risks and Open Questions

| Priority | Type | Risk, question, or research item | Impact | Smallest action or evidence needed | Owner |
|----------|------|----------------------------------|--------|------------------------------------|-------|
| M | Open question | Choose local stdio or deployed Streamable HTTP | Determines startup, configuration, and security work | Confirm the intended MCP consumers and deployment model | User or downstream planning |
| M | Risk | Current MCP SDK requires Python 3.11+, but the project declares Python 3.10+ | Adding the dependency can break the stated support floor | Raise the Python floor or select and test a compatible SDK version | Downstream planning |
| L | Risk | Stdio servers cannot emit ordinary output to stdout | Stray output can corrupt the protocol stream | Use stderr-backed logging and test host startup | Downstream implementation |

## Planning Readiness and Next Step

| Field                            | Record |
|----------------------------------|--------|
| Research disposition             | Executed |
| Decision participation           | User-owned, inherited from the active walkthrough |
| Planning Readiness               | Not applicable. This is explanatory research only |
| Research depth and helpers       | Wider, deeper, and contrarian waves complete; no helper used |
| Blockers                         | None |
| Output mode and planning support | Analysis; no planning handoff requested |
| Continuation owner               | Active walkthrough |
| Required gates or confirmations  | None for explanation; transport and Python-version decisions remain for implementation |
| Next action                      | Return the evidence-backed explanation to the active walkthrough |
| Primary evidence file            | .copilot-tracking/research/2026-10-14/real-mcp-server-research.md; date supplied by session context |

## Research Record

### Method and Boundaries

| Field                            | Record |
|----------------------------------|--------|
| Research posture and provenance  | Focused; brief-based because the user requested one bounded technical explanation |
| Completion basis                 | Stop when current official sources establish server construction, tool registration, transport startup, and host connection |
| Explicit limits or deadline      | No source changes; remain within the active walkthrough |
| Codebase and external scope      | src/ai_governance_harness/mcp_server and its callers; official MCP documentation and Python SDK |
| Initial candidate areas          | tools.py, pyproject.toml, MCP Python SDK server API, transports, and host configuration |
| Evidence root                    | Default repository .copilot-tracking/research root |
| Constraints and excluded sources | Research-only; no secrets; no deployment or implementation |
| Prior knowledge                  | Repository source and tests were directly reviewed during the walkthrough |

### Extensions and Participation

#### Extension Registry

| Extension | Status | Provenance | Scoped authority |
|-----------|--------|------------|------------------|
| rpi-walkthrough | Selected | Active user-requested walkthrough | Owns pacing and segment delivery |
| rpi-research | Selected | Walkthrough requires current external MCP contract | Owns the bounded evidence cycle |
| Repository Markdown and tracking instructions | Selected | Matching artifact path | Own artifact formatting and location |

### Research Cycle Log

| Cycle | Wave | Scope | Result | Re-entry effect |
|-------|------|-------|--------|-----------------|
| 1 | Wider | Current MCP architecture and Python SDK | Confirmed server object, decorated primitives, and standard transports | Prioritized tool registration and host startup |
| 1 | Deeper | Server, tools, transports, and host startup | Confirmed stdio child-process flow, Streamable HTTP flow, and VS Code configuration | Supported a thin-adapter explanation |
| 1 | Contrarian | Alternatives to a separate MCP process | Confirmed direct calls remain valid for the CLI and in-memory MCP clients support tests | Avoided recommending MCP inside every application path |
| 2 | Wider | Azure hosting alternatives | Compared Container Apps, App Service, and AKS for the selected HTTP boundary | Prioritized Container Apps |
| 2 | Deeper | Container Apps ingress, authentication, identity, probes, and scaling | Verified the capabilities used by the implementation plan | Supported deployment requirements |
| 2 | Contrarian | Stateful and cluster-based alternatives | Confirmed stateless Container Apps avoids sticky-session and AKS operational costs for current tools | Preserved App Service and AKS as later alternatives |

### Evidence Log

| ID | Type | Source | Retrieved | Supports |
|----|------|--------|-----------|----------|
| C1 | Code | src/ai_governance_harness/mcp_server/tools.py | 2026-10-14 | Current gateway and function definitions |
| C2 | Code | pyproject.toml | 2026-10-14 | No MCP SDK dependency |
| C3 | Code search | src/**/*.py | 2026-10-14 | No server instance or transport startup |
| W1 | Official SDK | https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md | 2026-10-14 | Current SDK requirement, server construction, and in-memory client |
| W2 | Official SDK docs | https://py.sdk.modelcontextprotocol.io/run/ | 2026-10-14 | Stdio and Streamable HTTP startup behavior |
| W3 | Official SDK docs | https://py.sdk.modelcontextprotocol.io/get-started/real-host/ | 2026-10-14 | Host subprocess launch and VS Code example |
| W4 | Official VS Code docs | https://code.visualstudio.com/docs/agent-customization/mcp-servers | 2026-10-14 | Workspace and portable MCP configuration |
| W5 | MCP specification | https://modelcontextprotocol.io/specification/2025-11-25/basic/transports | 2026-10-14 | Standard transport and security requirements |
| W6 | Microsoft Learn | https://learn.microsoft.com/azure/container-apps/ingress-overview | 2026-10-14 | Managed HTTPS ingress and transport configuration |
| W7 | Microsoft Learn | https://learn.microsoft.com/azure/container-apps/authentication | 2026-10-14 | Built-in authentication and token validation |
| W8 | Microsoft Learn | https://learn.microsoft.com/azure/container-apps/managed-identity | 2026-10-14 | System-assigned and user-assigned managed identity |
| W9 | Microsoft Learn | https://learn.microsoft.com/azure/container-apps/health-probes | 2026-10-14 | Startup, readiness, and liveness probes |
| W10 | Microsoft Learn | https://learn.microsoft.com/azure/container-apps/scale-app | 2026-10-14 | Replica scaling and scale-to-zero behavior |
| W11 | Microsoft Learn | https://learn.microsoft.com/azure/container-apps/sticky-sessions | 2026-10-14 | Stateful affinity limitations avoided by the stateless decision |
| W12 | MCP specification | https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization | 2026-10-14 | OAuth Protected Resource Metadata, HTTP 401 discovery, authorization-server discovery, and token audience requirements |

### Self-Check

* Opening state was persisted before external research.
* Wider, deeper, and contrarian waves completed in order.
* Each material finding maps to repository or official external evidence.
* Source changes, secrets, and environment values are excluded.
* No additional cycle is required because the bounded questions are answered and the remaining choices are implementation decisions.
