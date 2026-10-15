"""Agent orchestration uses explicitly simulated model/evidence boundaries."""

from __future__ import annotations

import functools
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

import test_agent_evaluation_judge as judge_simulation
from test_agent_evaluation_collection import WORKER_COMMAND
from test_agent_evaluation_contracts import simulated_evidence
from test_agent_evaluation_judge import SIMULATED_ENDPOINT, SimulatedJudgeProject

from ai_governance_harness.evaluation import agent_judge, agent_runner
from ai_governance_harness.evaluation.agent_contracts import (
    AgentEvaluationError,
    independent_agent_manifest,
    load_inputs,
)

JUDGE_COMMAND = [
    sys.executable,
    str(Path(judge_simulation.__file__).resolve()),
    "--simulation",
    "controls",
]


def run_simulation(directory, **kwargs):
    return agent_runner.run_agent(
        directory,
        **{
            "target_deployment": "target",
            "judge_deployment": "judge",
            "endpoint": SIMULATED_ENDPOINT,
            "confirm_inference": True,
            "timeout_seconds": 30,
            "collection_worker_command": WORKER_COMMAND,
            "judge_worker_command": JUDGE_COMMAND,
            **kwargs,
        },
    )


@pytest.fixture
def simulated_boundaries(monkeypatch):
    calls = {"collection": [], "judge": []}

    def collect(manifest, case, directory, **kwargs):
        calls["collection"].append(case.case_id)
        _, _, evidence = simulated_evidence(case.category)
        return evidence.model_copy(
            update={
                "case_id": case.case_id,
                "manifest_digest": agent_runner.digest(manifest),
            }
        )

    def judge(payload, directory, **kwargs):
        calls["judge"].append(payload.case.case_id)
        return agent_judge.evaluate(payload, confirm_inference=True)

    monkeypatch.setattr(agent_runner, "collect_case", collect)
    monkeypatch.setattr(agent_runner, "judge_response", judge)
    monkeypatch.setattr(agent_judge, "get_foundry_client", SimulatedJudgeProject)
    monkeypatch.setattr(judge_simulation, "SIMULATION_MODE", "controls")
    return calls


def test_real_cli_routes_mcp_and_isolated_judge_with_simulated_http(tmp_path):
    directory = tmp_path / "agent" / "smoke"
    process = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "agent",
            "--target-deployment",
            "target",
            "--judge-deployment",
            "judge",
            "--endpoint",
            SIMULATED_ENDPOINT,
            "--output",
            str(directory),
            "--confirm-inference",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    results = json.loads((directory / "agent-results.json").read_text())
    assert results["status"] == "passed"
    assert results["execution_kind"] == "simulated"
    assert len(results["baselines"]) == 2
    assert all(row["accepted"] for row in results["baselines"])
    assert len(results["controls"]) == 8
    assert all(row["accepted"] for row in results["controls"])
    assert (
        results["baselines"][0]["evidence"]["captures"]["mcp"]["backend_executions"]
        == 1
    )
    assert (
        results["baselines"][1]["evidence"]["captures"]["chat"]["target_requests"] == 1
    )
    assert results["baselines"][1]["evidence"]["http_status"] == 403
    assert results["baselines"][1]["evidence"]["response"] == (
        "Governance policy denied the requested operation."
    )
    assert directory.stat().st_mode & 0o777 == 0o700
    for path in directory.iterdir():
        assert path.is_file()
        assert path.stat().st_mode & 0o777 == 0o600
        assert "full_name" not in path.read_text()
        assert "recent_contributions" not in path.read_text()


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_private_fresh_artifacts_controls_and_no_overwrite(
    tmp_path, simulated_boundaries, monkeypatch, platform
):
    monkeypatch.setattr(sys, "platform", platform)
    directory = tmp_path / "agent" / "private"
    results = run_simulation(directory)
    assert results.status == "passed"
    assert len(simulated_boundaries["collection"]) == 2
    assert len(simulated_boundaries["judge"]) == 10
    assert len({row.control.control_id for row in results.controls}) == 8
    assert all(row.accepted for row in results.controls)
    assert results.configuration.target_deployment == "target"
    assert results.configuration.judge_deployment == "judge"
    assert all(row.judge.model_revision is None for row in results.baselines)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(FileExistsError):
        run_simulation(directory)
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}
    assert len(simulated_boundaries["collection"]) == 2


def test_injected_prompt_list_keeps_every_case_and_separate_controls(
    tmp_path, simulated_boundaries
):
    cases, _ = load_inputs()
    cases.extend(
        case.model_copy(update={"case_id": f"additional-{case.category}"})
        for case in cases[:]
    )
    dataset = tmp_path / "expanded.jsonl"
    dataset.write_text("\n".join(case.model_dump_json() for case in cases))
    results = run_simulation(tmp_path / "agent" / "expanded", dataset=dataset)
    assert results.status == "passed"
    assert {row.case_id for row in results.baselines} == {
        case.case_id for case in cases
    }
    assert len(results.baselines) == 4 and len(results.controls) == 8
    assert len(simulated_boundaries["collection"]) == 4
    assert len(simulated_boundaries["judge"]) == 12


def test_artifact_failure_retains_identifiable_unrun_outcomes_before_inference(
    tmp_path, monkeypatch, simulated_boundaries
):
    write = agent_runner.write_json

    def unavailable(path, value):
        if path.name == "rubric.json":
            raise PermissionError("fixture-only-private-artifact-sentinel")
        write(path, value)

    monkeypatch.setattr(agent_runner, "write_json", unavailable)
    directory = tmp_path / "agent" / "artifact-error"
    with pytest.raises(PermissionError):
        run_simulation(directory)
    saved = json.loads((directory / "agent-results.json").read_text())
    assert saved["status"] == "failed" and saved["error"] == "run_incomplete"
    assert len(saved["baselines"]) == 2 and len(saved["controls"]) == 8
    assert all(row["collection_status"] == "not_run" for row in saved["baselines"])
    assert all(row["judge_status"] == "not_run" for row in saved["controls"])
    assert simulated_boundaries == {"collection": [], "judge": []}
    assert "fixture-only-private-artifact-sentinel" not in json.dumps(saved)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"confirm_inference": False},
        {"target_deployment": ""},
        {"judge_deployment": ""},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": True},
        {"endpoint": "https://unapproved.example.test"},
    ],
)
def test_preflight_precedes_clients_and_artifacts(
    tmp_path, simulated_boundaries, kwargs
):
    directory = tmp_path / "agent" / "blocked"
    with pytest.raises((AgentEvaluationError, ValidationError)):
        run_simulation(directory, **kwargs)
    assert simulated_boundaries == {"collection": [], "judge": []}
    assert not directory.parent.exists()


@pytest.mark.parametrize("source", ["prompt", "rubric", "identity"])
def test_unsafe_inputs_and_control_collisions_precede_persistence(
    tmp_path, simulated_boundaries, source
):
    cases, rubric = load_inputs()
    sentinel = "api_key=fixture-only-sensitive-sentinel"
    rows = [case.model_dump(mode="json") for case in cases]
    rubric_data = rubric.model_dump(mode="json")
    if source == "prompt":
        rows[0]["prompt"] += " " + sentinel
    elif source == "rubric":
        rubric_data["criteria"]["allow"][0]["pass_condition"] += " " + sentinel
    else:
        rows[0]["case_id"] = "control-good-answer"
    dataset, rubric_path = tmp_path / "input.jsonl", tmp_path / "rubric.json"
    dataset.write_text("\n".join(json.dumps(row) for row in rows))
    rubric_path.write_text(json.dumps(rubric_data))
    directory = tmp_path / "agent" / "blocked"
    with pytest.raises(AgentEvaluationError) as error:
        run_simulation(directory, dataset=dataset, rubric_path=rubric_path)
    assert sentinel not in str(error.value)
    assert simulated_boundaries == {"collection": [], "judge": []}
    assert not directory.parent.exists()


@pytest.mark.parametrize("kind", ["offline-location", "symlink"])
def test_output_is_segregated_and_does_not_follow_symlinks(
    tmp_path, simulated_boundaries, kind
):
    if kind == "offline-location":
        directory = tmp_path / "20261014T030232Z-b68217988ad8"
    else:
        directory = tmp_path / "agent" / "run"
        directory.parent.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        directory.symlink_to(outside, target_is_directory=True)
    with pytest.raises(AgentEvaluationError):
        run_simulation(directory)
    assert simulated_boundaries == {"collection": [], "judge": []}
    assert not (directory / "agent-results.json").exists()


def test_favorable_judge_cannot_override_enforcement_violation(
    tmp_path, monkeypatch, simulated_boundaries
):
    collect = agent_runner.collect_case

    def violate(*args, **kwargs):
        evidence = collect(*args, **kwargs)
        if evidence.case_id == "agent-advice-deny":
            evidence.captures["mcp"].backend_executions = 1
        return evidence

    monkeypatch.setattr(agent_runner, "collect_case", violate)
    results = run_simulation(tmp_path / "agent" / "violation")
    assert results.status == "failed"
    denied = results.baselines[1]
    assert denied.collection_status == "completed"
    assert denied.policy_status == "completed" and denied.policy_score == 0.0
    assert denied.judge.score == 1.0 and not denied.accepted


def test_unsafe_response_is_not_retained_or_judged(
    tmp_path, monkeypatch, simulated_boundaries
):
    collect = agent_runner.collect_case
    sentinel = "api_key=fixture-only-private-output"

    def unsafe(*args, **kwargs):
        return collect(*args, **kwargs).model_copy(update={"response": sentinel})

    monkeypatch.setattr(agent_runner, "collect_case", unsafe)
    directory = tmp_path / "agent" / "unsafe"
    results = run_simulation(directory)
    assert results.status == "failed"
    assert all(row.collection_status == "error" for row in results.baselines)
    assert all(row.judge_status == "skipped" for row in results.baselines)
    assert len(simulated_boundaries["judge"]) == 8
    assert all(sentinel not in path.read_text() for path in directory.iterdir())


@pytest.mark.parametrize("mode", ["service", "malformed", "wrong-case"])
def test_judge_errors_are_not_successful_negative_controls(
    tmp_path, monkeypatch, simulated_boundaries, mode
):
    monkeypatch.setattr(judge_simulation, "SIMULATION_MODE", mode)
    results = run_simulation(tmp_path / "agent" / mode)
    assert results.status == "failed"
    assert all(row.judge.status == "error" for row in results.baselines)
    assert all(row.judge.score is None for row in results.controls)
    assert not any(row.accepted for row in results.controls)


def test_bad_control_requires_its_intended_failed_criterion(
    tmp_path, monkeypatch, simulated_boundaries
):
    judge = agent_runner.judge_response

    def wrong_failure(payload, *args, **kwargs):
        result = judge(payload, *args, **kwargs)
        if payload.case.case_id == "control-wrong-fact":
            for row in result.result.criteria:
                row.verdict = "fail" if row.criterion_id == "answer_clear" else "pass"
        return result

    monkeypatch.setattr(agent_runner, "judge_response", wrong_failure)
    results = run_simulation(tmp_path / "agent" / "wrong-criterion")
    assert results.status == "failed"
    control = next(
        row
        for row in results.controls
        if row.control.control_id == "control-wrong-fact"
    )
    assert control.judge.score == 0.0 and not control.accepted


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-baseline",
        "duplicate-baseline",
        "missing-control",
        "duplicate-control",
        "skipped-control",
        "altered-control",
    ],
)
def test_missing_duplicate_skipped_or_altered_outcomes_cannot_pass(
    tmp_path, simulated_boundaries, mutation
):
    results = run_simulation(tmp_path / "agent" / mutation)
    cases, rubric = load_inputs()
    manifest = independent_agent_manifest(cases, rubric)
    expected = agent_runner.response_controls(manifest)
    baselines, controls = results.baselines[:], results.controls[:]
    if mutation == "missing-baseline":
        baselines.pop()
    elif mutation == "duplicate-baseline":
        baselines[1] = baselines[0]
    elif mutation == "missing-control":
        controls.pop()
    elif mutation == "duplicate-control":
        controls[1] = controls[0]
    elif mutation == "skipped-control":
        controls[0] = controls[0].model_copy(update={"judge_status": "skipped"})
    else:
        controls[0].control = controls[0].control.model_copy(
            update={"response": "Changed trusted control."}
        )
    assert not agent_runner.accepted_outcomes(manifest, baselines, controls, expected)


@pytest.mark.parametrize("stage", ["collection", "baseline-judge", "control-judge"])
def test_cancellation_retains_all_expected_partial_outcomes(
    tmp_path, monkeypatch, simulated_boundaries, stage
):
    collect, judge = agent_runner.collect_case, agent_runner.judge_response

    def interrupt_collection(manifest, case, *args, **kwargs):
        if stage == "collection" and case.category == "deny":
            raise KeyboardInterrupt
        return collect(manifest, case, *args, **kwargs)

    def interrupt_judge(payload, *args, **kwargs):
        if (
            stage == "baseline-judge" and payload.case.case_id == "agent-profile-allow"
        ) or (
            stage == "control-judge" and payload.case.case_id == "control-good-answer"
        ):
            raise KeyboardInterrupt
        return judge(payload, *args, **kwargs)

    monkeypatch.setattr(agent_runner, "collect_case", interrupt_collection)
    monkeypatch.setattr(agent_runner, "judge_response", interrupt_judge)
    directory = tmp_path / "agent" / stage
    results = run_simulation(directory)
    assert results.status == "cancelled"
    assert len(results.baselines) == 2 and len(results.controls) == 8
    saved = json.loads((directory / "agent-results.json").read_text())
    assert saved["status"] == "cancelled" and saved["error"] == "run_cancelled"
    if stage == "collection":
        assert results.baselines[0].accepted
        assert results.baselines[1].collection_status == "cancelled"
    elif stage == "baseline-judge":
        assert results.baselines[0].evidence.collection_status == "completed"
        assert results.baselines[0].judge_status == "cancelled"
        assert results.baselines[1].collection_status == "not_run"
    else:
        assert all(row.accepted for row in results.baselines)
        assert results.controls[0].judge_status == "cancelled"
    assert all(row.judge_status == "not_run" for row in results.controls[1:])


def test_actual_worker_timeout_retains_failures_without_missing_rows(tmp_path):
    results = run_simulation(tmp_path / "agent" / "timeouts", timeout_seconds=0.01)
    assert results.status == "failed"
    assert len(results.baselines) == 2 and len(results.controls) == 8
    assert all(row.collection_status == "error" for row in results.baselines)
    assert all(row.judge_status == "skipped" for row in results.baselines)
    assert all(row.judge_status == "error" for row in results.controls)


if __name__ == "__main__":
    from ai_governance_harness.evaluation import __main__ as cli

    cli.run_agent = functools.partial(
        agent_runner.run_agent,
        collection_worker_command=WORKER_COMMAND,
        judge_worker_command=JUDGE_COMMAND,
    )
    sys.exit(cli.main())
