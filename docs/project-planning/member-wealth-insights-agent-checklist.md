---
checklist_id: "CHK-2026-SUPER-001"
title: "Member Whole-of-Wealth Insights Agent Implementation & Dependency Checklist"
status: "completed"
version: "1.0.0"
related_plan_id: "TASK-2026-SUPER-001"
related_prd_id: "PRD-2026-SUPER-001"
related_brd_id: "BRD-2026-SUPER-001"
related_sec_id: "SEC-2026-SUPER-001"
created_date: "2026-10-13"
last_updated: "2026-10-13"
license: "CC-BY 4.0 (Microsoft HVE-Core)"
---
<!-- markdownlint-disable-file -->
# Member Whole-of-Wealth Insights Agent - Implementation & Dependency Checklist

> **CHK-2026-SUPER-001** | Status: completed | Version: 1.0.0 | Last Updated: 2026-10-13

This document serves as the master implementation and dependency verification checklist for the Member Whole-of-Wealth Insights & Interaction Advisory Agent MVP. It operationalizes all requirements, acceptance criteria, and security guardrails from:
- [Business Requirements Document (BRD-2026-SUPER-001)](./member-wealth-insights-agent-brd.md)
- [Product Requirements Document (PRD-2026-SUPER-001)](./member-wealth-insights-agent.md)
- [Security Plan (SEC-2026-SUPER-001)](./member-wealth-insights-agent-security-plan.md)
- [RPI Implementation Plan](../../.copilot-tracking/plans/2026-10-13/member-wealth-insights-agent-plan.md)

---

## 1. Prerequisites and Environment Dependencies

- [x] **Python Runtime**: Verify Python 3.10+ is active (`python3 --version`).
- [x] **Core Dependencies**: Ensure base libraries are installed:
  - [x] `pydantic>=2.0.0` (data model schema validation)
  - [x] `python-dotenv>=1.0.0` (environment variable configuration)
  - [x] `azure-identity>=1.16.0` (cross-tenant authentication)
- [x] **Development & Testing Dependencies**:
  - [x] `pytest>=8.0.0` (automated unit and scenario test runner)
  - [x] `azure-ai-projects` for live Azure AI Foundry cloud integration
- [x] **Environment Configuration**: Ensure `.env` is configured (or defaults safely to offline mock mode):
  - [x] `AZURE_TENANT_ID`
  - [x] `AZURE_AI_PROJECT_CONNECTION_STRING` or subscription/resource group coordinates

---

## 2. Requirements & Regulatory Traceability Matrix

| Requirement / Control ID | Description | Source Document | Implementing Phase / Task | Verification Method | Status |
|---|---|---|---|---|---|
| **FR-001** | Internal Superannuation Profile Aggregation | PRD §FR-001 / BRD §FR-001 | `P01-T01`, `P02-T01`, `P04-T01` | Scenario `AC-001` test | ✅ Verified |
| **FR-002** | Member Movement & Churn Root-Cause Analytics | PRD §FR-002 / BRD §FR-002 | `P01-T01`, `P02-T01`, `P04-T01` | Scenario `AC-002` test | ✅ Verified |
| **FR-003** | FUM Outflow Diagnostics & Cohort Risk Sizing | PRD §FR-003 / BRD §FR-003 | `P01-T01`, `P02-T01`, `P04-T01` | Scenario `AC-003` test | ✅ Verified |
| **FR-004** | Staff-Facing Interaction Guidance | PRD §FR-004 / BRD §FR-004 | `P03-T01`, `P04-T01`, `P05-T01` | Scenario `AC-004` test | ✅ Verified |
| **BR-001 / DD-001** | ASIC RG 244 Advice Boundary (No personal advice) | BRD §BR-001 / PRD §CON-001 | `P03-T01` | Regex advice filter test | ✅ Verified |
| **BR-002 / DD-002** | In-Fund Data Scope Only (No external wealth claims) | BRD §BR-002 / PRD §CON-003 | `P01-T01`, `P03-T01` | Schema & invariant audit | ✅ Verified |
| **BR-003 / CON-002** | APRA CPS 234 Australian Sovereignty | BRD §BR-003 / PRD §CON-002 | `P03-T01` | Region validation gate | ✅ Verified |
| **CON-004** | Staff-Only Channel (Zero direct member messaging) | PRD §CON-004 / BRD §DD-003 | `P05-T01` | CLI architecture review | ✅ Verified |
| **SEC-001–006** | MCP Layer & Synthetic Customer Isolation | Security Plan §6 | `P01-T01`, `P02-T01` | Schema isolation & ACL test | ✅ Verified |
| **NFR-002** | Recommendation Latency <= 2.5s (95th percentile) | PRD §NFR-002 / BRD §NFR-002 | `P04-T01`, `P05-T02` | Automated timing benchmark | ✅ Verified |

---

## 3. Phase-by-Phase Implementation Checklist

### Phase 1: Synthetic Data Models & Generator (`P01`)

- [x] **P01-T01: Define Data Schemas & Synthetic Generator**
  - [x] Create package directory: `src/ai_governance_harness/synthetic_data/`
  - [x] Implement `src/ai_governance_harness/synthetic_data/schemas.py`:
    - [x] `MemberRecord` (`member_id`, `full_name`, `age`, `tenure_years`, `risk_profile`, `has_closure_inquiry`)
    - [x] `AccountRecord` (`account_id`, `member_id`, `balance`, `phase`, `option_allocation`)
    - [x] `ContributionRecord` (`account_id`, `date`, `amount`, `contribution_type`, `usual_monthly_baseline`)
    - [x] `InteractionRecord` (`interaction_id`, `member_id`, `timestamp`, `channel`, `category`, `notes`, `closure_inquiry_flag`)
    - [x] `DigitalActivityRecord` (`member_id`, `month`, `login_count`, `document_downloads`, `baseline_logins`)
  - [x] Implement `src/ai_governance_harness/synthetic_data/generator.py`:
    - [x] Deterministic seed for reproducible generation
    - [x] Explicit test persona `MEM-001`: Active loyal member (steady contributions, high digital activity)
    - [x] Explicit test persona `MEM-002`: Churn risk member (50% reduction in contributions relative to baseline)
    - [x] Explicit test persona `MEM-003`: Immediate outreach member (closure inquiry flag = true)
  - [x] Output generated records to `src/ai_governance_harness/data/synthetic/`:
    - [x] `members.json`
    - [x] `accounts.json`
    - [x] `contributions.json`
    - [x] `interactions.json`
    - [x] `digital_activity.json`
  - [x] Verify complete absence of real PII, TFNs, bank account numbers, or external assets.

---

### Phase 2: Model Context Protocol (MCP) Data Access Gateway (`P02`)

- [x] **P02-T01: Implement Sandboxed MCP Tools**
  - [x] Create package directory: `src/ai_governance_harness/mcp_server/`
  - [x] Implement `src/ai_governance_harness/mcp_server/tools.py`:
    - [x] Tool 1: `get_member_profile(member_id: str) -> dict`
      - Fetches member details, total balance across accounts, investment option breakdown, and interaction timeline.
    - [x] Tool 2: `get_member_disengagement_signals(member_id: str) -> dict`
      - Calculates relative contribution decline vs. baseline, digital login trend, and closure inquiry presence.
    - [x] Tool 3: `get_cohort_churn_analytics(cohort_filter: Optional[str] = None) -> dict`
      - Aggregates cohort attrition drivers, rollover destinations, and trailing churn counts.
    - [x] Tool 4: `get_fum_outflow_summary() -> dict`
      - Sizes cohort FUM at risk and returns high-risk member count.
  - [x] Enforce Pydantic validation on all tool parameters and return payloads.
  - [x] Enforce strict read-only execution: prevent any file mutation or path traversal outside `data/synthetic/`.

---

### Phase 3: Compliance Guardrails & Boundary Enforcement Gates (`P03`)

- [x] **P03-T01: Build Advice & Sovereignty Boundary Guardrails**
  - [x] Create package directory: `src/ai_governance_harness/guardrails/`
  - [x] Implement `src/ai_governance_harness/guardrails/sovereignty.py`:
    - [x] `SovereigntyGuardrail`: Inspects Azure AI Foundry target endpoint region; raises `SovereigntyViolationError` if outside `australiaeast` / `australiasoutheast`.
  - [x] Implement `src/ai_governance_harness/guardrails/advice_filter.py`:
    - [x] `AdviceClassificationGuardrail`: Regex scanner for directive personal advice phrases ("you should switch", "we recommend transferring", "best option for your situation").
    - [x] `DisclosureAttacher`: Appends mandatory statutory general advice notice and in-fund data scope disclaimer.
    - [x] `WholeOfWealthInvariant`: Intercepts and scrubs any text implying external wealth completeness.
    - [x] Fail-Safe Fallback: Replaces violated generative guidance with sanitized, raw factual account balances.

---

### Phase 4: Agent Core Orchestration & Foundry Integration (`P04`)

- [x] **P04-T01: Implement Insights Agent Orchestrator**
  - [x] Create package directory: `src/ai_governance_harness/agent/`
  - [x] Implement `src/ai_governance_harness/agent/orchestrator.py`:
    - [x] Connect system prompts, MCP tool calls, and post-invocation guardrails into a unified reasoning flow.
    - [x] Handle Intent 1: Unified Profile Inquiry (`FR-001`).
    - [x] Handle Intent 2: Churn Root-Cause Attribution (`FR-002`).
    - [x] Handle Intent 3: Cohort FUM Outflow Sizing (`FR-003`).
    - [x] Handle Intent 4: Staff Interaction Prep (`FR-004`), ensuring closure inquiry immediately surfaces an outreach recommendation.
    - [x] Dual Backend Support:
      - [x] Live Cloud Backend: Uses `AIProjectClient` from `src/ai_governance_harness/foundry_client.py`.
      - [x] Offline Mock Backend: Deterministic rule-based synthesis for offline CI and fast test execution without network dependency.

---

### Phase 5: Staff CLI & End-to-End Automated Test Suite (`P05`)

- [x] **P05-T01: Build Staff Operator CLI**
  - [x] Implement `src/ai_governance_harness/cli.py`:
    - [x] Command: `python -m ai_governance_harness.cli profile <member_id>`
    - [x] Command: `python -m ai_governance_harness.cli churn <member_id>`
    - [x] Command: `python -m ai_governance_harness.cli prep <member_id>`
    - [x] Command: `python -m ai_governance_harness.cli fum-outflows`
  - [x] Format console output with clear sections, visual indicators, and statutory compliance disclaimers.
- [x] **P05-T02: Author Acceptance & Boundary Test Suite**
  - [x] Create test directory: `tests/`
  - [x] Implement `tests/test_synthetic_data.py`:
    - [x] Validate schema conformance of all generated JSON files.
    - [x] Verify test personas `MEM-001`, `MEM-002`, and `MEM-003`.
    - [x] Assert absence of PII, TFNs, or external wealth attributes.
  - [x] Implement `tests/test_mcp_tools.py`:
    - [x] Test all 4 MCP tools for accurate data extraction and calculation.
    - [x] Assert read-only enforcement and rejection of invalid identifiers.
  - [x] Implement `tests/test_guardrails.py`:
    - [x] Test regex detection of prohibited personal financial advice phrases.
    - [x] Test statutory disclaimer appending.
    - [x] Test sovereignty check failure on non-Australian region.
  - [x] Implement `tests/test_agent_scenarios.py`:
    - [x] `AC-001`: Profile returned with balance trajectory and provenance within 2 seconds.
    - [x] `AC-002`: Churn analysis isolates observed contribution/login drops from inferred causes.
    - [x] `AC-003`: FUM outflow risk sizes potential outflow on disengaged cohort.
    - [x] `AC-004`: Closure inquiry alone on `MEM-003` surfaces staff outreach opportunity.
  - [x] Run test suite: `pytest tests/` and verify 100% pass rate.

---

## 4. Completion & Sign-off Gate

- [x] All unit and scenario tests pass (`pytest tests/`).
- [x] Code formatting and quality check pass (`git diff --check`).
- [x] Markdown documentation and tracking records verified (`markdownlint-cli2`).
- [x] Changes-record created: `.copilot-tracking/changes/2026-10-13/member-wealth-insights-agent-changes.md`.

