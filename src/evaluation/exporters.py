"""Phase 9 — Experiment exporters.

Pure conversion functions and IO helpers that write evaluation results
to JSON, CSV, and Markdown. No LLM, no PyBullet, no timestamps, no UUIDs.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, List, Mapping, Sequence

from src.evaluation.experiment import ExperimentManifest, ExperimentRun
from src.evaluation.result_schema import EvaluationResult

# Fixed output file names (spec).
_JSON_FILENAME = "experiment_result.json"
_CSV_FILENAME = "summary.csv"
_MD_FILENAME = "report.md"

# Exact CSV column order (spec — must not change).
_CSV_COLUMNS = [
    "experiment_id",
    "scenario_id",
    "scenario_name",
    "success",
    "expected_success",
    "final_status",
    "total_steps",
    "total_candidate_actions",
    "total_validated_actions",
    "total_rejected_actions",
    "total_executed_actions",
    "rejection_rate",
    "validation_pass_rate",
    "execution_rate",
    "rejection_reasons",
]


# ---------------------------------------------------------------------------
# Pure conversion helpers
# ---------------------------------------------------------------------------


def manifest_to_dict(manifest: ExperimentManifest) -> dict[str, Any]:
    """Return a JSON-compatible dict for the manifest."""
    return manifest.to_dict()


def experiment_run_to_dict(run: ExperimentRun) -> dict[str, Any]:
    """Return a JSON-compatible dict for the full experiment run."""
    return run.to_dict()


def result_to_summary_row(
    result: EvaluationResult, *, experiment_id: str
) -> dict[str, Any]:
    """Return a summary row dict for a single EvaluationResult."""
    metrics = result.metrics
    return {
        "experiment_id": experiment_id,
        "scenario_id": result.scenario_id,
        "scenario_name": result.scenario_name,
        "success": result.success,
        "expected_success": result.expected_success,
        "final_status": result.final_status,
        "total_steps": result.total_steps,
        "total_candidate_actions": result.total_candidate_actions,
        "total_validated_actions": result.total_validated_actions,
        "total_rejected_actions": result.total_rejected_actions,
        "total_executed_actions": result.total_executed_actions,
        "rejection_rate": metrics.get("rejection_rate", 0.0),
        "validation_pass_rate": metrics.get("validation_pass_rate", 0.0),
        "execution_rate": metrics.get("execution_rate", 0.0),
        "rejection_reasons": "|".join(result.rejection_reasons),
    }


def results_to_summary_rows(
    results: Sequence[EvaluationResult], *, experiment_id: str
) -> list[dict[str, Any]]:
    """Return summary rows preserving input order."""
    return [result_to_summary_row(r, experiment_id=experiment_id) for r in results]


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_experiment_json(output_dir: Path | str, run: ExperimentRun) -> Path:
    """Write experiment_result.json to *output_dir*. Returns the file path."""
    out = _ensure_dir(Path(output_dir))
    payload = experiment_run_to_dict(run)
    text = json.dumps(payload, indent=2, sort_keys=True)
    path = out / _JSON_FILENAME
    path.write_text(text, encoding="utf-8")
    return path


def write_summary_csv(output_dir: Path | str, run: ExperimentRun) -> Path:
    """Write summary.csv to *output_dir*. Returns the file path."""
    out = _ensure_dir(Path(output_dir))
    rows = results_to_summary_rows(run.results, experiment_id=run.manifest.experiment_id)
    path = out / _CSV_FILENAME
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _format_metric(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def write_markdown_report(output_dir: Path | str, run: ExperimentRun) -> Path:
    """Write report.md to *output_dir*. Returns the file path."""
    out = _ensure_dir(Path(output_dir))
    m = run.manifest
    results = run.results

    total = len(results)
    passed = sum(1 for r in results if r.success)

    all_rejection_reasons: list[str] = []
    for r in results:
        all_rejection_reasons.extend(r.rejection_reasons)

    lines: list[str] = []

    # Title
    lines.append(f"# Experiment Report: {m.name}")
    lines.append("")

    # Metadata
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Experiment ID**: {m.experiment_id}")
    lines.append(f"- **Name**: {m.name}")
    lines.append(f"- **Description**: {m.description}")
    lines.append(f"- **Planner**: {m.planner_name}")
    lines.append(f"- **Pipeline**: {m.pipeline_name}")
    lines.append(f"- **Version**: {m.version}")
    if m.tags:
        lines.append(f"- **Tags**: {', '.join(m.tags)}")
    lines.append("")

    # Summary metrics
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Scenarios**: {total}")
    lines.append(f"- **Passed**: {passed}")
    lines.append(f"- **Failed**: {total - passed}")
    if total:
        lines.append(f"- **Pass rate**: {passed / total:.4f}")
    lines.append("")

    # Scenario table
    lines.append("## Scenario Results")
    lines.append("")
    header = "| scenario_id | scenario_name | success | final_status | rejection_rate |"
    lines.append(header)
    lines.append("|---|---|---|---|---|")
    for r in results:
        rr = _format_metric(r.metrics.get("rejection_rate", 0.0))
        lines.append(
            f"| {r.scenario_id} | {r.scenario_name} | {r.success} "
            f"| {r.final_status} | {rr} |"
        )
    lines.append("")

    # Rejection reasons
    lines.append("## Rejection Reasons")
    lines.append("")
    if all_rejection_reasons:
        unique_sorted = sorted(set(all_rejection_reasons))
        for reason in unique_sorted:
            count = all_rejection_reasons.count(reason)
            lines.append(f"- `{reason}` ({count})")
    else:
        lines.append("No rejected actions recorded.")
    lines.append("")

    # Notes
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "This report is generated deterministically from evaluation results. "
        "No timestamps or non-deterministic values are included."
    )
    lines.append("")

    path = out / _MD_FILENAME
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_experiment_outputs(
    output_dir: Path | str, run: ExperimentRun
) -> tuple[Path, ...]:
    """Write all three output files and return paths in fixed order: (json, csv, md)."""
    p_json = write_experiment_json(output_dir, run)
    p_csv = write_summary_csv(output_dir, run)
    p_md = write_markdown_report(output_dir, run)
    return (p_json, p_csv, p_md)
