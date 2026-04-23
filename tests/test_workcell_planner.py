"""Phase 5 planner tests — written against the locked spec.

Covers all 10 baseline test cases from the Phase 5.1 lock spec:

1.  Empty state → empty plan
2.  Single known object → pick then place (correct bin)
3.  Unknown color → default bin routing
4.  Multiple objects → deterministic ascending-id ordering
5.  Ineligible object (on_conveyor=False) skipped
6.  Determinism: same input → same output across repeated calls
7.  Planner does not mutate input state
8.  Invalid state raises PlanningError
9.  Duplicate object IDs raise PlanningError
10. All emitted actions pass Phase 3 action schema validation

Plus:
- Module isolation (no PyBullet, no executor, no agents, no safety)
- Rules-module contract (routing table, predicates, ordering, builders)
"""

from __future__ import annotations

import ast
import importlib
import json

import pytest

from src.planning import planner as planner_module
from src.planning.errors import PlanningError
from src.planning.planner import Planner
from src.planning.rules import (
    BIN_ROUTING,
    DEFAULT_BIN,
    is_plannable_object,
    make_pick_action,
    make_place_action,
    resolve_target_bin,
    sort_plannable_objects,
)
from src.planning.types import Action, Plan
from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_state(objects: list[SpawnedObject] | None = None) -> WorkcellState:
    """Return a valid WorkcellState with default bins and the given objects."""
    return WorkcellState(
        conveyor=Conveyor(),
        objects=objects or [],
        bins=BinRegistry(),
    )


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


# ---------------------------------------------------------------------------
# Minimal stubs for edge-case testing outside WorkcellState
# ---------------------------------------------------------------------------


class _FakeState:
    """Minimal stub that exposes list_objects() for edge-case tests."""

    def __init__(self, objects: list) -> None:
        self._objects = objects

    def list_objects(self) -> list:
        return self._objects


class _MissingIdObject:
    """Object whose id attribute is None."""

    id = None
    color = "red"
    on_conveyor = True


class _DuplicateObj:
    """Plain object for duplicate-id tests."""

    def __init__(self, obj_id: str, color: str = "red") -> None:
        self.id = obj_id
        self.color = color
        self.on_conveyor = True


# ---------------------------------------------------------------------------
# Module isolation
# ---------------------------------------------------------------------------


class TestModuleIsolation:
    def test_planner_imports_without_pybullet_mocking(self) -> None:
        mod = importlib.import_module("src.planning.planner")
        assert hasattr(mod, "Planner")

    def test_rules_imports_without_pybullet_mocking(self) -> None:
        mod = importlib.import_module("src.planning.rules")
        assert hasattr(mod, "BIN_ROUTING")

    def test_planner_module_has_no_banned_imports(self) -> None:
        src_path = planner_module.__file__
        assert src_path is not None
        with open(src_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        banned_prefixes = {
            "pybullet",
            "src.simulation.grasp",
            "src.simulation.robot",
            "src.simulation.scene",
            "src.executor",
            "src.agents",
            "src.safety",
            "src.web_ui",
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


# ---------------------------------------------------------------------------
# Test 1 — Empty state returns empty plan
# ---------------------------------------------------------------------------


class TestEmptyState:
    def test_returns_plan_instance(self) -> None:
        plan = Planner().plan(_make_state([]))
        assert isinstance(plan, Plan)

    def test_action_list_is_empty(self) -> None:
        plan = Planner().plan(_make_state([]))
        assert len(plan.actions) == 0

    def test_to_dict_is_empty_actions(self) -> None:
        plan = Planner().plan(_make_state([]))
        assert plan.to_dict() == {"actions": []}

    def test_no_exception_on_empty(self) -> None:
        Planner().plan(_make_state([]))  # must not raise


# ---------------------------------------------------------------------------
# Test 2 — Single known object produces pick then place
# ---------------------------------------------------------------------------


class TestSingleKnownObject:
    def test_produces_exactly_two_actions(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", color="red")]))
        assert len(plan.actions) == 2

    def test_first_action_is_pick_target(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", color="red")]))
        assert plan.actions[0].action == "pick_target"

    def test_pick_references_correct_object_id(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", color="red")]))
        assert plan.actions[0].parameters["object_id"] == "obj_1"

    def test_second_action_is_place_in_bin(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", color="red")]))
        assert plan.actions[1].action == "place_in_bin"

    def test_red_routes_to_bin_a(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", color="red")]))
        assert plan.actions[1].parameters["bin_id"] == "bin_a"

    def test_blue_routes_to_bin_b(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", color="blue")]))
        assert plan.actions[1].parameters["bin_id"] == "bin_b"


# ---------------------------------------------------------------------------
# Test 3 — Unknown color routes to default bin
# ---------------------------------------------------------------------------


class TestUnknownColorRouting:
    def test_no_exception_on_unknown_color(self) -> None:
        Planner().plan(_make_state([_obj("obj_1", color="green")]))

    def test_produces_exactly_two_actions(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", color="green")]))
        assert len(plan.actions) == 2

    def test_routes_to_default_bin(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", color="green")]))
        assert plan.actions[1].parameters["bin_id"] == DEFAULT_BIN

    def test_default_bin_is_valid_known_bin(self) -> None:
        assert BinRegistry().is_valid(DEFAULT_BIN)


# ---------------------------------------------------------------------------
# Test 4 — Multiple objects ordered deterministically by id
# ---------------------------------------------------------------------------


class TestMultipleObjectOrdering:
    def test_output_order_is_ascending_by_id(self) -> None:
        state = _make_state([_obj("obj_9"), _obj("obj_2"), _obj("obj_5")])
        plan = Planner().plan(state)
        picked = [
            a.parameters["object_id"]
            for a in plan.actions
            if a.action == "pick_target"
        ]
        assert picked == ["obj_2", "obj_5", "obj_9"]

    def test_produces_six_actions_for_three_objects(self) -> None:
        state = _make_state([_obj("obj_9"), _obj("obj_2"), _obj("obj_5")])
        plan = Planner().plan(state)
        assert len(plan.actions) == 6

    def test_input_order_does_not_affect_output(self) -> None:
        plan_a = Planner().plan(_make_state([_obj("obj_9"), _obj("obj_2")]))
        plan_b = Planner().plan(_make_state([_obj("obj_2"), _obj("obj_9")]))
        assert plan_a == plan_b

    def test_pick_place_pairs_are_consecutive(self) -> None:
        state = _make_state([_obj("obj_1"), _obj("obj_2")])
        plan = Planner().plan(state)
        assert plan.actions[0].action == "pick_target"
        assert plan.actions[1].action == "place_in_bin"
        assert plan.actions[2].action == "pick_target"
        assert plan.actions[3].action == "place_in_bin"


# ---------------------------------------------------------------------------
# Test 5 — Ineligible object (on_conveyor=False) is skipped
# ---------------------------------------------------------------------------


class TestIneligibleObjectSkipped:
    def test_off_conveyor_object_not_in_output(self) -> None:
        state = _make_state([
            _obj("obj_1", on_conveyor=False),
            _obj("obj_2", on_conveyor=True),
        ])
        plan = Planner().plan(state)
        picked = [
            a.parameters["object_id"]
            for a in plan.actions
            if a.action == "pick_target"
        ]
        assert picked == ["obj_2"]

    def test_only_eligible_object_produces_actions(self) -> None:
        state = _make_state([
            _obj("obj_1", on_conveyor=False),
            _obj("obj_2", on_conveyor=True),
        ])
        plan = Planner().plan(state)
        assert len(plan.actions) == 2

    def test_all_ineligible_returns_empty_plan(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1", on_conveyor=False)]))
        assert len(plan.actions) == 0


# ---------------------------------------------------------------------------
# Test 6 — Determinism across repeated calls
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_calls_produce_equal_plans(self) -> None:
        state = _make_state([_obj("obj_1"), _obj("obj_2", color="blue")])
        plans = [Planner().plan(state) for _ in range(5)]
        assert all(p == plans[0] for p in plans[1:])

    def test_two_independent_planner_instances_agree(self) -> None:
        state = _make_state([_obj("obj_1"), _obj("obj_2", color="blue")])
        assert Planner().plan(state) == Planner().plan(state)


# ---------------------------------------------------------------------------
# Test 7 — Planner does not mutate input state
# ---------------------------------------------------------------------------


class TestStateImmutability:
    def test_state_snapshot_unchanged_after_plan(self) -> None:
        state = _make_state([_obj("obj_1"), _obj("obj_2")])
        before = state.to_dict()
        Planner().plan(state)
        assert state.to_dict() == before

    def test_object_count_unchanged_after_plan(self) -> None:
        state = _make_state([_obj("obj_1"), _obj("obj_2")])
        count_before = state.object_count()
        Planner().plan(state)
        assert state.object_count() == count_before

    def test_conveyor_state_unchanged_after_plan(self) -> None:
        state = _make_state([_obj("obj_1")])
        conveyor_before = state.conveyor_snapshot()
        Planner().plan(state)
        assert state.conveyor_snapshot() == conveyor_before


# ---------------------------------------------------------------------------
# Test 8 — Invalid state raises PlanningError
# ---------------------------------------------------------------------------


class TestInvalidStateRaisesError:
    def test_none_state_raises_planning_error(self) -> None:
        with pytest.raises(PlanningError):
            Planner().plan(None)

    def test_object_missing_id_raises_planning_error(self) -> None:
        with pytest.raises(PlanningError, match="missing id"):
            Planner().plan(_FakeState([_MissingIdObject()]))

    def test_state_without_list_objects_raises(self) -> None:
        with pytest.raises(PlanningError):
            Planner().plan(object())


# ---------------------------------------------------------------------------
# Test 9 — Duplicate object IDs raise PlanningError
# ---------------------------------------------------------------------------


class TestDuplicateIds:
    def test_duplicate_ids_raise_planning_error(self) -> None:
        state = _FakeState([_DuplicateObj("obj_1"), _DuplicateObj("obj_1")])
        with pytest.raises(PlanningError, match="duplicate object_id"):
            Planner().plan(state)

    def test_distinct_ids_do_not_raise(self) -> None:
        state = _FakeState([_DuplicateObj("obj_1"), _DuplicateObj("obj_2")])
        plan = Planner().plan(state)
        assert len(plan.actions) == 4


# ---------------------------------------------------------------------------
# Test 10 — All emitted actions conform to Phase 3 action schema
# ---------------------------------------------------------------------------


class TestSchemaCompliance:
    def test_all_actions_pass_workcell_schema_validation(self) -> None:
        from src.brain.action_schema import validate_workcell_plan

        state = _make_state([
            _obj("obj_1", color="red"),
            _obj("obj_2", color="blue"),
            _obj("obj_3", color="green"),
        ])
        plan = Planner().plan(state)
        result = validate_workcell_plan(plan.to_dict())
        assert result is not None, "Plan failed Phase 3 schema validation"
        assert len(result) == len(plan.actions)

    def test_all_actions_have_action_and_parameters_keys(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1"), _obj("obj_2", color="blue")]))
        for action in plan.actions:
            d = action.to_dict()
            assert "action" in d
            assert "parameters" in d
            assert isinstance(d["parameters"], dict)

    def test_each_pick_has_object_id_parameter(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1")]))
        picks = [a for a in plan.actions if a.action == "pick_target"]
        for p in picks:
            assert "object_id" in p.parameters

    def test_each_place_has_bin_id_parameter(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1")]))
        places = [a for a in plan.actions if a.action == "place_in_bin"]
        for p in places:
            assert "bin_id" in p.parameters

    def test_plan_to_dict_is_json_serialisable(self) -> None:
        plan = Planner().plan(_make_state([_obj("obj_1"), _obj("obj_2", color="blue")]))
        json.dumps(plan.to_dict())  # must not raise


# ---------------------------------------------------------------------------
# Rules module contract
# ---------------------------------------------------------------------------


class TestRoutingRules:
    def test_red_maps_to_bin_a(self) -> None:
        assert resolve_target_bin("red") == "bin_a"

    def test_blue_maps_to_bin_b(self) -> None:
        assert resolve_target_bin("blue") == "bin_b"

    def test_unknown_color_maps_to_default(self) -> None:
        assert resolve_target_bin("purple") == DEFAULT_BIN

    def test_routing_table_is_explicit(self) -> None:
        assert "red" in BIN_ROUTING
        assert "blue" in BIN_ROUTING

    def test_default_bin_is_in_registry(self) -> None:
        assert BinRegistry().is_valid(DEFAULT_BIN)


class TestEligibilityPredicate:
    def test_on_conveyor_is_plannable(self) -> None:
        assert is_plannable_object(_obj("obj_1", on_conveyor=True)) is True

    def test_off_conveyor_is_not_plannable(self) -> None:
        assert is_plannable_object(_obj("obj_1", on_conveyor=False)) is False


class TestSortingRule:
    def test_sorts_ascending_by_id(self) -> None:
        objects = [_obj("obj_9"), _obj("obj_2"), _obj("obj_5")]
        sorted_objs = sort_plannable_objects(objects)
        assert [o.id for o in sorted_objs] == ["obj_2", "obj_5", "obj_9"]

    def test_single_object_unchanged(self) -> None:
        objects = [_obj("obj_1")]
        assert sort_plannable_objects(objects) == objects


class TestActionBuilders:
    def test_make_pick_action_structure(self) -> None:
        action = make_pick_action("obj_1")
        assert isinstance(action, Action)
        assert action.action == "pick_target"
        assert action.parameters == {"object_id": "obj_1"}

    def test_make_place_action_structure(self) -> None:
        action = make_place_action("bin_a")
        assert isinstance(action, Action)
        assert action.action == "place_in_bin"
        assert action.parameters == {"bin_id": "bin_a"}

    def test_action_to_dict_is_json_serialisable(self) -> None:
        d = make_pick_action("obj_1").to_dict()
        json.dumps(d)  # must not raise
