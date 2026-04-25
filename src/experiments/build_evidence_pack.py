"""Phase 17 — CLI entrypoint for building the dissertation evidence pack.

Usage:
    python -m src.experiments.build_evidence_pack
    python -m src.experiments.build_evidence_pack \\
        --batch-summary outputs/experiments/batches/mybatch/summary.json \\
        --adversarial-summary outputs/experiments/adversarial/summary.json \\
        --output-dir outputs/evidence_pack

No PyBullet.  No GUI.  No live model inference.
Delegates entirely to build_evidence_pack().
"""

from __future__ import annotations

import argparse
import sys

from src.experiments.evidence_pack import build_evidence_pack


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.experiments.build_evidence_pack",
        description="Build dissertation evidence pack (Phase 17).",
    )
    parser.add_argument(
        "--batch-summary",
        default=None,
        dest="batch_summary_path",
        help="Explicit path to Phase 15 batch summary.json "
             "(default: auto-discover latest under outputs/experiments/batches/)",
    )
    parser.add_argument(
        "--adversarial-summary",
        default=None,
        dest="adversarial_summary_path",
        help="Explicit path to Phase 16 adversarial summary.json "
             "(default: auto-discover latest under outputs/experiments/adversarial/)",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/evidence_pack",
        dest="output_dir",
        help="Directory for evidence pack outputs (default: outputs/evidence_pack)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        result = build_evidence_pack(
            output_dir=args.output_dir,
            batch_summary_path=args.batch_summary_path,
            adversarial_summary_path=args.adversarial_summary_path,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"evidence_summary.json:   {result.evidence_summary_json_path}")
    print(f"evidence_summary.csv:    {result.evidence_summary_csv_path}")
    print(f"adversarial_summary.csv: {result.adversarial_summary_csv_path}")
    print(f"dissertation_metrics.md: {result.dissertation_metrics_md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
