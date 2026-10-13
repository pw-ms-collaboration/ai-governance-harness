---
title: "RAI Assessment Plan: Member Whole-of-Wealth Insights Agent"
description: "Phase 1 scoping draft for a member insights and interaction advisory agent in Australian superannuation."
projectSlug: member-wealth-insights-agent
entryMode: from-prd
framework: NIST AI Risk Management Framework 1.0
status: Phase 1 scoped; Phase 2 prohibited-uses gate pending
---

## System Definition

### Purpose and intended outcome

The draft BRD describes an internal capability for an Australian superannuation provider to combine internal member information, identify patterns associated with member growth or departure, estimate potential funds-under-management (FUM) outflow, and help staff prepare more relevant member interactions. The intended business outcome is improved retention. The business baseline, approved target, and causal interpretation remain unresolved; the BRD describes a provisional comparison target and explicitly treats outreach comparisons as associations rather than proof of causation.

The system is described as a staff-facing co-pilot. It is not intended to contact members directly or provide personalized financial advice. Outputs are intended to be analysis, factual information, and general guidance, subject to confirmation of the advice boundary by AFSL Compliance.

### Confirmed scope from the draft BRD

- Initial data scope is limited to information held in the fund's internal systems; external financial data is excluded.
- Intended operational users include member service consultants, retention specialists, business analysts, and relevant management and compliance reviewers.
- The process combines registry, transaction, and digital activity data; creates a superannuation profile; analyzes behavior and trends; produces churn, growth, and FUM diagnostics; and presents interaction guidance to staff through a compliance filter.
- Staff remain responsible for member engagement. No direct member communication or autonomous outreach is described.
- Australian regulatory jurisdiction and Australian data sovereignty are stated constraints. The specific hosting provider and deployment design are not named.
- The BRD is marked draft, version 0.1.0. A prior PRD-session record notes a six-month historical lookback for baseline and target validation, while data sufficiency remains unverified; it also says contribution and digital-activity calibration windows should be determined separately. The goal and KPI target remain provisional.

### Data and information flow

The BRD identifies internal member registry, transaction, CRM/interaction, and digital activity information. Listed profile attributes include account balance history, contributions, investment option allocations, insurance status, and interaction history. Other signals include changes in contribution or digital activity, closure inquiries, completed rollovers, and staff outreach or subsequent retention outcomes. Member appetite/preferences are mentioned but their source, availability, and reliability are untested. The BRD explicitly classifies member PII and financial balances as data requiring protection.

At a high level, internal fund data flows through ingestion and identity resolution to a profile engine, behavioral and trend analytics, churn/FUM diagnostic components, and an interaction advisory agent. Staff see the resulting profile and suggestions in their desktop workflow and may provide feedback. The user confirmed that only the minimum necessary approved structured account and activity fields needed for staff support should be used. Free-text interaction content and sensitive/contextual data are excluded by default; either may be considered only after separate justification and review. Member data must not be used for model training or sent to an external model/provider for inference unless separately approved. The exact allowed field list and identifiers, access rules, retention periods, and deletion behavior remain unspecified. A prior requirements-session record points to `docs/project-planning/member-wealth-insights-agent.md` as a PRD, but that file is absent; the available source of requirements is the draft BRD.

### Technology, models, and deployment

The BRD names secure REST/GraphQL integrations with fund registry, CRM, and data-lakehouse systems; a profile engine; analytics pipelines; churn and FUM prediction models; cohort analytics; an interaction/next-best-action advisory agent; and a compliance filter. It does not identify model families, vendors, foundation models, training or inference locations, feature stores, or whether generated language uses an LLM. It requires encryption, role-based access, auditability, drift monitoring, versioned rollback, and Australian data residency, but implementation evidence is not supplied.

### AI Component Inventory

| Component | Intended function | Inputs and outputs | Model or automation detail | Status |
|---|---|---|---|---|
| Internal superannuation profile engine | Assemble a unified internal profile with provenance | Registry, balances, contributions, investment allocation, insurance, interactions; outputs a member analytical view | Implementation and identity-resolution approach unknown | In scope per BRD |
| Movement and churn analytics | Identify and explain patterns associated with departure, inactivity, or consolidation | Internal transactions and interaction events; outputs contributing-factor attribution | Analytics/model approach and causal safeguards beyond the stated evidence distinction need confirmation | In scope per BRD |
| FUM outflow diagnostic/predictive model | Flag potential outflow and estimate FUM at risk | Contribution and digital activity changes, closure inquiries; outputs risk indicators and estimates | Predictive model stated; model family, thresholds, calibration, and decision impact unknown | In scope per BRD |
| Cohort and trend analytics | Identify behavioral and macro/cohort patterns | Internal profile and activity signals; outputs segment/trend summaries | Method and cohort rules unknown | In scope per BRD |
| Interaction and next-best-action advisory agent | Give staff contextual analysis, talking points, and engagement topics | Member profile and behavioral trends; outputs staff-facing suggestions and compliance guidance | Whether an LLM is used, prompt/data handling, tool access, and guardrail implementation unknown | In scope per BRD |
| Advice/compliance filter | Prevent or identify outputs outside the intended advice boundary | Advisory-agent outputs; presents permitted guidance/classification | Control design, enforcement point, and test evidence unknown | Required in BRD; effectiveness unverified |

### Scope boundaries and unresolved items

- **Out of scope for initial release:** external financial accounts/assets and direct member communication.
- **Not approved or not yet specified:** exact approved structured personal-information inventory and identifiers, model selection, training-data provenance, population/demographic coverage, fairness evaluation, member appetite/preference provenance, separate signal thresholds and observation windows, hosting/vendor details, and final output destination. The user confirmed no member-data training or external-provider inference without separate approval. Free text and sensitive/contextual data are excluded by default and require separate justification and review before any inclusion. The prior requirements-session state records comprehensive detail and one clarification question per turn as preferences.
- **Human decision boundary:** the BRD positions the system as staff support, but does not state whether staff must review every score/suggestion, how overrides are captured, or whether scores can trigger prioritization or workflow actions. Confirm before risk classification.
- **Advice boundary:** personalized advice is excluded, but the compliance team has not yet confirmed that the proposed outputs and classifications are appropriate for the use case.

## Stakeholder Impact

### Stakeholders and affected people

| Group | Relationship to the system | Potential benefit | Potential impact or concern |
|---|---|---|---|
| Superannuation fund members | Affected individuals whose internal records are analyzed and who may receive staff outreach | More timely and context-aware service | Privacy loss, inaccurate or stigmatizing labels, unwanted or inappropriate outreach, unequal service, or advice-boundary harm |
| Member service consultants and retention specialists | Primary users who review profiles and suggestions | Faster preparation and relevant context | Automation bias, over-reliance, unclear rationale, workflow pressure, or responsibility ambiguity |
| Business analysts, product and retention leads | Define signals, analyze cohorts, and use aggregate insights | Better visibility of behavior and retention patterns | Misleading attribution, poor cohort definitions, or incentives that prioritize fund retention over member interests |
| Data engineering and analytics teams | Integrate, prepare, and operate data and models | More consistent analytical capability | Excessive access, linkage errors, poor data quality, drift, or uncontrolled secondary use |
| AFSL Compliance, Legal, Risk, and Privacy reviewers | Review advice boundaries, data use, controls, and governance | Earlier visibility of risks and evidence | Incomplete audit trails, unvalidated controls, or ambiguity about accountability |

### PII and member-data impact considerations

The system processes identifiable member profiles alongside financial balances and behavioral/interaction signals. Linkage across registry, transaction, CRM, and digital activity can increase the sensitivity of the combined profile. Staff-facing access, inferred disengagement/retention scores, and generated talking points create risks even when data remains internal and no member-facing chatbot is deployed. The user confirmed that call notes and other free text, as well as health, hardship, disability, beneficiary, or other sensitive/contextual information, are excluded from the initial release unless separately justified and reviewed. Only the minimum fields needed for staff support should be used; member data must not be used for model training or sent to an external model/provider for inference unless separately approved. The exact approved structured fields and identifiers, access rules, retention periods, and deletion behavior remain unspecified.

Potential member harms to examine in later phases include unauthorized access or disclosure, re-identification through cohort reports, inaccurate inferences being treated as fact, differential outreach based on balance or predicted retention value, unfair performance across demographic groups, and staff acting on guidance that is misunderstood as personalized financial advice. These are assessment considerations, not findings or confirmed system behaviors.

### Open questions carried from the BRD

- Compliance validation of the advice boundary remains open (`Q-003`).
- Contribution-reduction and digital-activity thresholds and observation windows remain open (`Q-004`, `Q-005`).
- The provisional 5% comparison target remains open (`Q-008`). A six-month historical lookback was selected in the prior requirements session for baseline and target validation (`Q-009`), but its data sufficiency and cohort size still need validation.
- The BRD records internal outreach and retention outcome data and comparable non-outreach members as confirmed, but the quality and limitations of that evidence have not been assessed here (`Q-006`, `Q-007`).

### Phase 1 status

This is a scope extraction from a draft BRD, not a compliance conclusion. The user directed that no further questions be asked. Scope is recorded using stated boundaries and marking unspecified implementation facts as unknown. Comprehensive detail is the recorded output preference.





## Risk Classification Screening

### Prohibited uses gate

**Preliminary result: No prohibited use identified from the documented intended use.** The BRD describes an internal staff-support system that analyzes fund-held member data and presents contextual information or outreach opportunities for human staff review. It does not describe autonomous member contact, automated eligibility or benefit decisions, coercive manipulation, or use of sensitive/contextual data in the initial scope. The user has further excluded free text and sensitive/contextual data by default and prohibited member-data training or external-provider inference absent separate approval.

**Limitation:** The available evidence does not contain a fund-specific prohibited-use policy or a compliance determination. The screen is limited to the described scope; it is not legal clearance or confirmation against policies not supplied. No separate jurisdictional legal interpretation is made. Re-screen if system purpose, data use, or autonomy changes.

### Risk indicators

| Indicator | Activated | Screening evidence and rationale |
|---|---|---|
| `safety_reliability` | Yes | Inaccurate profiles, churn explanations, or FUM-risk estimates could influence staff interactions with members and the prioritization of outreach. These are consequential financial-service interactions even though the tool does not make financial decisions or contact members autonomously. |
| `rights_fairness_privacy` | Yes | The system links identifiable member, balance, contribution, investment, insurance, and behavioral/activity records to produce individual-level profiles and retention signals. This creates material privacy risk and potential for disparate outreach or treatment if errors, proxies, or untested cohort differences influence staff. Exclusions and minimization reduce scope but do not remove these risks. |
| `security_explainability` | Yes | The system handles identifiable financial and behavioral information and generates predictive estimates and staff-facing guidance. Unauthorized access, identity-linkage errors, opaque attribution, or over-reliance could affect members. Encryption, RBAC, auditability, rationale inspection, drift monitoring, and rollback are specified as requirements, not verified controls. |

### Suggested assessment depth

**Suggested tier: Comprehensive** (three activated indicators). This follows the RAI workflow rule that two or more activated indicators suggest Comprehensive depth. This is a screening recommendation, not a completed assessment or approved tier. The Phase 2 hard gate remains open until the user confirms the tier.

The BRD remains a draft. Exact structured-field allowlist, model/vendor, training and inference architecture, demographics and fairness evaluation, staff override controls, signal thresholds, and verified control evidence remain open assessment inputs. No aggregate numeric risk score is assigned because the available screening method does not define a score calculation.
