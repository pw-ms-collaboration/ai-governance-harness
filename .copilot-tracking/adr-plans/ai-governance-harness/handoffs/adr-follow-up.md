# AI Governance Harness ADR Follow-up

## Compact Summary

Seven proposed MADR records capture the implemented governance architecture,
tradeoffs, recovery procedures, and extension paths. Repository maintainers are
the deciders. The immediate operational priority is the expiring Toolkit
dependency exception; the next architectural expansion is hosted identity or a
privileged sandbox provider.

## Azure DevOps Work Item Draft

**Title:** Replace the temporary Toolkit cryptography VEX exception

**Description:** Track a released Agent Governance Toolkit version that supports
the fixed `cryptography` line. Validate feed availability, adapter compatibility,
policy semantics, full tests, package build, SBOM, and ordinary unqualified
dependency audit. Remove the temporary policy and issue a new OpenVEX revision.

**Acceptance criteria:**

* A released Toolkit package supports `cryptography>=50`.
* `ai-governance-audit` is replaced by or delegates to an audit with no ignored advisories.
* OpenVEX statements transition to `fixed` with version evidence.
* ADR 0006 is superseded by an accepted replacement.

## GitHub Issue Draft

**Title:** Replace the temporary Toolkit cryptography VEX exception

**Body:** Monitor for a compatible released Toolkit version, then remove the
expiring exception using the recovery runbook in ADR 0006. Keep all other
dependency findings blocking throughout the change.

**Definition of done:**

* The supported dependency graph contains a fixed `cryptography` release.
* Full validation and local allowed/denied acceptance pass.
* VEX, README, CI, and ADR lineage are updated together.

## Future Extension Candidate

Before enabling code, shell, filesystem-write, unrestricted-network, hosted
identity, or cloud sandbox capabilities, create a related ADR covering provider
selection, credentials, isolation, network policy, cleanup, cost, health,
rollback, and local developer behavior.
