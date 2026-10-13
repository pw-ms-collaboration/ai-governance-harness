# Dependency Vulnerability Exception

This directory contains the reviewed, temporary exception for three
`cryptography 48.0.1` advisories inherited through Agent Governance Toolkit
Core 4.1.0.

The Toolkit requires `cryptography>=46.0.7,<49.0`, while fully remediating the
current advisories requires `cryptography>=50.0.0`. The repository therefore
keeps the supported Toolkit dependency contract instead of forcing an
unsupported resolver override.

## Safety Conditions

The exception is valid only when all these conditions hold:

* Agent Governance Toolkit Core is exactly 4.1.0.
* `cryptography` is exactly 48.0.1.
* The exception has not passed its 13 November 2026 expiry date.
* Application and relevant dependency Python sources do not reference the
  affected PKCS#7 decrypt or X.509 verifier APIs.
* The OpenVEX document contains a matching `not_affected` statement with
  `vulnerable_code_not_in_execute_path` justification for every ignored
  advisory.

The `ai-governance-audit` command checks every condition before invoking
`pip-audit`. It ignores only the three identifiers listed in
[`audit-policy.yaml`](./audit-policy.yaml). Any other vulnerability, version
change, newly reachable symbol, missing VEX statement, malformed policy, or
expired exception fails the command.

## Team Workflow

After installing all development dependencies, run:

```sh
ai-governance-audit
```

Do not replace this command with an unrestricted `pip-audit --ignore-vuln`
invocation. Update the policy and OpenVEX document only after a new
reachability review.

When a compatible Toolkit release supports `cryptography>=50`, remove the
exception, upgrade the packages, restore an unqualified `pip-audit` command,
and issue a new OpenVEX revision with `fixed` statements.

The OpenVEX statements are AI-drafted assessment records. A human reviewer who
merges the change remains the accountable author of record.
