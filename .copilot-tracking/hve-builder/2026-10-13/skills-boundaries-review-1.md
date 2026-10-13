<!-- markdownlint-disable-file -->
# Skills Boundaries Authoring & Review Record

## Scope

* Active modes: `create`, inferred from caller request `create the skills boundries`.
* Approved source write boundary:
  - `.github/skills/skills-boundaries/SKILL.md`
  - `.github/skills/skills-boundaries/references/advice-boundaries.md`
  - `.github/skills/skills-boundaries/references/data-and-sovereignty-boundaries.md`
  - `.github/skills/skills-boundaries/references/skill-authority-matrix.md`
  - `.copilot-tracking/hve-builder/2026-10-13/skills-boundaries-review-1.md`
* Requirements: Establish authoritative operational, data scope, advice regulatory, channel, and cloud sovereignty boundaries for agent skills in the AI governance harness and Member Whole-of-Wealth Insights Agent.

## Baseline and Candidate Changes

* Baseline: Prior state had no skills defined in `.github/skills/`. PRD `PRD-2026-SUPER-001` and BRD `BRD-2026-SUPER-001` established core non-negotiable boundaries:
  - `DD-001`: Advice Boundary (Corporations Act 2001 Ch 7, ASIC RG 244)
  - `DD-002`: Internal-only data scope (no external assets or open banking)
  - `DD-003`: Staff-mediated interaction model (no direct member messaging)
  - `DD-004`: Sovereignty and compliance boundary (APRA CPS 234, Australia East/Southeast)
* Artifacts Authored:
  1. `SKILL.md`: Main entrypoint defining the 5 primary boundary categories, PRD functional skill mappings (`FR-001` to `FR-004`), verification protocol, and fail-safe stop rules.
  2. `references/advice-boundaries.md`: Regulatory taxonomy (Factual Information vs General Advice vs Personal Advice), concrete permitted and prohibited phrasing rules, litmus test, and mandatory statutory disclaimer.
  3. `references/data-and-sovereignty-boundaries.md`: Data ingestion inclusions and exclusions, the Whole-of-Wealth representation invariant, APRA CPS 234 Australian residency rules, encryption standards, and RBAC.
  4. `references/skill-authority-matrix.md`: Granular authority tier assignments (Advisory, Verified, Restricted), inputs/outputs contracts, permitted/prohibited actions, sequence diagram, and fail-closed escalation workflow.

## Validation

* `git diff --check`: Passed (clean whitespace, no trailing spaces).
* `markdownlint-cli2`: Passed (0 issues in 4 files).
* Frontmatter validation: Passed (standard portable fields only: `name`, `description`, `argument-hint`, `license`, `user-invocable`).

## Review and Outcome

* Review pass against `review-rubric.md`:
  - **Outcome and Structure**: PASS (Outcome-first, explicit success criteria, clear stop rules, unambiguous section hierarchy).
  - **Safety and Enforcement**: PASS (Strict personal advice prohibition, sovereign data residency enforcement, untrusted content handling, fail-closed exception handling).
  - **Context and Portability**: PASS (Skill-root relative paths used, clean frontmatter, no hard-coded machine paths).
  - **Instruction Quality**: PASS (Imperative voice, concrete positive and negative examples).
* Review verdict: **Pass**.
* Mechanical validation: **Pass**.
* Overall outcome: **Pass**.
* Stop reason: Target artifacts authored, verified, and validated; all acceptance criteria satisfied.
