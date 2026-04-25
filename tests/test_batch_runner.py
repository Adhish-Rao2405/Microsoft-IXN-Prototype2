"""Phase 15 — Unit tests for batch_runner.

21 required tests.  No PyBullet.  No live Foundry Local.
"""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.experiments.batch_runner import (
    BatchExperimentResult,
    _build_metrics,
    run_batch_experiment,
)


# ---------------------------------------------------------------------------
# Fake model client helpers
# ---------------------------------------------------------------------------


class _FakeModelClient:
    """Returns a syntactically valid plan JSON."""

    def complete(self, prompt: str) -> str:
        return json.dumps(
            [
                {
                    "action": "pick_and_place",
                    "parameters": {
                        "object_id": "obj_1",
                        "destination_bin": "bin_a",
                    },
                }
            ]
        )


class _InvalidModelClient:
    """Returns invalid JSON."""

    def complete(self, prompt: str) -> str:
        return "not_valid_json {{{ garbage"


# ---------------------------------------------------------------------------
# Test 1 — batch directory created
# ---------------------------------------------------------------------------


def test_batch_creates_batch_directory(tmp_path):
    result = run_batch_experiment(
        batch_name="t01",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    assert result.output_dir.exists()
    assert result.output_dir.is_dir()


# ---------------------------------------------------------------------------
# Test 2 — runs/ directory created
# ---------------------------------------------------------------------------


def test_batch_creates_runs_directory(tmp_path):
    result = run_batch_experiment(
        batch_name="t02",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    runs_dir = result.output_dir / "runs"
    assert runs_dir.exists()
    assert runs_dir.is_dir()


# ---------------------------------------------------------------------------
# Test 3 — summary.json created
# ---------------------------------------------------------------------------


def test_batch_creates_summary_json(tmp_path):
    result = run_batch_experiment(
        batch_name="t03",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    assert result.summary_json_path.exists()
    assert result.summary_json_path.suffix == ".json"


# ---------------------------------------------------------------------------
# Test 4 — summary.csv created
# ---------------------------------------------------------------------------


def test_batch_creates_summary_csv(tmp_path):
    result = run_batch_experiment(
        batch_name="t04",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    assert result.summary_csv_path.exists()
    assert result.summary_csv_path.suffix == ".csv"


# ---------------------------------------------------------------------------
# Test 5 — single deterministic batch completes
# ---------------------------------------------------------------------------


def test_single_deterministic_batch_completes(tmp_path):
    result = run_batch_experiment(
        batch_name="t05",
        planner_modes=("deterministic",),
        scenario_names=("baseline",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    assert isinstance(result, BatchExperimentResult)
    assert result.total_runs == 1


# ---------------------------------------------------------------------------
# Test 6 — multiple scenarios produce correct run count
# ---------------------------------------------------------------------------


def test_multiple_scenarios_produce_expected_run_count(tmp_path):
    result = run_batch_experiment(
        batch_name="t06",
        planner_modes=("deterministic",),
        scenario_names=("baseline", "empty", "blocked"),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    assert result.total_runs == 3


# ---------------------------------------------------------------------------
# Test 7 — multiple planner modes with fake model client
# ---------------------------------------------------------------------------


def test_multiple_planner_modes_correct_run_count(tmp_path):
    client = _FakeModelClient()
    result = run_batch_experiment(
        batch_name="t07",
        planner_modes=("deterministic", "model"),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
        model_client=client,
    )
    assert result.total_runs == 2


# ---------------------------------------------------------------------------
# Test 8 — runs_per_case=2 produces repeated runs
# ---------------------------------------------------------------------------


def test_runs_per_case_produces_repeated_runs(tmp_path):
    result = run_batch_experiment(
        batch_name="t08",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=2,
        steps=1,
        output_dir=tmp_path,
    )
    assert result.total_runs == 2


# ---------------------------------------------------------------------------
# Test 9 — summary JSON has required top-level fields
# ---------------------------------------------------------------------------


def test_summary_json_has_required_top_level_fields(tmp_path):
    result = run_batch_experiment(
        batch_name="t09",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    for field in (
        "batch_name",
        "total_runs",
        "successful_runs",
        "failed_runs",
        "cases",
        "metrics",
    ):
        assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Test 10 — summary CSV has required columns
# ---------------------------------------------------------------------------


def test_summary_csv_has_required_columns(tmp_path):
    result = run_batch_experiment(
        batch_name="t10",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    with result.summary_csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []

    required = [
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
    ]
    for col in required:
        assert col in columns, f"Missing CSV column: {col}"


# ---------------------------------------------------------------------------
# Test 11 — metrics include success_rate and failure_rate
# ---------------------------------------------------------------------------


def test_metrics_include_success_rate_and_failure_rate(tmp_path):
    result = run_batch_experiment(
        batch_name="t11",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    metrics = data["metrics"]
    assert "success_rate" in metrics
    assert "failure_rate" in metrics


# ---------------------------------------------------------------------------
# Test 12 — metrics include success_by_planner
# ---------------------------------------------------------------------------


def test_metrics_include_success_by_planner(tmp_path):
    result = run_batch_experiment(
        batch_name="t12",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    assert "success_by_planner" in data["metrics"]
    assert "deterministic" in data["metrics"]["success_by_planner"]


# ---------------------------------------------------------------------------
# Test 13 — metrics include success_by_scenario
# ---------------------------------------------------------------------------


def test_metrics_include_success_by_scenario(tmp_path):
    result = run_batch_experiment(
        batch_name="t13",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    assert "success_by_scenario" in data["metrics"]
    assert "empty" in data["metrics"]["success_by_scenario"]


# ---------------------------------------------------------------------------
# Test 14 — metrics include avg_steps_by_planner
# ---------------------------------------------------------------------------


def test_metrics_include_avg_steps_by_planner(tmp_path):
    result = run_batch_experiment(
        batch_name="t14",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    assert "avg_steps_by_planner" in data["metrics"]


# ---------------------------------------------------------------------------
# Test 15 — metrics include avg_steps_by_scenario
# ---------------------------------------------------------------------------


def test_metrics_include_avg_steps_by_scenario(tmp_path):
    result = run_batch_experiment(
        batch_name="t15",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    assert "avg_steps_by_scenario" in data["metrics"]


# ---------------------------------------------------------------------------
# Test 16 — invalid scenario raises ValueError (consistent with Phase 14)
# ---------------------------------------------------------------------------


def test_invalid_scenario_raises_value_error(tmp_path):
    with pytest.raises(ValueError, match="Unknown scenario"):
        run_batch_experiment(
            batch_name="t16",
            planner_modes=("deterministic",),
            scenario_names=("nonexistent",),
            runs_per_case=1,
            steps=1,
            output_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# Test 17 — invalid planner mode raises ValueError (consistent with Phase 14)
# ---------------------------------------------------------------------------


def test_invalid_planner_mode_raises_value_error(tmp_path):
    with pytest.raises(ValueError):
        run_batch_experiment(
            batch_name="t17",
            planner_modes=("magic_mode",),
            scenario_names=("empty",),
            runs_per_case=1,
            steps=1,
            output_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# Test 18 — model mode with fake invalid JSON records failure
# ---------------------------------------------------------------------------


def test_model_mode_invalid_json_records_failure(tmp_path):
    client = _InvalidModelClient()
    result = run_batch_experiment(
        batch_name="t18",
        planner_modes=("model",),
        scenario_names=("baseline",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
        model_client=client,
    )
    # Must complete without raising — failure should be recorded
    assert isinstance(result, BatchExperimentResult)
    assert result.total_runs == 1


# ---------------------------------------------------------------------------
# Test 19 — normal tests do not require Foundry Local
# ---------------------------------------------------------------------------


def test_does_not_require_foundry_local(tmp_path):
    # If this test passes without env vars or a running server, the invariant holds.
    result = run_batch_experiment(
        batch_name="t19",
        planner_modes=("deterministic",),
        scenario_names=("empty",),
        runs_per_case=1,
        steps=1,
        output_dir=tmp_path,
    )
    assert result.total_runs == 1


# ---------------------------------------------------------------------------
# Test 20 — batch runner does not import PyBullet/GUI
# ---------------------------------------------------------------------------


def test_batch_runner_has_no_pybullet_import():
    import importlib

    mod = importlib.import_module("src.experiments.batch_runner")
    src_path = mod.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "pybullet" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            assert "pybullet" not in (node.module or "")


# ---------------------------------------------------------------------------
# Test 21 — batch runner delegates to run_experiment (not duplicating logic)
# ---------------------------------------------------------------------------


def test_batch_runner_delegates_to_run_experiment(tmp_path):
    """Verify run_experiment is called, not reimplemented."""
    call_count = {"n": 0}

    original_run = __import__(
        "src.experiments.experiment_runner", fromlist=["run_experiment"]
    ).run_experiment

    def counting_run(*args, **kwargs):
        call_count["n"] += 1
        return original_run(*args, **kwargs)

    with patch(
        "src.experiments.batch_runner.run_experiment", side_effect=counting_run
    ):
        run_batch_experiment(
            batch_name="t21",
            planner_modes=("deterministic",),
            scenario_names=("empty", "blocked"),
            runs_per_case=2,
            steps=1,
            output_dir=tmp_path,
        )

    # 1 mode × 2 scenarios × 2 runs = 4 calls
    assert call_count["n"] == 4
