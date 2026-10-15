"""Browser-to-managed-runner orchestration without live inference or submission."""

import sys
import time

import pytest
from starlette.testclient import TestClient

from ai_governance_harness.chat.app import build_chat_app
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.chat.managed_evaluations import (
    ManagedEvaluationJob,
    ManagedEvaluationJobs,
    RESULT_ERROR,
)
from ai_governance_harness.evaluation.agent_managed_contracts import (
    ManagedAgentResults,
    ManagedOutcome,
    ManagedResponse,
    independent_manifest,
    load_cases,
    load_pin,
)
from ai_governance_harness.evaluation.agent_runner import (
    AgentConfiguration,
    CollectionOutcome,
)
from ai_governance_harness.evaluation.artifacts import write_json
from test_agent_evaluation_managed_contracts import ENDPOINT, registry_bundle
from ai_governance_harness.identity.constants import INTERACTIVE_ID

pytestmark = pytest.mark.usefixtures("mock_chat_environment")


def settings():
    return ChatSettings(
        model_deployment="target",
        sidecar_url="http://127.0.0.1:8002",
        interactive_agent_id=INTERACTIVE_ID,
    )


API = "/api/foundry/evaluation-jobs"
CONFIRM = {"confirm_inference": True, "confirm_submit": True}


@pytest.fixture
def configured(tmp_path, monkeypatch):
    registry = registry_bundle(tmp_path / "registry")
    monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", ENDPOINT)
    monkeypatch.setenv("AZURE_AI_EVALUATOR_REGISTRY", str(registry))
    monkeypatch.setenv("AZURE_AI_EVAL_JUDGE_DEPLOYMENT_NAME", "judge")
    return build_chat_app(
        settings(),
        service=object(),
        evaluation_directory=tmp_path / "evaluations",
    )


def wait(client, run_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"{API}/{run_id}")
        assert response.status_code == 200
        if response.json()["status"] != "running":
            return response.json()
        time.sleep(0.05)
    pytest.fail("Browser managed job did not finish")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"confirm_inference": True},
        {
            "confirm_inference": 1,
            "confirm_submit": True,
        },
        {"confirm_inference": True, "confirm_submit": False},
    ],
)
def test_both_explicit_confirmations_are_required(configured, monkeypatch, payload):
    monkeypatch.setattr(
        ManagedEvaluationJobs, "start", lambda _: pytest.fail("Must not start")
    )
    with TestClient(configured) as client:
        assert client.post(API, json=payload).status_code == 400
        assert client.get(API).json() is None


def test_command_reuses_existing_runner_and_separate_deployments(configured):
    with TestClient(configured) as client:
        jobs = client.app.state.managed_evaluation_jobs
        command = jobs._command(
            "20261015T000000Z-abcdefabcdef", jobs.directory, "judge", ENDPOINT
        )
        assert command[:4] == [
            sys.executable,
            "-m",
            "ai_governance_harness.evaluation",
            "agent-managed",
        ]
        assert command[command.index("--target-deployment") + 1] == "target"
        assert command[command.index("--judge-deployment") + 1] == "judge"
        assert "--confirm-inference" in command and "--confirm-submit" in command
        assert "--dataset" not in command
        assert command[command.index("--output") + 1].endswith(
            "/agent/20261015T000000Z-abcdefabcdef"
        )


def test_one_job_at_a_time_and_shutdown_retains_interruption(configured, monkeypatch):
    monkeypatch.setattr(
        ManagedEvaluationJobs,
        "_command",
        lambda *_: [
            sys.executable,
            "-c",
            "import time; time.sleep(60)",
        ],
    )
    with TestClient(configured) as client:
        first = client.post(API, json=CONFIRM)
        assert first.status_code == 202
        run_id = first.json()["run_id"]
        duplicate = client.post(API, json=CONFIRM)
        assert duplicate.status_code == 409
        assert duplicate.json()["run_id"] == run_id
        assert client.get("/health/live").status_code == 200
    with TestClient(configured) as client:
        restored = client.get(API).json()
        assert restored["run_id"] == run_id
        assert restored["status"] == "cancelled"
        assert "shutdown" in restored["error"]


def test_completed_job_is_private_and_restored(configured, monkeypatch):
    monkeypatch.setattr(
        ManagedEvaluationJobs,
        "_command",
        lambda *_: [
            sys.executable,
            "-c",
            "raise SystemExit(1)",
        ],
    )
    monkeypatch.setattr(
        ManagedEvaluationJobs,
        "_result",
        lambda _, run_id: ManagedEvaluationJob(
            run_id=run_id,
            status="failed",
            eval_id="eval-test",
            foundry_run_id="run-test",
        ),
    )
    with TestClient(configured) as client:
        run_id = client.post(API, json=CONFIRM).json()["run_id"]
        completed = wait(client, run_id)
        assert completed["status"] == "failed"
        assert completed["eval_id"] == "eval-test"
        path = (
            client.app.state.managed_evaluation_jobs.directory
            / f"{run_id}.browser-job.json"
        )
        assert path.stat().st_mode & 0o777 == 0o600
        assert "response" not in path.read_text()
    with TestClient(configured) as client:
        assert client.get(API).json() == completed


def test_retained_legacy_report_restores_cloud_ids_without_resubmitting(
    configured, monkeypatch
):
    monkeypatch.setattr(
        ManagedEvaluationJobs, "start", lambda _: pytest.fail("Must not resubmit")
    )
    run_id = "20261014T235232Z-f633759f499b"
    case = load_cases()[0]
    with TestClient(configured) as client:
        jobs = client.app.state.managed_evaluation_jobs
        jobs.directory.mkdir(parents=True)
        directory = jobs.directory / run_id
        directory.mkdir()
        result = ManagedAgentResults(
            run_id="retained-run",
            execution_kind="live",
            status="error",
            error="missing_or_duplicate_managed_metric",
            configuration=AgentConfiguration(
                target_deployment="target",
                judge_deployment="judge",
                endpoint=ENDPOINT,
                timeout_seconds=60,
            ),
            manifest=independent_manifest([case]),
            evaluator=load_pin(jobs.directory.parent.parent / "registry", ENDPOINT),
            eval_id="eval-retained",
            foundry_run_id="run-retained",
            foundry_status="completed",
            rows=[
                ManagedOutcome(
                    case=case,
                    collection=CollectionOutcome(case_id=case.id),
                    response=ManagedResponse(
                        status="error", error="missing_or_duplicate_managed_metric"
                    ),
                )
            ],
        )
        write_json(directory / "managed-agent-results.json", result)
        jobs._save(ManagedEvaluationJob(run_id=run_id))
        jobs._save(
            ManagedEvaluationJob(run_id=run_id, status="error", error=RESULT_ERROR)
        )
        original = (jobs.directory / f"{run_id}.browser-result.json").read_bytes()
        restored = client.get(API).json()
        assert restored["status"] == "error"
        assert restored["eval_id"] == "eval-retained"
        assert restored["foundry_run_id"] == "run-retained"
        assert "Foundry completed this run" in restored["error"]
        assert (
            jobs.directory / f"{run_id}.browser-result.json"
        ).read_bytes() == original
        jobs.job = ManagedEvaluationJob(
            run_id=run_id, status="error", error=RESULT_ERROR
        )
        assert client.get(API).json() == restored


@pytest.mark.parametrize("exit_code", [0, 2])
def test_missing_report_or_runner_error_is_explicit(configured, monkeypatch, exit_code):
    monkeypatch.setattr(
        ManagedEvaluationJobs,
        "_command",
        lambda *_: [
            sys.executable,
            "-c",
            f"raise SystemExit({exit_code})",
        ],
    )
    with TestClient(configured) as client:
        run_id = client.post(API, json=CONFIRM).json()["run_id"]
        job = wait(client, run_id)
        assert job["status"] == "error"
        assert "Check retained artifacts and Foundry" in job["error"]


def test_configuration_failure_never_starts_inference(configured, monkeypatch):
    monkeypatch.delenv("AZURE_AI_EVALUATOR_REGISTRY")
    monkeypatch.setattr(
        ManagedEvaluationJobs, "_command", lambda *_: pytest.fail("Must not start")
    )
    with TestClient(configured) as client:
        assert client.post(API, json=CONFIRM).status_code == 503
        assert client.get(API).json() is None


def test_invalid_ids_origin_and_remote_binding_are_rejected(configured):
    with TestClient(configured) as client:
        assert client.get(f"{API}/not-a-run").status_code == 404
        assert (
            client.post(
                API, json=CONFIRM, headers={"Origin": "https://untrusted.example"}
            ).status_code
            == 403
        )
        assert client.post(API, content="not JSON").status_code == 415
    remote = build_chat_app(
        settings().model_copy(update={"host": "0.0.0.0"}), service=object()
    )
    with TestClient(remote) as client:
        assert client.post(API, json=CONFIRM).status_code == 403
