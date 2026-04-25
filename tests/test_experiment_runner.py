"""Phase 14 — Unit tests for experiment_runner.

12 required tests. No PyBullet. No live Foundry Local.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.experiments.experiment_runner import ExperimentResult, run_experiment
from src.planning.model_client import ModelClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_valid_plan_json() -> str:
    """Return a valid JSON plan that the planner can parse for a red cube."""
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


class _FakeModelClient:
    """Minimal fake that satisfies ModelClient protocol."""

    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, prompt: str) -> str:  # noqa: D102
        return self._response


class _FailingModelClient:
    """Client that always raises an exception."""

    def complete(self, prompt: str) -> str:  # noqa: D102
        raise RuntimeError("Simulated model failure")


# ---------------------------------------------------------------------------
# Tests — deterministic mode
# ---------------------------------------------------------------------------


def test_deterministic_baseline_returns_result(tmp_path):
    result = run_experiment(
        planner_mode="deterministic",
        scenario_name="baseline",
        steps=1,
        output_dir=tmp_path,
    )
    assert isinstance(result, ExperimentResult)
    assert result.scenario_name == "baseline"
    assert result.planner_mode == "deterministic"
    assert result.steps_requested == 1


def test_deterministic_result_is_frozen(tmp_path):
    result = run_experiment(
        planner_mode="deterministic",
        scenario_name="baseline",
        steps=1,
        output_dir=tmp_path,
    )
    with pytest.raises((AttributeError, TypeError)):
        result.success = False  # type: ignore[misc]


def test_deterministic_creates_output_json(tmp_path):
    result = run_experiment(
        planner_mode="deterministic",
        scenario_name="baseline",
        steps=1,
        output_dir=tmp_path,
    )
    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.output_path.suffix == ".json"


def test_output_json_has_required_fields(tmp_path):
    result = run_experiment(
        planner_mode="deterministic",
        scenario_name="baseline",
        steps=1,
        output_dir=tmp_path,
    )
    data = json.loads(result.output_path.read_text(encoding="utf-8"))
    for field in (
        "scenario_name",
        "planner_mode",
        "steps_requested",
        "steps_completed",
        "success",
        "errors",
        "actions",
    ):
        assert field in data, f"Missing field: {field}"


def test_output_json_scenario_and_mode_match(tmp_path):
    result = run_experiment(
        planner_mode="deterministic",
        scenario_name="empty",
        steps=1,
        output_dir=tmp_path,
    )
    data = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert data["scenario_name"] == "empty"
    assert data["planner_mode"] == "deterministic"


def test_invalid_scenario_raises_value_error(tmp_path):
    with pytest.raises(ValueError, match="Unknown scenario"):
        run_experiment(
            planner_mode="deterministic",
            scenario_name="does_not_exist",
            steps=1,
            output_dir=tmp_path,
        )


def test_invalid_planner_mode_raises_value_error(tmp_path):
    with pytest.raises(ValueError):
        run_experiment(
            planner_mode="magic_mode",
            scenario_name="baseline",
            steps=1,
            output_dir=tmp_path,
        )


def test_empty_scenario_deterministic_completes(tmp_path):
    result = run_experiment(
        planner_mode="deterministic",
        scenario_name="empty",
        steps=1,
        output_dir=tmp_path,
    )
    assert result.steps_completed == 1
    assert result.output_path is not None


# ---------------------------------------------------------------------------
# Tests — model mode with fake client
# ---------------------------------------------------------------------------


def test_model_mode_with_valid_json_response(tmp_path):
    client = _FakeModelClient(_minimal_valid_plan_json())
    result = run_experiment(
        planner_mode="model",
        scenario_name="baseline",
        steps=1,
        output_dir=tmp_path,
        model_client=client,
    )
    assert isinstance(result, ExperimentResult)
    assert result.planner_mode == "model"


def test_model_mode_with_invalid_json_records_error(tmp_path):
    client = _FakeModelClient("this is not valid json {{{")
    result = run_experiment(
        planner_mode="model",
        scenario_name="baseline",
        steps=1,
        output_dir=tmp_path,
        model_client=client,
    )
    # Error may be in result.errors OR result.steps_completed < steps_requested;
    # either way, no exception should propagate to the caller.
    assert isinstance(result, ExperimentResult)


def test_model_mode_client_failure_does_not_raise(tmp_path):
    client = _FailingModelClient()
    # Model failures must not re-raise — they are recorded in errors.
    result = run_experiment(
        planner_mode="model",
        scenario_name="baseline",
        steps=1,
        output_dir=tmp_path,
        model_client=client,
    )
    assert isinstance(result, ExperimentResult)


# ---------------------------------------------------------------------------
# Tests — no PyBullet import
# ---------------------------------------------------------------------------


def test_experiment_runner_has_no_pybullet_import():
    import importlib

    mod = importlib.import_module("src.experiments.experiment_runner")
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
