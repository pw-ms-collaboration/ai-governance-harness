<!-- markdownlint-disable-file -->
# Task Research: cps-standards-policy-reuse

| Field              | Value       |
|--------------------|-------------|
| Date               | 2026-10-14  |
| Researcher / agent | RPI Research |
| Output mode        | convergence |

## Executive Summary

* Bottom line: Use the CPS CSVs as versioned regulatory source material for a control catalog and traceability matrix, then derive a deliberately small set of executable runtime rules. Do not convert the CSV rows directly into the existing policy YAML.
* Why this matters: The current YAML decides whether one agent action may execute. Most CPS 230 and CPS 234 obligations govern an organisation's risk program, Board accountability, asset classification, incident response, control testing, business continuity, audit, and service providers. Treating all of that prose as action rules would create false compliance claims and untestable policy.
* Research status: Complete for the bounded repository analysis. No source or runtime files were changed.
* Confidence and uncertainty: High confidence in the architectural fit and repository constraints. Legal applicability, authoritative-source validation, and clause interpretation still require compliance or legal ownership.

## What You May Not Know

* The CSV files are extracted regulatory fragments, not a control schema. They contain 137 CPS 230 rows and 50 CPS 234 rows, including headings, parent clauses, child clauses, long determination text, and extraction artefacts.
* The repository already separates executable policy from assurance evidence for OWASP Agentic controls. That is a strong precedent for a CPS control profile rather than one overloaded YAML file.
* The current BRD maps CPS 234 to specific TLS 1.3 and AES-256 requirements. Those may be sound organisational controls, but the inspected CPS 234 clauses are principles-based and do not establish those exact algorithms. The mapping should label them as derived implementation controls, not direct quotations or one-to-one regulatory requirements.

## Findings

### The CPS files should become a source catalog, not executable policy

The files preserve useful source identity through standard title, generation time, fragment ID, heading, and content. That supports traceability, change detection, control mapping, and review. It does not yet provide control IDs, applicability, control owners, evidence requirements, test methods, enforcement points, or implementation status.

* Questions: Q1, Q3
* Evidence state: Evidence-backed finding
* Evidence: C1 and C2 establish the source structure and obligation domains.
* Confidence and limits: High for repository use. The CSV provenance and authoritative status were not externally validated.

The raw files should remain immutable inputs. A normalized catalog should preserve the exact standard, version or effective date, fragment ID, source text hash, heading hierarchy, and source location. Derived fields should be kept separate so a changed source fragment can be detected without silently overwriting an interpretation.

### The existing YAML is a narrow action-enforcement contract

The packaged policy binds to one agent, maps lifecycle stages to exact action names, and denies unmatched actions. At evaluation time the engine sees an action type, a small privacy-minimized governance context, and optional per-call data. Current call sites provide counts, known-tool state, result type, and error state, not regulatory concepts such as asset criticality, control effectiveness, service-provider materiality, recovery tolerance, or incident severity.

* Questions: Q2, Q3
* Evidence state: Evidence-backed finding
* Evidence: C3, C4, C5, C6, and C9 establish the policy shape, engine inputs, call-site facts, and tested semantics.
* Confidence and limits: High for the current implementation. Future Toolkit versions may add capabilities, but ADR 0001 intentionally contains those behind the repository adapter.

This means only controls decidable from request-time facts belong in the runtime policy. Examples include denying unknown tools, requiring authenticated hosted access, requiring explicit approval for defined actions, denying capabilities without an approved sandbox, or denying access when a supplied asset classification exceeds an action's allowed handling class.

### Most CPS obligations need assurance evidence and operational workflows

CPS 234 covers accountability, security capability, policy framework, asset classification, third-party controls, incident response, annual testing, independent assurance, internal audit, and APRA notification. CPS 230 covers operational-risk management, critical operations and tolerances, incidents, business continuity, annual exercises, service-provider registers and agreements, monitoring, audit, and notifications.

* Questions: Q3, Q4
* Evidence state: Evidence-backed finding
* Evidence: C1 and C2 establish the obligation domains; C7 shows the repository already models non-runtime assurance separately.
* Confidence and limits: High for the categorisation. Whether a specific clause applies to this organisation or deployment remains an external compliance decision.

These obligations fit a control profile with evidence types such as policy documents, ownership records, asset registers, threat assessments, test results, incident records, continuity exercises, provider due diligence, contractual clauses, audit reports, remediation records, and notification timestamps. Some can emit runtime telemetry, but telemetry is evidence of operation, not proof that the broader obligation is satisfied.

### A three-part policy architecture provides the cleanest reuse boundary

The strongest design is:

1. A source layer preserving raw CPS fragments and provenance.
2. A control-profile layer mapping applicable clauses to control objectives, owners, evidence, tests, status, and related harness capabilities.
3. An enforcement layer containing only deterministic runtime rules supported by explicit policy inputs and semantic tests.

* Questions: Q3, Q4
* Evidence state: Evidence-backed finding
* Evidence: C1 through C9 support the separation between source obligations, repository assurance evidence, and action enforcement.
* Confidence and limits: High as an architecture recommendation. Exact schemas and migration tasks belong in Planning.

The mapping should allow one clause to produce several controls and one control to satisfy several clauses. It should also distinguish `direct`, `derived`, `supporting`, and `not-applicable` relationships so that controls such as TLS 1.3 or AES-256 are not presented as verbatim CPS mandates.

### Direct CSV-to-YAML conversion is unsafe

Direct conversion appears simple but loses the distinction between legal obligation, interpretation, organisational control, runtime decision, and evidence. It would also inherit extraction artefacts, duplicate or hierarchical fragments, long determination text, and clauses whose truth cannot be evaluated during an agent action.

* Questions: Q1, Q3, Q4
* Evidence state: Evidence-backed finding
* Evidence: C1, C2, C3, and C4 show the structural and semantic mismatch.
* Confidence and limits: High. A direct conversion could still generate a searchable reference index, but not a trustworthy executable policy.

## Recommendation and Alternatives

* Recommendation or decision state: Confirmed direction: pilot the three-part source, control-profile, and enforcement architecture with CPS 234, while retaining CPS 230 as a later extension.
* Rationale: It reuses the CSV material without overstating runtime enforcement, follows the repository's existing separation of policy and evidence, and preserves the default-deny contract (C1-C9).
* What could change this result: A requirement to build only a documentation crosswalk, an authoritative enterprise GRC schema that must be used instead, or evidence that the Toolkit supports and the team wants a richer control model inside one policy contract.

| Option | Benefits | Costs and risks | Evidence | Disposition |
|--------|----------|-----------------|----------|-------------|
| CPS 234 pilot using source catalog plus control profile plus derived runtime rules | Preserves provenance, supports audit and change tracking, keeps rules testable, avoids false compliance claims, and limits initial scope | Requires a mapping schema and ownership workflow; CPS 230 remains later work | C1-C9 | Selected |
| Documentation-only CPS crosswalk | Fastest and lowest runtime risk | Does not improve runtime policy or machine-checkable assurance | C1, C2, C7 | Viable for a smaller scope |
| Direct CSV-to-policy generation | Low initial transformation effort | Semantically incorrect for most clauses, difficult to test, and prone to extraction artefacts | C1-C4 | Rejected |
| Add CPS metadata directly to the current YAML | Keeps one file | Overloads an execution contract, complicates Toolkit linting, and mixes evidence with enforcement | C3, C4, C8 | Rejected |

## Scope and Questions

* Goal: Determine how the CPS 230 and CPS 234 material can inform or become part of the harness policies.
* Audience and use: Repository maintainers deciding how to model, evaluate, and maintain governance policies.
* In scope: The CPS CSV files, the existing policy schema and loader, evaluation surfaces, and directly related tests or documentation.
* Out of scope: Source changes, generated policies, runtime behavior changes, external publication, and implementation.
* Decision and evidence criteria: Preserve source traceability, fit existing contracts, avoid treating regulatory prose as executable logic without interpretation, and identify a maintainable adoption path.
* Requested output: A practical recommendation, alternatives, trade-offs, and planning-ready next steps.

| ID | Question | Source | Status |
|----|----------|--------|--------|
| Q1 | What information and structure do the CPS CSV files contain? | Explicit | Answered |
| Q2 | How are policies represented, loaded, and evaluated today? | Inferred | Answered |
| Q3 | Which CPS content can be reused directly, transformed, or only cited? | Explicit | Answered |
| Q4 | What adoption model best preserves traceability and maintainability? | Inferred | Answered, pending direction confirmation |

## Decisions and Feedback

| Group | Decision or feedback item | Status | Owner | Rationale or input needed | Evidence | Impact of answer |
|-------|---------------------------|--------|-------|---------------------------|----------|------------------|
| D1 | Research and plan only; stop before implementation | Confirmed | User | Selected research-and-plan working mode | User direction | Prevents source or behavior changes |
| D2 | Pilot a three-part source, control-profile, and enforcement architecture with CPS 234; retain CPS 230 as a later extension | Confirmed | User | Selected after reviewing full-scope, pilot, documentation-only, and stop alternatives | C1-C9 | Fixes the planning scope and deliverables |

## Risks and Open Questions

| Priority | Type | Risk, question, or research item | Impact | Smallest action or evidence needed | Owner |
|----------|------|----------------------------------|--------|------------------------------------|-------|
| High | Risk | The CSV provenance, currency, and legal applicability are not yet independently validated | A technically correct mapping could use a non-authoritative or inapplicable source | Assign a compliance owner to verify authoritative APRA sources and applicability before controls are approved | Downstream |
| High | Risk | Derived technical controls could be presented as direct CPS requirements | Misleading compliance claims | Require relationship type and rationale on every clause-to-control mapping | Downstream |
| Medium | Risk | Source extraction artefacts and parent-child rows could create duplicate or malformed controls | Mapping drift and noisy evidence | Normalize hierarchy and hash source text before interpretation | Downstream |
| Medium | Further research | CPS 230 extension sequencing after the CPS 234 pilot | Affects later roadmap only | Reassess using pilot evidence | Downstream |
| Medium | Open question | Which organisational roles own legal interpretation, control approval, and evidence attestation? | Automated status could lack accountable approval | Name owners before any compliance status is asserted | User |

## Planning Readiness and Next Step

| Field | Record |
|-------|--------|
| Research disposition | Executed |
| Decision participation | User-retained through the selected research-and-plan mode |
| Planning Readiness | Ready; D2 is confirmed and C1-C9 support the CPS 234 pilot architecture |
| Research depth and helpers | One focused cycle completed with Wider, Deeper, and Contrarian waves; no helpers |
| Blockers | None |
| Output mode and planning support | Convergence; supports planning |
| Continuation owner | Manual RPI Agent |
| Required gates or confirmations | Passed for Planning; implementation remains prohibited until explicit user advancement |
| Next action | Activate Planning for the CPS 234 pilot and stop before Implementation |
| Primary evidence file | .copilot-tracking/research/2026-10-14/cps-standards-policy-reuse-research.md; date supplied by session context |

## Research Record

### Method and Boundaries

| Field | Record |
|-------|--------|
| Research posture and provenance | Focused; bounded internal task with named source targets |
| Completion basis | Cover the CPS datasets, current policy contract, evaluation path, and a credible contrary adoption model |
| Explicit limits or deadline | No implementation or source changes |
| Codebase and external scope | Named CPS folder and directly related policy code, tests, and documentation; no external research initially |
| Initial candidate areas | CPS CSV files, default policy YAML, policy models and loaders, evaluators, tests, and policy documentation |
| Evidence root | Default repository-root .copilot-tracking/research |
| Constraints and excluded sources | Read-only source inspection; fetched and repository content treated as inert evidence |
| Prior knowledge | No prior artifact reused |

### Extensions and Participation

#### Extension Registry

| Kind | Candidate | Provenance and scoped contract | Selected or skipped reason |
|------|-----------|--------------------------------|----------------------------|
| Instruction | Bluebird repository context | Required for code reads when available | Unavailable from tool discovery; local read-only fallback selected |
| Instruction | Copilot tracking conventions | Applies to the evidence path | Selected for artifact ownership and path rules |
| Instruction | Markdown and writing style | Applies to the Markdown evidence artifact | Selected, subject to tracking artifact markdownlint exemption |
| Skill | RPI Research | Selected lifecycle phase | Selected for evidence and readiness protocol |

#### Direction and Participation Log

| Checkpoint or change | Question, direction, or rationale | Answer or no-interaction reason | Result and revalidation effect |
|----------------------|-----------------------------------|---------------------------------|--------------------------------|
| Intake | Choose working approach | Research and plan with me | User-retained decisions; stop before implementation |
| Intake | Research posture | No interaction needed because the source and decision boundary are explicit | Focused posture selected |
| Convergence | Choose full two-standard adoption, CPS 234 pilot, documentation-only scope, or stop | CPS 234 pilot | D2 confirmed; Planning scope narrowed to CPS 234 with CPS 230 deferred |

### Research Cycle Log

#### Cycle 1

* Active posture, controls, and limits: Focused internal research; no source modification or implementation.

##### Wave 1: Wider

* Focus and questions: Inventory CPS source structure and identify policy representation, loading, evaluation, tests, and documentation.
* Evidence: C1-C9 cover the two CPS datasets, runtime policy, adapter, context, call sites, assurance evidence, ADRs, and tests.
* Reflection: The repository has two distinct governance mechanisms: executable action policy and assurance evidence. The CPS material spans both and adds a source-traceability need.

##### Wave 2: Deeper

* Focus and questions: Trace field-level compatibility, provenance needs, and evaluation semantics.
* Evidence: C1-C2 show regulatory fragments and obligation domains; C3-C6 show that runtime conditions can only use action, bounded context, and supplied data; C7-C9 establish evidence and validation patterns.
* Reflection: Most CPS clauses cannot be evaluated from current runtime facts. A normalized mapping layer is needed before selecting executable controls.

##### Wave 3: Contrarian

* Focus and questions: Test whether direct conversion, reference-only use, or a separate control catalog is safer than embedding CPS content in executable policies.
* Evidence: Direct conversion conflicts with the current policy contract (C1-C4); reference-only use leaves machine-checkable assurance and runtime opportunities unused (C5-C9).
* Reflection: A three-part architecture retains the strengths of both alternatives without conflating them.

##### Synthesis and Re-entry

| Material or claim | Evidence | Disposition | Rationale | User-facing effect |
|-------------------|----------|-------------|-----------|--------------------|
| Raw CPS fragments are reusable as regulatory source records | C1, C2 | Accepted | Stable fragment IDs and source text support provenance and change tracking | Preserve an immutable source layer |
| Every CPS clause should become a YAML rule | C1-C6 | Rejected | Most obligations are not decidable during an action evaluation | Derive only deterministic runtime rules |
| CPS should be documentation only | C7-C9 | Rejected as the default | The repository can support machine-readable evidence and selected runtime enforcement | Use a control profile plus enforcement subset |
| CPS 234 pilot with three-part architecture | C1-C9 | Accepted and confirmed | Best semantic fit, strongest traceability, and lower-risk first increment | Planning can define schemas, gates, and validation |

* Another complete three-wave cycle needed: No.
* Trigger or stop basis: The bounded questions are answered, material claims are evidenced, and further code reads are unlikely to change the architecture choice.
* Readiness or revalidation effect: Planning is ready after the user-owned architecture decision.

### Evidence Log

* Helpers: None.

| ID | Claim or finding | Source or location | Retrieved and version | Tool | Confidence | Notes |
|----|------------------|--------------------|-----------------------|------|------------|-------|
| C1 | CPS 230 is a 137-row extracted source spanning operational risk, incidents, continuity, critical operations, service providers, testing, audit, and notifications | src/ai_governance_harness/governance/policies/CPS_Standards/cps_230_operational_risk_management _2026-10-14.csv; fragment and heading records | Not applicable | Read and structured parse | High | Includes headings, parent and child clauses, long determination text, and extraction artefacts |
| C2 | CPS 234 is a 50-row extracted source spanning accountability, security capability, assets, controls, incidents, testing, audit, and notifications | src/ai_governance_harness/governance/policies/CPS_Standards/cps_234_information_security _2026-10-14.csv; fragment and heading records | Not applicable | Read and structured parse | High | Principles-based obligations include related and third-party assets |
| C3 | The active policy is an exact-agent, default-deny list of lifecycle action rules | src/ai_governance_harness/governance/policies/default.yaml; policy document | Not applicable | Read | High | No regulatory metadata or control evidence schema |
| C4 | The adapter loads one YAML policy and evaluates action, bounded governance context, and optional data | src/ai_governance_harness/governance/engine.py; GovernanceEngine | Not applicable | Read | High | Toolkit semantics are intentionally contained |
| C5 | Policy context currently exposes workload, environment, authentication outcome, optional correlation ID, and principal hash | src/ai_governance_harness/governance/context.py; GovernanceContext | Not applicable | Read | High | No asset, provider, incident, or critical-operation fields |
| C6 | Current call sites supply counts, known-tool state, error state, and result type | src/ai_governance_harness/chat/service.py and src/ai_governance_harness/mcp_server; require_allowed calls | Not applicable | Search and read | High | These facts support narrow runtime decisions only |
| C7 | The repository already keeps an assurance control profile separate from executable policy | src/ai_governance_harness/governance/evidence/owasp-agentic.yaml and governance/snapshot.py; evidence summary | Not applicable | Read | High | Status, evidence, and limitation fields provide a precedent, not a complete CPS schema |
| C8 | Architecture decisions require one default-deny policy and repository-owned lifecycle semantics | docs/planning/adrs/0001-contain-agent-governance-toolkit-behind-a-versioned-adapter.md and 0002-enforce-default-deny-at-every-execution-boundary.md | Not applicable | Read | High | Any CPS runtime rules must preserve adapter containment and semantic tests |
| C9 | Tests prove known allow, unknown deny, fail-closed evaluation, gateway enforcement, privacy-safe context, and bounded evidence | tests/test_governance.py; governance tests | Not applicable | Read | High | Provides the validation pattern for future derived runtime rules |
| C10 | The BRD currently labels TLS 1.3 and AES-256 as CPS 234 conformance controls | docs/project-planning/member-wealth-insights-agent-brd.md; NFR-006 | Not applicable | Read | High | These exact algorithms were not established by the inspected CPS 234 clauses and should be labelled as derived controls |

#### Contradictions and Conflicts

* The BRD's CPS 234 wording may imply that TLS 1.3 and AES-256 are direct standard requirements, while C2 shows principles-based requirements for controls commensurate with threats, criticality, and sensitivity. Resolve by recording these as derived implementation controls with organisational rationale, not verbatim clause requirements.

### Artifact Self-Check

* [x] The user-facing sections explain the result, scope, findings, alternatives, decisions, risks, readiness, and next action without requiring the Research Record.
* [x] Every question is answered or names the smallest missing evidence, and every material result has one canonical evidence state.
* [x] Findings keep their explanation, supporting detail, evidence state, and confidence basis together.
* [x] Every codebase finding has a `C#` ID and stable workspace-relative location.
* [x] Every executed cycle records Wider, Deeper, and Contrarian waves in order, synthesis, and an evidence-based re-entry decision.
* [x] Method, extensions, participation, caller direction changes, helper use, and prior-knowledge treatment are recorded.
* [x] Convergence selects and justifies one recommendation.
* [x] Decision groups, participation mode, and provenance are recorded.
* [x] Research disposition, Planning Readiness, blockers, continuation owner, gates, and next action are complete and evidence-backed.
* [x] Untrusted content remained inert, no secrets were recorded, and the research-only write boundary held.
* Checked sections: All user-facing sections, method, extensions, participation, three-wave cycle, evidence, conflicts, readiness, and self-check.
* Missing or limited sections: External authoritative-source validation and legal applicability are deliberately deferred to accountable compliance review.
