"""Tests for Phase 9 exporters — JSON, CSV, Markdown.

Uses hand-built EvaluationResult objects. No real pipeline, no PyBullet.
"""

from __future__ import annotations

import ast
import csv
import json
import re
from pathlib import Path

import pytest

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
from src.evaluation.result_schema import EvaluationResult, EvaluationStepRecord

# ---------------------------------------------------------------------------
# Required CSV column order (from spec)
# ---------------------------------------------------------------------------

REQUIRED_CSV_COLUMNS = [
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
# Helpers
# ---------------------------------------------------------------------------


def _step() -> EvaluationStepRecord:
    return EvaluationStepRecord(
        step_index=0,
        state_before={},
        candidate_action_count=2,
        validated_action_count=2,
        rejected_action_count=0,
        executed_action_count=2,
        rejection_reasons=(),
        executor_status="executed",
        state_after={},
    )


def _result(
    scenario_id: str = "s001",
    scenario_name: str = "Test scenario",
    success: bool = True,
    rejection_reasons: tuple[str, ...] = (),
    total_candidate: int = 2,
    total_validated: int = 2,
    total_rejected: int = 0,
    total_executed: int = 2,
) -> EvaluationResult:
    return EvaluationResult(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        success=success,
        expected_success=True,
        total_steps=1,
        total_candidate_actions=total_candidate,
        total_validated_actions=total_validated,
        total_rejected_actions=total_rejected,
        total_executed_actions=total_executed,
        rejection_reasons=rejection_reasons,
        final_status="executed" if success else "rejected",
        step_records=(_step(),),
        metrics={
            "rejection_rate": total_rejected / total_candidate if total_candidate else 0.0,
            "validation_pass_rate": total_validated / total_candidate if total_candidate else 0.0,
            "execution_rate": total_executed / total_validated if total_validated else 0.0,
        },
    )


def _manifest(scenario_ids: tuple[str, ...] = ("s001", "s002")) -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id="exp_001",
        name="Phase 9 baseline",
        description="Deterministic output test.",
        scenario_ids=scenario_ids,
        planner_name="WorkcellPlanner",
        pipeline_name="WorkcellPipeline",
        version="prototype-2.1",
        tags=("test",),
    )


def _run(manifest: ExperimentManifest | None = None) -> ExperimentRun:
    m = manifest or _manifest()
    results = tuple(_result(sid) for sid in m.scenario_ids)
    return ExperimentRun(manifest=m, results=results)


# ---------------------------------------------------------------------------
# Pure conversion functions
# ---------------------------------------------------------------------------


class TestManifestToDict:
    def test_returns_json_compatible_dict(self) -> None:
        d = manifest_to_dict(_manifest())
        json.dumps(d)

    def test_has_all_required_keys(self) -> None:
        d = manifest_to_dict(_manifest())
        for key in ("experiment_id", "name", "description", "scenario_ids",
                    "planner_name", "pipeline_name", "version", "tags"):
            assert key in d


class TestExperimentRunToDict:
    def test_returns_json_compatible_dict(self) -> None:
        d = experiment_run_to_dict(_run())
        json.dumps(d)

    def test_has_manifest_and_results_keys(self) -> None:
        d = experiment_run_to_dict(_run())
        assert "manifest" in d
        assert "results" in d

    def test_results_is_list(self) -> None:
        d = experiment_run_to_dict(_run())
        assert isinstance(d["results"], list)


class TestResultToSummaryRow:
    def test_contains_all_required_columns(self) -> None:
        row = result_to_summary_row(_result(), experiment_id="exp_001")
        for col in REQUIRED_CSV_COLUMNS:
            assert col in row, f"Missing column: {col}"

    def test_scenario_id_correct(self) -> None:
        row = result_to_summary_row(_result(scenario_id="sc42"), experiment_id="exp_x")
        assert row["scenario_id"] == "sc42"

    def test_experiment_id_injected(self) -> None:
        row = result_to_summary_row(_result(), experiment_id="exp_999")
        assert row["experiment_id"] == "exp_999"

    def test_success_value(self) -> None:
        row = result_to_summary_row(_result(success=True), experiment_id="e")
        assert row["success"] in (True, "True", "true", 1)

    def test_rejection_rate_present(self) -> None:
        row = result_to_summary_row(
            _result(total_candidate=4, total_rejected=2), experiment_id="e"
        )
        assert float(row["rejection_rate"]) == pytest.approx(0.5)

    def test_no_timestamp_or_uuid_in_row(self) -> None:
        row = result_to_summary_row(_result(), experiment_id="exp_001")
        row_str = str(row)
        # No ISO timestamp pattern
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", row_str)


class TestResultsToSummaryRows:
    def test_preserves_order(self) -> None:
        ids = ["s003", "s001", "s002"]
        results = [_result(sid) for sid in ids]
        rows = results_to_summary_rows(results, experiment_id="exp_001")
        assert [r["scenario_id"] for r in rows] == ids

    def test_length_matches_input(self) -> None:
        results = [_result(f"s{i:03d}") for i in range(5)]
        rows = results_to_summary_rows(results, experiment_id="e")
        assert len(rows) == 5


# ---------------------------------------------------------------------------
# IO: JSON
# ---------------------------------------------------------------------------


class TestWriteExperimentJson:
    def test_creates_experiment_result_json(self, tmp_path: Path) -> None:
        write_experiment_json(tmp_path, _run())
        assert (tmp_path / "experiment_result.json").exists()

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        write_experiment_json(tmp_path, _run())
        content = (tmp_path / "experiment_result.json").read_text(encoding="utf-8")
        json.loads(content)

    def test_output_is_deterministic(self, tmp_path: Path) -> None:
        run = _run()
        write_experiment_json(tmp_path, run)
        first = (tmp_path / "experiment_result.json").read_text(encoding="utf-8")
        write_experiment_json(tmp_path, run)
        second = (tmp_path / "experiment_result.json").read_text(encoding="utf-8")
        assert first == second

    def test_keys_are_sorted(self, tmp_path: Path) -> None:
        write_experiment_json(tmp_path, _run())
        content = (tmp_path / "experiment_result.json").read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert list(parsed.keys()) == sorted(parsed.keys())

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "new_subdir"
        assert not target.exists()
        write_experiment_json(target, _run())
        assert (target / "experiment_result.json").exists()

    def test_no_timestamp_in_json(self, tmp_path: Path) -> None:
        write_experiment_json(tmp_path, _run())
        content = (tmp_path / "experiment_result.json").read_text(encoding="utf-8")
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", content)

    def test_returns_path(self, tmp_path: Path) -> None:
        p = write_experiment_json(tmp_path, _run())
        assert isinstance(p, Path)
        assert p.name == "experiment_result.json"


# ---------------------------------------------------------------------------
# IO: CSV
# ---------------------------------------------------------------------------


class TestWriteSummaryCsv:
    def test_creates_summary_csv(self, tmp_path: Path) -> None:
        write_summary_csv(tmp_path, _run())
        assert (tmp_path / "summary.csv").exists()

    def test_header_order_is_exact(self, tmp_path: Path) -> None:
        write_summary_csv(tmp_path, _run())
        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames is not None
            assert list(reader.fieldnames) == REQUIRED_CSV_COLUMNS

    def test_row_count_matches_scenario_count(self, tmp_path: Path) -> None:
        m = _manifest(scenario_ids=("s001", "s002", "s003"))
        run = ExperimentRun(manifest=m, results=tuple(_result(sid) for sid in m.scenario_ids))
        write_summary_csv(tmp_path, run)
        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3

    def test_rows_preserve_scenario_order(self, tmp_path: Path) -> None:
        m = _manifest(scenario_ids=("s003", "s001", "s002"))
        run = ExperimentRun(manifest=m, results=tuple(_result(sid) for sid in m.scenario_ids))
        write_summary_csv(tmp_path, run)
        with open(tmp_path / "summary.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert [r["scenario_id"] for r in rows] == ["s003", "s001", "s002"]

    def test_output_is_deterministic(self, tmp_path: Path) -> None:
        run = _run()
        write_summary_csv(tmp_path, run)
        first = (tmp_path / "summary.csv").read_text(encoding="utf-8")
        write_summary_csv(tmp_path, run)
        second = (tmp_path / "summary.csv").read_text(encoding="utf-8")
        assert first == second

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "output"
        write_summary_csv(target, _run())
        assert (target / "summary.csv").exists()

    def test_returns_path(self, tmp_path: Path) -> None:
        p = write_summary_csv(tmp_path, _run())
        assert isinstance(p, Path)
        assert p.name == "summary.csv"


# ---------------------------------------------------------------------------
# IO: Markdown
# ---------------------------------------------------------------------------


class TestWriteMarkdownReport:
    def test_creates_report_md(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        assert (tmp_path / "report.md").exists()

    def test_contains_experiment_id(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert "exp_001" in content

    def test_contains_planner_name(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert "WorkcellPlanner" in content

    def test_contains_pipeline_name(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert "WorkcellPipeline" in content

    def test_contains_scenario_table(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        # Markdown table has | delimiters
        assert "|" in content
        assert "s001" in content

    def test_contains_notes_section(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert "Notes" in content

    def test_output_is_deterministic(self, tmp_path: Path) -> None:
        run = _run()
        write_markdown_report(tmp_path, run)
        first = (tmp_path / "report.md").read_text(encoding="utf-8")
        write_markdown_report(tmp_path, run)
        second = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert first == second

    def test_no_timestamp_in_report(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", content)

    def test_contains_rejection_reasons_section(self, tmp_path: Path) -> None:
        m = _manifest(scenario_ids=("s001",))
        r = _result("s001", rejection_reasons=("no_object_held",), success=False,
                    total_rejected=1)
        run = ExperimentRun(manifest=m, results=(r,))
        write_markdown_report(tmp_path, run)
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert "no_object_held" in content

    def test_no_rejection_reasons_message_when_none(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert "No rejected actions" in content

    def test_returns_path(self, tmp_path: Path) -> None:
        p = write_markdown_report(tmp_path, _run())
        assert isinstance(p, Path)
        assert p.name == "report.md"

    def test_contains_summary_metrics(self, tmp_path: Path) -> None:
        write_markdown_report(tmp_path, _run())
        content = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert "Summary" in content


# ---------------------------------------------------------------------------
# IO: write_experiment_outputs
# ---------------------------------------------------------------------------


class TestWriteExperimentOutputs:
    def test_writes_exactly_three_files(self, tmp_path: Path) -> None:
        paths = write_experiment_outputs(tmp_path, _run())
        assert len(paths) == 3

    def test_returns_paths_in_deterministic_order(self, tmp_path: Path) -> None:
        paths = write_experiment_outputs(tmp_path, _run())
        names = [p.name for p in paths]
        assert names == ["experiment_result.json", "summary.csv", "report.md"]

    def test_all_files_exist(self, tmp_path: Path) -> None:
        write_experiment_outputs(tmp_path, _run())
        assert (tmp_path / "experiment_result.json").exists()
        assert (tmp_path / "summary.csv").exists()
        assert (tmp_path / "report.md").exists()

    def test_output_is_deterministic(self, tmp_path: Path) -> None:
        run = _run()
        write_experiment_outputs(tmp_path, run)
        contents_a = {
            f.name: f.read_text(encoding="utf-8")
            for f in tmp_path.iterdir()
        }
        write_experiment_outputs(tmp_path, run)
        contents_b = {
            f.name: f.read_text(encoding="utf-8")
            for f in tmp_path.iterdir()
        }
        assert contents_a == contents_b


# ---------------------------------------------------------------------------
# No forbidden imports
# ---------------------------------------------------------------------------


class TestExportersNoBannedImports:
    def _check_module(self, module_path: str) -> None:
        import importlib
        mod = importlib.import_module(module_path)
        src_path = mod.__file__
        assert src_path is not None
        with open(src_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        banned = {"pybullet", "pybullet_data", "openai", "src.brain.planner", "src.agents"}

        def _is_banned(name: str) -> bool:
            return any(name == b or name.startswith(b + ".") for b in banned)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_banned(alias.name), f"banned import in {module_path}: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                assert not _is_banned(node.module or ""), \
                    f"banned import in {module_path}: {node.module}"

    def test_exporters_no_pybullet(self) -> None:
        self._check_module("src.evaluation.exporters")

    def test_experiment_no_pybullet(self) -> None:
        self._check_module("src.evaluation.experiment")
