<!-- markdownlint-disable-file -->
# HVE Builder Security Boundaries

## Scope

* Active modes: create, improve, and refactor, inferred from the HVE Builder default. The existing target was improved and refactored; no new artifact was needed.
* Approved source write boundary: `<user-home>/.vscode/agent-plugins/github.com/microsoft/hve-core/.github/skills/hve-core/hve-builder/SKILL.md`
* Requirements: keep untrusted content from changing instruction authority or write scope; sanitize source-derived content before reuse; prohibit unsafe Vally stimulus authoring or import.

## Baseline and Change

The target already required treating read or fetched content as data and keeping secrets out of artifacts, but it did not define an operational sanitization procedure or explicitly cover source artifacts under review, tool results, reviewer returns, and Vally stimuli. Existing mode routing, lifecycle, capability-bearing frontmatter, opaque tools-configuration boundary, and confirmation rule were retained.

The candidate replaces the generic content rule with explicit authority isolation and source-text minimization, secret and unnecessary personal-data removal, neutral or delimited representation of instruction-like content, provenance handling, and a Vally category-level refusal rule.

Candidate file SHA-1: 27c411fc3bbd66118cb4606617a927054b44c28b

## Validation

* Passed: git diff --check in the HVE Core checkout.
* Passed: npx vally lint --strict .github/skills/hve-core/hve-builder (one skill, two of two checks).
* Not assessed: markdownlint-cli2 reports zero files because the repository CLI configuration excludes .github/skills/**.
* Deferred: npm run validate:skills could not start because pwsh is unavailable. Rerun this command after PowerShell 7 is installed and available as pwsh.
* Environment note: npm ci completed to install lockfile dependencies and reported six high-severity dependency advisories; no audit remediation was attempted.

## Review and Outcome

The HVE Builder Reviewer initially returned one required High finding in Safety and enforcement: policy-sensitive Vally stimuli were not explicitly prohibited. The parent verified the supplied content-policy guard, added the narrow refusal rule, and requested targeted closure. The reviewer confirmed the finding closed with no directly related regression.

* Review verdict: Pass after one correction cycle.
* Mechanical validation: Deferred because the repository-owned skill validator could not run; the targeted Vally check and whitespace check passed.
* Overall outcome: Deferred. The source change and review are complete, but the missing PowerShell validation must run before claiming full lifecycle completion.
* Stop reason: no remaining supported source correction; stop pending the explicit validation prerequisite.
* Distribution: no artifact was added, moved, or removed, so plugin membership synchronization was not applicable.