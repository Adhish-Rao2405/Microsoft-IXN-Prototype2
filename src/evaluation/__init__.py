"""Phase 8-9 evaluation package — deterministic experiment harness and exporters."""

from __future__ import annotations

from src.evaluation.experiment import ExperimentManifest, ExperimentRun
from src.evaluation.exporters import (
    experiment_run_to_dict,
    manifest_to_dict,
    result_to_summary_row,
    results_to_summary_rows,
    write_experiment_json,
    write_experiment_outputs,
    write_markdown_report,
    write_summary_csv,
)
from src.evaluation.harness import EvaluationHarness
from src.evaluation.metrics import compute_metrics
from src.evaluation.result_schema import EvaluationResult, EvaluationStepRecord
from src.evaluation.scenario import EvaluationScenario

__all__ = [
    "EvaluationHarness",
    "EvaluationResult",
    "EvaluationScenario",
    "EvaluationStepRecord",
    "ExperimentManifest",
    "ExperimentRun",
    "compute_metrics",
    "experiment_run_to_dict",
    "manifest_to_dict",
    "result_to_summary_row",
    "results_to_summary_rows",
    "write_experiment_json",
    "write_experiment_outputs",
    "write_markdown_report",
    "write_summary_csv",
]
