"""Structured judge boundaries use real SDK calls with simulated HTTP only."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from openai import OpenAI
from pydantic import ValidationError

from ai_governance_harness.evaluation import agent_judge
from ai_governance_harness.evaluation.agent_contracts import (
    AgentEvaluationError,
    independent_agent_manifest,
    load_inputs,
)

SIMULATION_MODE = "success"
SIMULATED_ENDPOINT = (
    "https://australiaeast.services.ai.azure.com/api/projects/simulation"
)
SIMULATED_RESPONSE = (
    "MEM-001: Balance $145,000. Phase: Accumulation. "
    "Investment allocation: Growth 70%; Australian Shares 30%."
)


class SimulatedJudgeProject:
    def __init__(self):
        self.calls = 0
        self.closed = False
        self.client = None

    def get_openai_client(self):
        def completion(request):
            self.calls += 1
            data = json.loads(request.content)
            assert data["store"] is False
            assert "tools" not in data
            assert data["response_format"]["json_schema"]["strict"] is True
            assert data["messages"][0]["content"] == agent_judge.JUDGE_INSTRUCTIONS
            item = json.loads(data["messages"][1]["content"])
            assert "policy_score" not in item
            assert set(item["trusted_reference_facts"]) == {
                "balance",
                "phase",
                "option_allocation",
            }
            if SIMULATION_MODE == "service":
                return httpx.Response(
                    500, json={"error": {"message": "Simulation only."}}
                )
            result = {
                "case_id": item["case_id"],
                "rubric_version": item["rubric_version"],
                "criteria": [
                    {
                        "criterion_id": row["criterion_id"],
                        "verdict": "pass",
                        "rationale": "Simulated result, not live judge evidence.",
                        "response_evidence": item["public_response"][:100],
                    }
                    for row in item["criteria"]
                ],
            }
            if SIMULATION_MODE == "fail":
                result["criteria"][0]["verdict"] = "fail"
            elif SIMULATION_MODE == "wrong-case":
                result["case_id"] = "wrong-case"
            elif SIMULATION_MODE == "wrong-version":
                result["rubric_version"] = "incorrect"
            elif SIMULATION_MODE == "duplicate":
                result["criteria"][1]["criterion_id"] = result["criteria"][0][
                    "criterion_id"
                ]
            elif SIMULATION_MODE == "excerpt":
                result["criteria"][0]["response_evidence"] = (
                    "Never present in the response."
                )
            elif SIMULATION_MODE == "omitted":
                result["criteria"].pop()
            elif SIMULATION_MODE == "extra":
                result["unexpected"] = "Not allowed."
            elif SIMULATION_MODE == "missing-pass":
                result["criteria"][0]["response_evidence"] = "[missing content]"
            elif SIMULATION_MODE == "controls":
                failures = {
                    "control-wrong-fact": ["grounded_facts"],
                    "control-missing-field": ["requested_fields_complete"],
                    "control-unnecessary-refusal": ["requested_fields_complete"],
                    "control-advice-disclaimer": ["prohibited_content_withheld"],
                    "control-bypass": ["no_bypass"],
                    "control-judge-injection": ["grounded_facts"],
                }.get(item["case_id"], [])
                for row in result["criteria"]:
                    if row["criterion_id"] in failures:
                        row["verdict"] = "fail"
            content = (
                "{not JSON" if SIMULATION_MODE == "malformed" else json.dumps(result)
            )
            if SIMULATION_MODE == "empty":
                content = ""
            message = {"role": "assistant", "content": content}
            if SIMULATION_MODE == "refusal":
                message["refusal"] = "Simulation refusal."
            reason = {"filter": "content_filter", "length": "length"}.get(
                SIMULATION_MODE, "stop"
            )
            reply = {
                "id": "simulated-judge",
                "created": 1,
                "object": "chat.completion",
                "model": "simulated-judge-model",
                "choices": [{"index": 0, "finish_reason": reason, "message": message}],
            }
            if SIMULATION_MODE == "null-choices":
                reply["choices"] = None
            elif SIMULATION_MODE == "missing-choices":
                del reply["choices"]
            elif SIMULATION_MODE == "null-message":
                reply["choices"][0]["message"] = None
            return httpx.Response(200, json=reply)

        self.client = OpenAI(
            api_key="simulation-only",
            base_url="https://simulation.invalid/v1/",
            http_client=httpx.Client(
                transport=httpx.MockTransport(completion), trust_env=False
            ),
        )
        return self.client

    def close(self):
        self.closed = True


def simulated_input(timeout=20):
    cases, rubric = load_inputs()
    manifest = independent_agent_manifest(cases, rubric)
    return agent_judge.JudgeInput(
        case=cases[0],
        rubric=rubric,
        reference_facts=manifest.reference_facts,
        response=SIMULATED_RESPONSE,
        deployment="judge",
        timeout_seconds=timeout,
    )


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "fail",
        "service",
        "malformed",
        "wrong-case",
        "wrong-version",
        "duplicate",
        "excerpt",
        "omitted",
        "extra",
        "missing-pass",
        "empty",
        "refusal",
        "filter",
        "length",
        "null-choices",
        "missing-choices",
        "null-message",
    ],
)
def test_real_sdk_judge_contracts_and_nonretrying_errors(monkeypatch, mode):
    monkeypatch.setattr(sys.modules[__name__], "SIMULATION_MODE", mode)
    project = SimulatedJudgeProject()
    monkeypatch.setattr(agent_judge, "get_foundry_client", lambda: project)
    result = agent_judge.evaluate(simulated_input(), confirm_inference=True)
    assert project.calls == 1
    assert project.closed and project.client.is_closed()
    assert result.judge_requests == 1
    if mode in {"success", "fail"}:
        assert result.status == "completed"
        assert result.score == (1.0 if mode == "success" else 0.0)
        assert result.model_identity == "simulated-judge-model"
        assert result.model_revision is None
    else:
        assert result.status == "error"
        assert result.score is None and result.result is None and result.error


@pytest.mark.parametrize("mode", ["success", "malformed", "timeout"])
def test_isolated_judge_worker_cleanup(tmp_path, monkeypatch, mode):
    payload = simulated_input(timeout=0.02 if mode == "timeout" else 20)
    processes = []
    original = subprocess.Popen

    def launch(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(agent_judge.subprocess, "Popen", launch)
    result = agent_judge.judge_response(
        payload,
        tmp_path,
        endpoint=SIMULATED_ENDPOINT,
        confirm_inference=True,
        worker_command=[
            sys.executable,
            str(Path(__file__).resolve()),
            "--simulation",
            "malformed" if mode == "malformed" else "success",
        ],
    )
    assert result.status == ("completed" if mode == "success" else "error")
    assert all(process.poll() is not None for process in processes)
    assert list(tmp_path.iterdir()) == []


def test_judge_preflight_and_confirmation_precede_client(monkeypatch):
    def forbidden():
        pytest.fail("No client may be constructed.")

    monkeypatch.setattr(agent_judge, "get_foundry_client", forbidden)
    payload = simulated_input()
    with pytest.raises(AgentEvaluationError, match="inference_confirmation_required"):
        agent_judge.evaluate(payload)
    with pytest.raises(ValidationError):
        agent_judge.evaluate(
            payload.model_copy(
                update={"response": '{"full_name":"Synthetic Private Sentinel"}'}
            ),
            confirm_inference=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation", default="success")
    args, rest = parser.parse_known_args()
    SIMULATION_MODE = args.simulation
    sys.argv = [sys.argv[0], *rest]
    agent_judge.get_foundry_client = SimulatedJudgeProject
    sys.exit(agent_judge.main())
