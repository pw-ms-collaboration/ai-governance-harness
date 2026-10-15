"""Command-line entrypoint for synthetic governance enforcement evaluation."""

from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import anyio
from pydantic import ValidationError

from ai_governance_harness.evaluation.agent_contracts import (
    DEFAULT_PROMPTS,
    DEFAULT_RUBRIC,
    AgentEvaluationError,
)
from ai_governance_harness.evaluation.agent_runner import run_agent
from ai_governance_harness.evaluation.agent_managed import (
    retrieve_agent_managed,
    run_agent_managed,
)
from ai_governance_harness.evaluation.collector import run_local
from ai_governance_harness.evaluation.foundry import run_managed
from ai_governance_harness.evals.runner import DEFAULT_DATASET


def main() -> int:
    """Create a fresh local evidence bundle and report exact acceptance."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    local = commands.add_parser("local", help="Run the real allow/deny stdio cases")
    local.add_argument("--output", type=Path)
    local.add_argument("--timeout", type=float, default=30.0)
    managed = commands.add_parser(
        "managed", help="Register and grade a local bundle in Foundry"
    )
    managed.add_argument("--input", type=Path, required=True)
    managed.add_argument("--output", type=Path)
    managed.add_argument("--endpoint", default=os.getenv("AZURE_AI_PROJECT_ENDPOINT"))
    managed.add_argument(
        "--deployment", default=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    )
    managed.add_argument("--timeout", type=float, default=600.0)
    managed.add_argument("--confirm-submit", action="store_true")
    agent = commands.add_parser(
        "agent", help="Run the real governed agent and a separate live response judge"
    )
    agent.add_argument("--dataset", type=Path, default=DEFAULT_PROMPTS)
    agent.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    agent.add_argument("--target-deployment", required=True)
    agent.add_argument("--judge-deployment", required=True)
    agent.add_argument("--endpoint", default=os.getenv("AZURE_AI_PROJECT_ENDPOINT"))
    agent.add_argument(
        "--output", type=Path, help="Fresh directory under an agent folder"
    )
    agent.add_argument("--timeout", type=float, default=60.0)
    agent.add_argument("--confirm-inference", action="store_true")
    behavior = commands.add_parser(
        "agent-managed",
        help="Run reviewed dataset scenarios locally and score with Governance behavior match",
    )
    behavior.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    behavior.add_argument(
        "--registry",
        type=Path,
        required=True,
        help="Verified behavior evaluator registration directory",
    )
    behavior.add_argument("--target-deployment", required=True)
    behavior.add_argument("--judge-deployment", required=True)
    behavior.add_argument("--endpoint", default=os.getenv("AZURE_AI_PROJECT_ENDPOINT"))
    behavior.add_argument(
        "--output", type=Path, help="Fresh directory under an agent folder"
    )
    behavior.add_argument(
        "--timeout", type=float, default=60.0, help="Collection deadline per case"
    )
    behavior.add_argument(
        "--managed-timeout",
        type=float,
        default=600.0,
        help="Total submission/retrieval deadline",
    )
    behavior.add_argument("--confirm-inference", action="store_true")
    behavior.add_argument("--confirm-submit", action="store_true")
    retrieval = commands.add_parser(
        "agent-managed-results",
        help="Retrieve a saved managed agent run without repeating execution or submission",
    )
    retrieval.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Saved checkpoint-run-created.json or checkpoint-retrieved.json",
    )
    retrieval.add_argument("--endpoint", default=os.getenv("AZURE_AI_PROJECT_ENDPOINT"))
    retrieval.add_argument(
        "--output", type=Path, help="Fresh directory under an agent folder"
    )
    retrieval.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    if args.command in {"agent-managed", "agent-managed-results"}:
        directory = args.output or (
            Path(".local/evaluations/agent")
            / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}"
        )
        try:
            if args.command == "agent-managed":
                results = run_agent_managed(
                    directory,
                    registry=args.registry,
                    dataset=args.dataset,
                    target_deployment=args.target_deployment,
                    judge_deployment=args.judge_deployment,
                    endpoint=args.endpoint,
                    timeout_seconds=args.timeout,
                    managed_timeout_seconds=args.managed_timeout,
                    confirm_inference=args.confirm_inference,
                    confirm_submit=args.confirm_submit,
                )
            else:
                results = retrieve_agent_managed(
                    args.input,
                    directory,
                    endpoint=args.endpoint,
                    timeout_seconds=args.timeout,
                )
        except AgentEvaluationError as error:
            print(f"Managed agent evaluation blocked: {error}.", file=sys.stderr)
            return 2
        except (OSError, ValidationError) as error:
            print(
                f"Managed agent artifact/configuration error ({type(error).__name__}).",
                file=sys.stderr,
            )
            return 2
        print(
            f"Managed agent evaluation {results.status}: {directory / 'managed-agent-results.json'}"
        )
        if results.status == "cancelled":
            return 130
        return 0 if results.status == "passed" else 1
    if args.command == "agent":
        directory = args.output or (
            Path(".local/evaluations/agent")
            / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}"
        )
        try:
            results = run_agent(
                directory,
                dataset=args.dataset,
                rubric_path=args.rubric,
                target_deployment=args.target_deployment,
                judge_deployment=args.judge_deployment,
                endpoint=args.endpoint,
                timeout_seconds=args.timeout,
                confirm_inference=args.confirm_inference,
            )
        except AgentEvaluationError as error:
            print(f"Agent evaluation blocked: {error}.", file=sys.stderr)
            return 2
        except (OSError, ValidationError) as error:
            print(
                f"Agent artifact/configuration error ({type(error).__name__}).",
                file=sys.stderr,
            )
            return 2
        print(f"Agent evaluation {results.status}: {directory / 'agent-results.json'}")
        if results.status == "cancelled":
            return 130
        return 0 if results.status == "passed" else 1
    if args.command == "managed":
        directory = args.output or (args.input / f"managed-{uuid4().hex[:12]}")
        try:
            results = run_managed(
                args.input,
                directory,
                endpoint=args.endpoint,
                deployment=args.deployment,
                confirm_submit=args.confirm_submit,
                timeout_seconds=args.timeout,
            )
        except OSError as error:
            print(f"Managed artifact error ({type(error).__name__}).", file=sys.stderr)
            return 2
        print(
            f"Managed evaluation {results['status']}: {directory / 'managed-results.json'}"
        )
        return 0 if results["status"] == "passed" else 1
    directory = args.output or (
        Path(".local/evaluations")
        / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}"
    )
    try:

        async def collect() -> dict[str, object]:
            return await run_local(directory, timeout_seconds=args.timeout)

        results = anyio.run(collect)
    except (OSError, ValidationError) as error:
        print(f"Evaluation artifact error ({type(error).__name__}).", file=sys.stderr)
        return 2
    print(f"Local evaluation {results['status']}: {directory}")
    return 0 if results["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
