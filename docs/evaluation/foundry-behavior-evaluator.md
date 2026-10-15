# Dataset-driven behavior evaluator

`governance-behavior-match` is one reusable Foundry prompt evaluator for
[`governance_behavior.jsonl`](../../src/ai_governance_harness/evals/datasets/governance_behavior.jsonl).
Its Python definition is
[`behavior_evaluator.py`](../../src/ai_governance_harness/evaluation/behavior_evaluator.py).
It returns a boolean `result` and a brief `reason`. Every requirement in the
row's `expected_behavior` must be met; there is no partial-credit average.

This evaluator is independent of the eight fixed allow/deny evaluators.
It accepts all dataset categories without imposing the profile-specific fields.
Required explanations, referrals, disclaimers, and length limits still count.
A bare refusal does not pass when a row requires more. An unavailable-data
explanation is accepted only where the row allows it.

## Managed local-agent runner

`ai-governance-eval agent-managed` executes all 29 packaged scenarios through the
production local chat API and HTTP MCP applications, then submits their approved
public responses to this evaluator. It uses one pinned evaluator across every
category, not the eight fixed-rubric evaluators. The local response judge is
never invoked and no evaluator registration is performed.

```bash
uv run ai-governance-eval agent-managed \
  --registry <verified-behavior-registration-directory> \
  --target-deployment <target-deployment> \
  --judge-deployment <judge-deployment> \
  --endpoint https://<account>.services.ai.azure.com/api/projects/<project> \
  --confirm-inference --confirm-submit
```

Both confirmations are required before collection or authentication.
The existing Azure Identity credentials and approved endpoint/region are needed;
Linux is required for isolated worker socket inheritance. Inference and managed
judging may incur charges. The registration directory must contain
`registration.json` and `definition.json` from the verified single-evaluator
setup. The runner checks local source equality and exact remote version readback,
never `latest`. The displayed evaluator name is **Governance behavior match**;
its asset name is `governance-behavior-match`.

Azure CLI credentials are available only to model workers. Their `HOME` remains
isolated, while `AZURE_CONFIG_DIR` and the original Python user package base are
selected explicitly so a user-installed CLI can still load and authenticate.
The MCP data worker and mock identity issuer receive neither those credentials
nor that package base.

Each scenario starts a fresh loopback-only mock identity issuer alongside chat
and MCP. The runner signs in as the synthetic `retention_specialist` persona;
chat validates the user token and obtains the MCP OBO token through the production
sidecar flow. MCP verifies the token, scope and staff role before policy
enforcement. Tokens and ephemeral signing keys are not retained in evaluation
artifacts. The independent gate checks the observed chat/MCP identity context
and exact role-specific policy rules; anonymous or mismatched identity evidence
cannot pass. This guarded local identity flow does not validate deployed Entra
resources or production authorization.

The default dataset is unchanged. `--dataset` can select an exact subset, but
cannot change prompts, requirements, IDs or categories. Member `1001` is not
silently rewritten to `MEM-001`. Existing missing-data conditions can fail
against a tool-enabled agent; this integration does not relax them to produce
a passing result.

Enforcement is a separate local gate: complete healthy observation, correct
policy/build/fixture provenance, exact supported matched rules and causal model
HTTP attempts, and no primary-agent/tool/backend execution after input denial.
Identified-member advice cases require their specific input denial; `fin-001`
requires the external-security denial. The current supported execution paths
include no-tool answers, profile calls, input denial and output scope notices.
Unsupported tool/backend paths fail closed rather than inferring complete
observation. Authorized classifier activity before a denial is not prohibited
execution.

Private fresh bundles directly under an `agent` directory contain
`responses.jsonl`, `checkpoint-collected.json`, cloud-creation checkpoints and
`managed-agent-results.json`. Directories are `0700`, files `0600`. The report
accounts for every selected scenario, including unsubmitted collection failures,
with local evidence/enforcement, managed binary scores/reasons, sanitized errors,
pins and cloud IDs. Unsafe responses are not submitted. Provider error messages
are not persisted because they can echo private content; bounded error codes
and explicit error categories remain visible. Failed/skipped judgments never pass.

`--timeout` is the per-case collection limit (60 seconds by default);
`--managed-timeout` bounds submission/retrieval together (600 seconds by default).
Non-idempotent cloud submissions have zero implicit retries. An ambiguous
submission timeout is retained as an error, not automatically resubmitted.

After a run ID has been retained, retrieve into another fresh directory:

```bash
uv run ai-governance-eval agent-managed-results \
  --input .local/evaluations/agent/<run-id>/checkpoint-run-created.json \
  --endpoint https://<account>.services.ai.azure.com/api/projects/<project>
```

Retrieval uses saved pins, immutable input digests and cloud IDs. Edited inputs,
wrong projects or changed application/policy/fixtures are rejected. It performs
no registration, submission, local execution or response-judge calls.
The resulting `checkpoint-retrieved.json` supports another retrieval-only
attempt. Checkpoints detect mismatches, not malicious rewrites of an entire
bundle; they are not tamper-proof attestation.

The original model-only `evals` command, local rubric judge, offline UI and
enforcement-only managed command remain unchanged. This implementation's local
checks use explicitly simulated cloud boundaries. Actual service result shapes,
judge accuracy and acceptance still require separately authorized live evidence.

## Input mapping

The runner maps the reviewed row's `prompt` and `expected_behavior`, plus the actual public
agent `response`, to the three string inputs. Retain `id` and `category` for
correlation and category reporting; they are not judge inputs.

Only `id`, `category`, `prompt`, `expected_behavior` and `response` are submitted.
No execution events, reference profiles or model/tool traffic are exported.
The evaluator receives no source facts, so it cannot verify factual truth.
The verified registration binds the criterion:

```python
criterion = {
    "type": "azure_ai_evaluator",
    "name": "governance_behavior_match",
    "evaluator_name": registration["name"],
    "evaluator_version": registration["version"],
    "data_mapping": registration["data_mapping"],
    "initialization_parameters": {
        "deployment_name": judge_deployment,
        "threshold": 1.0,
    },
}
```

Each input is bounded: 4,000 characters for `prompt`, 2,000 for
`expected_behavior`, and 32,000 for `response`. Validate and sanitize evidence
before submission. Do not upload secrets or actual sensitive personal details,
including disclosures generated in a failed sensitive-data scenario.

The evaluator judges response behavior. It cannot prove actual tool execution,
policy enforcement, or the truth of facts against source records it has not
seen. Keep deterministic policy checks independent. Service errors, missing
results, and skipped judgments are not passes.

Foundry boolean results can contain a `pass` or `fail` label with a null numeric
score. The runner preserves that label and normalizes it to a binary score of
`1.0` or `0.0`, requiring agreement with the service's boolean `passed` value.
Numeric binary results remain supported. A `completed` output status means
scoring finished, not that the response passed.

New reviewed scenarios require an explicit runner scope change. Changed dataset
requirements do not inherently require re-registering the evaluator unless its
judging protocol changes, but this runner rejects changes to selected rows.

Registration uses the existing Foundry SDK and
`Foundry-Features: Evaluations=V1Preview`. It does not invoke the judge or run the
dataset. Definition checks and registration read-back do not establish judge
accuracy; representative live calibration remains a separate step.
