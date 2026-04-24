"""Tests for EvaluationStepRecord and EvaluationResult — Phase 8."""

from __future__ import annotations

import json

import pytest

from src.evaluation.result_schema import EvaluationResult, EvaluationStepRecord


def _step(
    step_index: int = 0,
    candidate_action_count: int = 2,
    validated_action_count: int = 2,
    rejected_action_count: int = 0,
    executed_action_count: int = 2,
    rejection_reasons: tuple[str, ...] = (),
    executor_status: str = "executed",
    state_before: dict | None = None,
    state_after: dict | None = None,
) -> EvaluationStepRecord:
    return EvaluationStepRecord(
        step_index=step_index,
        state_before=state_before or {"objects": [], "bins": []},
        candidate_action_count=candidate_action_count,
        validated_action_count=validated_action_count,
        rejected_action_count=rejected_action_count,
        executed_action_count=executed_action_count,
        rejection_reasons=rejection_reasons,
        executor_status=executor_status,
        state_after=state_after or {"objects": [], "bins": []},
    )


def _result(
    scenario_id: str = "s001",
    scenario_name: str = "Test",
    success: bool = True,
    expected_success: bool = True,
    total_steps: int = 1,
    total_candidate_actions: int = 2,
    total_validated_actions: int = 2,
    total_rejected_actions: int = 0,
    total_executed_actions: int = 2,
    rejection_reasons: tuple[str, ...] = (),
    final_status: str = "executed",
    step_records: tuple[EvaluationStepRecord, ...] | None = None,
    metrics: dict | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        success=success,
        expected_success=expected_success,
        total_steps=total_steps,
        total_candidate_actions=total_candidate_actions,
        total_validated_actions=total_validated_actions,
        total_rejected_actions=total_rejected_actions,
        total_executed_actions=total_executed_actions,
        rejection_reasons=rejection_reasons,
        final_status=final_status,
        step_records=step_records or (_step(),),
        metrics=metrics or {},
    )


class TestEvaluationStepRecord:
    def test_step_record_constructs(self) -> None:
        s = _step()
        assert s.step_index == 0
        assert s.executor_status == "executed"

    def test_step_record_to_dict_returns_dict(self) -> None:
        d = _step().to_dict()
        assert isinstance(d, dict)

    def test_step_record_to_dict_has_required_keys(self) -> None:
        d = _step().to_dict()
        for key in (
            "step_index", "state_before", "candidate_action_count",
            "validated_action_count", "rejected_action_count",
            "executed_action_count", "rejection_reasons",
            "executor_status", "state_after",
        ):
            assert key in d, f"Missing key: {key}"

    def test_step_record_is_json_serialisable(self) -> None:
        d = _step().to_dict()
        json.dumps(d)  # must not raise

    def test_same_inputs_same_dict(self) -> None:
        d1 = _step(step_index=3, candidate_action_count=4).to_dict()
        d2 = _step(step_index=3, candidate_action_count=4).to_dict()
        assert d1 == d2

    def test_rejection_reasons_serialised_as_list(self) -> None:
        d = _step(rejection_reasons=("reason_a",)).to_dict()
        assert isinstance(d["rejection_reasons"], list)
        assert d["rejection_reasons"] == ["reason_a"]

    def test_step_with_rejection(self) -> None:
        s = _step(rejected_action_count=1, rejection_reasons=("no_object_held",))
        assert s.rejected_action_count == 1
        assert "no_object_held" in s.rejection_reasons


class TestEvaluationResult:
    def test_result_constructs(self) -> None:
        r = _result()
        assert r.scenario_id == "s001"
        assert r.success is True

    def test_result_to_dict_returns_dict(self) -> None:
        d = _result().to_dict()
        assert isinstance(d, dict)

    def test_result_to_dict_has_required_keys(self) -> None:
        d = _result().to_dict()
        for key in (
            "scenario_id", "scenario_name", "success", "expected_success",
            "total_steps", "total_candidate_actions", "total_validated_actions",
            "total_rejected_actions", "total_executed_actions",
            "rejection_reasons", "final_status", "step_records", "metrics",
        ):
            assert key in d, f"Missing key: {key}"

    def test_result_is_json_serialisable(self) -> None:
        d = _result().to_dict()
        json.dumps(d)  # must not raise

    def test_step_records_serialised_as_list(self) -> None:
        d = _result().to_dict()
        assert isinstance(d["step_records"], list)

    def test_metrics_serialised_as_dict(self) -> None:
        r = _result(metrics={"rejection_rate": 0.0, "success": True})
        d = r.to_dict()
        assert isinstance(d["metrics"], dict)

    def test_same_inputs_same_dict(self) -> None:
        d1 = _result(scenario_id="x", total_steps=3).to_dict()
        d2 = _result(scenario_id="x", total_steps=3).to_dict()
        assert d1 == d2

    def test_result_only_json_compatible_values(self) -> None:
        d = _result().to_dict()
        # Full recursive check via JSON round-trip
        serialised = json.dumps(d)
        recovered = json.loads(serialised)
        assert isinstance(recovered, dict)

    def test_rejection_reasons_serialised_as_list(self) -> None:
        r = _result(rejection_reasons=("a", "b"))
        d = r.to_dict()
        assert isinstance(d["rejection_reasons"], list)

    def test_metrics_with_numeric_values(self) -> None:
        r = _result(metrics={"rejection_rate": 0.5, "total_steps": 2})
        d = r.to_dict()
        assert d["metrics"]["rejection_rate"] == 0.5
