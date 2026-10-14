"""Real production HTTP/MCP integration with an explicitly simulated model."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import anyio
import httpx
import httpx2
import pytest
from azure.ai.projects import AIProjectClient
from azure.core.credentials import AccessToken
from azure.identity import AzureCliCredential
from mcp.client.client import CallToolResult
from openai import OpenAI

from ai_governance_harness.evaluation import agent_collector
from ai_governance_harness.evaluation.agent_contracts import (
    AgentEvaluationError,
    independent_agent_manifest,
    load_inputs,
    policy_score,
)
from ai_governance_harness.evaluation.agent_worker import ExecutionObserver

SIMULATED_ENDPOINT = (
    "https://australiaeast.services.ai.azure.com/api/projects/simulation"
)
WORKER_COMMAND = [sys.executable, str(Path(__file__).resolve())]


class SimulatedProject:
    def get_openai_client(self):
        attempts = 0
        response_type = (
            httpx2.Response
            if os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "").startswith("default")
            else httpx.Response
        )

        def completion(request):
            nonlocal attempts
            attempts += 1
            if os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") == "default-cli":
                assert request.headers["authorization"] == "Bearer simulated-cli-token"
            if (
                os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
                in {"retry", "default-retry"}
                and attempts == 1
            ):
                return response_type(
                    429, json={"error": {"message": "Simulated retry."}}
                )
            body = json.loads(request.content)
            assert body["store"] is False
            if "response_format" in body:
                schema = body["response_format"]["json_schema"]
                assert schema["strict"] is True
                assert schema["name"] == "advice_request_classification"
                assert "tools" not in body
                context = json.loads(body["messages"][1]["content"])
                advice = context["current_user_turn"].startswith("Recommend")
                if os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") == "default-behavior":
                    from ai_governance_harness.evaluation.agent_managed_contracts import (
                        load_cases,
                    )

                    case = next(
                        row
                        for row in load_cases()
                        if row.prompt == context["current_user_turn"]
                    )
                    advice = case.category in {
                        "personal_advice",
                        "banking_advice",
                        "superannuation_advice",
                    }
                classification = {
                    "classification_status": "classified",
                    "request_intent": (
                        "financial_recommendation" if advice else "factual_information"
                    ),
                    "advice_subject": "identified_member" if advice else "none",
                    "financial_action": "invest" if advice else "none",
                    "product_scope": "superannuation_option" if advice else "none",
                    "confidence": "high",
                }
                message = {
                    "role": "assistant",
                    "content": json.dumps(classification),
                }
                reason = "stop"
            else:
                assert body["parallel_tool_calls"] is False
                assert [item["function"]["name"] for item in body["tools"]] == [
                    "get_member_profile",
                    "prepare_member_outreach_case",
                ]
                assert not any(
                    message["role"] == "tool" for message in body["messages"]
                )
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "simulated-profile-call",
                            "type": "function",
                            "function": {
                                "name": "get_member_profile",
                                "arguments": '{"member_id":"MEM-001"}',
                            },
                        }
                    ],
                }
                reason = "tool_calls"
                if os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") == "default-behavior":
                    prompt = next(
                        item["content"]
                        for item in reversed(body["messages"])
                        if item["role"] == "user"
                    )
                    if prompt == "What does a disengagement signal mean in this tool?":
                        message = {
                            "role": "assistant",
                            "content": "A disengagement signal is an in-fund indicator of reduced member engagement.",
                        }
                        reason = "stop"
            return response_type(
                200,
                json={
                    "id": "simulated-completion",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "simulated-model",
                    "choices": [
                        {"index": 0, "message": message, "finish_reason": reason}
                    ],
                },
            )

        if response_type is httpx2.Response:

            class Credential:
                def get_token(self, *args, **kwargs):
                    return AccessToken("simulation-only", 4_000_000_000)

            # Keep the SDK's default client and logging transport; intercept only HTTP I/O.
            httpx2.HTTPTransport.handle_request = lambda self, request: completion(
                request
            )
            project = AIProjectClient(
                endpoint=SIMULATED_ENDPOINT, credential=Credential()
            )
            if os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") == "default-cli":
                project = AIProjectClient(
                    endpoint=SIMULATED_ENDPOINT,
                    credential=AzureCliCredential(process_timeout=5),
                )
                return project.get_openai_client()
            return project.get_openai_client(api_key="simulation-only")
        return OpenAI(
            api_key="simulation-only",
            base_url="https://simulation.invalid/v1/",
            http_client=httpx.Client(
                transport=httpx.MockTransport(completion),
                trust_env=False,
            ),
        )

    def close(self):
        pass


def collect_simulation(tmp_path, category, timeout=30, deployment=None):
    cases, rubric = load_inputs()
    manifest = independent_agent_manifest(cases, rubric)
    case = next(row for row in cases if row.category == category)
    deployment = deployment or "target"
    row = agent_collector.collect_case(
        manifest,
        case,
        tmp_path,
        target_deployment=deployment,
        endpoint=SIMULATED_ENDPOINT,
        timeout_seconds=timeout,
        confirm_inference=True,
        worker_command=WORKER_COMMAND,
    )
    return manifest, case, row, deployment


def test_actual_sdk_retry_attempts_keep_their_policy_permit(tmp_path):
    manifest, case, row, deployment = collect_simulation(
        tmp_path, "allow", deployment="retry"
    )
    assert row.collection_status == "completed", row.collection_error
    assert policy_score(manifest, case, row, deployment) == 1.0
    capture = row.captures["chat"]
    assert capture.target_requests == 2
    assert capture.target_http_attempts == 3
    assert (
        capture.target_http_event_sequences[:2]
        == [
            capture.target_request_event_sequences[0],
        ]
        * 2
    )


@pytest.mark.parametrize("category", ["allow", "deny"])
@pytest.mark.parametrize("deployment", ["default", "default-retry"])
def test_default_foundry_transport_is_observed_end_to_end(
    tmp_path, category, deployment
):
    manifest, case, row, _ = collect_simulation(
        tmp_path, category, deployment=deployment
    )
    assert row.collection_status == "completed", row.collection_error
    capture = row.captures["chat"]
    expected = capture.target_requests + int(deployment == "default-retry")
    assert capture.target_http_attempts == expected
    assert policy_score(manifest, case, row, deployment) == 1.0


@pytest.mark.parametrize("category", ["allow", "deny"])
def test_real_http_route_and_mcp_capture_with_simulated_model(
    tmp_path, monkeypatch, category
):
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "fixture-only-auth-sentinel")
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING", "fixture-only-export-sentinel"
    )
    monkeypatch.setenv("GOVERNANCE_ENABLED", "false")
    (tmp_path / ".env").write_text("GOVERNANCE_ENABLED=false\n")
    manifest, case, row, deployment = collect_simulation(tmp_path, category)
    assert row.collection_status == "completed", row.model_dump_json()
    assert policy_score(manifest, case, row, deployment) == 1.0
    assert row.exit_codes == {"chat": 0, "mcp": 0}
    if category == "allow":
        assert "synthetic profile for MEM-001" in row.response
        assert "Balance: $145,000.00" in row.response
        assert "Phase: Accumulation" in row.response
        assert (
            "Investment allocation: Growth: 70%, Australian Shares: 30%" in row.response
        )
        assert row.captures["chat"].target_requests == 2
        assert row.captures["chat"].target_http_attempts == 2
        assert len(row.captures["chat"].tool_calls) == 1
        assert row.captures["mcp"].backend_executions == 1
        assert row.captures["mcp"].operation_facts == [manifest.reference_facts]
    else:
        assert row.http_status == 403
        assert row.error_rule == "deny-identified-member-financial-recommendation"
        assert row.response == "Governance policy denied the requested operation."
        assert row.captures["chat"].target_requests == 1
        assert row.captures["chat"].target_http_attempts == 1
        assert [event.action for event in row.captures["chat"].events] == [
            "foundry.advice_classifier",
            "foundry.advice_classifier",
            "chat.input",
        ]
        assert row.captures["chat"].tool_calls == []
        assert row.captures["mcp"].backend_executions == 0
    assert "full_name" not in row.model_dump_json()
    assert "fixture-only-auth-sentinel" not in row.model_dump_json()
    assert list(tmp_path.iterdir()) == [tmp_path / ".env"]


def test_multiple_coroutine_resumptions_count_one_tool_invocation():
    observer = ExecutionObserver("simulated-request", "chat")

    async def tool(name, arguments):
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return CallToolResult.model_validate({"content": [], "isError": False})

    observer._tool_code = tool.__code__
    observer.install()
    try:
        anyio.run(tool, "get_member_profile", {"member_id": "MEM-001"})
    finally:
        observer._stopping = True
        sys.setprofile(None)
        threading.setprofile(None)
    assert len(observer.tool_calls) == 1
    assert observer.tool_calls[0].successful is True


def test_user_installed_cli_authenticates_inside_real_local_agent(
    tmp_path, monkeypatch
):
    python = Path("/usr/bin/python3")
    if not python.is_file():
        pytest.skip("Requires the system Python used by a user-installed Azure CLI.")
    user_base = tmp_path / "user-packages"
    monkeypatch.setenv("PYTHONUSERBASE", str(user_base))
    site_directory = Path(
        subprocess.check_output(
            [str(python), "-c", "import site; print(site.getusersitepackages())"],
            text=True,
        ).strip()
    )
    site_directory.mkdir(parents=True)
    (site_directory / "evaluation_cli_package.py").write_text(
        "TOKEN = 'simulated-cli-token'\n"
    )
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    cli = bin_directory / "az"
    cli.write_text(
        "#!/usr/bin/python3\n"
        "import json\n"
        "from evaluation_cli_package import TOKEN\n"
        "print(json.dumps({'accessToken': TOKEN, 'expires_on': 4000000000}))\n"
    )
    cli.chmod(0o700)
    monkeypatch.setenv("PATH", str(bin_directory) + os.pathsep + os.environ["PATH"])
    manifest, case, evidence, deployment = collect_simulation(
        tmp_path, "allow", deployment="default-cli"
    )
    assert evidence.collection_status == "completed", evidence.collection_error
    assert policy_score(manifest, case, evidence, deployment) == 1.0
    assert evidence.captures["chat"].target_http_attempts == 2


@pytest.mark.parametrize("cancel", [False, True])
def test_timeout_and_cancellation_reap_all_owned_children(
    tmp_path, monkeypatch, cancel
):
    children = []
    original = subprocess.Popen

    def launch(*args, **kwargs):
        process = original(*args, **kwargs)
        children.append(process)
        return process

    monkeypatch.setattr(agent_collector.subprocess, "Popen", launch)
    if cancel:

        def interrupt(*args, **kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(httpx.Client, "stream", interrupt)
        with pytest.raises(KeyboardInterrupt):
            collect_simulation(tmp_path, "allow")
    else:
        _, _, row, _ = collect_simulation(tmp_path, "allow", timeout=0.02)
        assert row.collection_status == "error"
        assert row.collection_error == "startup_timeout"
    assert children and all(process.poll() is not None for process in children)
    assert list(tmp_path.iterdir()) == []


def test_no_consent_prevents_processes_and_artifacts(tmp_path, monkeypatch):
    cases, rubric = load_inputs()
    manifest = independent_agent_manifest(cases, rubric)

    def forbidden(*args, **kwargs):
        pytest.fail("No process may start without inference consent.")

    monkeypatch.setattr(agent_collector.subprocess, "Popen", forbidden)
    with pytest.raises(AgentEvaluationError, match="inference_confirmation_required"):
        agent_collector.collect_case(
            manifest,
            cases[0],
            tmp_path,
            target_deployment="target",
            endpoint=SIMULATED_ENDPOINT,
            timeout_seconds=30,
        )
    assert list(tmp_path.iterdir()) == []


if __name__ == "__main__":
    from ai_governance_harness.chat import service
    from ai_governance_harness.evaluation import agent_worker

    role = sys.argv[sys.argv.index("--role") + 1]
    assert os.environ["PYTHON_DOTENV_DISABLED"] == "true"
    assert "APPLICATIONINSIGHTS_CONNECTION_STRING" not in os.environ
    if role == "mcp":
        assert not any(os.getenv(key) for key in agent_collector.MODEL_ENV_KEYS)
        assert not os.getenv("PYTHONUSERBASE")
    service.get_foundry_client = SimulatedProject
    sys.exit(agent_worker.main())
