"""Phase 14 — Non-PyBullet experiment runner.

Runs controlled planner experiments through the existing workcell pipeline.
No PyBullet.  No GUI.  No retries.  No JSON repair.  No fallback planner.

Public API:
    run_experiment(...)  -> ExperimentResult
    ExperimentResult     (frozen dataclass)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.scenarios import create_scenario
from src.orchestration.pipeline import WorkcellPipeline
from src.orchestration.types import PipelineStatus
from src.planning.planner_factory import create_planner
from src.safety.workcell_safety import WorkcellSafetyValidator


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperimentResult:
    """Immutable result returned by run_experiment()."""

    scenario_name: str
    planner_mode: str
    steps_requested: int
    steps_completed: int
    success: bool
    output_path: Path | None
    errors: tuple[str, ...]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_experiment(
    planner_mode: str = "deterministic",
    scenario_name: str = "baseline",
    steps: int = 1,
    output_dir: str | Path = "outputs/experiments",
    model_client: Any = None,
) -> ExperimentResult:
    """Run a single experiment and export results to JSON.

    Args:
        planner_mode:   ``"deterministic"`` or ``"model"``.
        scenario_name:  One of the scenarios in ``src/experiments/scenarios.py``.
        steps:          Number of pipeline steps to run.
        output_dir:     Directory for the exported JSON file.
        model_client:   Optional injected ModelClient (for model mode tests
                        without live Foundry Local).

    Returns:
        ExperimentResult with outcome metadata and output file path.

    Raises:
        ValueError:  For unknown scenario or invalid planner mode (both are
                     raised immediately, before any pipeline work begins).
    """
    # Validate early — ValueError propagates to caller immediately.
    state = create_scenario(scenario_name)          # raises ValueError if unknown
    planner = create_planner(planner_mode, model_client=model_client)  # raises ValueError if bad mode

    safety = WorkcellSafetyValidator()
    pipeline = WorkcellPipeline(planner=planner, safety_validator=safety)

    steps_completed = 0
    errors: list[str] = []
    all_actions: list[dict] = []

    for _ in range(steps):
        try:
            result = pipeline.run(state, execute=False)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            break

        steps_completed += 1

        # Collect validated actions as dicts for export
        for action in (result.validated_actions or []):
            a = action
            if hasattr(a, "to_dict"):
                a = a.to_dict()
            all_actions.append(a)

        # Stop early on terminal pipeline states
        if result.status in (PipelineStatus.EMPTY, PipelineStatus.REJECTED):
            if result.status == PipelineStatus.REJECTED and result.rejection_reason:
                errors.append(result.rejection_reason)
            break

    success = len(errors) == 0

    output_path = _export(
        scenario_name=scenario_name,
        planner_mode=planner_mode,
        steps_requested=steps,
        steps_completed=steps_completed,
        success=success,
        errors=errors,
        actions=all_actions,
        output_dir=Path(output_dir),
    )

    return ExperimentResult(
        scenario_name=scenario_name,
        planner_mode=planner_mode,
        steps_requested=steps,
        steps_completed=steps_completed,
        success=success,
        output_path=output_path,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _export(
    *,
    scenario_name: str,
    planner_mode: str,
    steps_requested: int,
    steps_completed: int,
    success: bool,
    errors: list[str],
    actions: list[dict],
    output_dir: Path,
) -> Path:
    """Write experiment result JSON to *output_dir* and return the file path."""
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{scenario_name}_{planner_mode}_{ts}.json"
    output_path = output_dir / filename

    payload = {
        "scenario_name": scenario_name,
        "planner_mode": planner_mode,
        "steps_requested": steps_requested,
        "steps_completed": steps_completed,
        "success": success,
        "errors": errors,
        "actions": actions,
        "evaluations": [],
    }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path
