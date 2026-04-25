"""Phase 16 — CLI entrypoint for adversarial evaluation.

Usage:
    python -m src.experiments.run_adversarial --scenario baseline
    python -m src.experiments.run_adversarial --scenario empty --output-dir outputs/experiments/adversarial

No PyBullet.  No GUI.  Delegates entirely to run_adversarial_evaluation().
"""

from __future__ import annotations

import argparse
import sys

from src.experiments.adversarial_runner import run_adversarial_evaluation


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.experiments.run_adversarial",
        description="Run adversarial model-output evaluation (Phase 16).",
    )
    parser.add_argument(
        "--scenario",
        default="baseline",
        dest="scenario_name",
        help="Scenario name to evaluate against (default: baseline)",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/experiments/adversarial",
        dest="output_dir",
        help="Directory for summary outputs",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        result = run_adversarial_evaluation(
            scenario_name=args.scenario_name,
            output_dir=args.output_dir,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Total cases:   {result.total_cases}")
    print(f"Safe failures: {result.safe_failures}")
    print(f"Unsafe passes: {result.unsafe_passes}")
    print(f"summary.json:  {result.summary_json_path}")
    print(f"summary.csv:   {result.summary_csv_path}")
    return 0 if result.unsafe_passes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
