"""Phase 16 — Unit tests for adversarial_runner.

16 required tests.  No PyBullet.  No live Foundry Local.
"""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

import pytest

from src.experiments.adversarial_runner import (
    AdversarialEvaluationResult,
    run_adversarial_evaluation,
)


# ---------------------------------------------------------------------------
# Test 1 — runner creates output directory
# ---------------------------------------------------------------------------


def test_runner_creates_output_directory(tmp_path):
    result = run_adversarial_evaluation(
        scenario_name="baseline",
        output_dir=tmp_path / "adv",
    )
    assert result.output_dir.exists()
    assert result.output_dir.is_dir()


# ---------------------------------------------------------------------------
# Test 2 — runner creates summary.json
# ---------------------------------------------------------------------------


def test_runner_creates_summary_json(tmp_path):
    result = run_adversarial_evaluation(
        scenario_name="baseline",
        output_dir=tmp_path,
    )
    assert result.summary_json_path.exists()
    assert result.summary_json_path.suffix == ".json"


# ---------------------------------------------------------------------------
# Test 3 — runner creates summary.csv
# ---------------------------------------------------------------------------


def test_runner_creates_summary_csv(tmp_path):
    result = run_adversarial_evaluation(
        scenario_name="baseline",
        output_dir=tmp_path,
    )
    assert result.summary_csv_path.exists()
    assert result.summary_csv_path.suffix == ".csv"


# ---------------------------------------------------------------------------
# Test 4 — summary JSON includes required fields
# ---------------------------------------------------------------------------


def test_summary_json_has_required_fields(tmp_path):
    result = run_adversarial_evaluation(
        scenario_name="baseline",
        output_dir=tmp_path,
    )
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    for field in ("scenario_name", "total_cases", "safe_failures", "unsafe_passes", "cases"):
        assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Test 5 — summary CSV includes required columns
# ---------------------------------------------------------------------------


def test_summary_csv_has_required_columns(tmp_path):
    result = run_adversarial_evaluation(
        scenario_name="baseline",
        output_dir=tmp_path,
    )
    with result.summary_csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []

    required_cols = [
        "case_name",
        "description",
        "expected_safe_failure",
        "success",
        "safe_failure",
        "unsafe_pass",
        "error_count",
        "errors",
    ]
    for col in required_cols:
        assert col in columns, f"Missing CSV column: {col}"


# ---------------------------------------------------------------------------
# Test 6 — all required cases are evaluated
# ---------------------------------------------------------------------------


def test_all_required_cases_are_evaluated(tmp_path):
    from src.experiments.adversarial_cases import get_adversarial_cases

    expected_names = {c.name for c in get_adversarial_cases()}
    result = run_adversarial_evaluation(
        scenario_name="baseline",
        output_dir=tmp_path,
    )
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    evaluated_names = {c["case_name"] for c in data["cases"]}
    assert expected_names == evaluated_names


# ---------------------------------------------------------------------------
# Test 7 — malformed_json recorded as safe failure
# ---------------------------------------------------------------------------


def test_malformed_json_is_safe_failure(tmp_path):
    result = run_adversarial_evaluation(scenario_name="baseline", output_dir=tmp_path)
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    case = next(c for c in data["cases"] if c["case_name"] == "malformed_json")
    assert case["safe_failure"] is True
    assert case["unsafe_pass"] is False


# ---------------------------------------------------------------------------
# Test 8 — unknown_action_type recorded as safe failure
# ---------------------------------------------------------------------------


def test_unknown_action_type_is_safe_failure(tmp_path):
    result = run_adversarial_evaluation(scenario_name="baseline", output_dir=tmp_path)
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    case = next(c for c in data["cases"] if c["case_name"] == "unknown_action_type")
    assert case["safe_failure"] is True
    assert case["unsafe_pass"] is False


# ---------------------------------------------------------------------------
# Test 9 — missing_required_fields recorded as safe failure
# ---------------------------------------------------------------------------


def test_missing_required_fields_is_safe_failure(tmp_path):
    result = run_adversarial_evaluation(scenario_name="baseline", output_dir=tmp_path)
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    case = next(c for c in data["cases"] if c["case_name"] == "missing_required_fields")
    assert case["safe_failure"] is True
    assert case["unsafe_pass"] is False


# ---------------------------------------------------------------------------
# Test 10 — empty_response recorded as safe failure
# ---------------------------------------------------------------------------


def test_empty_response_is_safe_failure(tmp_path):
    result = run_adversarial_evaluation(scenario_name="baseline", output_dir=tmp_path)
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    case = next(c for c in data["cases"] if c["case_name"] == "empty_response")
    assert case["safe_failure"] is True
    assert case["unsafe_pass"] is False


# ---------------------------------------------------------------------------
# Test 11 — markdown_wrapped_json recorded as safe failure
# ---------------------------------------------------------------------------


def test_markdown_wrapped_json_is_safe_failure(tmp_path):
    result = run_adversarial_evaluation(scenario_name="baseline", output_dir=tmp_path)
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    case = next(c for c in data["cases"] if c["case_name"] == "markdown_wrapped_json")
    assert case["safe_failure"] is True
    assert case["unsafe_pass"] is False


# ---------------------------------------------------------------------------
# Test 12 — unsafe_target_coordinates safely rejected
# ---------------------------------------------------------------------------


def test_unsafe_target_coordinates_safely_rejected(tmp_path):
    result = run_adversarial_evaluation(scenario_name="baseline", output_dir=tmp_path)
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    case = next(c for c in data["cases"] if c["case_name"] == "unsafe_target_coordinates")
    assert case["safe_failure"] is True
    assert case["unsafe_pass"] is False


# ---------------------------------------------------------------------------
# Test 13 — unsafe_passes == 0
# ---------------------------------------------------------------------------


def test_unsafe_passes_is_zero(tmp_path):
    result = run_adversarial_evaluation(scenario_name="baseline", output_dir=tmp_path)
    assert result.unsafe_passes == 0
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    assert data["unsafe_passes"] == 0


# ---------------------------------------------------------------------------
# Test 14 — does not require Foundry Local
# ---------------------------------------------------------------------------


def test_does_not_require_foundry_local(tmp_path):
    # Passes without live server or FOUNDRY_LOCAL env vars
    result = run_adversarial_evaluation(scenario_name="empty", output_dir=tmp_path)
    assert isinstance(result, AdversarialEvaluationResult)


# ---------------------------------------------------------------------------
# Test 15 — runner does not import PyBullet/GUI
# ---------------------------------------------------------------------------


def test_adversarial_runner_has_no_pybullet_import():
    import importlib

    mod = importlib.import_module("src.experiments.adversarial_runner")
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
# Test 16 — existing model output is not repaired
# ---------------------------------------------------------------------------


def test_model_output_is_not_repaired(tmp_path):
    """Verify that a model response with a syntax error is recorded as-is,
    not silently repaired into a valid action."""
    result = run_adversarial_evaluation(scenario_name="baseline", output_dir=tmp_path)
    data = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    # The prose_before_json case has prose mixed into JSON — verify it was NOT parsed
    case = next(c for c in data["cases"] if c["case_name"] == "prose_before_json")
    assert case["success"] is False, "prose_before_json must not be repaired into a valid plan"
    assert case["safe_failure"] is True
