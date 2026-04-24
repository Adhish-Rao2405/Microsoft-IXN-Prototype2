"""Immutable result records for evaluation runs — Phase 8.

All records are passive data containers.  No planning logic lives here.
All records are JSON-serialisable via their to_dict() methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class EvaluationStepRecord:
    """Snapshot of one pipeline step within a scenario run.

    Parameters
    ----------
    step_index:
        Zero-based index of this step within the scenario run.
    state_before:
        JSON-serialisable snapshot of the workcell state before the pipeline ran.
    candidate_action_count:
        Number of actions proposed by the planner.
    validated_action_count:
        Number of actions that passed safety validation.
    rejected_action_count:
        Number of actions that failed safety validation (0 or 1 per step under
        current stop-on-first-rejection semantics).
    executed_action_count:
        Number of actions that were successfully executed.
    rejection_reasons:
        Tuple of rejection reason strings (empty when no rejection occurred).
    executor_status:
        String label describing execution outcome (e.g. "executed", "rejected",
        "empty", "validated").
    state_after:
        JSON-serialisable snapshot of the workcell state after the pipeline ran.
    """

    step_index: int
    state_before: Any
    candidate_action_count: int
    validated_action_count: int
    rejected_action_count: int
    executed_action_count: int
    rejection_reasons: Tuple[str, ...]
    executor_status: str
    state_after: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "state_before": self.state_before,
            "candidate_action_count": self.candidate_action_count,
            "validated_action_count": self.validated_action_count,
            "rejected_action_count": self.rejected_action_count,
            "executed_action_count": self.executed_action_count,
            "rejection_reasons": list(self.rejection_reasons),
            "executor_status": self.executor_status,
            "state_after": self.state_after,
        }


@dataclass(frozen=True)
class EvaluationResult:
    """Aggregated result for a complete scenario run.

    Parameters
    ----------
    scenario_id:
        Matches EvaluationScenario.scenario_id for traceability.
    scenario_name:
        Human-readable name from the scenario.
    success:
        True if the pipeline completed without rejection/error within max_steps.
    expected_success:
        The declared expected_success from the scenario (declarative only).
    total_steps:
        Number of pipeline steps actually executed.
    total_candidate_actions:
        Sum of candidate action counts across all steps.
    total_validated_actions:
        Sum of validated action counts across all steps.
    total_rejected_actions:
        Sum of rejected action counts across all steps.
    total_executed_actions:
        Sum of executed action counts across all steps.
    rejection_reasons:
        Tuple of all rejection reason strings seen during the run.
    final_status:
        String label from the final pipeline step status.
    step_records:
        Ordered tuple of per-step records.
    metrics:
        Flat mapping of computed metric name → scalar value (populated by harness
        after calling compute_metrics).
    """

    scenario_id: str
    scenario_name: str
    success: bool
    expected_success: bool
    total_steps: int
    total_candidate_actions: int
    total_validated_actions: int
    total_rejected_actions: int
    total_executed_actions: int
    rejection_reasons: Tuple[str, ...]
    final_status: str
    step_records: Tuple[EvaluationStepRecord, ...]
    metrics: Mapping[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "success": self.success,
            "expected_success": self.expected_success,
            "total_steps": self.total_steps,
            "total_candidate_actions": self.total_candidate_actions,
            "total_validated_actions": self.total_validated_actions,
            "total_rejected_actions": self.total_rejected_actions,
            "total_executed_actions": self.total_executed_actions,
            "rejection_reasons": list(self.rejection_reasons),
            "final_status": self.final_status,
            "step_records": [s.to_dict() for s in self.step_records],
            "metrics": dict(self.metrics),
        }
