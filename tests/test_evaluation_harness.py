"""Tests for EvaluationHarness — Phase 8.

Uses fake/stub deterministic pipeline objects only.
No PyBullet, no LLM, no wall-clock dependency.
"""

from __future__ import annotations

import ast
from typing import Any

import pytest

from src.evaluation.harness import EvaluationHarness
from src.evaluation.result_schema import EvaluationResult
from src.evaluation.scenario import EvaluationScenario
from src.orchestration.types import PipelineResult, PipelineStatus


# ---------------------------------------------------------------------------
# Fake pipeline infrastructure
# ---------------------------------------------------------------------------


class _FakePipelineResult:
    """Minimal PipelineResult-duck-type."""

    def __init__(
        self,
        status: PipelineStatus,
        candidate_actions: list | None = None,
        validated_actions: list | None = None,
        executed_actions: list | None = None,
        rejected_action: Any = None,
        rejection_reason: str | None = None,
    ) -> None:
        self.status = status
        self.candidate_actions = candidate_actions or []
        self.validated_actions = validated_actions or []
        self.executed_actions = executed_actions or []
        self.rejected_action = rejected_action
        self.rejection_reason = rejection_reason


class _FixedPipeline:
    """Returns the same PipelineResult every call. Records call count."""

    def __init__(self, result: _FakePipelineResult) -> None:
        self._result = result
        self.calls: int = 0

    def run(self, state: Any, execute: bool = True) -> _FakePipelineResult:
        self.calls += 1
        return self._result


class _SequencePipeline:
    """Returns a different result per step from a pre-defined sequence."""

    def __init__(self, results: list[_FakePipelineResult]) -> None:
        self._results = list(results)
        self.calls: int = 0

    def run(self, state: Any, execute: bool = True) -> _FakePipelineResult:
        result = self._results[self.calls % len(self._results)]
        self.calls += 1
        return result


def _executed_result(n_actions: int = 2) -> _FakePipelineResult:
    actions = [{"action": f"act_{i}", "parameters": {}} for i in range(n_actions)]
    return _FakePipelineResult(
        status=PipelineStatus.EXECUTED,
        candidate_actions=list(actions),
        validated_actions=list(actions),
        executed_actions=list(actions),
    )


def _empty_result() -> _FakePipelineResult:
    return _FakePipelineResult(status=PipelineStatus.EMPTY)


def _rejected_result() -> _FakePipelineResult:
    return _FakePipelineResult(
        status=PipelineStatus.REJECTED,
        candidate_actions=[{"action": "pick_target", "parameters": {}}],
        validated_actions=[],
        executed_actions=[],
        rejected_action={"action": "pick_target", "parameters": {}},
        rejection_reason="no_object_on_conveyor",
    )


# ---------------------------------------------------------------------------
# Scenario factory
# ---------------------------------------------------------------------------


def _scenario(
    max_steps: int = 1,
    scenario_id: str = "s001",
    expected_success: bool = True,
    objects: list | None = None,
) -> EvaluationScenario:
    return EvaluationScenario(
        scenario_id=scenario_id,
        name="Harness test scenario",
        description="Automated test scenario.",
        objects=objects or [],
        max_steps=max_steps,
        expected_success=expected_success,
        success_conditions=("all_objects_placed",),
        tags=(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHarnessRunScenarioReturnsResult:
    def test_returns_evaluation_result(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario())
        assert isinstance(r, EvaluationResult)

    def test_result_has_correct_scenario_id(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario(scenario_id="sc42"))
        assert r.scenario_id == "sc42"

    def test_result_has_correct_scenario_name(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario())
        assert r.scenario_name == "Harness test scenario"

    def test_success_is_true_when_executed(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario())
        assert r.success is True

    def test_success_is_false_when_rejected(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_rejected_result()))
        r = harness.run_scenario(_scenario())
        assert r.success is False

    def test_expected_success_propagated(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario(expected_success=False))
        assert r.expected_success is False


class TestHarnessPipelineCallCount:
    def test_pipeline_called_once_for_max_steps_one(self) -> None:
        pipeline = _FixedPipeline(_executed_result())
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=1))
        assert pipeline.calls == 1

    def test_pipeline_called_up_to_max_steps(self) -> None:
        pipeline = _FixedPipeline(_executed_result())
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=3))
        assert pipeline.calls == 3

    def test_pipeline_stops_early_on_empty(self) -> None:
        """EMPTY status is terminal — no more objects to process."""
        pipeline = _FixedPipeline(_empty_result())
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=5))
        assert pipeline.calls == 1

    def test_pipeline_stops_early_on_rejected(self) -> None:
        """REJECTED status is terminal — do not retry."""
        pipeline = _FixedPipeline(_rejected_result())
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=5))
        assert pipeline.calls == 1


class TestHarnessActionCounts:
    def test_records_candidate_action_count(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result(n_actions=4)))
        r = harness.run_scenario(_scenario())
        assert r.total_candidate_actions == 4

    def test_records_validated_action_count(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result(n_actions=4)))
        r = harness.run_scenario(_scenario())
        assert r.total_validated_actions == 4

    def test_records_executed_action_count(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result(n_actions=2)))
        r = harness.run_scenario(_scenario())
        assert r.total_executed_actions == 2

    def test_records_rejected_action_count_when_rejected(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_rejected_result()))
        r = harness.run_scenario(_scenario())
        assert r.total_rejected_actions == 1

    def test_zero_rejected_when_fully_executed(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario())
        assert r.total_rejected_actions == 0


class TestHarnessRejectionReasons:
    def test_rejection_reason_captured(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_rejected_result()))
        r = harness.run_scenario(_scenario())
        assert "no_object_on_conveyor" in r.rejection_reasons

    def test_no_rejection_reasons_when_successful(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario())
        assert len(r.rejection_reasons) == 0


class TestHarnessStepRecords:
    def test_step_records_count_equals_pipeline_calls(self) -> None:
        pipeline = _FixedPipeline(_executed_result())
        harness = EvaluationHarness(pipeline)
        r = harness.run_scenario(_scenario(max_steps=3))
        assert len(r.step_records) == pipeline.calls

    def test_step_records_have_correct_step_indices(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario(max_steps=2))
        indices = [s.step_index for s in r.step_records]
        assert indices == list(range(len(r.step_records)))

    def test_step_record_has_state_before_and_after(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        r = harness.run_scenario(_scenario())
        step = r.step_records[0]
        assert step.state_before is not None
        assert step.state_after is not None


class TestHarnessDoesNotRetry:
    def test_rejected_pipeline_not_retried(self) -> None:
        pipeline = _FixedPipeline(_rejected_result())
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=10))
        assert pipeline.calls == 1

    def test_empty_pipeline_not_retried(self) -> None:
        pipeline = _FixedPipeline(_empty_result())
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=10))
        assert pipeline.calls == 1


class TestHarnessMaxSteps:
    def test_exactly_max_steps_called_when_executed(self) -> None:
        pipeline = _FixedPipeline(_executed_result())
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=7))
        assert pipeline.calls == 7

    def test_total_steps_recorded_correctly(self) -> None:
        pipeline = _FixedPipeline(_executed_result())
        harness = EvaluationHarness(pipeline)
        r = harness.run_scenario(_scenario(max_steps=4))
        assert r.total_steps == pipeline.calls


class TestHarnessEarlyTerminalStop:
    def test_stops_on_empty_before_max_steps(self) -> None:
        pipeline = _SequencePipeline([
            _executed_result(),
            _empty_result(),   # terminal — harness must stop here
            _executed_result(),
        ])
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=5))
        assert pipeline.calls == 2

    def test_stops_on_rejected_before_max_steps(self) -> None:
        pipeline = _SequencePipeline([
            _executed_result(),
            _rejected_result(),  # terminal
            _executed_result(),
        ])
        harness = EvaluationHarness(pipeline)
        harness.run_scenario(_scenario(max_steps=5))
        assert pipeline.calls == 2


class TestHarnessDeterminism:
    def test_same_scenario_same_result(self) -> None:
        def _run():
            pipeline = _FixedPipeline(_executed_result(n_actions=2))
            harness = EvaluationHarness(pipeline)
            return harness.run_scenario(_scenario(max_steps=2))

        r1, r2, r3 = _run(), _run(), _run()
        assert r1.success == r2.success == r3.success
        assert r1.total_candidate_actions == r2.total_candidate_actions == r3.total_candidate_actions
        assert r1.total_steps == r2.total_steps == r3.total_steps

    def test_no_randomness(self) -> None:
        statuses = []
        for _ in range(5):
            pipeline = _FixedPipeline(_executed_result())
            h = EvaluationHarness(pipeline)
            statuses.append(h.run_scenario(_scenario()).final_status)
        assert len(set(statuses)) == 1


class TestHarnessRunMany:
    def test_run_many_returns_tuple_of_results(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        scenarios = [_scenario(scenario_id=f"s{i}") for i in range(3)]
        results = harness.run_many(scenarios)
        assert len(results) == 3

    def test_run_many_preserves_order(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        ids = [f"scn_{i:03d}" for i in range(5)]
        scenarios = [_scenario(scenario_id=sid) for sid in ids]
        results = harness.run_many(scenarios)
        for i, r in enumerate(results):
            assert r.scenario_id == ids[i]

    def test_run_many_empty_returns_empty_tuple(self) -> None:
        harness = EvaluationHarness(_FixedPipeline(_executed_result()))
        results = harness.run_many([])
        assert len(results) == 0


class TestHarnessNoPyBulletImport:
    def test_harness_module_has_no_pybullet(self) -> None:
        import src.evaluation.harness as hm

        src_path = hm.__file__
        assert src_path is not None
        with open(src_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "pybullet" not in alias.name
            elif isinstance(node, ast.ImportFrom):
                assert "pybullet" not in (node.module or "")
