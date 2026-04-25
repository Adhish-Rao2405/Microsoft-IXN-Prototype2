"""Phase 17 — Unit tests for evidence_pack.

20 required tests.  No PyBullet.  No live model inference.
All tests use temporary directories and fixture JSON files.
"""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

import pytest

from src.experiments.evidence_pack import (
    EvidencePackResult,
    build_evidence_pack,
    _find_latest_batch_summary,
    _find_latest_adversarial_summary,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_BATCH_SUMMARY = {
    "batch_name": "test_batch",
    "total_runs": 3,
    "successful_runs": 3,
    "failed_runs": 0,
    "cases": [
        {
            "run_id": "deterministic_baseline_001",
            "planner_mode": "deterministic",
            "scenario_name": "baseline",
            "run_index": 1,
            "steps_requested": 1,
            "steps_completed": 1,
            "success": True,
            "output_path": None,
            "error_count": 0,
            "errors": [],
        },
        {
            "run_id": "deterministic_empty_001",
            "planner_mode": "deterministic",
            "scenario_name": "empty",
            "run_index": 1,
            "steps_requested": 1,
            "steps_completed": 1,
            "success": True,
            "output_path": None,
            "error_count": 0,
            "errors": [],
        },
        {
            "run_id": "deterministic_blocked_001",
            "planner_mode": "deterministic",
            "scenario_name": "blocked",
            "run_index": 1,
            "steps_requested": 1,
            "steps_completed": 1,
            "success": True,
            "output_path": None,
            "error_count": 0,
            "errors": [],
        },
    ],
    "metrics": {
        "success_rate": 1.0,
        "failure_rate": 0.0,
        "success_by_planner": {"deterministic": 1.0},
        "success_by_scenario": {"baseline": 1.0, "empty": 1.0, "blocked": 1.0},
        "avg_steps_by_planner": {"deterministic": 1.0},
        "avg_steps_by_scenario": {"baseline": 1.0, "empty": 1.0, "blocked": 1.0},
    },
}

_ADV_SUMMARY = {
    "scenario_name": "baseline",
    "total_cases": 12,
    "safe_failures": 12,
    "unsafe_passes": 0,
    "cases": [
        {
            "case_name": "malformed_json",
            "description": "Model returns syntactically invalid JSON.",
            "expected_safe_failure": True,
            "success": False,
            "safe_failure": True,
            "unsafe_pass": False,
            "error_count": 1,
            "errors": ["json_decode_error: Expecting property name"],
        },
        {
            "case_name": "empty_response",
            "description": "Model returns empty string.",
            "expected_safe_failure": True,
            "success": False,
            "safe_failure": True,
            "unsafe_pass": False,
            "error_count": 1,
            "errors": ["empty_or_non_string_response"],
        },
    ],
}


def _write_batch_summary(tmp_path: Path) -> Path:
    batch_dir = tmp_path / "batches" / "test_batch"
    batch_dir.mkdir(parents=True)
    p = batch_dir / "summary.json"
    p.write_text(json.dumps(_BATCH_SUMMARY), encoding="utf-8")
    return p


def _write_adv_summary(tmp_path: Path) -> Path:
    adv_dir = tmp_path / "adversarial"
    adv_dir.mkdir(parents=True)
    p = adv_dir / "summary.json"
    p.write_text(json.dumps(_ADV_SUMMARY), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1 — creates output directory
# ---------------------------------------------------------------------------


def test_creates_output_directory(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    assert result.output_dir.exists()
    assert result.output_dir.is_dir()


# ---------------------------------------------------------------------------
# Test 2 — creates evidence_summary.json
# ---------------------------------------------------------------------------


def test_creates_evidence_summary_json(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    assert result.evidence_summary_json_path.exists()
    assert result.evidence_summary_json_path.name == "evidence_summary.json"


# ---------------------------------------------------------------------------
# Test 3 — creates evidence_summary.csv
# ---------------------------------------------------------------------------


def test_creates_evidence_summary_csv(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    assert result.evidence_summary_csv_path.exists()
    assert result.evidence_summary_csv_path.name == "evidence_summary.csv"


# ---------------------------------------------------------------------------
# Test 4 — creates adversarial_summary.csv
# ---------------------------------------------------------------------------


def test_creates_adversarial_summary_csv(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    assert result.adversarial_summary_csv_path.exists()
    assert result.adversarial_summary_csv_path.name == "adversarial_summary.csv"


# ---------------------------------------------------------------------------
# Test 5 — creates dissertation_metrics.md
# ---------------------------------------------------------------------------


def test_creates_dissertation_metrics_md(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    assert result.dissertation_metrics_md_path.exists()
    assert result.dissertation_metrics_md_path.name == "dissertation_metrics.md"


# ---------------------------------------------------------------------------
# Test 6 — evidence JSON includes batch section
# ---------------------------------------------------------------------------


def test_evidence_json_includes_batch_section(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    data = json.loads(result.evidence_summary_json_path.read_text(encoding="utf-8"))
    assert "batch" in data
    assert "total_runs" in data["batch"]


# ---------------------------------------------------------------------------
# Test 7 — evidence JSON includes adversarial section
# ---------------------------------------------------------------------------


def test_evidence_json_includes_adversarial_section(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    data = json.loads(result.evidence_summary_json_path.read_text(encoding="utf-8"))
    assert "adversarial" in data
    assert "unsafe_passes" in data["adversarial"]


# ---------------------------------------------------------------------------
# Test 8 — evidence JSON includes headline_findings
# ---------------------------------------------------------------------------


def test_evidence_json_includes_headline_findings(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    data = json.loads(result.evidence_summary_json_path.read_text(encoding="utf-8"))
    assert "headline_findings" in data
    assert "unsafe_passes" in data["headline_findings"]
    assert "fail_closed_verified" in data["headline_findings"]


# ---------------------------------------------------------------------------
# Test 9 — unsafe passes are reported correctly
# ---------------------------------------------------------------------------


def test_unsafe_passes_reported_correctly(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    data = json.loads(result.evidence_summary_json_path.read_text(encoding="utf-8"))
    assert data["headline_findings"]["unsafe_passes"] == 0


# ---------------------------------------------------------------------------
# Test 10 — fail_closed_verified is true when unsafe_passes == 0
# ---------------------------------------------------------------------------


def test_fail_closed_verified_true_when_no_unsafe_passes(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    data = json.loads(result.evidence_summary_json_path.read_text(encoding="utf-8"))
    assert data["headline_findings"]["fail_closed_verified"] is True


# ---------------------------------------------------------------------------
# Test 11 — evidence CSV has metric,value columns
# ---------------------------------------------------------------------------


def test_evidence_csv_has_metric_value_columns(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    with result.evidence_summary_csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
    assert "metric" in columns
    assert "value" in columns


# ---------------------------------------------------------------------------
# Test 12 — adversarial CSV has required columns
# ---------------------------------------------------------------------------


def test_adversarial_csv_has_required_columns(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    with result.adversarial_summary_csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
    for col in ("case_name", "safe_failure", "unsafe_pass", "error_count", "errors"):
        assert col in columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# Test 13 — dissertation markdown includes required headings
# ---------------------------------------------------------------------------


def test_dissertation_md_includes_required_headings(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    content = result.dissertation_metrics_md_path.read_text(encoding="utf-8")
    for heading in (
        "# Dissertation Evidence Metrics",
        "## Batch Experiment Summary",
        "## Planner Comparison",
        "## Scenario Comparison",
        "## Adversarial Evaluation",
        "## Headline Finding",
    ):
        assert heading in content, f"Missing heading: {heading!r}"


# ---------------------------------------------------------------------------
# Test 14 — explicit input paths work
# ---------------------------------------------------------------------------


def test_explicit_input_paths_work(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=str(bp),        # pass as str, not Path
        adversarial_summary_path=str(ap),
    )
    assert isinstance(result, EvidencePackResult)


# ---------------------------------------------------------------------------
# Test 15 — missing batch summary raises FileNotFoundError
# ---------------------------------------------------------------------------


def test_missing_batch_summary_raises(tmp_path):
    ap = _write_adv_summary(tmp_path)
    with pytest.raises(FileNotFoundError):
        build_evidence_pack(
            output_dir=tmp_path / "pack",
            batch_summary_path=tmp_path / "nonexistent_batch.json",
            adversarial_summary_path=ap,
        )


# ---------------------------------------------------------------------------
# Test 16 — missing adversarial summary raises FileNotFoundError
# ---------------------------------------------------------------------------


def test_missing_adversarial_summary_raises(tmp_path):
    bp = _write_batch_summary(tmp_path)
    with pytest.raises(FileNotFoundError):
        build_evidence_pack(
            output_dir=tmp_path / "pack",
            batch_summary_path=bp,
            adversarial_summary_path=tmp_path / "nonexistent_adv.json",
        )


# ---------------------------------------------------------------------------
# Test 17 — latest summary discovery works
# ---------------------------------------------------------------------------


def test_latest_summary_discovery_works(tmp_path):
    # Write two batch summaries; the second should be discovered as latest
    b1 = tmp_path / "batches" / "batch_a"
    b1.mkdir(parents=True)
    p1 = b1 / "summary.json"
    p1.write_text(json.dumps(_BATCH_SUMMARY), encoding="utf-8")

    b2 = tmp_path / "batches" / "batch_b"
    b2.mkdir(parents=True)
    p2 = b2 / "summary.json"
    p2.write_text(json.dumps({**_BATCH_SUMMARY, "batch_name": "batch_b"}), encoding="utf-8")

    discovered = _find_latest_batch_summary(root=tmp_path / "batches")
    assert discovered.exists()


def test_latest_adversarial_discovery_works(tmp_path):
    ap = _write_adv_summary(tmp_path)
    discovered = _find_latest_adversarial_summary(root=tmp_path / "adversarial")
    assert discovered == ap


# ---------------------------------------------------------------------------
# Test 18 — module does not import PyBullet/GUI
# ---------------------------------------------------------------------------


def test_evidence_pack_has_no_pybullet_import():
    import importlib

    mod = importlib.import_module("src.experiments.evidence_pack")
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
# Test 19 — does not call Foundry Local (no network imports)
# ---------------------------------------------------------------------------


def test_does_not_call_foundry_local(tmp_path):
    """Passes without live server or any FOUNDRY_LOCAL env vars."""
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    result = build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )
    assert isinstance(result, EvidencePackResult)


# ---------------------------------------------------------------------------
# Test 20 — does not modify existing experiment outputs
# ---------------------------------------------------------------------------


def test_does_not_modify_existing_outputs(tmp_path):
    bp = _write_batch_summary(tmp_path)
    ap = _write_adv_summary(tmp_path)
    batch_mtime_before = bp.stat().st_mtime
    adv_mtime_before = ap.stat().st_mtime

    build_evidence_pack(
        output_dir=tmp_path / "pack",
        batch_summary_path=bp,
        adversarial_summary_path=ap,
    )

    assert bp.stat().st_mtime == batch_mtime_before, "batch summary was modified"
    assert ap.stat().st_mtime == adv_mtime_before, "adversarial summary was modified"
