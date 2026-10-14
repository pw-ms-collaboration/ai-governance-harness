"""Background browser jobs for the existing managed agent evaluation CLI."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

import anyio
from pydantic import Field

from ai_governance_harness.chat.evaluations import RUN_ID
from ai_governance_harness.evaluation.agent_contracts import AgentEvaluationError
from ai_governance_harness.evaluation.agent_managed_contracts import (
    ManagedAgentResults,
    load_cases,
    load_pin,
    read_private_json,
)
from ai_governance_harness.evaluation.artifacts import write_json
from ai_governance_harness.evaluation.evaluator import StrictModel
from ai_governance_harness.evaluation.register_agent_evaluators import (
    _validate_endpoint,
)

logger = logging.getLogger(__name__)
RESOURCE_ID = r"^[A-Za-z0-9_.-]{1,256}$"


class ManagedEvaluationJob(StrictModel):
    run_id: str = Field(pattern=RUN_ID.pattern)
    status: Literal["running", "passed", "failed", "error", "cancelled"] = "running"
    eval_id: str | None = Field(default=None, pattern=RESOURCE_ID)
    foundry_run_id: str | None = Field(default=None, pattern=RESOURCE_ID)
    error: str | None = None


class ManagedEvaluationJobs:
    def __init__(
        self, directory: Path, tasks: anyio.abc.TaskGroup, target_deployment: str
    ) -> None:
        self.directory = directory.resolve() / "agent"
        self.tasks = tasks
        self.target_deployment = target_deployment
        self.job: ManagedEvaluationJob | None = None

    @property
    def active_run_id(self) -> str | None:
        return self.job.run_id if self.job and self.job.status == "running" else None

    def _save(self, job: ManagedEvaluationJob) -> None:
        suffix = "job" if job.status == "running" else "result"
        write_json(self.directory / f"{job.run_id}.browser-{suffix}.json", job)

    def start(self) -> ManagedEvaluationJob:
        if self.job and self.job.status == "running":
            return self.job.model_copy()
        endpoint = _validate_endpoint(os.getenv("AZURE_AI_PROJECT_ENDPOINT"))
        registry = os.getenv("AZURE_AI_EVALUATOR_REGISTRY", "").strip()
        judge = os.getenv("AZURE_AI_EVAL_JUDGE_DEPLOYMENT_NAME", "").strip()
        if not registry or not judge:
            raise AgentEvaluationError("managed_browser_configuration_required")
        try:
            load_pin(Path(registry), endpoint)
            cases = load_cases()
        except (OSError, ValueError) as error:
            logger.warning(
                "Managed evaluation preflight failed: %s", type(error).__name__
            )
            raise AgentEvaluationError(
                "invalid_managed_browser_configuration"
            ) from None
        if self.directory.is_symlink():
            raise AgentEvaluationError("invalid_browser_job_directory")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        job = ManagedEvaluationJob(
            run_id=f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}"
        )
        self._save(job)
        self.job = job
        self.tasks.start_soon(
            self._run, job, Path(registry), judge, endpoint, len(cases) * 60 + 630
        )
        return job.model_copy()

    def read(self, run_id: str) -> ManagedEvaluationJob:
        if not RUN_ID.fullmatch(run_id):
            raise FileNotFoundError("Unknown managed evaluation job.")
        if self.job and self.job.run_id == run_id:
            return self.job.model_copy()
        terminal = self.directory / f"{run_id}.browser-result.json"
        path = (
            terminal
            if terminal.exists()
            else self.directory / f"{run_id}.browser-job.json"
        )
        job = ManagedEvaluationJob.model_validate(read_private_json(path))
        if job.run_id != run_id:
            raise ValueError("Managed job identity mismatch.")
        if job.status == "running":
            job.status = "error"
            job.error = "Evaluation was interrupted. Check retained artifacts and Foundry before starting another run."
            self._save(job)
        return job

    def latest(self) -> ManagedEvaluationJob | None:
        if self.job:
            return self.job.model_copy()
        files = sorted(self.directory.glob("*.browser-job.json"))
        return (
            self.read(files[-1].name.removesuffix(".browser-job.json"))
            if files
            else None
        )

    def _command(
        self, run_id: str, registry: Path, judge: str, endpoint: str
    ) -> list[str]:
        return [
            sys.executable,
            "-m",
            "ai_governance_harness.evaluation",
            "agent-managed",
            "--registry",
            str(registry),
            "--target-deployment",
            self.target_deployment,
            "--judge-deployment",
            judge,
            "--endpoint",
            endpoint,
            "--output",
            str(self.directory / run_id),
            "--confirm-inference",
            "--confirm-submit",
        ]

    def _result(self, run_id: str) -> ManagedEvaluationJob:
        result = ManagedAgentResults.model_validate(
            read_private_json(self.directory / run_id / "managed-agent-results.json")
        )
        return ManagedEvaluationJob(
            run_id=run_id,
            status=result.status,
            eval_id=result.eval_id,
            foundry_run_id=result.foundry_run_id,
            error=result.error,
        )

    async def _run(
        self,
        job: ManagedEvaluationJob,
        registry: Path,
        judge: str,
        endpoint: str,
        timeout: float,
    ) -> None:
        process = None
        final_job = job.model_copy()
        try:
            with anyio.fail_after(timeout):
                process = await anyio.open_process(
                    self._command(job.run_id, registry, judge, endpoint),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                exit_code = await process.wait()
                if exit_code not in (0, 1):
                    raise ValueError("Managed evaluation runner did not complete.")
                final_job = self._result(job.run_id)
        except (OSError, ValueError, AgentEvaluationError, TimeoutError) as error:
            logger.warning("Managed evaluation job failed: %s", type(error).__name__)
            final_job.status = "error"
            final_job.error = "Evaluation could not complete or save a valid result. Check retained artifacts and Foundry before retrying."
        except anyio.get_cancelled_exc_class():
            final_job.status = "cancelled"
            final_job.error = "Evaluation was interrupted by server shutdown. Check Foundry before retrying."
            raise
        finally:
            with anyio.CancelScope(shield=True):
                if process is not None:
                    if process.returncode is None:
                        self._signal(process.pid, signal.SIGINT)
                        with anyio.move_on_after(10):
                            await process.wait()
                        if process.returncode is None:
                            self._signal(process.pid, signal.SIGKILL)
                            await process.wait()
                    await process.aclose()
                try:
                    self._save(final_job)
                except OSError as error:
                    logger.error(
                        "Managed evaluation status write failed: %s",
                        type(error).__name__,
                    )
                    final_job.status = "error"
                    final_job.error = "Evaluation status could not be saved. Check retained artifacts and Foundry before retrying."
                self.job = final_job

    @staticmethod
    def _signal(pid: int, signal_number: int) -> None:
        try:
            os.killpg(pid, signal_number)
        except ProcessLookupError:
            logger.info("Managed evaluation process already exited.")
