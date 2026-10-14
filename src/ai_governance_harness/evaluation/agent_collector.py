"""Isolated single-turn collection through the production chat/HTTP MCP apps."""

from __future__ import annotations

import json
import math
import os
import shutil
import site
import socket
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from pydantic import ValidationError

from ai_governance_harness.chat.service import ChatResponse
from ai_governance_harness.evaluation.agent_contracts import (
    AgentCapture,
    AgentCase,
    AgentEvaluationError,
    AgentEvidence,
    AgentManifest,
    digest,
    private_text,
)
from ai_governance_harness.evaluation.artifacts import (
    DATA_DIRECTORY,
    DEFAULT_POLICY,
    FIXTURE_NAMES,
)
from ai_governance_harness.evaluation.collector import isolated_environment
from ai_governance_harness.guardrails.sovereignty import (
    SovereigntyGuardrail,
    SovereigntyViolationError,
)

if TYPE_CHECKING:
    from ai_governance_harness.evaluation.agent_managed_contracts import (
        BehaviorCase,
        BehaviorManifest,
    )

MODEL_ENV_KEYS = (
    "AZURE_AI_PROJECT_ENDPOINT",
    "AZURE_AI_PROJECT_CONNECTION_STRING",
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_RESOURCE_GROUP",
    "AZURE_AI_PROJECT_NAME",
    "AZURE_AI_PROJECT_REGION",
    "AZURE_REGION",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_CLIENT_CERTIFICATE_PATH",
    "AZURE_CLIENT_CERTIFICATE_PASSWORD",
    "AZURE_CLIENT_SEND_CERTIFICATE_CHAIN",
    "AZURE_FEDERATED_TOKEN_FILE",
    "IDENTITY_ENDPOINT",
    "IDENTITY_HEADER",
    "IMDS_ENDPOINT",
    "MSI_ENDPOINT",
    "MSI_SECRET",
    "AZURE_CONFIG_DIR",
)


def validate_connection(endpoint: str | None) -> str | None:
    selected = endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    try:
        if selected:
            parsed = urlsplit(selected)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.port not in {None, 443}
                or not any(
                    parsed.hostname.endswith(suffix)
                    for suffix in (
                        ".services.ai.azure.com",
                        ".api.azureml.ms",
                    )
                )
            ):
                raise AgentEvaluationError("invalid_foundry_endpoint")
            SovereigntyGuardrail().validate_endpoint(selected)
            return selected
        connection = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
        if connection:
            parts = connection.split(";")
            if len(parts) != 4 or not all(parts):
                raise AgentEvaluationError("invalid_foundry_connection_string")
            validate_connection("https://" + parts[0])
        if not (
            connection
            or all(
                os.getenv(key)
                for key in (
                    "AZURE_SUBSCRIPTION_ID",
                    "AZURE_RESOURCE_GROUP",
                    "AZURE_AI_PROJECT_NAME",
                )
            )
        ):
            raise AgentEvaluationError("missing_foundry_connection")
        region = os.getenv("AZURE_AI_PROJECT_REGION") or os.getenv("AZURE_REGION")
        if not region:
            raise AgentEvaluationError("missing_foundry_connection_region")
        SovereigntyGuardrail().validate_region(region)
    except SovereigntyViolationError:
        raise AgentEvaluationError("unapproved_foundry_endpoint_or_region") from None
    except ValueError as error:
        if isinstance(error, AgentEvaluationError):
            raise
        raise AgentEvaluationError("invalid_foundry_endpoint") from None
    return None


def model_environment(
    directory: Path, policy: Path, endpoint: str | None
) -> dict[str, str]:
    env = isolated_environment(directory, policy)
    env.update({key: os.environ[key] for key in MODEL_ENV_KEYS if key in os.environ})
    if endpoint:
        env["AZURE_AI_PROJECT_ENDPOINT"] = endpoint
        env.pop("AZURE_AI_PROJECT_CONNECTION_STRING", None)
        for key in (
            "AZURE_SUBSCRIPTION_ID",
            "AZURE_RESOURCE_GROUP",
            "AZURE_AI_PROJECT_NAME",
        ):
            env.pop(key, None)
    azure_cli = shutil.which("az")
    if azure_cli:
        env["PATH"] = os.path.dirname(azure_cli) + os.pathsep + os.defpath
        # The isolated HOME must not hide a user-installed CLI's Python packages.
        env["PYTHONUSERBASE"] = os.getenv("PYTHONUSERBASE") or site.getuserbase()
        config = Path(os.getenv("AZURE_CONFIG_DIR", str(Path.home() / ".azure")))
        if config.is_dir():
            env["AZURE_CONFIG_DIR"] = str(config)
    return env


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    return remaining


def _stop(process: subprocess.Popen, deadline: float) -> int:
    if process.poll() is None:
        if process.stdin is None or process.stdin.closed:
            process.terminate()
        else:
            try:
                process.stdin.write(b"stop\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                process.terminate()
            finally:
                process.stdin.close()
        try:
            return process.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                return process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                return process.wait(timeout=5)
    if process.stdin and not process.stdin.closed:
        process.stdin.close()
    return process.wait()


def collect_case(
    manifest: AgentManifest | BehaviorManifest,
    case: AgentCase | BehaviorCase,
    directory: Path,
    *,
    target_deployment: str,
    endpoint: str | None,
    timeout_seconds: float,
    confirm_inference: bool = False,
    worker_command: list[str] | None = None,
) -> AgentEvidence:
    if confirm_inference is not True:
        raise AgentEvaluationError("inference_confirmation_required")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise AgentEvaluationError("invalid_collection_timeout")
    private_text(case.prompt)
    private_text(case.expected_behavior)
    endpoint = validate_connection(endpoint)
    if sys.platform != "linux":
        raise AgentEvaluationError("unsupported_owned_socket_platform")
    request_id = uuid4().hex
    deadline = time.monotonic() + timeout_seconds
    captures: dict[str, AgentCapture] = {}
    exit_codes: dict[str, int] = {}
    public: dict[str, object] = {
        "http_status": None,
        "response": None,
        "error_code": None,
        "error_rule": None,
        "tools_used": [],
    }
    failure = None
    stage = "startup"
    with TemporaryDirectory(prefix=".capture-", dir=directory) as temporary:
        work = Path(temporary)
        policy = work / "policy.yaml"
        policy.write_bytes(DEFAULT_POLICY.read_bytes())
        policy.chmod(0o600)
        for name in FIXTURE_NAMES:
            path = work / name
            shutil.copyfile(DATA_DIRECTORY / name, path)
            path.chmod(0o600)
        processes: dict[str, subprocess.Popen] = {}
        with ExitStack() as stack:
            sockets = {}
            for role in ("mcp", "chat"):
                listener = stack.enter_context(socket.socket())
                listener.bind(("127.0.0.1", 0))
                listener.listen(128)
                sockets[role] = listener
            urls = {
                role: f"http://127.0.0.1:{listener.getsockname()[1]}"
                for role, listener in sockets.items()
            }
            client = stack.enter_context(httpx.Client(trust_env=False))
            try:
                for role in ("mcp", "chat"):
                    listener = sockets[role]
                    env = (
                        model_environment(work, policy, endpoint)
                        if role == "chat"
                        else isolated_environment(work, policy)
                    )
                    env.update(
                        {
                            "MCP_TRANSPORT": "streamable-http",
                            "MCP_HOST": "127.0.0.1",
                            "MCP_PORT": str(sockets["mcp"].getsockname()[1]),
                            "CHAT_HOST": "127.0.0.1",
                            "CHAT_PORT": str(sockets["chat"].getsockname()[1]),
                            "MCP_SERVER_URL": urls["mcp"] + "/mcp",
                            "AZURE_AI_MODEL_DEPLOYMENT_NAME": target_deployment,
                        }
                        if role == "chat"
                        else {
                            "MCP_TRANSPORT": "streamable-http",
                            "MCP_HOST": "127.0.0.1",
                            "MCP_PORT": str(listener.getsockname()[1]),
                        }
                    )
                    command = worker_command or [
                        sys.executable,
                        "-m",
                        "ai_governance_harness.evaluation.agent_worker",
                    ]
                    processes[role] = subprocess.Popen(
                        [
                            *command,
                            "--role",
                            role,
                            "--socket-fd",
                            str(listener.fileno()),
                            "--capture",
                            str(work / f"{role}.json"),
                            "--fixture",
                            str(work),
                            "--request-id",
                            request_id,
                            "--confirm-inference",
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        cwd=work,
                        env=env,
                        pass_fds=(listener.fileno(),),
                    )
                    while True:
                        if processes[role].poll() is not None:
                            raise AgentEvaluationError("startup_worker_exit")
                        try:
                            ready = client.get(
                                urls[role] + "/health/ready",
                                timeout=min(0.25, _remaining(deadline)),
                            )
                        except httpx.HTTPError:
                            _remaining(deadline)
                        else:
                            if ready.status_code == 200:
                                state = ready.json()
                                if (
                                    state["status"] != "ready"
                                    or state["governance"]["enforcement"] != "enabled"
                                    or state["governance"]["policy_digest"]
                                    != manifest.policy_digest
                                ):
                                    raise AgentEvaluationError(
                                        "unexpected_readiness_policy"
                                    )
                                break
                        time.sleep(min(0.05, _remaining(deadline)))
                stage = "request"
                with client.stream(
                    "POST",
                    urls["chat"] + "/api/chat",
                    json={"messages": [{"role": "user", "content": case.prompt}]},
                    headers={"x-correlation-id": request_id},
                    timeout=_remaining(deadline),
                ) as response:
                    public["http_status"] = response.status_code
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        _remaining(deadline)
                        body.extend(chunk)
                        if len(body) > 65_536:
                            raise AgentEvaluationError("oversized_public_response")
                payload = json.loads(body)
                if public["http_status"] == 200:
                    answer = ChatResponse.model_validate(payload)
                    public["response"] = private_text(answer.message)
                    public["tools_used"] = answer.tools_used
                    if answer.policy_notice is not None:
                        public["error_rule"] = answer.policy_notice.rule
                elif public["http_status"] == 403:
                    error = payload["error"]
                    if (
                        not isinstance(error, dict)
                        or not isinstance(error.get("message"), str)
                        or error["code"] != "governance_denied"
                        or error["correlation_id"] != request_id
                    ):
                        raise AgentEvaluationError("unexpected_public_denial")
                    public["response"] = private_text(error["message"])
                    public["error_code"] = error["code"]
                    public["error_rule"] = error.get("details", {}).get("matched_rule")
                else:
                    raise AgentEvaluationError("public_chat_failure")
                stage = "shutdown"
            except TimeoutError:
                failure = f"{stage}_timeout"
            except httpx.HTTPError:
                failure = f"{stage}_transport_error"
            except (
                OSError,
                json.JSONDecodeError,
                ValidationError,
                KeyError,
                TypeError,
            ):
                failure = f"{stage}_protocol_error"
            except AgentEvaluationError as error:
                failure = str(error)
            finally:
                for role in reversed(processes):
                    exit_codes[role] = _stop(processes[role], deadline)
                    if exit_codes[role] != 0:
                        failure = failure or "abnormal_worker_exit"
                for role in processes:
                    path = work / f"{role}.json"
                    try:
                        if path.is_symlink() or path.stat().st_size > 1_048_576:
                            raise AgentEvaluationError("invalid_worker_capture")
                        captures[role] = AgentCapture.model_validate_json(
                            path.read_text()
                        )
                    except (OSError, ValidationError, AgentEvaluationError):
                        failure = failure or "missing_or_invalid_worker_capture"
                if (
                    set(captures) != {"chat", "mcp"}
                    or any(
                        not row.healthy or not row.complete for row in captures.values()
                    )
                    or not captures.get("chat")
                    or not captures["chat"].request_completed
                ):
                    failure = failure or "unhealthy_or_incomplete_capture"
    return AgentEvidence(
        case_id=case.case_id,
        request_id=request_id,
        manifest_digest=digest(manifest),
        collection_status="error" if failure else "completed",
        collection_error=failure,
        captures=captures,
        exit_codes=exit_codes,
        **public,
    )
