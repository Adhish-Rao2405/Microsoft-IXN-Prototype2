"""Deterministic metric calculation from evaluation results — Phase 8.

Pure functions only.  No file IO, no wall-clock timing, no randomness,
no scenario mutation.
"""

from __future__ import annotations

from typing import Any, Dict

from src.evaluation.result_schema import EvaluationResult


def compute_metrics(result: EvaluationResult) -> Dict[str, Any]:
    """Return a flat dict of deterministic metrics derived from *result*.

    Definitions
    -----------
    rejection_rate
        total_rejected_actions / total_candidate_actions,
        or 0.0 when total_candidate_actions == 0.
    validation_pass_rate
        total_validated_actions / total_candidate_actions,
        or 0.0 when total_candidate_actions == 0.
    execution_rate
        total_executed_actions / total_validated_actions,
        or 0.0 when total_validated_actions == 0.
    """
    candidate = result.total_candidate_actions
    validated = result.total_validated_actions
    rejected = result.total_rejected_actions
    executed = result.total_executed_actions

    rejection_rate: float = rejected / candidate if candidate > 0 else 0.0
    validation_pass_rate: float = validated / candidate if candidate > 0 else 0.0
    execution_rate: float = executed / validated if validated > 0 else 0.0

    return {
        "scenario_success": result.success,
        "total_steps": result.total_steps,
        "total_candidate_actions": candidate,
        "total_validated_actions": validated,
        "total_rejected_actions": rejected,
        "total_executed_actions": executed,
        "rejection_rate": rejection_rate,
        "validation_pass_rate": validation_pass_rate,
        "execution_rate": execution_rate,
    }
