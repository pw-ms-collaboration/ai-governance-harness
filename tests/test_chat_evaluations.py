"""Browser API coverage for background jobs and retained evaluation output."""

from __future__ import annotations

import json
import time
from pathlib import Path

import anyio
import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from ai_governance_harness.chat.app import build_chat_app
from ai_governance_harness.chat.config import ChatSettings
from ai_governance_harness.evaluation.artifacts import write_json
from ai_governance_harness.identity.constants import INTERACTIVE_ID

pytestmark = pytest.mark.usefixtures("mock_chat_environment")

RUN_ID = "20261014T030232Z-b68217988ad8"
API = "/api/governance/evaluations"


def _app(directory: Path) -> Starlette:
    return build_chat_app(
        ChatSettings(
            model_deployment="test-model",
            sidecar_url="http://127.0.0.1:8002",
            interactive_agent_id=INTERACTIVE_ID,
        ),
        evaluation_directory=directory,
    )


def _results(*, passed: bool = True) -> dict[str, object]:
    return {
        "status": "passed" if passed else "failed",
        "manifest_digest": "a" * 64,
        "baselines": [
            {
                "row_id": f"baseline-{variant}",
                "request_id": variant,
                "stage": "shutdown",
                "error": None,
                "child_exit_code": 0,
                "score": 1.0 if passed else 0.0,
                "grader_error": None,
                "accepted": passed,
            }
            for variant in ("allow", "deny")
        ],
        "controls": [
            {
                "row_id": f"control-{index}",
                "control_id": f"control-{index}",
                "score": 0.0 if index < 11 else None,
                "error": None if index < 11 else "invalid_evidence_schema",
                "expected_error": None if index < 11 else "invalid_evidence_schema",
                "accepted": True,
            }
            for index in range(18)
        ]
        if passed
        else [],
    }


def _save(directory: Path, results: dict[str, object]) -> None:
    directory.mkdir(mode=0o700, parents=True)
    write_json(directory / "local-results.json", results)


def _wait(client: TestClient, run_id: str, *, timeout: float = 45) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"{API}/{run_id}")
        assert response.status_code == 200, response.text
        job = response.json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    pytest.fail(f"Evaluation {run_id} did not complete within {timeout} seconds.")


def test_real_local_job_runs_and_restores_saved_results(tmp_path: Path) -> None:
    directory = tmp_path / "evaluations"
    with TestClient(_app(directory)) as client:
        assert client.get(API).json() is None
        response = client.post(API)
        assert response.status_code == 202
        assert response.headers["Cache-Control"] == "no-store"
        running = response.json()
        assert running["status"] == "running"
        assert client.get("/health/live").json() == {"status": "live"}
        job = _wait(client, running["run_id"])
        assert job["status"] == "passed", job
        assert len(job["results"]["baselines"]) == 2
        assert len(job["results"]["controls"]) == 18
        assert all(row["accepted"] for row in job["results"]["controls"])
        saved = directory / job["run_id"] / "local-results.json"
        assert job["results"] == json.loads(saved.read_text())
        assert saved.stat().st_mode & 0o777 == 0o600
        assert "full_name" not in saved.read_text()
        assert client.get(API).json() == job

    with TestClient(_app(directory)) as restarted:
        assert restarted.get(API).json() == job


def test_duplicate_click_attaches_to_job_and_shutdown_is_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def blocked(directory: Path, *, timeout_seconds: float) -> dict[str, object]:
        directory.mkdir()
        await anyio.sleep_forever()
        raise AssertionError("Unreachable")

    monkeypatch.setattr("ai_governance_harness.chat.evaluations.run_local", blocked)
    with TestClient(_app(tmp_path)) as client:
        first = client.post(API).json()
        second = client.post(API)
        assert second.status_code == 409
        assert second.json()["run_id"] == first["run_id"]
        assert client.get(API).json()["status"] == "running"
        assert client.get("/health/live").status_code == 200

    with TestClient(_app(tmp_path)) as restarted:
        job = restarted.get(API).json()
        assert job["status"] == "error"
        assert job["error"] == "Evaluation was interrupted by server shutdown."
        assert job["run_id"] == first["run_id"]


@pytest.mark.parametrize("failure", ["timeout", "runner", "missing", "invalid"])
def test_job_failure_is_explicit_and_another_job_can_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    async def broken(directory: Path, *, timeout_seconds: float) -> dict[str, object]:
        if failure == "timeout":
            await anyio.sleep_forever()
        if failure == "runner":
            raise OSError("sensitive detail sentinel")
        if failure == "invalid":
            _save(directory, {"status": "passed"})
        return {"status": "passed"}

    monkeypatch.setattr("ai_governance_harness.chat.evaluations.run_local", broken)
    monkeypatch.setattr(
        "ai_governance_harness.chat.evaluations.JOB_TIMEOUT_SECONDS", 0.05
    )
    with TestClient(_app(tmp_path)) as client:
        first = client.post(API).json()
        job = _wait(client, first["run_id"], timeout=5)
        assert job["status"] == "error"
        assert job["results"] is None
        assert "sensitive detail sentinel" not in json.dumps(job)
        assert job["error"]
        assert client.post(API).status_code == 202


@pytest.mark.parametrize("passed", [True, False])
def test_existing_cli_output_is_read_without_running_again(
    tmp_path: Path, passed: bool
) -> None:
    results = _results(passed=passed)
    _save(tmp_path / RUN_ID, results)
    with TestClient(_app(tmp_path)) as client:
        latest = client.get(API)
        assert latest.status_code == 200
        assert latest.json()["results"] == results
        assert latest.json()["status"] == results["status"]
        assert client.get(f"{API}/{RUN_ID}").json() == latest.json()


def test_incomplete_cli_output_is_not_reported_as_passed(tmp_path: Path) -> None:
    (tmp_path / RUN_ID).mkdir()
    with TestClient(_app(tmp_path)) as client:
        job = client.get(API).json()
        assert job["status"] == "error"
        assert job["results"] is None
        assert "did not save a result" in job["error"]


@pytest.mark.parametrize("invalid", ["malformed", "contradictory", "symlink"])
def test_invalid_saved_output_returns_sanitized_error(
    tmp_path: Path, invalid: str
) -> None:
    directory = tmp_path / RUN_ID
    directory.mkdir()
    path = directory / "local-results.json"
    if invalid == "malformed":
        path.write_text("sensitive detail sentinel")
    elif invalid == "contradictory":
        results = _results(passed=False)
        results["status"] = "passed"
        write_json(path, results)
    else:
        secret = tmp_path / "secret.json"
        secret.write_text("sensitive detail sentinel")
        path.symlink_to(secret)
    with TestClient(_app(tmp_path)) as client:
        response = client.get(f"{API}/{RUN_ID}")
        assert response.status_code == 500
        assert "sensitive detail sentinel" not in response.text
        assert response.json()["error"]


def test_unknown_ids_and_symlink_directories_are_not_read(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    _save(outside, _results())
    (tmp_path / RUN_ID).symlink_to(outside, target_is_directory=True)
    with TestClient(_app(tmp_path)) as client:
        for run_id in (
            RUN_ID,
            "unknown",
            "../outside",
            "20261014T030232Z-000000000000",
        ):
            assert client.get(f"{API}/{run_id}").status_code == 404
        assert client.get(API).json() is None


def test_disallowed_browser_origin_cannot_start_eval(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path)) as client:
        response = client.post(API, headers={"Origin": "https://attacker.example"})
        assert response.status_code == 403
        assert not list(tmp_path.iterdir())


def test_agent_subdirectory_is_not_interpreted_as_offline_results(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "agent" / RUN_ID
    directory.mkdir(parents=True, mode=0o700)
    write_json(directory / "agent-results.json", {"status": "passed"})
    with TestClient(_app(tmp_path)) as client:
        assert client.get(API).json() is None
        assert client.get(f"{API}/{RUN_ID}").status_code == 404
        assert client.get("/health/live").status_code == 200
