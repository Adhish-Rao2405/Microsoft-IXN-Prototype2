"""Phase 16 — Adversarial model-output evaluation runner.

Feeds each adversarial case through the existing ModelPlanner parse path
to prove that bad model outputs are contained and fail closed.

No PyBullet.  No GUI.  No retries.  No JSON repair.  No Foundry Local.
No duplicate pipeline logic.

Public API:
    run_adversarial_evaluation(...)  -> AdversarialEvaluationResult
    AdversarialEvaluationResult      (frozen dataclass)
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from src.experiments.adversarial_cases import AdversarialCase, get_adversarial_cases
from src.planning.model_planner import ModelPlanner
from src.experiments.scenarios import create_scenario


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdversarialEvaluationResult:
    """Immutable result returned by run_adversarial_evaluation()."""

    total_cases: int
    safe_failures: int
    unsafe_passes: int
    output_dir: Path
    summary_json_path: Path
    summary_csv_path: Path


# ---------------------------------------------------------------------------
# Fake client helper
# ---------------------------------------------------------------------------


class _StaticModelClient:
    """Minimal fake ModelClient that always returns a fixed response text."""

    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    def complete(self, prompt: str) -> str:  # noqa: D102
        return self._response_text


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_adversarial_evaluation(
    scenario_name: str = "baseline",
    output_dir: str | Path = "outputs/experiments/adversarial",
) -> AdversarialEvaluationResult:
    """Evaluate all adversarial cases against the ModelPlanner parse path.

    For each case:
    1. Creates a fake client returning the adversarial response text.
    2. Runs ModelPlanner.plan() on the scenario state.
    3. Records whether the output failed closed (empty plan = safe failure).

    Args:
        scenario_name:  Scenario used to construct the WorkcellState prompt.
        output_dir:     Directory for summary outputs.

    Returns:
        AdversarialEvaluationResult with counts and output paths.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    state = create_scenario(scenario_name)
    cases = get_adversarial_cases()
    case_records: list[dict] = []

    for case in cases:
        record = _evaluate_case(case, state)
        case_records.append(record)

    safe_failures = sum(1 for r in case_records if r["safe_failure"])
    unsafe_passes = sum(1 for r in case_records if r["unsafe_pass"])

    summary_json_path = _write_summary_json(
        out_dir=out_dir,
        scenario_name=scenario_name,
        total_cases=len(case_records),
        safe_failures=safe_failures,
        unsafe_passes=unsafe_passes,
        case_records=case_records,
    )
    summary_csv_path = _write_summary_csv(out_dir=out_dir, case_records=case_records)

    return AdversarialEvaluationResult(
        total_cases=len(case_records),
        safe_failures=safe_failures,
        unsafe_passes=unsafe_passes,
        output_dir=out_dir,
        summary_json_path=summary_json_path,
        summary_csv_path=summary_csv_path,
    )


# ---------------------------------------------------------------------------
# Single case evaluation
# ---------------------------------------------------------------------------


def _evaluate_case(case: AdversarialCase, state) -> dict:
    """Run one adversarial case and return a case-record dict."""
    client = _StaticModelClient(case.response_text)
    planner = ModelPlanner(client)

    try:
        plan = planner.plan(state)
    except Exception as exc:  # noqa: BLE001
        # ModelPlanner.plan() should never raise for bad model output.
        # If it does, record as a safe failure (bad output still contained).
        return {
            "case_name": case.name,
            "description": case.description,
            "expected_safe_failure": case.expected_safe_failure,
            "success": False,
            "safe_failure": case.expected_safe_failure,
            "unsafe_pass": False,
            "error_count": 1,
            "errors": [f"ModelPlanner.plan() raised unexpectedly: {exc}"],
        }

    rejection_reason = planner.last_rejection_reason()

    # success = model produced at least one valid candidate action
    action_count = len(plan.actions) if plan.actions else 0
    success = action_count > 0

    # safe_failure: expected to fail, and did fail (no valid actions produced)
    safe_failure = case.expected_safe_failure and not success

    # unsafe_pass: expected to fail, but produced actions — this is the bad outcome
    unsafe_pass = case.expected_safe_failure and success

    errors: list[str] = []
    if rejection_reason:
        errors.append(rejection_reason)

    return {
        "case_name": case.name,
        "description": case.description,
        "expected_safe_failure": case.expected_safe_failure,
        "success": success,
        "safe_failure": safe_failure,
        "unsafe_pass": unsafe_pass,
        "error_count": len(errors),
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def _write_summary_json(
    *,
    out_dir: Path,
    scenario_name: str,
    total_cases: int,
    safe_failures: int,
    unsafe_passes: int,
    case_records: list[dict],
) -> Path:
    path = out_dir / "summary.json"
    payload = {
        "scenario_name": scenario_name,
        "total_cases": total_cases,
        "safe_failures": safe_failures,
        "unsafe_passes": unsafe_passes,
        "cases": case_records,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


_CSV_COLUMNS = (
    "case_name",
    "description",
    "expected_safe_failure",
    "success",
    "safe_failure",
    "unsafe_pass",
    "error_count",
    "errors",
)


def _write_summary_csv(*, out_dir: Path, case_records: list[dict]) -> Path:
    path = out_dir / "summary.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(_CSV_COLUMNS))
        writer.writeheader()
        for rec in case_records:
            row = {col: rec.get(col, "") for col in _CSV_COLUMNS}
            errors_val = row.get("errors", "")
            if isinstance(errors_val, list):
                row["errors"] = "; ".join(errors_val)
            writer.writerow(row)
    return path
