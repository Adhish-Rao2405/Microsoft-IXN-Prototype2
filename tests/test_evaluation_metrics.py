"""Tests for deterministic metric calculation — Phase 8."""

from __future__ import annotations

import pytest

from src.evaluation.metrics import compute_metrics
from src.evaluation.result_schema import EvaluationResult, EvaluationStepRecord


def _step(
    step_index: int = 0,
    candidate: int = 2,
    validated: int = 2,
    rejected: int = 0,
    executed: int = 2,
    rejection_reasons: tuple[str, ...] = (),
) -> EvaluationStepRecord:
    return EvaluationStepRecord(
        step_index=step_index,
        state_before={},
        candidate_action_count=candidate,
        validated_action_count=validated,
        rejected_action_count=rejected,
        executed_action_count=executed,
        rejection_reasons=rejection_reasons,
        executor_status="executed",
        state_after={},
    )


def _result(
    success: bool = True,
    total_candidate: int = 4,
    total_validated: int = 4,
    total_rejected: int = 0,
    total_executed: int = 4,
    total_steps: int = 1,
    step_records: tuple[EvaluationStepRecord, ...] | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        scenario_id="s001",
        scenario_name="Test",
        success=success,
        expected_success=True,
        total_steps=total_steps,
        total_candidate_actions=total_candidate,
        total_validated_actions=total_validated,
        total_rejected_actions=total_rejected,
        total_executed_actions=total_executed,
        rejection_reasons=(),
        final_status="executed",
        step_records=step_records or (_step(),),
        metrics={},
    )


class TestComputeMetrics:
    def test_returns_dict(self) -> None:
        assert isinstance(compute_metrics(_result()), dict)

    def test_scenario_success_true(self) -> None:
        m = compute_metrics(_result(success=True))
        assert m["scenario_success"] is True

    def test_scenario_success_false(self) -> None:
        m = compute_metrics(_result(success=False))
        assert m["scenario_success"] is False

    def test_total_steps(self) -> None:
        m = compute_metrics(_result(total_steps=3))
        assert m["total_steps"] == 3

    def test_total_candidate_actions(self) -> None:
        m = compute_metrics(_result(total_candidate=6))
        assert m["total_candidate_actions"] == 6

    def test_total_validated_actions(self) -> None:
        m = compute_metrics(_result(total_validated=5))
        assert m["total_validated_actions"] == 5

    def test_total_rejected_actions(self) -> None:
        m = compute_metrics(_result(total_rejected=1))
        assert m["total_rejected_actions"] == 1

    def test_total_executed_actions(self) -> None:
        m = compute_metrics(_result(total_executed=4))
        assert m["total_executed_actions"] == 4


class TestRejectionRate:
    def test_no_rejections(self) -> None:
        m = compute_metrics(_result(total_candidate=4, total_rejected=0))
        assert m["rejection_rate"] == 0.0

    def test_all_rejected(self) -> None:
        m = compute_metrics(_result(total_candidate=4, total_rejected=4))
        assert m["rejection_rate"] == 1.0

    def test_half_rejected(self) -> None:
        m = compute_metrics(_result(total_candidate=4, total_rejected=2))
        assert m["rejection_rate"] == 0.5

    def test_zero_candidate_actions_no_division_error(self) -> None:
        m = compute_metrics(_result(total_candidate=0, total_rejected=0))
        assert m["rejection_rate"] == 0.0


class TestValidationPassRate:
    def test_all_pass(self) -> None:
        m = compute_metrics(_result(total_candidate=4, total_validated=4))
        assert m["validation_pass_rate"] == 1.0

    def test_none_pass(self) -> None:
        m = compute_metrics(_result(total_candidate=4, total_validated=0))
        assert m["validation_pass_rate"] == 0.0

    def test_half_pass(self) -> None:
        m = compute_metrics(_result(total_candidate=4, total_validated=2))
        assert m["validation_pass_rate"] == 0.5

    def test_zero_candidate_no_division_error(self) -> None:
        m = compute_metrics(_result(total_candidate=0, total_validated=0))
        assert m["validation_pass_rate"] == 0.0


class TestExecutionRate:
    def test_all_executed(self) -> None:
        m = compute_metrics(_result(total_validated=4, total_executed=4))
        assert m["execution_rate"] == 1.0

    def test_none_executed(self) -> None:
        m = compute_metrics(_result(total_validated=4, total_executed=0))
        assert m["execution_rate"] == 0.0

    def test_zero_validated_no_division_error(self) -> None:
        m = compute_metrics(_result(total_validated=0, total_executed=0))
        assert m["execution_rate"] == 0.0


class TestMetricsDeterminism:
    def test_same_result_gives_same_metrics(self) -> None:
        r = _result(total_candidate=4, total_validated=3, total_rejected=1, total_executed=3)
        m1 = compute_metrics(r)
        m2 = compute_metrics(r)
        assert m1 == m2

    def test_metrics_called_twice_same_output(self) -> None:
        r = _result()
        assert compute_metrics(r) == compute_metrics(r)

    def test_no_randomness_in_metrics(self) -> None:
        r = _result(total_candidate=6, total_validated=5, total_rejected=1, total_executed=5)
        results = [compute_metrics(r) for _ in range(10)]
        first = results[0]
        for m in results[1:]:
            assert m == first
