"""Phase 15 — CLI entrypoint for batch experiments.

Usage:
    python -m src.experiments.run_batch \\
        --batch-name my_batch \\
        --planner deterministic \\
        --scenarios baseline empty blocked \\
        --runs 1 \\
        --steps 1 \\
        --output-dir outputs/experiments/batches

No PyBullet.  No GUI.  Delegates entirely to run_batch_experiment().
"""

from __future__ import annotations

import argparse
import sys

from src.experiments.batch_runner import run_batch_experiment


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.experiments.run_batch",
        description="Run a batch of planner experiments (Phase 15).",
    )
    parser.add_argument(
        "--batch-name",
        default="phase15_batch",
        help="Identifier for this batch (default: phase15_batch)",
    )
    parser.add_argument(
        "--planner",
        nargs="+",
        default=["deterministic"],
        dest="planner_modes",
        help="Planner mode(s) to evaluate (default: deterministic)",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=["baseline", "empty", "blocked"],
        dest="scenario_names",
        help="Scenario name(s) to evaluate (default: baseline empty blocked)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        dest="runs_per_case",
        help="Number of repeated runs per (mode, scenario) pair (default: 1)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1,
        help="Number of pipeline steps per run (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/experiments/batches",
        dest="output_dir",
        help="Root directory for batch outputs",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        result = run_batch_experiment(
            batch_name=args.batch_name,
            planner_modes=tuple(args.planner_modes),
            scenario_names=tuple(args.scenario_names),
            runs_per_case=args.runs_per_case,
            steps=args.steps,
            output_dir=args.output_dir,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Batch: {result.batch_name}")
    print(f"Total runs:      {result.total_runs}")
    print(f"Successful runs: {result.successful_runs}")
    print(f"Failed runs:     {result.failed_runs}")
    print(f"summary.json:    {result.summary_json_path}")
    print(f"summary.csv:     {result.summary_csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
