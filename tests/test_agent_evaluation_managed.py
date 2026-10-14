"""Real SDK serialization and explicitly simulated managed scoring boundaries."""

from __future__ import annotations

import json
from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

import httpx2
import pytest
from azure.ai.projects.models import EvaluatorVersion
from openai import OpenAI

from ai_governance_harness.evaluation import agent_managed, agent_runner
from ai_governance_harness.evaluation.agent_contracts import (
    AgentEvaluationError,
    digest,
)
from ai_governance_harness.evaluation.agent_managed_contracts import (
    METRIC,
    ManagedAgentResults,
    independent_manifest,
    load_cases,
)
from ai_governance_harness.evaluation.behavior_evaluator import evaluator_definition
from test_agent_evaluation_collection import WORKER_COMMAND
from test_agent_evaluation_contracts import simulated_evidence
from test_agent_evaluation_managed_contracts import ENDPOINT, registry_bundle


def collected(manifest, case, directory, **kwargs):
    denied = case.category in agent_managed.ADVICE_CATEGORIES
    _, _, evidence = simulated_evidence("deny" if denied else "allow")
    evidence = evidence.model_copy(deep=True)
    evidence.case_id = case.id
    evidence.manifest_digest = digest(manifest)
    evidence.request_id = case.id
    for capture in evidence.captures.values():
        capture.versions = manifest.versions
        capture.request_id = case.id
        for event in capture.events:
            event.request_id = case.id
    if not denied and case.id == "ben-001":
        chat, mcp = evidence.captures["chat"], evidence.captures["mcp"]
        chat.events = [
            event
            for event in chat.events
            if event.lifecycle_point not in {"pre_tool", "post_tool"}
        ]
        for index, event in enumerate(chat.events, 1):
            event.sequence = index
        chat.tool_calls = []
        mcp.events = []
        mcp.backend_executions = 0
        mcp.operation_facts = []
        evidence.tools_used = []
    for capture in evidence.captures.values():
        capture.target_deployments = [
            kwargs["target_deployment"]
        ] * capture.target_requests
    return evidence


class Service:
    def __init__(self, failure=None, *, boolean_labels=False):
        self.failure = failure
        self.boolean_labels = boolean_labels
        self.calls = []
        self.records = []
        self.pin = EvaluatorVersion(
            **evaluator_definition().as_dict(),
            version="1",
            id="azureai://accounts/example/projects/example/evaluators/governance-behavior-match/versions/1",
        )
        self.evaluators = SimpleNamespace(get_version=self.get_version)

    def get_version(self, **kwargs):
        self.calls.append(("get_version", kwargs))
        assert kwargs["version"] == "1"
        assert kwargs["headers"] == {"Foundry-Features": "Evaluations=V1Preview"}
        returned = EvaluatorVersion(self.pin.as_dict())
        if self.failure == "wrong-pin":
            returned.definition.prompt_text = "Changed protocol."
        return returned

    def get_openai_client(self, **kwargs):
        assert kwargs["max_retries"] == 0
        return OpenAI(
            api_key="simulation-only",
            base_url="https://simulation.invalid/",
            http_client=httpx2.Client(transport=httpx2.MockTransport(self.http)),
            **kwargs,
        )

    def http(self, request):
        payload = json.loads(request.content) if request.content else {}
        path = request.url.path
        self.calls.append((request.method + " " + path, deepcopy(payload)))
        assert request.headers["Foundry-Features"] == "Evaluations=V1Preview"
        if request.method == "POST" and path == "/evals":
            criterion = payload["testing_criteria"][0]
            assert len(payload["testing_criteria"]) == 1
            assert criterion["evaluator_name"] == "governance-behavior-match"
            assert criterion["evaluator_version"] == "1"
            assert criterion["initialization_parameters"] == {
                "deployment_name": "judge",
                "threshold": 1.0,
            }
            return httpx2.Response(200, json={"id": "eval-test"})
        if request.method == "POST":
            assert path == "/evals/eval-test/runs"
            assert payload["data_source"]["type"] == "jsonl"
            assert "model" not in payload["data_source"]
            self.records = [
                entry["item"] for entry in payload["data_source"]["source"]["content"]
            ]
            self.run_name = payload["name"]
            if self.failure == "submit":
                raise httpx2.ConnectError("password=secret-sentinel")
            if self.failure == "cancel":
                raise KeyboardInterrupt
            return httpx2.Response(200, json={"id": "run-test"})
        if path == "/evals/eval-test/runs/run-test":
            return httpx2.Response(
                200,
                json={
                    "id": "run-test",
                    "eval_id": "eval-test",
                    "name": self.run_name,
                    "status": "failed" if self.failure == "run-failed" else "completed",
                },
            )
        assert path == "/evals/eval-test/runs/run-test/output_items"
        outputs = []
        for index, item in enumerate(self.records):
            score = (
                0
                if (self.failure == "response-fail" and index == 0)
                or (self.boolean_labels and index != 1)
                else 1
            )
            result = {
                "name": METRIC,
                "score": score,
                "passed": bool(score),
                "reason": "Meets the dataset's requirements.",
            }
            if self.boolean_labels:
                result.update(
                    type="azure_ai_evaluator",
                    metric=METRIC,
                    score=None,
                    label="pass" if score else "fail",
                    threshold=None,
                    status="completed",
                )
            if index == 0:
                if self.failure == "service-error":
                    result["error"] = {
                        "code": "JudgeTimeout",
                        "message": "password=secret-sentinel",
                    }
                elif self.failure == "string-score":
                    result["score"] = "1"
                elif self.failure == "bad-score":
                    result["score"] = 0.5
                elif self.failure == "string-passed":
                    result["passed"] = "true"
                elif self.failure == "missing-reason":
                    result.pop("reason")
                elif self.failure == "unsafe-reason":
                    result["reason"] = "password=secret-sentinel"
                elif self.failure == "wrong-metric":
                    result["name"] = "other"
                elif self.failure == "invalid-label":
                    result["label"] = "partial"
                elif self.failure == "missing-label":
                    result.pop("label")
                elif self.failure == "label-passed-mismatch":
                    result["passed"] = not bool(score)
                elif self.failure == "label-score-mismatch":
                    result.update(score=1, passed=True)
                elif self.failure == "wrong-wire-metric":
                    result["metric"] = "other"
                elif self.failure == "wrong-wire-type":
                    result["type"] = "string_check"
            outputs.append(
                {
                    "id": f"output-{index}",
                    "eval_id": "eval-test",
                    "run_id": "run-test",
                    "datasource_item_id": index,
                    "datasource_item": deepcopy(item),
                    "status": (
                        "completed"
                        if self.boolean_labels
                        else "pass"
                        if score
                        else "fail"
                    ),
                    "results": [result],
                }
            )
        if self.failure == "missing-row":
            outputs.pop()
        if self.failure == "duplicate-row":
            outputs.append(deepcopy(outputs[0]))
        if self.failure == "wrong-row":
            outputs[0]["datasource_item"]["response"] = "Altered."
        if self.failure == "wrong-run":
            outputs[0]["run_id"] = "wrong"
        if self.failure == "error-only":
            outputs[0].update(
                status="error", results=[], error={"code": "JudgeUnavailable"}
            )
        cursor = request.url.params.get("after")
        offset = next(
            (i + 1 for i, output in enumerate(outputs) if output["id"] == cursor), 0
        )
        page = outputs[offset : offset + 1]
        return httpx2.Response(
            200, json={"data": page, "has_more": offset + len(page) < len(outputs)}
        )


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("AZURE_AI_PROJECT_REGION", "australiaeast")
    registry = registry_bundle(tmp_path / "registry")
    dataset = tmp_path / "subset.jsonl"
    dataset.write_text(
        "\n".join(
            case.model_dump_json()
            for case in load_cases()
            if case.id in {"adv-001", "ben-001", "cus-001"}
        )
    )
    monkeypatch.setattr(
        agent_managed, "get_azure_credential", lambda: nullcontext(object())
    )
    monkeypatch.setattr(agent_managed, "collect_case", collected)

    def forbidden(*args, **kwargs):
        pytest.fail("Managed scoring must never invoke the local response judge.")

    monkeypatch.setattr(agent_runner, "judge_response", forbidden)
    return {
        "registry": registry,
        "dataset": dataset,
        "endpoint": ENDPOINT,
        "target_deployment": "target",
        "judge_deployment": "judge",
        "confirm_inference": True,
        "confirm_submit": True,
        "collection_worker_command": ["explicit-simulation"],
    }


def install_service(monkeypatch, service):
    monkeypatch.setattr(
        agent_managed, "AIProjectClient", lambda **kwargs: nullcontext(service)
    )


def test_real_sdk_submission_pagination_and_private_artifacts(
    setup, tmp_path, monkeypatch
):
    service = Service()
    install_service(monkeypatch, service)
    directory = tmp_path / "agent" / "managed"
    results = agent_managed.run_agent_managed(directory, **setup)
    assert results.status == "passed", results.model_dump_json()
    assert len(results.rows) == 3
    assert all(row.accepted and row.response.reason for row in results.rows)
    assert all(
        set(record) == {"id", "category", "prompt", "expected_behavior", "response"}
        for record in service.records
    )
    assert len([call for call in service.calls if "output_items" in call[0]]) == 3
    assert directory.stat().st_mode & 0o777 == 0o700
    for path in directory.iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
        assert "secret-sentinel" not in path.read_text()
    before = list(service.calls)
    with pytest.raises(FileExistsError):
        agent_managed.run_agent_managed(directory, **setup)
    assert service.calls == before


def test_real_sdk_completed_boolean_labels_preserve_binary_verdicts(
    setup, tmp_path, monkeypatch
):
    service = Service(boolean_labels=True)
    install_service(monkeypatch, service)
    directory = tmp_path / "agent" / "boolean-labels"
    results = agent_managed.run_agent_managed(directory, **setup)
    assert results.status == "failed"
    assert results.error == "managed_acceptance_failed"
    assert [row.response.status for row in results.rows] == ["completed"] * 3
    assert [row.response.score for row in results.rows] == [0.0, 1.0, 0.0]
    assert [row.response.label for row in results.rows] == ["fail", "pass", "fail"]
    assert [row.accepted for row in results.rows] == [False, True, False]
    saved = json.loads((directory / "managed-agent-results.json").read_text())
    assert [row["response"]["label"] for row in saved["rows"]] == [
        "fail",
        "pass",
        "fail",
    ]


@pytest.mark.parametrize(
    "failure",
    [
        "invalid-label",
        "missing-label",
        "label-passed-mismatch",
        "label-score-mismatch",
        "wrong-wire-metric",
        "wrong-wire-type",
        "string-passed",
        "bad-score",
        "missing-reason",
        "unsafe-reason",
        "service-error",
    ],
)
def test_real_sdk_malformed_boolean_labels_never_pass(
    setup, tmp_path, monkeypatch, failure
):
    service = Service(failure, boolean_labels=True)
    install_service(monkeypatch, service)
    results = agent_managed.run_agent_managed(tmp_path / "agent" / failure, **setup)
    assert results.status == "error" or results.rows[0].response.status == "error"
    assert not results.rows[0].accepted


@pytest.mark.parametrize(
    "failure",
    [
        "wrong-pin",
        "submit",
        "cancel",
        "run-failed",
        "service-error",
        "string-score",
        "bad-score",
        "string-passed",
        "missing-reason",
        "unsafe-reason",
        "wrong-metric",
        "missing-row",
        "duplicate-row",
        "wrong-row",
        "wrong-run",
        "response-fail",
        "error-only",
    ],
)
def test_errors_and_invalid_or_negative_results_never_pass(
    setup, tmp_path, monkeypatch, failure
):
    service = Service(failure)
    install_service(monkeypatch, service)
    directory = tmp_path / "agent" / failure
    results = agent_managed.run_agent_managed(directory, **setup)
    assert results.status != "passed"
    assert (
        "secret-sentinel" not in (directory / "managed-agent-results.json").read_text()
    )
    if failure == "service-error":
        response = results.rows[0].response
        assert response.error == "foundry_evaluator_error"
        assert response.provider_error_code == "JudgeTimeout"
    if failure == "submit":
        assert results.eval_id == "eval-test"
        assert results.foundry_run_id is None
        assert (
            len(
                [
                    name
                    for name, _ in service.calls
                    if name == "POST /evals/eval-test/runs"
                ]
            )
            == 1
        )
    if failure == "wrong-pin":
        assert not any(name.startswith("POST") for name, _ in service.calls)


def test_enforcement_failure_is_not_overridden_by_response_pass(
    setup, tmp_path, monkeypatch
):
    service = Service()
    install_service(monkeypatch, service)

    def violation(*args, **kwargs):
        evidence = collected(*args, **kwargs)
        evidence.captures["mcp"].backend_executions += 1
        return evidence

    monkeypatch.setattr(agent_managed, "collect_case", violation)
    results = agent_managed.run_agent_managed(tmp_path / "agent" / "violation", **setup)
    assert results.status == "failed"
    assert all(
        row.response.score == 1.0 and row.collection.policy_score == 0.0
        for row in results.rows
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "unhealthy",
        "incomplete",
        "missing-http",
        "wrong-deployment",
        "wrong-rule",
        "wrong-sequence",
        "blocked-backend",
        "blocked-tool",
        "extra-event",
    ],
)
def test_input_denial_requires_complete_exact_policy_and_zero_blocked_execution(
    tmp_path, mutation
):
    case = load_cases()[0]
    manifest = independent_manifest([case])
    evidence = collected(manifest, case, tmp_path, target_deployment="target")
    chat, mcp = evidence.captures["chat"], evidence.captures["mcp"]
    if mutation == "unhealthy":
        chat.healthy = False
    elif mutation == "incomplete":
        chat.complete = False
    elif mutation == "missing-http":
        chat.target_http_attempts = 0
        chat.target_http_event_sequences = []
    elif mutation == "wrong-deployment":
        chat.target_deployments = ["other"]
    elif mutation == "wrong-rule":
        chat.events[-1].matched_rule = "deny-external-security-recommendation"
    elif mutation == "wrong-sequence":
        chat.events[-1].sequence = 1
    elif mutation == "blocked-backend":
        mcp.backend_executions = 1
    elif mutation == "blocked-tool":
        from ai_governance_harness.evaluation.agent_contracts import ToolInvocation

        chat.tool_calls = [
            ToolInvocation(
                name="get_member_profile", member_id_matches=True, successful=True
            )
        ]
    elif mutation == "extra-event":
        chat.events.append(chat.events[-1].model_copy(update={"sequence": 4}))
    try:
        assert (
            agent_managed.behavior_policy_score(manifest, case, evidence, "target")
            == 0.0
        )
    except AgentEvaluationError as error:
        assert str(error) == "incomplete_or_unhealthy_agent_collection"


def test_unsafe_collected_content_is_never_exported_or_submitted(
    setup, tmp_path, monkeypatch
):
    def unsafe(*args, **kwargs):
        evidence = collected(*args, **kwargs)
        evidence.response = "password=secret-sentinel"
        return evidence

    def forbidden(*args, **kwargs):
        pytest.fail("No approved responses means no credentials or submission.")

    monkeypatch.setattr(agent_managed, "collect_case", unsafe)
    monkeypatch.setattr(agent_managed, "get_azure_credential", forbidden)
    directory = tmp_path / "agent" / "unsafe"
    results = agent_managed.run_agent_managed(directory, **setup)
    assert results.error == "no_approved_responses"
    assert all(
        row.record is None and row.response.status == "skipped" for row in results.rows
    )
    assert (directory / "responses.jsonl").read_text() == ""
    assert all(
        "secret-sentinel" not in path.read_text() for path in directory.iterdir()
    )


def test_retrieval_deadline_retains_ids_and_partial_results(
    setup, tmp_path, monkeypatch
):
    service = Service()
    install_service(monkeypatch, service)
    ticks = iter(index / 10 for index in range(100))
    monkeypatch.setattr(agent_managed, "monotonic", lambda: next(ticks))
    setup["managed_timeout_seconds"] = 0.75
    results = agent_managed.run_agent_managed(tmp_path / "agent" / "timeout", **setup)
    assert results.error == "managed_deadline_exceeded"
    assert results.eval_id == "eval-test"
    assert results.foundry_run_id == "run-test"
    assert any(row.response.status == "completed" for row in results.rows)
    assert any(row.response.status == "error" for row in results.rows)


@pytest.mark.parametrize(
    ("inference", "submission"), [(False, False), (True, False), (False, True)]
)
def test_consent_blocks_before_collection_credentials_or_artifacts(
    setup, tmp_path, monkeypatch, inference, submission
):
    def forbidden(*args, **kwargs):
        pytest.fail("Missing confirmation must block all execution and credentials.")

    monkeypatch.setattr(agent_managed, "collect_case", forbidden)
    monkeypatch.setattr(agent_managed, "get_azure_credential", forbidden)
    setup.update(confirm_inference=inference, confirm_submit=submission)
    directory = tmp_path / "agent" / "blocked"
    with pytest.raises(AgentEvaluationError, match="confirmation_required"):
        agent_managed.run_agent_managed(directory, **setup)
    assert not directory.parent.exists()


def test_failed_retrieval_resumes_without_reexecuting_or_resubmitting(
    setup, tmp_path, monkeypatch
):
    service = Service("missing-row")
    install_service(monkeypatch, service)
    directory = tmp_path / "agent" / "initial"
    initial = agent_managed.run_agent_managed(directory, **setup)
    assert initial.error == "missing_managed_outputs"
    service.failure = None
    before = len(service.calls)

    def forbidden(*args, **kwargs):
        pytest.fail("Retrieval-only cannot collect or submit.")

    monkeypatch.setattr(agent_managed, "collect_case", forbidden)
    results = agent_managed.retrieve_agent_managed(
        directory / "checkpoint-run-created.json",
        tmp_path / "agent" / "retrieved",
        endpoint=ENDPOINT,
    )
    assert results.status == "passed"
    assert all(not name.startswith("POST") for name, _ in service.calls[before:])
    checkpoint = ManagedAgentResults.model_validate_json(
        (directory / "checkpoint-run-created.json").read_text()
    )
    assert checkpoint.foundry_run_id == initial.foundry_run_id


def test_altered_checkpoint_is_rejected_before_credentials(
    setup, tmp_path, monkeypatch
):
    service = Service()
    install_service(monkeypatch, service)
    directory = tmp_path / "agent" / "initial"
    agent_managed.run_agent_managed(directory, **setup)
    checkpoint = directory / "checkpoint-run-created.json"
    value = json.loads(checkpoint.read_text())
    value["rows"][0]["record"]["response"] = "Edited."
    checkpoint.write_text(json.dumps(value))

    def forbidden(*args, **kwargs):
        pytest.fail("Altered checkpoint cannot access Azure.")

    monkeypatch.setattr(agent_managed, "get_azure_credential", forbidden)
    with pytest.raises(AgentEvaluationError, match="altered"):
        agent_managed.retrieve_agent_managed(
            checkpoint, tmp_path / "agent" / "blocked", endpoint=ENDPOINT
        )


def test_real_local_dataset_path_then_managed_sdk_submission(
    setup, tmp_path, monkeypatch
):
    service = Service()
    install_service(monkeypatch, service)
    from ai_governance_harness.evaluation.agent_collector import collect_case

    monkeypatch.setattr(agent_managed, "collect_case", collect_case)
    setup.update(
        target_deployment="default-behavior", collection_worker_command=WORKER_COMMAND
    )
    results = agent_managed.run_agent_managed(
        tmp_path / "agent" / "real-local", **setup
    )
    assert results.status == "passed", results.model_dump_json()
    assert all(row.collection.enforcement_accepted for row in results.rows)
    benign = next(row for row in results.rows if row.case.id == "ben-001")
    assert benign.collection.evidence.captures["mcp"].backend_executions == 0
    assert benign.collection.evidence.captures["chat"].target_http_attempts == 2
    advice = next(row for row in results.rows if row.case.id == "adv-001")
    assert advice.collection.evidence.http_status == 403
    assert advice.collection.evidence.captures["mcp"].backend_executions == 0
