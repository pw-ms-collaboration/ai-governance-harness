"""Evaluation-only probes around unchanged chat and HTTP MCP entrypoints."""

from __future__ import annotations

import argparse
import dis
import inspect
import socket
import sys
import threading
from functools import partial
from pathlib import Path
from types import FrameType

import httpx
import httpx2
import uvicorn
from mcp import Client
from mcp.client.client import CallToolResult
from openai import DefaultHttpxClient
from openai.resources.chat.completions import Completions
from pydantic import ValidationError

from ai_governance_harness.chat import __main__ as chat_main
from ai_governance_harness.chat.service import ChatService
from ai_governance_harness.evaluation.agent_contracts import (
    AgentCapture,
    AgentEvaluationError,
    ReferenceFacts,
    ToolInvocation,
    private_text,
)
from ai_governance_harness.evaluation.artifacts import (
    FIXTURE_NAMES,
    build_versions,
    files_digest,
    write_json,
)
from ai_governance_harness.evaluation.evaluator import ObservedEvent
from ai_governance_harness.governance import get_governance_engine
from ai_governance_harness.governance.events import (
    GovernanceEvent,
    GovernanceEventStore,
)
from ai_governance_harness.mcp_server import __main__ as mcp_main
from ai_governance_harness.mcp_server.tools import SuperannuationDataGateway
from ai_governance_harness.identity import __main__ as identity_main


def _terminal(frame: FrameType) -> bool:
    return dis.opname[frame.f_code.co_code[frame.f_lasti]] not in {
        "YIELD_VALUE",
        "YIELD_FROM",
    }


class ExecutionObserver:
    def __init__(self, request_id: str, role: str) -> None:
        self.request_id = request_id
        self.role = role
        self.events: list[ObservedEvent] = []
        self.target_deployments: list[str] = []
        self.target_sequences: list[int] = []
        self.http_sequences: list[int] = []
        self.model_identities: list[str] = []
        self.model_revisions: list[str] = []
        self.tool_calls: list[ToolInvocation] = []
        self.operation_facts: list[ReferenceFacts] = []
        self.backend_executions = 0
        self.request_completed = False
        self.server_entered = False
        self.server_finished = False
        self._healthy = True
        self._startup = False
        self._shutdown = False
        self._stopping = False
        self._last_sequence = 0
        self._request_frames: set[FrameType] = set()
        self._tool_frames: dict[FrameType, int] = {}
        self._operation_code = inspect.unwrap(
            SuperannuationDataGateway.get_member_profile
        ).__code__
        self._event_code = GovernanceEventStore.record.__code__
        self._completion_code = inspect.unwrap(Completions.create).__code__
        self._send_codes = {
            httpx.Client.send.__code__,
            DefaultHttpxClient.send.__code__,
        }
        self._tool_code = inspect.unwrap(Client.call_tool).__code__
        self._request_code = ChatService.complete.__code__
        self._hook = self._observe

    def _append(self, destination: list, value: object, limit: int = 128) -> None:
        if len(destination) >= limit:
            self._healthy = False
        else:
            destination.append(value)

    def _model_identity(self, value: object) -> None:
        for name, destination in (
            ("model", self.model_identities),
            ("model_version", self.model_revisions),
        ):
            label = getattr(value, name, None)
            if label is not None:
                if not isinstance(label, str) or len(label) > 128:
                    self._healthy = False
                    continue
                try:
                    private_text(label)
                except AgentEvaluationError:
                    self._healthy = False
                else:
                    self._append(destination, label)

    def _observe(self, frame: FrameType, event: str, value: object) -> None:
        if not self._stopping and (
            (event == "c_call" and value is sys.setprofile)
            or (event == "call" and frame.f_code is threading.setprofile.__code__)
        ):
            self._healthy = False
        code = frame.f_code
        if code is self._request_code:
            if event == "call":
                self._request_frames.add(frame)
                self._healthy &= len(self._request_frames) == 1
            elif event == "return" and _terminal(frame):
                self.request_completed = True
        elif code is self._completion_code:
            if event == "call":
                deployment = frame.f_locals.get("model")
                if not isinstance(deployment, str):
                    self._healthy = False
                else:
                    self._append(self.target_deployments, deployment)
                self._append(self.target_sequences, self._last_sequence)
            elif event == "return" and value is not None:
                self._model_identity(value)
        elif code in self._send_codes and event == "call":
            request = frame.f_locals.get("request")
            if (
                isinstance(request, (httpx.Request, httpx2.Request))
                and request.method == "POST"
                and request.url.path.rstrip("/").endswith("/chat/completions")
            ):
                self._append(self.http_sequences, self._last_sequence)
        elif code is self._tool_code:
            if event == "call" and frame not in self._tool_frames:
                name = frame.f_locals.get("name")
                arguments = frame.f_locals.get("arguments")
                if len(self.tool_calls) >= 32:
                    self._healthy = False
                else:
                    try:
                        call = ToolInvocation(
                            name=name,
                            member_id_matches=arguments == {"member_id": "MEM-001"},
                            successful=None,
                        )
                    except ValidationError:
                        self._healthy = False
                    else:
                        self._tool_frames[frame] = len(self.tool_calls)
                        self.tool_calls.append(call)
            elif event == "return" and _terminal(frame) and frame in self._tool_frames:
                self.tool_calls[self._tool_frames[frame]].successful = (
                    not value.is_error if isinstance(value, CallToolResult) else False
                )
        elif code is self._operation_code:
            if event == "call":
                self.backend_executions += 1
            elif event == "return" and value is not None:
                try:
                    facts = ReferenceFacts.from_profile(value)
                except (ValidationError, AgentEvaluationError):
                    self._healthy = False
                else:
                    self._append(self.operation_facts, facts, 32)
        elif code is self._event_code and event == "return":
            if not isinstance(value, GovernanceEvent):
                self._healthy = False
                return
            if value.source == "mcp" and value.action == "agent.startup":
                self._startup = value.allowed
            elif value.source == "mcp" and value.action == "agent.shutdown":
                self._shutdown = value.allowed
            elif value.source in {"chat", "gateway"}:
                self._append(
                    self.events,
                    ObservedEvent(
                        **value.model_dump(
                            exclude={
                                "occurred_at",
                                "policy_name",
                                "provenance",
                                "evaluation_ms",
                            }
                        ),
                        request_id=self.request_id,
                    ),
                )
                if value.source == "chat":
                    self._last_sequence = value.sequence

    def install(self) -> None:
        if sys.getprofile() is not None or threading.getprofile() is not None:
            raise AgentEvaluationError("existing_worker_profile_hook")
        threading.setprofile(self._hook)
        sys.setprofile(self._hook)

    def finish(self, exit_code: int, fixture: Path) -> AgentCapture:
        healthy = (
            self._healthy
            and sys.getprofile() is self._hook
            and threading.getprofile() is self._hook
            and self.server_entered
            and all(
                self.http_sequences.count(sequence)
                >= self.target_sequences.count(sequence)
                for sequence in self.target_sequences
            )
        )
        versions = build_versions().model_copy(
            update={
                "fixture_digest": files_digest(fixture, FIXTURE_NAMES),
            }
        )
        capture = AgentCapture(
            role=self.role,
            request_id=self.request_id,
            policy_digest=get_governance_engine().policy_digest,
            versions=versions,
            healthy=healthy,
            complete=healthy
            and self.server_finished
            and exit_code == 0
            and (self.role == "chat" or (self._startup and self._shutdown)),
            request_completed=self.request_completed,
            events=sorted(self.events, key=lambda row: row.sequence),
            target_requests=len(self.target_sequences),
            target_http_attempts=len(self.http_sequences),
            target_deployments=self.target_deployments,
            target_request_event_sequences=self.target_sequences,
            target_http_event_sequences=self.http_sequences,
            target_model_identities=self.model_identities,
            target_model_revisions=self.model_revisions,
            tool_calls=self.tool_calls,
            backend_executions=self.backend_executions,
            operation_facts=self.operation_facts,
        )
        self._stopping = True
        sys.setprofile(None)
        threading.setprofile(None)
        return capture


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("identity", "chat", "mcp"), required=True)
    parser.add_argument("--socket-fd", type=int, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--confirm-inference", action="store_true")
    args = parser.parse_args()
    if args.role == "chat" and not args.confirm_inference:
        raise AgentEvaluationError("inference_confirmation_required")
    observer = (
        ExecutionObserver(args.request_id, args.role)
        if args.role != "identity"
        else None
    )
    exit_code = 1
    with socket.socket(fileno=args.socket_fd) as listener:
        original_run = uvicorn.run
        original_initialize = mcp_main.initialize_gateway

        def serve(app, **kwargs) -> None:
            server = uvicorn.Server(
                uvicorn.Config(
                    app,
                    log_config=None,
                    access_log=False,
                    timeout_graceful_shutdown=5,
                )
            )

            def stop() -> None:
                sys.stdin.buffer.readline()
                server.should_exit = True

            threading.Thread(target=stop, daemon=True).start()
            if observer is not None:
                observer.server_entered = True
            server.run(sockets=[listener])
            if observer is not None:
                observer.server_finished = True

        uvicorn.run = serve
        mcp_main.initialize_gateway = partial(original_initialize, args.fixture)
        if observer is not None:
            observer.install()
        try:
            entrypoint = {
                "chat": chat_main.main,
                "mcp": mcp_main.main,
                "identity": identity_main.main,
            }[args.role]
            exit_code = entrypoint()
            return exit_code
        finally:
            uvicorn.run = original_run
            mcp_main.initialize_gateway = original_initialize
            if observer is not None:
                write_json(args.capture, observer.finish(exit_code, args.fixture))


if __name__ == "__main__":
    sys.exit(main())
