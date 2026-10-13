<!-- markdownlint-disable-file -->
# Data Scope and Sovereignty Boundaries

## Data Scope Boundary

### In-Fund Superannuation Data Only

The Member Whole-of-Wealth Insights Agent and its underlying skills are strictly bounded to internal superannuation fund data systems. External data integration is deliberately excluded from the architecture to ensure compliance with privacy laws, the Australian Privacy Principles (APPs), and superannuation licensing conditions.

| Data Domain | Included Internal Sources | Excluded External Sources | Boundary Rule |
|---|---|---|---|
| **Member Registry** | Fund member ID, tenure, age cohort, employment status on file, communication preferences. | External credit scores, public records, social media profiles. | Strictly use internal registry; do not attempt identity enrichment from third parties. |
| **Account Balances** | In-fund accumulation balances, pension phase balances, transition-to-retirement (TTR) balances. | External bank accounts, term deposits, non-fund super accounts, SMSF holdings. | Balances represent in-fund holdings only; never infer external total net worth. |
| **Contributions** | Concessional contributions, non-concessional contributions, SG employer contributions to the fund. | Salary outside employer records, external investment dividends, partner income. | Contribution tracking is relative to historical fund contribution cadence only. |
| **Investments** | Selected fund investment options (e.g., Balanced, Growth, Cash), historical switching logs within the fund. | External share portfolios, cryptocurrency, residential property assets. | Analyze internal allocation shifts only; do not estimate total asset allocation. |
| **Insurance** | Death, TPD, and Income Protection policies held inside the fund. | External private health insurance, direct retail life insurance. | Insurance status reflects in-fund policy status only. |
| **Interactions & Digital** | Contact center call logs, digital portal logins, document downloads, account closure inquiries. | External website browsing, third-party app analytics. | Behavioral indicators must derive from fund-owned digital touchpoints only. |

### The Whole-of-Wealth Representation Invariant

The project is titled "Member Whole-of-Wealth Insights Agent" from a strategic perspective of consolidating disparate internal fund data silos. However, to avoid misleading representations under the *Australian Consumer Law* and ASIC guidance:

1. **Explicit Provenance Labeling**: Every profile view and analytical summary must explicitly display:
   > *"Data Scope: Internal Superannuation Fund Data Only. External assets, liabilities, and external superannuation balances are not captured."*
2. **No Extrapolation**: Models and skills must never estimate, impute, or extrapolate a member's total household wealth, mortgage balances, or external liquid savings.
3. **No Completeness Claims**: Reports must never state or imply that the fund possesses a complete financial picture of the member.

## Australian Sovereignty and Cloud Hosting Boundary (APRA CPS 234)

Under the Australian Prudential Regulation Authority's (APRA) Prudential Standard **CPS 234 (Information Security)** and the *Superannuation Industry (Supervision) Act 1993* (SIS Act), superannuation trustees bear strict accountability for protecting member data and ensuring business continuity.

### Geographic Confinement Rules

* **Storage Residency**: All relational databases, data lakes, vector embeddings, cache layers, and backup vaults must be provisioned exclusively within Microsoft Azure regions located within Australian sovereign territory (`Australia East` and `Australia Southeast`).
* **Inference Confinement**: All LLM inference calls via Azure AI Foundry or Azure OpenAI Service must execute strictly within Australian model deployment endpoints (e.g., `australiaeast`). Global model routing, preview models deployed in international regions, or fallback endpoints outside Australia are strictly prohibited.
* **Network Isolation**: All communication between application components and Azure AI Foundry must travel over private endpoints (Azure Private Link) within a designated Azure Virtual Network (VNet). Public internet exposure of AI inference or database endpoints is prohibited.

### Cross-Border Transfer Prevention

* Automated pipeline guardrails must verify tenant and deployment region configurations prior to invocation.
* Any request routed to a non-Australian resource identifier must fail immediately with a `SovereigntyBoundaryException`.

## Security and Privacy Controls (APRA CPS 234 & Privacy Act 1988)

1. **Encryption Standards**:
   * Transit: Enforce TLS 1.3 for all internal service mesh and API interactions.
   * Rest: Enforce AES-256 encryption across all data stores, vector caches, and persistent state files.
2. **Role-Based Access Control (RBAC)**:
   * Principle of Least Privilege: Consultants only access profiles of members currently assigned or actively inquiring.
   * Business analysts access aggregated, de-identified cohort analytics for churn modeling.
3. **Data Sanitization and Telemetry**:
   * Raw Member Identifiers (Tax File Numbers - TFNs, bank account numbers, physical addresses) must be scrubbed from prompts, LLM context windows, and logs.
   * Audit logs capture user ID, timestamp, member ID hash, skill invoked, and boundary disposition, without logging raw conversational PII.
