"""Tests for the deterministic Phase 6 workcell pipeline."""

from __future__ import annotations

import ast
import copy
import importlib

import pytest

from src.orchestration import pipeline as pipeline_module
from src.orchestration.errors import PipelineError
from src.orchestration.pipeline import WorkcellPipeline
from src.orchestration.types import PipelineResult, PipelineStatus
from src.planning.errors import PlanningError
from src.planning.types import Action, Plan
from src.safety.workcell_safety import ValidationResult
from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState


def _obj(
    obj_id: str,
    *,
    color: str = "red",
    on_conveyor: bool = True,
) -> SpawnedObject:
    return SpawnedObject(
        id=obj_id,
        type="cube",
        color=color,
        position=[0.5, 0.0, 0.5],
        on_conveyor=on_conveyor,
    )


def _state(objects: list[SpawnedObject] | None = None) -> WorkcellState:
    return WorkcellState(
        conveyor=Conveyor(),
        objects=objects or [],
        bins=BinRegistry(),
    )


class FakePlanner:
    def __init__(self, plan: Plan | None = None, error: Exception | None = None) -> None:
        self._plan = plan
        self._error = error
        self.calls: list[object] = []

    def plan(self, state: object) -> Plan | None:
        self.calls.append(state)
        if self._error is not None:
            raise self._error
        return self._plan


class FakeSafety:
    def __init__(self, results: list[ValidationResult] | None = None) -> None:
        self._results = list(results or [])
        self.calls: list[tuple[object, dict]] = []

    def validate_action(self, state: object, action: dict) -> ValidationResult:
        self.calls.append((state, action))
        if self._results:
            return self._results.pop(0)
        return ValidationResult(is_valid=True)


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute(self, action: str, parameters: dict) -> dict:
        self.calls.append((action, dict(parameters)))
        return {"action": action, "success": True}


class TestModuleIsolation:
    def test_imports_without_pybullet_mocking(self) -> None:
        mod = importlib.import_module("src.orchestration.pipeline")
        assert hasattr(mod, "WorkcellPipeline")

    def test_module_has_no_banned_imports(self) -> None:
        src_path = pipeline_module.__file__
        assert src_path is not None
        with open(src_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        banned_prefixes = {
            "pybullet",
            "pybullet_data",
            "random",
            "time",
            "datetime",
            "src.simulation.grasp",
            "src.simulation.robot",
            "src.simulation.scene",
            "src.brain.planner",
            "src.agents",
            "openai",
        }

        def _is_banned(name: str) -> bool:
            return any(name == p or name.startswith(p + ".") for p in banned_prefixes)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_banned(alias.name), f"banned import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not _is_banned(module), f"banned import: {module}"


class TestEmptyPlan:
    def test_empty_plan_returns_empty_result(self) -> None:
        planner = FakePlanner(plan=Plan(actions=[]))
        safety = FakeSafety()
        executor = FakeExecutor()

        result = WorkcellPipeline(planner, safety, executor).run(_state(), execute=False)

        assert isinstance(result, PipelineResult)
        assert result.status is PipelineStatus.EMPTY
        assert result.candidate_actions == []
        assert result.validated_actions == []
        assert result.executed_actions == []
        assert result.rejected_action is None
        assert result.rejection_reason is None
        assert executor.calls == []


class TestValidationOnlyFlow:
    def test_valid_actions_are_safety_validated(self) -> None:
        actions = [
            Action(action="pick_target", parameters={"object_id": "obj_1"}),
            Action(action="place_in_bin", parameters={"bin_id": "bin_a"}),
        ]
        planner = FakePlanner(plan=Plan(actions=actions))
        safety = FakeSafety(
            results=[ValidationResult(is_valid=True), ValidationResult(is_valid=True)]
        )

        result = WorkcellPipeline(planner, safety).run(_state([_obj("obj_1")]), execute=False)

        assert result.status is PipelineStatus.VALIDATED
        assert result.candidate_actions == actions
        assert result.validated_actions == actions
        assert result.executed_actions == []
        assert [call[1] for call in safety.calls] == [a.to_dict() for a in actions]

    def test_execute_false_never_calls_executor(self) -> None:
        actions = [Action(action="inspect_workcell", parameters={})]
        planner = FakePlanner(plan=Plan(actions=actions))
        safety = FakeSafety(results=[ValidationResult(is_valid=True)])
        executor = FakeExecutor()

        result = WorkcellPipeline(planner, safety, executor).run(_state(), execute=False)

        assert result.status is PipelineStatus.VALIDATED
        assert executor.calls == []


class TestExecuteFlow:
    def test_execute_true_calls_executor_after_full_validation(self) -> None:
        actions = [
            Action(action="pick_target", parameters={"object_id": "obj_1"}),
            Action(action="place_in_bin", parameters={"bin_id": "bin_a"}),
        ]
        planner = FakePlanner(plan=Plan(actions=actions))
        safety = FakeSafety(
            results=[ValidationResult(is_valid=True), ValidationResult(is_valid=True)]
        )
        executor = FakeExecutor()

        result = WorkcellPipeline(planner, safety, executor).run(_state([_obj("obj_1")]), execute=True)

        assert result.status is PipelineStatus.EXECUTED
        assert executor.calls == [
            ("pick_target", {"object_id": "obj_1"}),
            ("place_in_bin", {"bin_id": "bin_a"}),
        ]
        assert result.executed_actions == actions
        assert [call[1] for call in safety.calls] == [a.to_dict() for a in actions]

    def test_execute_true_without_executor_raises_pipeline_error(self) -> None:
        planner = FakePlanner(plan=Plan(actions=[Action(action="inspect_workcell", parameters={})]))
        safety = FakeSafety(results=[ValidationResult(is_valid=True)])

        with pytest.raises(PipelineError, match="Execution requested but no executor was provided"):
            WorkcellPipeline(planner, safety).run(_state(), execute=True)


class TestSafetyRejection:
    def test_safety_rejection_stops_pipeline(self) -> None:
        actions = [
            Action(action="inspect_workcell", parameters={}),
            Action(action="pick_target", parameters={"object_id": "obj_1"}),
            Action(action="place_in_bin", parameters={"bin_id": "bin_a"}),
        ]
        planner = FakePlanner(plan=Plan(actions=actions))
        safety = FakeSafety(
            results=[
                ValidationResult(is_valid=True),
                ValidationResult(
                    is_valid=False,
                    errors=["object_not_found"],
                    messages=["target object is missing"],
                ),
            ]
        )
        executor = FakeExecutor()

        result = WorkcellPipeline(planner, safety, executor).run(_state(), execute=False)

        assert result.status is PipelineStatus.REJECTED
        assert result.validated_actions == [actions[0]]
        assert result.rejected_action == actions[1]
        assert result.executed_actions == []
        assert len(safety.calls) == 2
        assert executor.calls == []

    def test_no_partial_execution_on_rejection(self) -> None:
        actions = [
            Action(action="inspect_workcell", parameters={}),
            Action(action="pick_target", parameters={"object_id": "obj_1"}),
        ]
        planner = FakePlanner(plan=Plan(actions=actions))
        safety = FakeSafety(
            results=[
                ValidationResult(is_valid=True),
                ValidationResult(
                    is_valid=False,
                    errors=["object_not_found"],
                    messages=["target object is missing"],
                ),
            ]
        )
        executor = FakeExecutor()

        result = WorkcellPipeline(planner, safety, executor).run(_state(), execute=True)

        assert result.status is PipelineStatus.REJECTED
        assert result.executed_actions == []
        assert executor.calls == []

    def test_rejection_reason_is_preserved(self) -> None:
        actions = [Action(action="place_in_bin", parameters={"bin_id": "bin_z"})]
        planner = FakePlanner(plan=Plan(actions=actions))
        safety = FakeSafety(
            results=[
                ValidationResult(
                    is_valid=False,
                    errors=["bin_not_found"],
                    messages=["target bin does not exist"],
                )
            ]
        )

        result = WorkcellPipeline(planner, safety).run(_state(), execute=False)

        assert result.status is PipelineStatus.REJECTED
        assert result.rejection_reason == "target bin does not exist"


class TestPlannerInteraction:
    def test_planner_called_exactly_once_with_original_state(self) -> None:
        state = _state([_obj("obj_1")])
        planner = FakePlanner(plan=Plan(actions=[]))
        safety = FakeSafety()

        WorkcellPipeline(planner, safety).run(state, execute=False)

        assert planner.calls == [state]

    def test_candidate_action_order_is_preserved(self) -> None:
        actions = [
            Action(action="wait", parameters={"seconds": 2.0}),
            Action(action="inspect_workcell", parameters={}),
            Action(action="stop_conveyor", parameters={}),
        ]
        planner = FakePlanner(plan=Plan(actions=actions))
        safety = FakeSafety(
            results=[
                ValidationResult(is_valid=True),
                ValidationResult(is_valid=True),
                ValidationResult(is_valid=True),
            ]
        )
        executor = FakeExecutor()

        result = WorkcellPipeline(planner, safety, executor).run(_state(), execute=True)

        assert result.candidate_actions == actions
        assert [call[1] for call in safety.calls] == [a.to_dict() for a in actions]
        assert executor.calls == [
            ("wait", {"seconds": 2.0}),
            ("inspect_workcell", {}),
            ("stop_conveyor", {}),
        ]

    def test_pipeline_does_not_modify_planner_output(self) -> None:
        actions = [Action(action="pick_target", parameters={"object_id": "obj_1"})]
        original = copy.deepcopy(actions)
        planner = FakePlanner(plan=Plan(actions=actions))
        safety = FakeSafety(results=[ValidationResult(is_valid=True)])

        result = WorkcellPipeline(planner, safety).run(_state([_obj("obj_1")]), execute=False)

        assert actions == original
        assert result.candidate_actions == original

    def test_pipeline_does_not_mutate_input_state(self) -> None:
        state = _state([_obj("obj_1"), _obj("obj_2", color="blue")])
        before = state.to_dict()
        planner = FakePlanner(
            plan=Plan(actions=[Action(action="inspect_workcell", parameters={})])
        )
        safety = FakeSafety(results=[ValidationResult(is_valid=True)])

        WorkcellPipeline(planner, safety).run(state, execute=False)

        assert state.to_dict() == before

    def test_planning_error_propagates_unchanged(self) -> None:
        planner = FakePlanner(error=PlanningError("bad state"))
        safety = FakeSafety()

        with pytest.raises(PlanningError, match="bad state"):
            WorkcellPipeline(planner, safety).run(_state(), execute=False)

    @pytest.mark.parametrize("bad_plan", [None, object()])
    def test_malformed_planner_output_raises_pipeline_error(self, bad_plan: object) -> None:
        planner = FakePlanner(plan=bad_plan)  # type: ignore[arg-type]
        safety = FakeSafety()

        with pytest.raises(PipelineError, match="Planner returned invalid plan"):
            WorkcellPipeline(planner, safety).run(_state(), execute=False)

    def test_repeated_runs_are_deterministic(self) -> None:
        actions = [
            Action(action="pick_target", parameters={"object_id": "obj_1"}),
            Action(action="place_in_bin", parameters={"bin_id": "bin_a"}),
        ]

        result_a = WorkcellPipeline(
            FakePlanner(plan=Plan(actions=copy.deepcopy(actions))),
            FakeSafety(results=[ValidationResult(is_valid=True), ValidationResult(is_valid=True)]),
        ).run(_state([_obj("obj_1")]), execute=False)

        result_b = WorkcellPipeline(
            FakePlanner(plan=Plan(actions=copy.deepcopy(actions))),
            FakeSafety(results=[ValidationResult(is_valid=True), ValidationResult(is_valid=True)]),
        ).run(_state([_obj("obj_1")]), execute=False)

        assert result_a == result_b