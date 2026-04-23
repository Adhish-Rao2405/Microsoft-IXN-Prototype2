"""Tests for deterministic workcell safety validation (Phase 4)."""

from __future__ import annotations

import ast
import copy
import importlib
import json

from src.safety import workcell_safety as safety_module
from src.safety.workcell_safety import ValidationResult, WorkcellSafetyValidator


def _state(
    *,
    conveyor_running: bool = False,
    objects: list[dict] | None = None,
    bins: list[dict] | None = None,
    holding_object_id: str | None = None,
) -> dict:
    return {
        "conveyor": {"running": conveyor_running, "speed": 0.3 if conveyor_running else 0.0},
        "objects": list(objects or []),
        "bins": list(bins or [
            {"bin_id": "bin_a", "position": [0.6, 0.4, 0.0], "count": 0},
            {"bin_id": "bin_b", "position": [0.6, -0.4, 0.0], "count": 0},
        ]),
        "holding_object_id": holding_object_id,
    }


def _obj(obj_id: str, on_conveyor: bool = True) -> dict:
    return {
        "id": obj_id,
        "type": "cube",
        "color": "red",
        "position": [0.5, 0.0, 0.5],
        "on_conveyor": on_conveyor,
    }


class TestModuleIsolation:
    def test_imports_without_pybullet_mocking(self) -> None:
        mod = importlib.import_module("src.safety.workcell_safety")
        assert hasattr(mod, "WorkcellSafetyValidator")

    def test_has_no_banned_imports(self) -> None:
        src = safety_module.__file__
        assert src is not None
        with open(src, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        banned_prefixes = {
            "pybullet",
            "src.simulation.grasp",
            "src.simulation.robot",
            "src.simulation.scene",
            "src.executor",
            "src.agents",
            "src.brain.planner",
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


class TestValidationResult:
    def test_valid_result_json_friendly(self) -> None:
        r = ValidationResult(is_valid=True)
        payload = r.to_dict()
        assert payload == {"is_valid": True, "errors": [], "messages": []}
        json.dumps(payload)

    def test_invalid_result_json_friendly(self) -> None:
        r = ValidationResult(
            is_valid=False,
            errors=["bin_not_found"],
            messages=["Unknown bin"],
        )
        payload = r.to_dict()
        assert payload["is_valid"] is False
        assert payload["errors"] == ["bin_not_found"]
        assert payload["messages"] == ["Unknown bin"]
        json.dumps(payload)


class TestActionCoverage:
    def setup_method(self) -> None:
        self.v = WorkcellSafetyValidator()

    def test_inspect_workcell_valid(self) -> None:
        state = _state()
        action = {"action": "inspect_workcell", "parameters": {}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is True

    def test_start_conveyor_valid_when_stopped(self) -> None:
        state = _state(conveyor_running=False)
        action = {"action": "start_conveyor", "parameters": {"speed": 0.3}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is True

    def test_start_conveyor_redundant_rejected(self) -> None:
        state = _state(conveyor_running=True)
        action = {"action": "start_conveyor", "parameters": {"speed": 0.3}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is False
        assert r.errors == ["conveyor_already_running"]

    def test_stop_conveyor_valid_when_running(self) -> None:
        state = _state(conveyor_running=True)
        action = {"action": "stop_conveyor", "parameters": {}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is True

    def test_stop_conveyor_redundant_rejected(self) -> None:
        state = _state(conveyor_running=False)
        action = {"action": "stop_conveyor", "parameters": {}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is False
        assert r.errors == ["conveyor_already_stopped"]

    def test_wait_valid(self) -> None:
        state = _state()
        action = {"action": "wait", "parameters": {"seconds": 2.0}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is True

    def test_pick_target_valid_case(self) -> None:
        state = _state(conveyor_running=False, objects=[_obj("obj_1")], holding_object_id=None)
        action = {"action": "pick_target", "parameters": {"object_id": "obj_1"}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is True

    def test_pick_target_unknown_object(self) -> None:
        state = _state(conveyor_running=False, objects=[])
        action = {"action": "pick_target", "parameters": {"object_id": "obj_404"}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is False
        assert r.errors == ["object_not_found"]

    def test_pick_target_rejects_when_already_holding(self) -> None:
        state = _state(conveyor_running=False, objects=[_obj("obj_1")], holding_object_id="obj_x")
        action = {"action": "pick_target", "parameters": {"object_id": "obj_1"}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is False
        assert r.errors == ["already_holding_object"]

    def test_pick_target_rejects_when_conveyor_running(self) -> None:
        state = _state(conveyor_running=True, objects=[_obj("obj_1")])
        action = {"action": "pick_target", "parameters": {"object_id": "obj_1"}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is False
        assert r.errors == ["conveyor_must_be_stopped_for_pick"]

    def test_pick_target_rejects_object_not_on_conveyor(self) -> None:
        state = _state(conveyor_running=False, objects=[_obj("obj_1", on_conveyor=False)])
        action = {"action": "pick_target", "parameters": {"object_id": "obj_1"}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is False
        assert r.errors == ["object_not_pickable"]

    def test_place_in_bin_valid_case(self) -> None:
        state = _state(holding_object_id="obj_1")
        action = {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is True

    def test_place_in_bin_rejects_when_not_holding(self) -> None:
        state = _state(holding_object_id=None)
        action = {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is False
        assert r.errors == ["no_object_held"]

    def test_place_in_bin_rejects_unknown_bin(self) -> None:
        state = _state(holding_object_id="obj_1")
        action = {"action": "place_in_bin", "parameters": {"bin_id": "bin_z"}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is False
        assert r.errors == ["bin_not_found"]

    def test_reset_workcell_valid(self) -> None:
        state = _state()
        action = {"action": "reset_workcell", "parameters": {}}
        r = self.v.validate_action(state, action)
        assert r.is_valid is True


class TestGenericValidation:
    def setup_method(self) -> None:
        self.v = WorkcellSafetyValidator()

    def test_unknown_action_rejected(self) -> None:
        r = self.v.validate_action(_state(), {"action": "fly_away", "parameters": {}})
        assert r.is_valid is False
        assert r.errors == ["unknown_action"]

    def test_missing_required_parameter_rejected(self) -> None:
        r = self.v.validate_action(_state(), {"action": "start_conveyor", "parameters": {}})
        assert r.is_valid is False
        assert r.errors == ["missing_required_parameter"]

    def test_unexpected_parameter_rejected(self) -> None:
        r = self.v.validate_action(_state(), {"action": "stop_conveyor", "parameters": {"extra": 1}})
        assert r.is_valid is False
        assert r.errors == ["unexpected_parameter"]

    def test_parameter_type_mismatch_rejected(self) -> None:
        r = self.v.validate_action(_state(), {"action": "wait", "parameters": {"seconds": "2"}})
        assert r.is_valid is False
        assert r.errors == ["parameter_type_mismatch"]


class TestReadOnlyBehavior:
    def setup_method(self) -> None:
        self.v = WorkcellSafetyValidator()

    def test_does_not_mutate_state(self) -> None:
        state = _state(conveyor_running=False, objects=[_obj("obj_1")], holding_object_id=None)
        before = copy.deepcopy(state)
        action = {"action": "pick_target", "parameters": {"object_id": "obj_1"}}

        self.v.validate_action(state, action)

        assert state == before

    def test_does_not_mutate_action(self) -> None:
        state = _state()
        action = {"action": "stop_conveyor", "parameters": {}}
        before = copy.deepcopy(action)

        self.v.validate_action(state, action)

        assert action == before


class TestNoHiddenIntelligence:
    def test_output_has_no_strategy_fields(self) -> None:
        v = WorkcellSafetyValidator()
        r = v.validate_action(_state(), {"action": "stop_conveyor", "parameters": {}})
        payload = r.to_dict()

        forbidden = {
            "suggested_action",
            "recommended_action",
            "recommended_bin",
            "recommended_object",
            "strategy",
            "next_action",
        }
        assert forbidden.isdisjoint(payload.keys())

    def test_validate_plan_preserves_order(self) -> None:
        v = WorkcellSafetyValidator()
        actions = [
            {"action": "stop_conveyor", "parameters": {}},
            {"action": "wait", "parameters": {"seconds": 1.0}},
            {"action": "start_conveyor", "parameters": {"speed": 0.2}},
        ]
        results = v.validate_plan(_state(conveyor_running=True), actions)

        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is True
        assert results[2].is_valid is False
        assert results[2].errors == ["conveyor_already_running"]
