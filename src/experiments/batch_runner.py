"""Phase 15 — Batch experiment runner.

Executes multiple Phase 14 run_experiment() calls across planner modes,
scenarios, and repeated runs, then writes summary JSON/CSV with descriptive
metrics.

No PyBullet.  No GUI.  No retries.  No JSON repair.  No fallback planner.
No duplicate pipeline logic.

Public API:
    run_batch_experiment(...)  -> BatchExperimentResult
    BatchExperimentResult      (frozen dataclass)
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.experiments.experiment_runner import run_experiment


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchExperimentResult:
    """Immutable result returned by run_batch_experiment()."""

    batch_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    output_dir: Path
    summary_json_path: Path
    summary_csv_path: Path


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------


def run_batch_experiment(
    batch_name: str = "phase15_batch",
    planner_modes: tuple[str, ...] = ("deterministic",),
    scenario_names: tuple[str, ...] = ("baseline", "empty", "blocked"),
    runs_per_case: int = 1,
    steps: int = 1,
    output_dir: str | Path = "outputs/experiments/batches",
    model_client: Any = None,
) -> BatchExperimentResult:
    """Run a batch of experiments across planner modes and scenarios.

    Delegates each individual run to Phase 14 ``run_experiment()``.
    Collects results and writes ``summary.json`` and ``summary.csv``
    to the batch output directory.

    Args:
        batch_name:     Identifier for this batch; used as directory name.
        planner_modes:  Tuple of planner mode strings to evaluate.
        scenario_names: Tuple of scenario names to evaluate.
        runs_per_case:  Number of repeated runs per (mode, scenario) pair.
        steps:          Steps per individual run (passed to run_experiment).
        output_dir:     Root directory for batch outputs.
        model_client:   Optional injected ModelClient for model mode tests.

    Returns:
        BatchExperimentResult with paths to all outputs.
    """
    batch_dir = Path(output_dir) / batch_name
    runs_dir = batch_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    cases: list[dict] = []

    for planner_mode in planner_modes:
        for scenario_name in scenario_names:
            for run_index in range(1, runs_per_case + 1):
                run_id = f"{planner_mode}_{scenario_name}_{run_index:03d}"
                case = _run_single(
                    run_id=run_id,
                    planner_mode=planner_mode,
                    scenario_name=scenario_name,
                    run_index=run_index,
                    steps=steps,
                    runs_dir=runs_dir,
                    model_client=model_client,
                )
                cases.append(case)

    metrics = _build_metrics(cases)

    successful = sum(1 for c in cases if c["success"])
    failed = len(cases) - successful

    summary_json_path = _write_summary_json(
        batch_dir=batch_dir,
        batch_name=batch_name,
        total_runs=len(cases),
        successful_runs=successful,
        failed_runs=failed,
        cases=cases,
        metrics=metrics,
    )

    summary_csv_path = _write_summary_csv(
        batch_dir=batch_dir,
        batch_name=batch_name,
        cases=cases,
    )

    return BatchExperimentResult(
        batch_name=batch_name,
        total_runs=len(cases),
        successful_runs=successful,
        failed_runs=failed,
        output_dir=batch_dir,
        summary_json_path=summary_json_path,
        summary_csv_path=summary_csv_path,
    )


# ---------------------------------------------------------------------------
# Single run helper
# ---------------------------------------------------------------------------


def _run_single(
    *,
    run_id: str,
    planner_mode: str,
    scenario_name: str,
    run_index: int,
    steps: int,
    runs_dir: Path,
    model_client: Any,
) -> dict:
    """Invoke run_experiment() for one case and return a case-record dict.

    ValueError from unknown scenario or invalid planner mode is re-raised
    immediately (consistent with Phase 14 semantics).

    All other exceptions are caught and recorded in the case record so the
    batch continues.
    """
    try:
        result = run_experiment(
            planner_mode=planner_mode,
            scenario_name=scenario_name,
            steps=steps,
            output_dir=runs_dir,
            model_client=model_client,
        )
    except ValueError:
        raise  # propagate invalid scenario / invalid mode immediately
    except Exception as exc:  # noqa: BLE001
        return {
            "run_id": run_id,
            "planner_mode": planner_mode,
            "scenario_name": scenario_name,
            "run_index": run_index,
            "steps_requested": steps,
            "steps_completed": 0,
            "success": False,
            "output_path": None,
            "error_count": 1,
            "errors": [str(exc)],
        }

    output_str = str(result.output_path) if result.output_path else None
    return {
        "run_id": run_id,
        "planner_mode": planner_mode,
        "scenario_name": scenario_name,
        "run_index": run_index,
        "steps_requested": result.steps_requested,
        "steps_completed": result.steps_completed,
        "success": result.success,
        "output_path": output_str,
        "error_count": len(result.errors),
        "errors": list(result.errors),
    }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _build_metrics(cases: list[dict]) -> dict:
    """Compute descriptive metrics from a list of case-record dicts.

    Handles empty input safely (all rates default to 0.0).
    """
    total = len(cases)
    if total == 0:
        return {
            "success_rate": 0.0,
            "failure_rate": 0.0,
            "success_by_planner": {},
            "success_by_scenario": {},
            "avg_steps_by_planner": {},
            "avg_steps_by_scenario": {},
        }

    successful = sum(1 for c in cases if c["success"])
    success_rate = successful / total
    failure_rate = 1.0 - success_rate

    # Group by planner
    planner_success: dict[str, list[bool]] = {}
    planner_steps: dict[str, list[int]] = {}
    for c in cases:
        mode = c["planner_mode"]
        planner_success.setdefault(mode, []).append(c["success"])
        planner_steps.setdefault(mode, []).append(c["steps_completed"])

    success_by_planner = {
        mode: sum(1 for v in vals if v) / len(vals)
        for mode, vals in planner_success.items()
    }
    avg_steps_by_planner = {
        mode: sum(vals) / len(vals)
        for mode, vals in planner_steps.items()
    }

    # Group by scenario
    scenario_success: dict[str, list[bool]] = {}
    scenario_steps: dict[str, list[int]] = {}
    for c in cases:
        name = c["scenario_name"]
        scenario_success.setdefault(name, []).append(c["success"])
        scenario_steps.setdefault(name, []).append(c["steps_completed"])

    success_by_scenario = {
        name: sum(1 for v in vals if v) / len(vals)
        for name, vals in scenario_success.items()
    }
    avg_steps_by_scenario = {
        name: sum(vals) / len(vals)
        for name, vals in scenario_steps.items()
    }

    return {
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "success_by_planner": success_by_planner,
        "success_by_scenario": success_by_scenario,
        "avg_steps_by_planner": avg_steps_by_planner,
        "avg_steps_by_scenario": avg_steps_by_scenario,
    }


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def _write_summary_json(
    *,
    batch_dir: Path,
    batch_name: str,
    total_runs: int,
    successful_runs: int,
    failed_runs: int,
    cases: list[dict],
    metrics: dict,
) -> Path:
    path = batch_dir / "summary.json"
    payload = {
        "batch_name": batch_name,
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "cases": cases,
        "metrics": metrics,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


_CSV_COLUMNS = (
    "batch_name",
    "run_id",
    "planner_mode",
    "scenario_name",
    "run_index",
    "steps_requested",
    "steps_completed",
    "success",
    "error_count",
    "output_path",
    "errors",
)


def _write_summary_csv(
    *,
    batch_dir: Path,
    batch_name: str,
    cases: list[dict],
) -> Path:
    path = batch_dir / "summary.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(_CSV_COLUMNS))
        writer.writeheader()
        for case in cases:
            row = {col: case.get(col, "") for col in _CSV_COLUMNS}
            # batch_name is not in per-case dict — inject it
            row["batch_name"] = batch_name
            # errors list → semicolon-joined string for CSV readability
            errors_val = row.get("errors", "")
            if isinstance(errors_val, list):
                row["errors"] = "; ".join(errors_val)
            writer.writerow(row)
    return path
