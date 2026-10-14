"""Evaluation-only observation around the unchanged real stdio server."""

from __future__ import annotations

import argparse
import inspect
import json
import subprocess
import sys
import threading
from pathlib import Path
from types import FrameType

from ai_governance_harness.evaluation.artifacts import build_versions, write_json
from ai_governance_harness.evaluation.evaluator import (
    ACTION,
    BuildVersions,
    ObservedEvent,
    StrictModel,
)
from ai_governance_harness.governance.events import (
    GovernanceEvent,
    GovernanceEventStore,
)
from ai_governance_harness.mcp_server import __main__ as server
from ai_governance_harness.mcp_server.tools import SuperannuationDataGateway


class WorkerCapture(StrictModel):
    """Minimal observer state after the real server returns."""

    request_id: str
    events: list[ObservedEvent]
    backend_execution_count: int
    event_probe_ready: bool
    operation_probe_ready: bool
    events_complete: bool
    versions: BuildVersions


class WorkerReport(StrictModel):
    """Actual child exit status, recorded by a transparent stdio supervisor."""

    child_exit_code: int
    capture: WorkerCapture | None


class ExecutionObserver:
    """Observe original operation calls and actual recorded event returns."""

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        self.events: list[ObservedEvent] = []
        self.backend_execution_count = 0
        self._operation_code = inspect.unwrap(
            SuperannuationDataGateway.get_member_profile
        ).__code__
        self._event_code = GovernanceEventStore.record.__code__
        self._hook = self._observe
        self._recording_healthy = True
        self._startup_seen = False
        self._shutdown_seen = False
        self._thread_hooks_healthy = True

    def _observe(self, frame: FrameType, event: str, value: object) -> None:
        if frame.f_code is self._operation_code and event == "call":
            self.backend_execution_count += 1
        if frame.f_code is not self._event_code or event != "return":
            return
        self._thread_hooks_healthy &= sys.getprofile() is self._hook
        if not isinstance(value, GovernanceEvent):
            self._recording_healthy = False
            return
        if value.source == "mcp" and value.action == "agent.startup":
            self._startup_seen = True
        if value.source == "mcp" and value.action == "agent.shutdown":
            self._shutdown_seen = True
        if value.source == "gateway" and value.action == ACTION:
            self.events.append(
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
                )
            )

    def install(self) -> None:
        """Install before the server creates its execution threads."""
        if sys.getprofile() is not None or threading.getprofile() is not None:
            raise RuntimeError("Evaluation worker already has a profiling hook.")
        threading.setprofile(self._hook)
        sys.setprofile(self._hook)

    def finish(self, exit_code: int) -> WorkerCapture:
        """Verify hook health before removing this worker's own observers."""
        healthy = (
            sys.getprofile() is self._hook
            and threading.getprofile() is self._hook
            and self._thread_hooks_healthy
        )
        capture = WorkerCapture(
            request_id=self.request_id,
            events=sorted(self.events, key=lambda item: item.sequence),
            backend_execution_count=self.backend_execution_count,
            event_probe_ready=healthy
            and self._recording_healthy
            and self._startup_seen,
            operation_probe_ready=healthy,
            events_complete=(
                healthy
                and self._recording_healthy
                and self._startup_seen
                and self._shutdown_seen
                and exit_code == 0
            ),
            versions=build_versions(),
        )
        sys.setprofile(None)
        threading.setprofile(None)
        return capture


def main() -> int:
    """Run the observer child or supervise its actual process exit."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    capture_path = args.report.with_suffix(".capture.json")
    if args.child:
        observer = ExecutionObserver(args.request_id)
        observer.install()
        exit_code = 1
        try:
            exit_code = server.main()
            return exit_code
        finally:
            write_json(capture_path, observer.finish(exit_code))

    # Inherit the protocol pipes unchanged; the supervisor never reads profiles.
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ai_governance_harness.evaluation.worker",
            "--child",
            "--report",
            str(args.report),
            "--request-id",
            args.request_id,
        ],
        stderr=subprocess.DEVNULL,
    )
    exit_code = process.wait()
    capture = (
        WorkerCapture.model_validate(json.loads(capture_path.read_text()))
        if capture_path.is_file()
        else None
    )
    write_json(args.report, WorkerReport(child_exit_code=exit_code, capture=capture))
    return exit_code if exit_code >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
