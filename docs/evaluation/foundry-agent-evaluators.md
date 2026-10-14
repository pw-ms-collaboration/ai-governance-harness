# Foundry agent-response evaluator setup

This setup registers the existing response rubric, not the agent. It does not
run prompts, upload agent outputs, create evaluation runs, or change the UI.
Local deterministic enforcement checks remain independent and mandatory.

The source of truth is
[`agent-rubric.json`](../../src/ai_governance_harness/evaluation/agent-rubric.json).
Each of its eight criteria becomes one prompt-based binary evaluator. An allow
response uses only the four allow evaluators; a denial uses only the four deny
evaluators. Every applicable criterion must pass, with no weighted averages.

## Prepare locally

From the repository root:

```bash
.venv/bin/python -m ai_governance_harness.evaluation.register_agent_evaluators \
  --output .local/evaluations/agent-evaluator-definitions
```

This default makes no Azure requests and does not instantiate a credential.
It creates private, non-overwriting `definitions.json` and `registration.json`
artifacts. `prepared` means definitions exist locally, not in Foundry.
Use a new output directory for each invocation.

## Register once when ready

```bash
.venv/bin/python -m ai_governance_harness.evaluation.register_agent_evaluators \
  --output .local/evaluations/agent-evaluator-registration \
  --confirm-register
```

The endpoint comes from `AZURE_AI_PROJECT_ENDPOINT` in the environment or `.env`;
`--endpoint` overrides it. The shared Azure credential helper supplies Entra
authentication. Existing model access does not guarantee permission to register
evaluators. Confirm the project and write permission before invoking this command.

The command uses `AIProjectClient.evaluators.create_version` from the installed
Azure AI Projects 2.8+ SDK, then reads back each returned version. It does not
deploy a model or invoke one. HTTP retries are disabled to avoid accidentally
creating duplicate versions.
Evaluator requests include the service-required preview opt-in header
`Foundry-Features: Evaluations=V1Preview`.
The pass threshold is fixed to `1.0` in initialization parameters. The service
does not retain a threshold on a boolean metric or `additionalProperties` on
these schemas; the runner must enforce its evidence contract before submission.

`registration.json` retains each criterion's category, evaluator name, version,
asset ID, verification status, and data mapping. If a request fails, the command
exits unsuccessfully and preserves registrations returned before the failure.
A timed-out create request might have committed on the service without returning
an identity. Check Foundry before retrying. Every confirmed invocation creates
new versions; there is no automatic version lookup, reuse, or rollback. Reuse the
returned versions for evaluation runs, and rerun setup only for intentional
definition changes.

## Contract for the agent-runner integration

Each evaluator takes four bounded string fields:

| Field | Source |
| --- | --- |
| `prompt` | Reviewed synthetic scenario prompt |
| `expected_behavior` | Reviewed scenario expectation |
| `reference_facts` | JSON-serialized independently approved balance, phase, and allocation facts; `"{}"` for a denial |
| `response` | Actual public agent answer or public policy-denial message |

Do not submit full profiles, secrets, production data, trace content, or local
enforcement verdicts as response evidence. The runner must validate and sanitize
evidence before submission. Schema bounds do not replace privacy validation.

Build Foundry testing criteria from the **verified registered** entries, filtered
by scenario category:

```python
criterion = {
    "type": "azure_ai_evaluator",
    "name": entry["criterion_id"],
    "evaluator_name": entry["name"],
    "evaluator_version": entry["version"],
    "data_mapping": entry["data_mapping"],
    "initialization_parameters": {
        "deployment_name": judge_deployment,
        "threshold": 1.0,
    },
}
```

The judge deployment is supplied when creating the evaluation, not when
registering definitions. The evaluator's output metric is `result`; the prompt
requires `{"result": true_or_false, "reason": "brief explanation with evidence"}`.
Foundry service errors, skipped criteria, missing results, and malformed outputs
are not successful judgments. Overall application acceptance requires successful
local enforcement checks plus all four applicable completed passing criteria.
Do not apply all eight evaluators indiscriminately to a mixed allow/deny dataset.

This setup is separate from managed agent collection, submission, result
retrieval, and UI integration. Local tests cover request serialization and failure
handling; live registration and judge behavior require separately authorized
Azure verification.

Reference: [Foundry custom evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/custom-evaluators).
