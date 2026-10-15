"""Background local evaluation jobs backed by private on-disk results."""

from __future__ import annotations

import logging
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

import anyio
from pydantic import Field, model_validator

from ai_governance_harness.evaluation.artifacts import write_json
from ai_governance_harness.evaluation.collector import run_local
from ai_governance_harness.evaluation.evaluator import SHA256, StrictModel

logger = logging.getLogger(__name__)
RUN_ID = re.compile(r"\d{8}T\d{6}Z-[a-f0-9]{12}")
JOB_TIMEOUT_SECONDS = 90


class BaselineResult(StrictModel):
    row_id: Literal["baseline-allow", "baseline-deny"]
    request_id: str
    stage: str
    error: str | None
    child_exit_code: int | None
    score: Literal[0.0, 1.0] | None
    grader_error: str | None
    accepted: bool


class ControlResult(StrictModel):
    row_id: str
    control_id: str
    score: Literal[0.0, 1.0] | None
    error: str | None
    expected_error: str | None
    accepted: bool


class LocalResults(StrictModel):
    status: Literal["passed", "failed"]
    manifest_digest: str = Field(pattern=SHA256)
    baselines: list[BaselineResult]
    controls: list[ControlResult]

    @model_validator(mode="after")
    def validate_status(self) -> LocalResults:
        passed = (
            {row.row_id for row in self.baselines}
            == {"baseline-allow", "baseline-deny"}
            and len(self.baselines) == 2
            and all(row.accepted for row in self.baselines)
            and len(self.controls) == 18
            and all(row.accepted for row in self.controls)
        )
        if (self.status == "passed") != passed:
            raise ValueError("Saved evaluation status does not match its rows.")
        return self


class JobError(StrictModel):
    error: str


class EvaluationJob(StrictModel):
    run_id: str
    status: Literal["running", "passed", "failed", "error"]
    artifact: str
    results: LocalResults | None = None
    error: str | None = None


class LocalEvaluationJobs:
    """Run one evaluation at a time without altering the live governance engine."""

    def __init__(self, directory: Path, tasks: anyio.abc.TaskGroup) -> None:
        self.directory = directory.resolve()
        self._tasks = tasks
        self.active_run_id: str | None = None

    def start(self) -> EvaluationJob:
        if self.active_run_id is not None:
            return self.read(self.active_run_id)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}"
        self.active_run_id = run_id
        self._tasks.start_soon(self._run, run_id)
        return self.read(run_id)

    def read(self, run_id: str) -> EvaluationJob:
        if RUN_ID.fullmatch(run_id) is None:
            raise FileNotFoundError("Unknown evaluation run.")
        directory = self.directory / run_id
        if directory.is_symlink():
            raise FileNotFoundError("Unknown evaluation run.")
        job = EvaluationJob(
            run_id=run_id,
            status="running",
            artifact=f".local/evaluations/{run_id}/local-results.json",
        )
        if run_id == self.active_run_id:
            return job
        if not directory.is_dir():
            raise FileNotFoundError("Unknown evaluation run.")
        error_path = directory / "job-error.json"
        result_path = directory / "local-results.json"
        if error_path.exists():
            job.status = "error"
            job.error = JobError.model_validate_json(
                self._read_artifact(error_path)
            ).error
        elif result_path.exists():
            job.results = LocalResults.model_validate_json(
                self._read_artifact(result_path)
            )
            job.status = job.results.status
        else:
            job.status = "error"
            job.error = "Evaluation was interrupted or did not save a result."
        return job

    def latest(self) -> EvaluationJob | None:
        if self.active_run_id is not None:
            return self.read(self.active_run_id)
        run_ids: set[str] = set()
        if self.directory.exists():
            run_ids.update(
                path.name
                for path in self.directory.iterdir()
                if RUN_ID.fullmatch(path.name)
                and path.is_dir()
                and not path.is_symlink()
            )
        return self.read(max(run_ids)) if run_ids else None

    @staticmethod
    def _read_artifact(path: Path) -> str:
        if path.is_symlink() or path.stat().st_size > 256 * 1024:
            raise ValueError("Invalid evaluation result artifact.")
        return path.read_text(encoding="utf-8")

    def _save_error(self, run_id: str, message: str) -> None:
        directory = self.directory / run_id
        try:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            write_json(directory / "job-error.json", {"error": message})
        except OSError:
            logger.exception("Could not save evaluation job failure: %s", run_id)

    async def _run(self, run_id: str) -> None:
        try:
            with anyio.fail_after(JOB_TIMEOUT_SECONDS):
                await run_local(self.directory / run_id, timeout_seconds=30)
                # Read the persisted artifact, not just the runner's return value.
                LocalResults.model_validate_json(
                    self._read_artifact(self.directory / run_id / "local-results.json")
                )
        except TimeoutError:
            logger.error("Local evaluation timed out: %s", run_id)
            self._save_error(
                run_id, "Local evaluation exceeded its 90-second deadline."
            )
        except (OSError, ValueError, subprocess.SubprocessError):
            logger.exception("Local evaluation job failed: %s", run_id)
            self._save_error(
                run_id, "Local evaluation could not complete or save a valid result."
            )
        except anyio.get_cancelled_exc_class():
            self._save_error(run_id, "Evaluation was interrupted by server shutdown.")
            raise
        finally:
            self.active_run_id = None
