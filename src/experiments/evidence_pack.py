"""Phase 17 — Dissertation evidence pack.

Aggregates Phase 15 batch experiment results and Phase 16 adversarial
evaluation results into a final evidence pack with JSON, CSV, and
dissertation-ready markdown outputs.

No PyBullet.  No GUI.  No live model inference.  Reads existing outputs only.

Public API:
    build_evidence_pack(...)  -> EvidencePackResult
    EvidencePackResult        (frozen dataclass)
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidencePackResult:
    """Immutable result returned by build_evidence_pack()."""

    output_dir: Path
    evidence_summary_json_path: Path
    evidence_summary_csv_path: Path
    adversarial_summary_csv_path: Path
    dissertation_metrics_md_path: Path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_evidence_pack(
    output_dir: str | Path = "outputs/evidence_pack",
    batch_summary_path: str | Path | None = None,
    adversarial_summary_path: str | Path | None = None,
) -> EvidencePackResult:
    """Aggregate batch and adversarial results into a dissertation evidence pack.

    Args:
        output_dir:               Directory where evidence files will be written.
        batch_summary_path:       Explicit path to a Phase 15 ``summary.json``.
                                  If ``None``, the latest one is discovered
                                  under ``outputs/experiments/batches/``.
        adversarial_summary_path: Explicit path to a Phase 16 ``summary.json``.
                                  If ``None``, the latest one is discovered
                                  under ``outputs/experiments/adversarial/``.

    Returns:
        EvidencePackResult with paths to all four output files.

    Raises:
        FileNotFoundError: If a required summary cannot be found.
    """
    # Resolve summary paths
    batch_path = (
        Path(batch_summary_path)
        if batch_summary_path is not None
        else _find_latest_batch_summary()
    )
    adv_path = (
        Path(adversarial_summary_path)
        if adversarial_summary_path is not None
        else _find_latest_adversarial_summary()
    )

    if not batch_path.exists():
        raise FileNotFoundError(f"Batch summary not found: {batch_path}")
    if not adv_path.exists():
        raise FileNotFoundError(f"Adversarial summary not found: {adv_path}")

    batch_data: dict[str, Any] = json.loads(batch_path.read_text(encoding="utf-8"))
    adv_data: dict[str, Any] = json.loads(adv_path.read_text(encoding="utf-8"))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence = _build_evidence_summary(batch_data, adv_data)

    json_path = _write_evidence_json(out_dir, evidence)
    csv_path = _write_evidence_csv(out_dir, evidence)
    adv_csv_path = _write_adversarial_csv(out_dir, adv_data)
    md_path = _write_dissertation_md(out_dir, evidence, batch_data, adv_data)

    return EvidencePackResult(
        output_dir=out_dir,
        evidence_summary_json_path=json_path,
        evidence_summary_csv_path=csv_path,
        adversarial_summary_csv_path=adv_csv_path,
        dissertation_metrics_md_path=md_path,
    )


# ---------------------------------------------------------------------------
# Summary discovery
# ---------------------------------------------------------------------------


def _find_latest_batch_summary(
    root: str | Path = "outputs/experiments/batches",
) -> Path:
    """Return the most recently modified summary.json under *root*.

    Raises:
        FileNotFoundError: If no summary.json exists under *root*.
    """
    candidates = sorted(
        Path(root).rglob("summary.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No batch summary.json found under {root!r}. "
            "Run a Phase 15 batch experiment first."
        )
    return candidates[0]


def _find_latest_adversarial_summary(
    root: str | Path = "outputs/experiments/adversarial",
) -> Path:
    """Return the most recently modified summary.json under *root*.

    Raises:
        FileNotFoundError: If no summary.json exists under *root*.
    """
    candidates = sorted(
        Path(root).rglob("summary.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No adversarial summary.json found under {root!r}. "
            "Run a Phase 16 adversarial evaluation first."
        )
    return candidates[0]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _build_evidence_summary(
    batch_data: dict[str, Any],
    adv_data: dict[str, Any],
) -> dict[str, Any]:
    """Build the top-level evidence summary dict from loaded JSON data."""
    metrics: dict[str, Any] = batch_data.get("metrics", {})

    total = batch_data.get("total_runs", 0)
    successful = batch_data.get("successful_runs", 0)
    failed = batch_data.get("failed_runs", 0)

    total_adv = adv_data.get("total_cases", 0)
    safe_failures = adv_data.get("safe_failures", 0)
    unsafe_passes = adv_data.get("unsafe_passes", 0)

    safe_failure_rate = safe_failures / total_adv if total_adv else 0.0
    unsafe_pass_rate = unsafe_passes / total_adv if total_adv else 0.0

    return {
        "batch": {
            "total_runs": total,
            "successful_runs": successful,
            "failed_runs": failed,
            "success_rate": metrics.get("success_rate", 0.0),
            "failure_rate": metrics.get("failure_rate", 0.0),
            "success_by_planner": metrics.get("success_by_planner", {}),
            "success_by_scenario": metrics.get("success_by_scenario", {}),
        },
        "adversarial": {
            "total_cases": total_adv,
            "safe_failures": safe_failures,
            "unsafe_passes": unsafe_passes,
            "safe_failure_rate": safe_failure_rate,
            "unsafe_pass_rate": unsafe_pass_rate,
        },
        "headline_findings": {
            "unsafe_passes": unsafe_passes,
            "fail_closed_verified": unsafe_passes == 0,
        },
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _write_evidence_json(out_dir: Path, evidence: dict[str, Any]) -> Path:
    path = out_dir / "evidence_summary.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return path


def _write_evidence_csv(out_dir: Path, evidence: dict[str, Any]) -> Path:
    """Flatten evidence summary into metric/value rows."""
    path = out_dir / "evidence_summary.csv"
    batch = evidence["batch"]
    adv = evidence["adversarial"]
    headline = evidence["headline_findings"]

    rows: list[tuple[str, Any]] = [
        # Batch metrics
        ("batch.total_runs", batch["total_runs"]),
        ("batch.successful_runs", batch["successful_runs"]),
        ("batch.failed_runs", batch["failed_runs"]),
        ("batch.success_rate", batch["success_rate"]),
        ("batch.failure_rate", batch["failure_rate"]),
    ]
    for planner, rate in batch.get("success_by_planner", {}).items():
        rows.append((f"batch.success_by_planner.{planner}", rate))
    for scenario, rate in batch.get("success_by_scenario", {}).items():
        rows.append((f"batch.success_by_scenario.{scenario}", rate))

    rows += [
        # Adversarial metrics
        ("adversarial.total_cases", adv["total_cases"]),
        ("adversarial.safe_failures", adv["safe_failures"]),
        ("adversarial.unsafe_passes", adv["unsafe_passes"]),
        ("adversarial.safe_failure_rate", adv["safe_failure_rate"]),
        ("adversarial.unsafe_pass_rate", adv["unsafe_pass_rate"]),
        # Headline
        ("headline.unsafe_passes", headline["unsafe_passes"]),
        ("headline.fail_closed_verified", headline["fail_closed_verified"]),
    ]

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)
    return path


def _write_adversarial_csv(out_dir: Path, adv_data: dict[str, Any]) -> Path:
    path = out_dir / "adversarial_summary.csv"
    columns = ["case_name", "safe_failure", "unsafe_pass", "error_count", "errors"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for case in adv_data.get("cases", []):
            row = {col: case.get(col, "") for col in columns}
            errors_val = row.get("errors", "")
            if isinstance(errors_val, list):
                row["errors"] = "; ".join(errors_val)
            writer.writerow(row)
    return path


def _write_dissertation_md(
    out_dir: Path,
    evidence: dict[str, Any],
    batch_data: dict[str, Any],
    adv_data: dict[str, Any],
) -> Path:
    path = out_dir / "dissertation_metrics.md"
    batch = evidence["batch"]
    adv = evidence["adversarial"]
    headline = evidence["headline_findings"]
    metrics: dict[str, Any] = batch_data.get("metrics", {})

    lines: list[str] = [
        "# Dissertation Evidence Metrics",
        "",
        "## Batch Experiment Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total runs | {batch['total_runs']} |",
        f"| Successful runs | {batch['successful_runs']} |",
        f"| Failed runs | {batch['failed_runs']} |",
        f"| Success rate | {batch['success_rate']:.2%} |",
        f"| Failure rate | {batch['failure_rate']:.2%} |",
        "",
        "## Planner Comparison",
        "",
        "| Planner | Success Rate |",
        "|---------|-------------|",
    ]
    for planner, rate in batch.get("success_by_planner", {}).items():
        lines.append(f"| {planner} | {rate:.2%} |")

    lines += [
        "",
        "## Scenario Comparison",
        "",
        "| Scenario | Success Rate |",
        "|----------|-------------|",
    ]
    for scenario, rate in batch.get("success_by_scenario", {}).items():
        lines.append(f"| {scenario} | {rate:.2%} |")

    lines += [
        "",
        "## Adversarial Evaluation",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total adversarial cases | {adv['total_cases']} |",
        f"| Safe failures | {adv['safe_failures']} |",
        f"| Unsafe passes | {adv['unsafe_passes']} |",
        f"| Safe failure rate | {adv['safe_failure_rate']:.2%} |",
        f"| Unsafe pass rate | {adv['unsafe_pass_rate']:.2%} |",
        "",
        "### Case Detail",
        "",
        "| Case | Safe Failure | Unsafe Pass |",
        "|------|-------------|------------|",
    ]
    for case in adv_data.get("cases", []):
        name = case.get("case_name", "")
        sf = case.get("safe_failure", False)
        up = case.get("unsafe_pass", False)
        lines.append(f"| {name} | {sf} | {up} |")

    lines += [
        "",
        "## Headline Finding",
        "",
    ]
    if headline["fail_closed_verified"]:
        lines.append("**Unsafe passes: 0**")
        lines.append("")
        lines.append(
            "All adversarial model outputs failed closed. "
            "No unsafe or malformed model output reached execution."
        )
    else:
        unsafe = headline["unsafe_passes"]
        lines.append(f"**Unsafe passes: {unsafe}**")
        lines.append("")
        lines.append(
            f"WARNING: {unsafe} adversarial case(s) produced unsafe passes. "
            "Safety boundary investigation required."
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
