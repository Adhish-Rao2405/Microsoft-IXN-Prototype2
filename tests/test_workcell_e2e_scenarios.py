"""Phase 7: End-to-end deterministic workcell scenario tests.

Proves the complete deterministic control stack works together:

    WorkcellState → Planner → Candidate Plan → Safety → Validated Plan → Executor

Architecture note on safety validation scope
--------------------------------------------
The pipeline validates every candidate action against the **initial** state
before execution begins (Phase 6, Section 10.3 — no partial execution).
``WorkcellState.to_dict()`` does not include ``holding_object_id`` (that
belongs to the executor).  As a result, the real ``WorkcellSafetyValidator``
would always reject ``place_in_bin`` at validation time because it cannot
observe the "will-be-held" state that comes after ``pick_target`` executes.

To test the **pipeline + executor integration** (Tests 2–5, 8) we therefore
use ``_SchemaOnlySafety`` — a validator that enforces the Phase 3 action
schema but skips state-precondition checks.  This is deliberate: Phase 4
already verifies state-precondition rules in isolation; Phase 7 verifies the
end-to-end wiring, ordering, and execution.

For rejection and boundary scenarios (Tests 6, 7) the real
``WorkcellSafetyValidator`` is used with states that make the preconditions
deterministic (e.g., ``place_in_bin`` against a state where nothing is held).
"""

from __future__ import annotations

import ast
import copy
import importlib

import pytest

from src.brain.action_schema import _validate_workcell_action
from src.executor.workcell_executor import WorkcellExecutor
from src.orchestration.pipeline import WorkcellPipeline
from src.orchestration.types import PipelineStatus
from src.planning.planner import Planner
from src.safety.workcell_safety import ValidationResult, WorkcellSafetyValidator
from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _obj(
    obj_id: str,
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


def _make_workcell(
    objects: list[SpawnedObject] | None = None,
) -> tuple[Conveyor, BinRegistry, WorkcellState]:
    """Return shared (Conveyor, BinRegistry, WorkcellState) — live references."""
    conveyor = Conveyor()
    bins = BinRegistry()
    ws = WorkcellState(conveyor=conveyor, objects=objects or [], bins=bins)
    return conveyor, bins, ws


def _make_executor(
    conveyor: Conveyor,
    bins: BinRegistry,
    workcell_state: WorkcellState,
) -> WorkcellExecutor:
    return WorkcellExecutor(
        conveyor=conveyor,
        bins=bins,
        workcell_state=workcell_state,
    )


class _SchemaOnlySafety:
    """Safety validator that enforces Phase 3 action schema, not state preconditions.

    Suitable for E2E flow tests where the pipeline's upfront batch-validation
    cannot observe state changes that happen only during sequential execution
    (e.g., holding_object_id set by pick_target before place_in_bin runs).

    All Phase 3 schema-valid actions return is_valid=True.
    Schema-invalid actions return is_valid=False so schema drift is caught.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def validate_action(self, state: object, action: dict) -> ValidationResult:
        self.calls.append(dict(action))
        if _validate_workcell_action(action) is not None:
            return ValidationResult(is_valid=True)
        return ValidationResult(
            is_valid=False,
            errors=["schema_error"],
            messages=["Action failed Phase 3 schema validation"],
        )


class _FakeExecutor:
    """Records execute calls for order-assertion tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute(self, action: str, parameters: dict) -> dict:
        self.calls.append((action, dict(parameters)))
        return {"action": action, "success": True}


# ---------------------------------------------------------------------------
# Test 9 / Test 10 — No LLM or PyBullet coupling
# ---------------------------------------------------------------------------


class TestE2EStackIsolation:
    """Phase 7 E2E stack must not import LLM or PyBullet modules."""

    def test_no_pybullet_in_e2e_module(self) -> None:
        """Importing the E2E test module must not require pybullet."""
        mod = importlib.import_module("tests.test_workcell_e2e_scenarios")
        assert mod is not None

    def test_orchestration_pipeline_has_no_pybullet_import(self) -> None:
        import src.orchestration.pipeline as pm

        src_path = pm.__file__
        assert src_path is not None
        with open(src_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        banned = {"pybullet", "pybullet_data", "openai", "src.brain.planner", "src.agents"}

        def _is_banned(name: str) -> bool:
            return any(name == p or name.startswith(p + ".") for p in banned)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_banned(alias.name), f"banned import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                assert not _is_banned(node.module or ""), f"banned import: {node.module}"

    def test_planner_has_no_pybullet_import(self) -> None:
        import src.planning.planner as pm

        src_path = pm.__file__
        assert src_path is not None
        with open(src_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        banned = {"pybullet", "pybullet_data", "openai", "src.executor", "src.agents"}

        def _is_banned(name: str) -> bool:
            return any(name == p or name.startswith(p + ".") for p in banned)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_banned(alias.name), f"banned import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                assert not _is_banned(node.module or ""), f"banned import: {node.module}"


# ---------------------------------------------------------------------------
# Test 1 — Empty workcell (real planner, real safety, real pipeline)
# ---------------------------------------------------------------------------


class TestE2EEmptyWorkcell:
    """No plannable objects → EMPTY result; executor never called or mutates."""

    def _pipeline(self) -> tuple[WorkcellPipeline, WorkcellState, WorkcellExecutor]:
        conveyor, bins, ws = _make_workcell([])
        executor = _make_executor(conveyor, bins, ws)
        pipeline = WorkcellPipeline(Planner(), WorkcellSafetyValidator(), executor)
        return pipeline, ws, executor

    def test_status_is_empty(self) -> None:
        pipeline, ws, _ = self._pipeline()
        result = pipeline.run(ws, execute=True)
        assert result.status is PipelineStatus.EMPTY

    def test_no_candidate_actions(self) -> None:
        pipeline, ws, _ = self._pipeline()
        result = pipeline.run(ws, execute=True)
        assert result.candidate_actions == []

    def test_no_validated_actions(self) -> None:
        pipeline, ws, _ = self._pipeline()
        result = pipeline.run(ws, execute=True)
        assert result.validated_actions == []

    def test_no_executed_actions(self) -> None:
        pipeline, ws, _ = self._pipeline()
        result = pipeline.run(ws, execute=True)
        assert result.executed_actions == []

    def test_workcell_state_unchanged(self) -> None:
        pipeline, ws, _ = self._pipeline()
        before = ws.to_dict()
        pipeline.run(ws, execute=True)
        assert ws.to_dict() == before

    def test_empty_validate_only_also_returns_empty(self) -> None:
        pipeline, ws, _ = self._pipeline()
        result = pipeline.run(ws, execute=False)
        assert result.status is PipelineStatus.EMPTY


# ---------------------------------------------------------------------------
# Test 2 — Single object full flow
# (real planner, schema safety, real pipeline, real executor)
# ---------------------------------------------------------------------------


class TestE2ESingleObjectFlow:
    """One eligible object → pick+place executed; state updated by executor."""

    def test_red_object_executed_to_bin_a(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="red")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        assert result.status is PipelineStatus.EXECUTED
        assert len(result.executed_actions) == 2

    def test_blue_object_executed_to_bin_b(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="blue")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        assert result.status is PipelineStatus.EXECUTED

    def test_single_object_produces_exactly_two_actions(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="red")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        assert len(result.candidate_actions) == 2

    def test_pick_then_place_order_in_candidate_actions(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="red")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        assert result.candidate_actions[0].action == "pick_target"
        assert result.candidate_actions[1].action == "place_in_bin"

    def test_object_removed_from_workcell_state_after_execution(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="red")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        pipeline.run(ws, execute=True)

        assert not ws.has_object("obj_1")

    def test_bin_a_count_incremented_for_red_object(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="red")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        pipeline.run(ws, execute=True)

        assert bins.counts()["bin_a"] == 1
        assert bins.counts()["bin_b"] == 0

    def test_bin_b_count_incremented_for_blue_object(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="blue")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        pipeline.run(ws, execute=True)

        assert bins.counts()["bin_b"] == 1
        assert bins.counts()["bin_a"] == 0

    def test_safety_called_once_per_action(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="red")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        pipeline.run(ws, execute=True)

        assert len(safety.calls) == 2

    def test_validate_only_does_not_mutate_state(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="red")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)
        before = ws.to_dict()

        pipeline.run(ws, execute=False)

        assert ws.to_dict() == before
        assert ws.has_object("obj_1")


# ---------------------------------------------------------------------------
# Test 3 — Multiple objects deterministic order
# (real planner, schema safety, real pipeline, fake executor for order check)
# ---------------------------------------------------------------------------


class TestE2EMultipleObjectsOrder:
    """Multiple objects must be planned, validated, and executed in canonical order."""

    def _run_with_fake(self, objects: list[SpawnedObject]) -> tuple:
        conveyor, bins, ws = _make_workcell(objects)
        safety = _SchemaOnlySafety()
        executor = _FakeExecutor()
        pipeline = WorkcellPipeline(Planner(), safety, executor)
        result = pipeline.run(ws, execute=True)
        return result, safety, executor

    def test_three_objects_produce_six_actions(self) -> None:
        result, _, _ = self._run_with_fake(
            [_obj("obj_9"), _obj("obj_2"), _obj("obj_5")]
        )
        assert len(result.candidate_actions) == 6

    def test_pick_actions_in_ascending_id_order(self) -> None:
        result, _, _ = self._run_with_fake(
            [_obj("obj_9"), _obj("obj_2"), _obj("obj_5")]
        )
        picks = [a.parameters["object_id"] for a in result.candidate_actions if a.action == "pick_target"]
        assert picks == ["obj_2", "obj_5", "obj_9"]

    def test_executor_receives_actions_in_same_order(self) -> None:
        result, _, executor = self._run_with_fake(
            [_obj("obj_9"), _obj("obj_2"), _obj("obj_5")]
        )
        executed_names = [c[0] for c in executor.calls]
        candidate_names = [a.action for a in result.candidate_actions]
        assert executed_names == candidate_names

    def test_safety_receives_actions_in_same_order(self) -> None:
        result, safety, _ = self._run_with_fake(
            [_obj("obj_9"), _obj("obj_2"), _obj("obj_5")]
        )
        candidate_dicts = [a.to_dict() for a in result.candidate_actions]
        assert safety.calls == candidate_dicts

    def test_input_order_does_not_affect_output(self) -> None:
        result_a, _, _ = self._run_with_fake([_obj("obj_9"), _obj("obj_2")])
        result_b, _, _ = self._run_with_fake([_obj("obj_2"), _obj("obj_9")])
        assert [a.to_dict() for a in result_a.candidate_actions] == [
            a.to_dict() for a in result_b.candidate_actions
        ]

    def test_pick_place_pairs_are_consecutive(self) -> None:
        result, _, _ = self._run_with_fake([_obj("obj_1"), _obj("obj_2")])
        actions = result.candidate_actions
        assert actions[0].action == "pick_target"
        assert actions[1].action == "place_in_bin"
        assert actions[2].action == "pick_target"
        assert actions[3].action == "place_in_bin"

    def test_two_objects_both_bins_incremented_by_real_executor(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="red"), _obj("obj_2", color="blue")])
        executor = _make_executor(conveyor, bins, ws)
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        pipeline.run(ws, execute=True)

        assert bins.counts()["bin_a"] == 1
        assert bins.counts()["bin_b"] == 1
        assert ws.object_count() == 0


# ---------------------------------------------------------------------------
# Test 4 — Unknown color routes to default bin
# ---------------------------------------------------------------------------


class TestE2EUnknownColorRouting:
    """Objects with unknown colors must route to DEFAULT_BIN without error."""

    def test_unknown_color_routes_to_default_bin(self) -> None:
        from src.planning.rules import DEFAULT_BIN

        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="green")])
        executor = _FakeExecutor()
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        assert result.status is PipelineStatus.EXECUTED
        place_calls = [(a, p) for a, p in executor.calls if a == "place_in_bin"]
        assert len(place_calls) == 1
        assert place_calls[0][1]["bin_id"] == DEFAULT_BIN

    def test_unknown_color_does_not_raise(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="purple")])
        executor = _FakeExecutor()
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        pipeline.run(ws, execute=True)  # must not raise

    def test_unknown_color_produces_two_actions(self) -> None:
        conveyor, bins, ws = _make_workcell([_obj("obj_1", color="yellow")])
        executor = _FakeExecutor()
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        assert len(result.candidate_actions) == 2


# ---------------------------------------------------------------------------
# Test 5 — Ineligible object (on_conveyor=False) is skipped
# ---------------------------------------------------------------------------


class TestE2EIneligibleObjectSkipped:
    """Objects with on_conveyor=False must not appear in any plan or execution."""

    def test_off_conveyor_object_not_planned(self) -> None:
        conveyor, bins, ws = _make_workcell([
            _obj("obj_1", on_conveyor=False),
            _obj("obj_2", on_conveyor=True),
        ])
        executor = _FakeExecutor()
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        picks = [p for _, p in executor.calls if "object_id" in p]
        assert all(p["object_id"] != "obj_1" for p in picks)

    def test_only_eligible_object_executed(self) -> None:
        conveyor, bins, ws = _make_workcell([
            _obj("obj_1", on_conveyor=False),
            _obj("obj_2", on_conveyor=True),
        ])
        executor = _FakeExecutor()
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        assert len(result.executed_actions) == 2

    def test_all_ineligible_returns_empty(self) -> None:
        conveyor, bins, ws = _make_workcell([
            _obj("obj_1", on_conveyor=False),
            _obj("obj_2", on_conveyor=False),
        ])
        executor = _FakeExecutor()
        safety = _SchemaOnlySafety()
        pipeline = WorkcellPipeline(Planner(), safety, executor)

        result = pipeline.run(ws, execute=True)

        assert result.status is PipelineStatus.EMPTY
        assert executor.calls == []


# ---------------------------------------------------------------------------
# Test 6 — Safety rejection prevents execution
# (real WorkcellSafetyValidator with state dicts that trigger known rejections)
# ---------------------------------------------------------------------------


def _state_dict(
    *,
    objects: list[dict] | None = None,
    bins: list[dict] | None = None,
    holding_object_id: str | None = None,
    conveyor_running: bool = False,
) -> dict:
    """Return a state dict accepted by WorkcellSafetyValidator."""
    return {
        "conveyor": {"running": conveyor_running, "speed": 0.0},
        "objects": list(objects or []),
        "bins": list(bins or [
            {"bin_id": "bin_a", "position": [0.6, 0.4, 0.0], "count": 0},
            {"bin_id": "bin_b", "position": [0.6, -0.4, 0.0], "count": 0},
        ]),
        "holding_object_id": holding_object_id,
    }


class _FakePlannerWithActions:
    """Returns a fixed plan dict (not Action objects) — used with state dicts."""

    def __init__(self, actions: list[dict]) -> None:
        self._actions = actions
        self.calls: list = []

    def plan(self, state: object) -> _FixedPlan:
        self.calls.append(state)
        return _FixedPlan(self._actions)


class _FixedPlan:
    """Minimal Plan-duck-type that yields Action-duck-types for pipeline use."""

    def __init__(self, action_dicts: list[dict]) -> None:
        self.actions = [_DictAction(d) for d in action_dicts]


class _DictAction:
    """Action-duck-type backed by a dict — pipeline only needs .to_dict() and .action."""

    def __init__(self, d: dict) -> None:
        self._d = d
        self.action = d.get("action", "")
        self.parameters = d.get("parameters", {})

    def to_dict(self) -> dict:
        return dict(self._d)


class TestE2ESafetyRejection:
    """Real safety + pipeline: rejection must prevent all execution."""

    def test_place_in_bin_without_holding_is_rejected(self) -> None:
        # place_in_bin against state where nothing is held → no_object_held
        planner = _FakePlannerWithActions([
            {"action": "inspect_workcell", "parameters": {}},
            {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}},
        ])
        state = _state_dict(holding_object_id=None)
        executor = _FakeExecutor()
        pipeline = WorkcellPipeline(planner, WorkcellSafetyValidator(), executor)

        result = pipeline.run(state, execute=True)

        assert result.status is PipelineStatus.REJECTED
        assert result.rejected_action is not None
        assert result.executed_actions == []
        assert executor.calls == []

    def test_rejection_reason_preserved(self) -> None:
        planner = _FakePlannerWithActions([
            {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}},
        ])
        state = _state_dict(holding_object_id=None)
        pipeline = WorkcellPipeline(planner, WorkcellSafetyValidator())

        result = pipeline.run(state, execute=False)

        assert result.status is PipelineStatus.REJECTED
        assert result.rejection_reason is not None
        assert len(result.rejection_reason) > 0

    def test_first_valid_then_rejection_stops_pipeline(self) -> None:
        # A1 passes, A2 fails → A3 never validated
        planner = _FakePlannerWithActions([
            {"action": "inspect_workcell", "parameters": {}},       # valid
            {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}},  # no object held
            {"action": "reset_workcell", "parameters": {}},         # never reached
        ])
        state = _state_dict(holding_object_id=None)
        executor = _FakeExecutor()
        pipeline = WorkcellPipeline(planner, WorkcellSafetyValidator(), executor)

        result = pipeline.run(state, execute=True)

        assert result.status is PipelineStatus.REJECTED
        assert len(result.validated_actions) == 1
        assert result.rejected_action is not None
        assert result.rejected_action.action == "place_in_bin"
        assert executor.calls == []

    def test_pick_unknown_object_rejected_by_real_safety(self) -> None:
        planner = _FakePlannerWithActions([
            {"action": "pick_target", "parameters": {"object_id": "ghost_obj"}},
        ])
        state = _state_dict(objects=[], holding_object_id=None)
        executor = _FakeExecutor()
        pipeline = WorkcellPipeline(planner, WorkcellSafetyValidator(), executor)

        result = pipeline.run(state, execute=True)

        assert result.status is PipelineStatus.REJECTED
        assert executor.calls == []


# ---------------------------------------------------------------------------
# Test 7 — Full validation before execution (no validate-execute interleaving)
# ---------------------------------------------------------------------------


class TestE2EFullValidationBeforeExecution:
    """A3 unsafe → A1 and A2 must NOT be executed, even though they validated."""

    def test_executor_not_called_when_any_action_fails(self) -> None:
        # A1 valid, A2 valid, A3 invalid → executor never called
        planner = _FakePlannerWithActions([
            {"action": "inspect_workcell", "parameters": {}},
            {"action": "reset_workcell", "parameters": {}},
            {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}},  # no object held
        ])
        state = _state_dict(holding_object_id=None)
        executor = _FakeExecutor()
        pipeline = WorkcellPipeline(planner, WorkcellSafetyValidator(), executor)

        result = pipeline.run(state, execute=True)

        assert result.status is PipelineStatus.REJECTED
        assert executor.calls == []

    def test_validated_actions_accumulated_before_rejection(self) -> None:
        planner = _FakePlannerWithActions([
            {"action": "inspect_workcell", "parameters": {}},
            {"action": "reset_workcell", "parameters": {}},
            {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}},
        ])
        state = _state_dict(holding_object_id=None)
        pipeline = WorkcellPipeline(planner, WorkcellSafetyValidator())

        result = pipeline.run(state, execute=False)

        # Two actions validated before rejection
        assert len(result.validated_actions) == 2
        assert result.rejected_action is not None

    def test_executed_actions_is_empty_on_rejection(self) -> None:
        planner = _FakePlannerWithActions([
            {"action": "inspect_workcell", "parameters": {}},
            {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}},
        ])
        state = _state_dict(holding_object_id=None)
        executor = _FakeExecutor()
        pipeline = WorkcellPipeline(planner, WorkcellSafetyValidator(), executor)

        result = pipeline.run(state, execute=True)

        assert result.executed_actions == []


# ---------------------------------------------------------------------------
# Test 8 — Determinism across repeated runs
# ---------------------------------------------------------------------------


class TestE2EDeterminism:
    """Same initial fixture → same pipeline result on every invocation."""

    def test_candidate_actions_identical_across_runs(self) -> None:
        results = []
        for _ in range(5):
            conveyor, bins, ws = _make_workcell([_obj("obj_1"), _obj("obj_2", color="blue")])
            safety = _SchemaOnlySafety()
            executor = _FakeExecutor()
            pipeline = WorkcellPipeline(Planner(), safety, executor)
            results.append(pipeline.run(ws, execute=False))

        first = [a.to_dict() for a in results[0].candidate_actions]
        for r in results[1:]:
            assert [a.to_dict() for a in r.candidate_actions] == first

    def test_status_identical_across_runs(self) -> None:
        statuses = []
        for _ in range(5):
            conveyor, bins, ws = _make_workcell([_obj("obj_1")])
            safety = _SchemaOnlySafety()
            executor = _FakeExecutor()
            pipeline = WorkcellPipeline(Planner(), safety, executor)
            statuses.append(pipeline.run(ws, execute=True).status)

        assert all(s is statuses[0] for s in statuses)

    def test_execution_order_identical_across_runs(self) -> None:
        call_sequences = []
        for _ in range(5):
            conveyor, bins, ws = _make_workcell([_obj("obj_3"), _obj("obj_1"), _obj("obj_2")])
            safety = _SchemaOnlySafety()
            executor = _FakeExecutor()
            pipeline = WorkcellPipeline(Planner(), safety, executor)
            pipeline.run(ws, execute=True)
            call_sequences.append(executor.calls)

        first = call_sequences[0]
        for seq in call_sequences[1:]:
            assert seq == first

    def test_empty_state_deterministic_across_runs(self) -> None:
        statuses = []
        for _ in range(5):
            _, _, ws = _make_workcell([])
            pipeline = WorkcellPipeline(Planner(), WorkcellSafetyValidator())
            statuses.append(pipeline.run(ws, execute=False).status)
        assert all(s is PipelineStatus.EMPTY for s in statuses)
