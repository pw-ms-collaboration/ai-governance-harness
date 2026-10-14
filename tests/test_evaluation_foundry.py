"""Real SDK serialization and fake-service managed acceptance boundaries."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx2
import pytest
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import EvaluatorVersion
from azure.core.credentials import AccessToken
from azure.core.exceptions import AzureError
from openai import APIConnectionError, OpenAI
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.evals.runs.output_item_list_response import (
    OutputItemListResponse,
    Result,
)

from ai_governance_harness.evaluation import foundry
from ai_governance_harness.evaluation.artifacts import (
    create_manifest,
    portable_code,
    regression_controls,
    write_jsonl,
)
from ai_governance_harness.evaluation.evaluator import Evidence
from test_evaluation import baseline_row

ENDPOINT = "https://example.services.ai.azure.com/api/projects/example"


class Credential:
    def get_token(self, *scopes: str, **kwargs: object) -> AccessToken:
        return AccessToken("unused-test-token", 0)

    def __enter__(self) -> Credential:
        return self

    def __exit__(self, *args: object) -> None:
        pass


class Service:
    def __init__(self, failure: str | None = None) -> None:
        self.failure = failure
        self.registration: EvaluatorVersion | None = None
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.rows: dict[str, list[dict[str, object]]] = {}
        self.evaluators = SimpleNamespace(
            create_version=self.register, get_version=self.get_version
        )
        self.deployments = SimpleNamespace(get=self.get_deployment)
        self.evals = SimpleNamespace(
            create=self.create_eval,
            runs=SimpleNamespace(
                create=self.create_run,
                retrieve=self.retrieve,
                output_items=SimpleNamespace(list=self.list_items),
            ),
        )

    def __enter__(self) -> Service:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def register(self, **kwargs: Any) -> EvaluatorVersion:
        self.calls.append(("register", kwargs))
        if self.failure == "authentication":
            raise AzureError("secret-sentinel")
        self.registration = EvaluatorVersion(
            **kwargs["evaluator_version"].as_dict(),
            name=kwargs["name"],
            version="7",
            id="evaluator-asset-id",
        )
        return self.registration

    def get_deployment(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(("get_deployment", kwargs))
        if self.failure == "deployment-access":
            raise AzureError("secret-sentinel")
        return SimpleNamespace(
            name="wrong-deployment"
            if self.failure == "wrong-deployment"
            else kwargs["name"]
        )

    def get_version(self, **kwargs: Any) -> EvaluatorVersion:
        self.calls.append(("get_version", kwargs))
        assert self.registration is not None
        result = EvaluatorVersion(self.registration.as_dict())
        if self.failure == "wrong-version":
            result.version = "latest-not-pinned"
        elif self.failure == "wrong-definition":
            result.definition.code_text = "different code"
        return result

    def get_openai_client(self, **kwargs: Any) -> Service:
        self.calls.append(("get_openai_client", kwargs))
        return self

    def create_eval(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(("create_eval", kwargs))
        if self.failure == "submission":
            raise APIConnectionError(
                message="secret-sentinel", request=httpx2.Request("POST", ENDPOINT)
            )
        return SimpleNamespace(
            id=None if self.failure == "invalid-eval-id" else "eval-test"
        )

    def create_run(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(("create_run", kwargs))
        kind = "baseline" if kwargs["name"].endswith("-baseline") else "controls"
        run_id = f"run-{kind}"
        self.rows[run_id] = [
            entry["item"] for entry in kwargs["data_source"]["source"]["content"]
        ]
        return SimpleNamespace(
            id=None if self.failure == "invalid-run-id" else run_id, status="queued"
        )

    def retrieve(self, run_id: str, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(("retrieve", kwargs))
        return SimpleNamespace(
            id=run_id,
            status=self.failure
            if self.failure in {"failed", "canceled", "cancelled", "queued"}
            else "completed",
            report_url=(
                "https://ai.azure.com/report?sig=secret-sentinel"
                if self.failure == "unsafe-report-url"
                else f"https://ai.azure.com/report/{run_id}"
            ),
        )

    def list_items(self, run_id: str, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(("list_items", kwargs))
        if self.failure == "invalid-page":
            return SimpleNamespace(data=[], has_next_page=lambda: True)
        if self.failure == "invalid-page-data":
            return SimpleNamespace(data=None, has_next_page=lambda: False)
        outputs = []
        assert self.registration is not None
        for index, row in enumerate(self.rows[run_id]):
            error = None
            score = 1.0 if run_id == "run-baseline" else 0.0
            if run_id == "run-controls":
                error = CONTROL_ERRORS.get(row["row_id"])
            result = {
                "name": foundry.METRIC,
                "score": score,
                "passed": score == 1.0,
                "status": "error" if error else "completed",
            }
            if error:
                result["error"] = {
                    "code": "CodeEvaluatorException",
                    "message": (
                        "EvidenceValidationError: invalid_control_identity"
                        if self.failure == "wrong-control-category"
                        else f"EvidenceValidationError: {error}"
                    ),
                }
            output_status = "pass" if score else "fail"
            if index == 0 and run_id == "run-baseline":
                if self.failure == "wrong-metric":
                    result["name"] = "wrong-metric"
                elif self.failure == "bad-score":
                    result["score"] = 2.0
                elif self.failure == "skipped":
                    result["status"] = output_status = "skipped"
                elif self.failure == "baseline-error":
                    result.update(score=0.0, passed=False, status="error")
                    result["error"] = {"message": "TimeoutError: unrelated"}
                    output_status = "fail"
            if self.failure == "unrelated-control-error" and run_id == "run-controls":
                result.update(score=0.0, passed=False, status="error")
                result["error"] = {"message": "TimeoutError: unrelated"}
            output = OutputItemListResponse.model_construct(
                id=f"output-{run_id}-{index}",
                created_at=0,
                datasource_item=deepcopy(row),
                datasource_item_id=index,
                eval_id="eval-test",
                run_id=run_id,
                object="eval.run.output_item",
                sample=None,
                status=output_status,
                results=[Result.model_validate(result)],
            )
            if self.failure == "changed-row" and index == 0:
                output.datasource_item["evidence"]["backend_execution_count"] = 999
            if self.failure == "missing-output-id":
                del output.__dict__["id"]
            elif self.failure == "missing-output-results":
                del output.__dict__["results"]
            elif self.failure == "invalid-datasource-id":
                output.__dict__["datasource_item_id"] = []
            outputs.append(output)
        if self.failure == "missing-row" and run_id == "run-baseline":
            outputs.pop()
        if self.failure == "duplicate-row" and run_id == "run-baseline":
            duplicate = outputs[0].model_copy(deep=True)
            duplicate.id = "duplicate-output"
            outputs.insert(1, duplicate)
        after = kwargs.get("after")
        offset = (
            next(index for index, output in enumerate(outputs) if output.id == after)
            + 1
            if after
            else 0
        )
        page = outputs[offset : offset + 1]
        return SimpleNamespace(
            data=page, has_next_page=lambda: offset + len(page) < len(outputs)
        )


CONTROL_ERRORS = {
    "control-missing-field": "invalid_evidence_schema",
    "control-boolean-count": "invalid_evidence_schema",
    "control-unknown-schema": "invalid_evidence_schema",
    "control-unknown-case": "unsupported_case",
    "control-unhealthy-operation-probe": "incomplete_or_unhealthy_collection",
    "control-incomplete-events": "incomplete_or_unhealthy_collection",
    "control-failed-collection": "incomplete_or_unhealthy_collection",
}


@pytest.fixture()
def bundle(tmp_path: Path) -> Path:
    directory = tmp_path / "local"
    directory.mkdir(mode=0o700)
    manifest = create_manifest(directory)
    baselines = [
        Evidence.model_validate(baseline_row(manifest, variant))
        for variant in ("allow", "deny")
    ]
    write_jsonl(
        directory / "baseline.jsonl", [row.model_dump(mode="json") for row in baselines]
    )
    write_jsonl(
        directory / "controls.jsonl",
        [control.item for control in regression_controls(baselines)],
    )
    (directory / "grader.py").write_text(portable_code(manifest))
    return directory


def install_service(monkeypatch: pytest.MonkeyPatch, service: Service) -> None:
    monkeypatch.setattr(foundry, "get_azure_credential", Credential)

    def project(**kwargs: Any) -> Service:
        assert kwargs["endpoint"] == ENDPOINT
        assert "connection_string" not in kwargs
        assert kwargs["retry_total"] == 0
        return service

    monkeypatch.setattr(foundry, "AIProjectClient", project)


def test_given_managed_contract_when_serialized_then_real_sdk_wire_is_pinned() -> None:
    definition = foundry.evaluator_definition(
        "def grade(sample, item): return 1.0"
    ).as_dict()
    assert definition["definition"]["type"] == "code"
    assert definition["definition"]["metrics"][foundry.METRIC]["max_value"] == 1.0
    criterion = foundry.testing_criterion("evaluator", "7", "deployment")
    assert criterion["evaluator_version"] == "7"
    assert criterion["initialization_parameters"]["pass_threshold"] == 1.0
    requests = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(200, json={"id": "eval-wire"})

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as http:
        with OpenAI(api_key="not-a-secret", http_client=http) as client:
            client.evals.create(
                data_source_config=DataSourceConfigCustom(
                    type="custom", item_schema=foundry.INPUT_SCHEMA
                ),
                testing_criteria=[],
                extra_body={"testing_criteria": [criterion]},
            )
    assert requests[0]["testing_criteria"] == [criterion]
    with AIProjectClient(endpoint=ENDPOINT, credential=Credential()) as project:
        assert hasattr(project.evaluators, "create_version")
        assert hasattr(project.evaluators, "get_version")


def test_given_all_pages_when_managed_runs_then_every_identity_is_checked(
    bundle: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = Service()
    install_service(monkeypatch, service)
    monkeypatch.setenv("AZURE_AI_PROJECT_CONNECTION_STRING", "secret-sentinel")
    results = foundry.run_managed(
        bundle,
        tmp_path / "managed",
        endpoint=ENDPOINT,
        deployment="deployment",
        confirm_submit=True,
    )
    assert results["status"] == "passed", results
    assert results["evaluator"]["version"] == "7"
    assert [len(run["items"]) for run in results["runs"]] == [2, 18]
    assert sum(name == "list_items" for name, _ in service.calls) == 20
    for name, kwargs in service.calls:
        if name in {"create_eval", "create_run", "retrieve", "list_items"}:
            assert 0 < kwargs["timeout"] <= 30
    text = (tmp_path / "managed/managed-results.json").read_text()
    assert "secret-sentinel" not in text
    assert "full_name" not in text


@pytest.mark.parametrize(
    "failure",
    [
        "authentication",
        "deployment-access",
        "wrong-deployment",
        "submission",
        "invalid-eval-id",
        "invalid-run-id",
        "wrong-version",
        "wrong-definition",
        "failed",
        "canceled",
        "cancelled",
        "missing-row",
        "duplicate-row",
        "wrong-metric",
        "bad-score",
        "skipped",
        "baseline-error",
        "unrelated-control-error",
        "wrong-control-category",
        "changed-row",
        "unsafe-report-url",
        "invalid-page",
        "invalid-page-data",
        "missing-output-id",
        "missing-output-results",
        "invalid-datasource-id",
    ],
)
def test_given_managed_failure_when_run_then_never_reports_success(
    bundle: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    service = Service(failure)
    install_service(monkeypatch, service)
    report = foundry.run_managed(
        bundle,
        tmp_path / "managed",
        endpoint=ENDPOINT,
        deployment="deployment",
        confirm_submit=True,
    )
    assert report["status"] in {"failed", "error"}, report
    assert report["error"] is not None
    text = (tmp_path / "managed/managed-results.json").read_text()
    assert "secret-sentinel" not in text


@pytest.mark.parametrize(
    "endpoint,deployment,confirmed,category",
    [
        (None, "deployment", True, "missing_endpoint"),
        (ENDPOINT, None, True, "missing_deployment"),
        ("http://example.invalid", "deployment", True, "invalid_project_endpoint"),
        (ENDPOINT, "deployment", False, "submission_confirmation_required"),
    ],
)
def test_given_missing_prerequisite_when_run_then_no_authentication_or_upload(
    bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str | None,
    deployment: str | None,
    confirmed: bool,
    category: str,
) -> None:
    def forbidden() -> None:
        raise AssertionError("Must not authenticate a blocked run.")

    monkeypatch.setattr(foundry, "get_azure_credential", forbidden)
    report = foundry.run_managed(
        bundle,
        tmp_path / "managed",
        endpoint=endpoint,
        deployment=deployment,
        confirm_submit=confirmed,
    )
    assert report["status"] == "blocked"
    assert report["error"]["category"] == category


@pytest.mark.parametrize("artifact", ["baseline.jsonl", "controls.jsonl", "grader.py"])
def test_given_poisoned_artifact_when_run_then_no_upload(
    bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
) -> None:
    service = Service()
    install_service(monkeypatch, service)
    (bundle / artifact).write_text('{"full_profile":"secret-sentinel"}\n')
    report = foundry.run_managed(
        bundle,
        tmp_path / "managed",
        endpoint=ENDPOINT,
        deployment="deployment",
        confirm_submit=True,
    )
    assert report["status"] == "error"
    assert not service.calls
    assert (
        "secret-sentinel" not in (tmp_path / "managed/managed-results.json").read_text()
    )


def test_given_deadline_during_pages_when_run_then_partial_ids_are_retained(
    bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = Service()
    install_service(monkeypatch, service)
    ticks = iter(index * 0.1 for index in range(100))
    monkeypatch.setattr(foundry, "monotonic", lambda: next(ticks))
    report = foundry.run_managed(
        bundle,
        tmp_path / "managed",
        endpoint=ENDPOINT,
        deployment="deployment",
        confirm_submit=True,
        timeout_seconds=1.1,
    )
    assert report["status"] == "error"
    assert report["error"]["category"] == "managed_deadline_exceeded"
    assert report["eval_id"] == "eval-test"


def test_given_queued_run_when_deadline_expires_then_run_identity_is_retained(
    bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = Service("queued")
    install_service(monkeypatch, service)
    ticks = iter(index * 0.1 for index in range(100))
    monkeypatch.setattr(foundry, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(foundry, "sleep", lambda seconds: None)
    report = foundry.run_managed(
        bundle,
        tmp_path / "managed",
        endpoint=ENDPOINT,
        deployment="deployment",
        confirm_submit=True,
        timeout_seconds=1.1,
    )
    assert report["status"] == "error"
    assert report["error"]["category"] == "managed_deadline_exceeded"
    assert report["runs"][0]["run_id"] == "run-baseline"
    assert report["runs"][0]["status"] == "queued"
    assert not any(name == "list_items" for name, _ in service.calls)
