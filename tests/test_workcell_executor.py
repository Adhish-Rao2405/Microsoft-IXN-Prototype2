"""Tests for WorkcellExecutor – Phase 3 (Tasks 3.2 + 3.3)."""

from __future__ import annotations

import ast
import importlib

import pytest

from src.executor import workcell_executor as workcell_executor_module
from src.executor.workcell_executor import WorkcellExecutor
from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestModuleIsolation:
    def test_pure_module_imports_cleanly(self) -> None:
        mod = importlib.import_module("src.executor.workcell_executor")
        assert hasattr(mod, "WorkcellExecutor")

    def test_module_has_no_banned_imports(self) -> None:
        src = workcell_executor_module.__file__
        assert src is not None
        with open(src, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        banned_prefixes = {
            "pybullet",
            "src.simulation.grasp",
            "src.simulation.robot",
            "src.simulation.scene",
            "src.brain.planner",
            "src.agents",
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


def _make_object(obj_id: str, on_conveyor: bool = True) -> SpawnedObject:
    return SpawnedObject(
        id=obj_id, type="cube", color="red",
        position=[0.5, 0.0, 0.5], on_conveyor=on_conveyor,
    )


def _make_executor(
    objects: list[SpawnedObject] | None = None,
    max_speed: float = 1.0,
    max_wait: float = 30.0,
) -> WorkcellExecutor:
    conveyor = Conveyor()
    bins = BinRegistry()
    ws = WorkcellState(
        conveyor=conveyor,
        objects=objects or [],
        bins=bins,
    )
    return WorkcellExecutor(
        conveyor=conveyor,
        bins=bins,
        workcell_state=ws,
        max_conveyor_speed=max_speed,
        max_wait_seconds=max_wait,
    )


# ---------------------------------------------------------------------------
# inspect_workcell
# ---------------------------------------------------------------------------


class TestInspectWorkcell:
    def test_returns_success(self) -> None:
        ex = _make_executor()
        r = ex.execute("inspect_workcell", {})
        assert r["success"] is True

    def test_returns_state_snapshot(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        r = ex.execute("inspect_workcell", {})
        assert "state" in r
        assert "conveyor" in r["state"]
        assert "objects" in r["state"]
        assert "bins" in r["state"]

    def test_snapshot_is_json_friendly(self) -> None:
        import json
        ex = _make_executor(objects=[_make_object("obj_1")])
        r = ex.execute("inspect_workcell", {})
        json.dumps(r["state"])  # must not raise


# ---------------------------------------------------------------------------
# start_conveyor
# ---------------------------------------------------------------------------


class TestStartConveyor:
    def test_starts_conveyor(self) -> None:
        ex = _make_executor()
        r = ex.execute("start_conveyor", {"speed": 0.5})
        assert r["success"] is True
        assert ex._conveyor.running is True
        assert ex._conveyor.speed == pytest.approx(0.5)

    def test_returns_speed_in_result(self) -> None:
        ex = _make_executor()
        r = ex.execute("start_conveyor", {"speed": 0.3})
        assert r["speed"] == pytest.approx(0.3)

    def test_rejects_missing_speed(self) -> None:
        ex = _make_executor()
        r = ex.execute("start_conveyor", {})
        assert r["success"] is False
        assert "speed" in r["error"]

    def test_rejects_zero_speed(self) -> None:
        ex = _make_executor()
        r = ex.execute("start_conveyor", {"speed": 0.0})
        assert r["success"] is False

    def test_rejects_negative_speed(self) -> None:
        ex = _make_executor()
        r = ex.execute("start_conveyor", {"speed": -1.0})
        assert r["success"] is False

    def test_rejects_speed_above_max(self) -> None:
        ex = _make_executor(max_speed=0.5)
        r = ex.execute("start_conveyor", {"speed": 0.9})
        assert r["success"] is False

    def test_accepts_speed_at_max(self) -> None:
        ex = _make_executor(max_speed=0.5)
        r = ex.execute("start_conveyor", {"speed": 0.5})
        assert r["success"] is True


# ---------------------------------------------------------------------------
# stop_conveyor
# ---------------------------------------------------------------------------


class TestStopConveyor:
    def test_stops_running_conveyor(self) -> None:
        ex = _make_executor()
        ex._conveyor.start(0.5)
        r = ex.execute("stop_conveyor", {})
        assert r["success"] is True
        assert ex._conveyor.running is False

    def test_stop_already_stopped_is_ok(self) -> None:
        ex = _make_executor()
        r = ex.execute("stop_conveyor", {})
        assert r["success"] is True

    def test_stop_freezes_speed_at_zero(self) -> None:
        ex = _make_executor()
        ex._conveyor.start(1.0)
        ex.execute("stop_conveyor", {})
        assert ex._conveyor.speed == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# wait
# ---------------------------------------------------------------------------


class TestWait:
    def test_wait_returns_success(self) -> None:
        ex = _make_executor()
        r = ex.execute("wait", {"seconds": 1.5})
        assert r["success"] is True
        assert r["seconds"] == pytest.approx(1.5)

    def test_wait_rejects_missing_seconds(self) -> None:
        ex = _make_executor()
        r = ex.execute("wait", {})
        assert r["success"] is False

    def test_wait_rejects_zero_seconds(self) -> None:
        ex = _make_executor()
        r = ex.execute("wait", {"seconds": 0.0})
        assert r["success"] is False

    def test_wait_rejects_negative_seconds(self) -> None:
        ex = _make_executor()
        r = ex.execute("wait", {"seconds": -1.0})
        assert r["success"] is False

    def test_wait_rejects_above_max(self) -> None:
        ex = _make_executor(max_wait=10.0)
        r = ex.execute("wait", {"seconds": 15.0})
        assert r["success"] is False

    def test_wait_does_not_sleep(self, monkeypatch) -> None:
        """wait must not call time.sleep or any real-time primitive."""
        import time
        calls: list = []
        monkeypatch.setattr(time, "sleep", lambda s: calls.append(s))
        ex = _make_executor()
        ex.execute("wait", {"seconds": 5.0})
        assert calls == []


# ---------------------------------------------------------------------------
# pick_target
# ---------------------------------------------------------------------------


class TestPickTarget:
    def test_pick_known_object(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        r = ex.execute("pick_target", {"object_id": "obj_1"})
        assert r["success"] is True
        assert r["object_id"] == "obj_1"

    def test_pick_sets_holding_state(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        ex.execute("pick_target", {"object_id": "obj_1"})
        assert ex.holding_object_id == "obj_1"
        assert ex.is_holding is True

    def test_pick_removes_object_from_workcell_state(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        ex.execute("pick_target", {"object_id": "obj_1"})
        assert not ex._workcell_state.has_object("obj_1")

    def test_pick_unknown_object_fails(self) -> None:
        ex = _make_executor()
        r = ex.execute("pick_target", {"object_id": "nonexistent"})
        assert r["success"] is False
        assert "nonexistent" in r["error"]

    def test_pick_missing_object_id_fails(self) -> None:
        ex = _make_executor()
        r = ex.execute("pick_target", {})
        assert r["success"] is False


# ---------------------------------------------------------------------------
# place_in_bin
# ---------------------------------------------------------------------------


class TestPlaceInBin:
    def _pick_first(self, ex: WorkcellExecutor) -> None:
        ex.execute("pick_target", {"object_id": "obj_1"})

    def test_place_increments_bin_count(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        self._pick_first(ex)
        ex.execute("place_in_bin", {"bin_id": "bin_a"})
        assert ex._bins.get("bin_a").count == 1

    def test_place_clears_holding_state(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        self._pick_first(ex)
        ex.execute("place_in_bin", {"bin_id": "bin_a"})
        assert ex.is_holding is False
        assert ex.holding_object_id is None

    def test_place_returns_success(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        self._pick_first(ex)
        r = ex.execute("place_in_bin", {"bin_id": "bin_a"})
        assert r["success"] is True
        assert r["bin_id"] == "bin_a"
        assert r["object_id"] == "obj_1"

    def test_place_unknown_bin_fails(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        self._pick_first(ex)
        r = ex.execute("place_in_bin", {"bin_id": "bin_z"})
        assert r["success"] is False

    def test_place_without_holding_fails(self) -> None:
        ex = _make_executor()
        r = ex.execute("place_in_bin", {"bin_id": "bin_a"})
        assert r["success"] is False
        assert "not holding" in r["error"]

    def test_place_missing_bin_id_fails(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        self._pick_first(ex)
        r = ex.execute("place_in_bin", {})
        assert r["success"] is False


# ---------------------------------------------------------------------------
# reset_workcell
# ---------------------------------------------------------------------------


class TestResetWorkcell:
    def test_reset_stops_conveyor(self) -> None:
        ex = _make_executor()
        ex._conveyor.start(0.5)
        ex.execute("reset_workcell", {})
        assert ex._conveyor.running is False

    def test_reset_clears_holding_state(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        ex.execute("pick_target", {"object_id": "obj_1"})
        ex.execute("reset_workcell", {})
        assert ex.is_holding is False

    def test_reset_clears_bin_counts(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1"), _make_object("obj_2")])
        ex.execute("pick_target", {"object_id": "obj_1"})
        ex.execute("place_in_bin", {"bin_id": "bin_a"})
        ex.execute("reset_workcell", {})
        assert ex._bins.get("bin_a").count == 0

    def test_reset_clears_workcell_objects(self) -> None:
        ex = _make_executor(objects=[_make_object("obj_1")])
        ex.execute("reset_workcell", {})
        assert ex._workcell_state.object_count() == 0

    def test_reset_returns_success(self) -> None:
        ex = _make_executor()
        r = ex.execute("reset_workcell", {})
        assert r["success"] is True


# ---------------------------------------------------------------------------
# Unknown action
# ---------------------------------------------------------------------------


class TestUnknownAction:
    def test_unknown_action_returns_failure(self) -> None:
        ex = _make_executor()
        r = ex.execute("fly_to_moon", {})
        assert r["success"] is False
        assert "unknown action" in r["error"]


# ---------------------------------------------------------------------------
# execute_plan
# ---------------------------------------------------------------------------


class TestExecutePlan:
    def test_execute_empty_plan(self) -> None:
        ex = _make_executor()
        results = ex.execute_plan([])
        assert results == []

    def test_execute_plan_returns_one_result_per_action(self) -> None:
        ex = _make_executor()
        plan = [
            {"action": "stop_conveyor", "parameters": {}},
            {"action": "inspect_workcell", "parameters": {}},
        ]
        results = ex.execute_plan(plan)
        assert len(results) == 2

    def test_execute_plan_all_succeed(self) -> None:
        ex = _make_executor()
        plan = [
            {"action": "start_conveyor", "parameters": {"speed": 0.5}},
            {"action": "stop_conveyor", "parameters": {}},
        ]
        results = ex.execute_plan(plan)
        assert all(r["success"] for r in results)


# ---------------------------------------------------------------------------
# Scripted stop-pick-place-restart cycle (Task 3.3 acceptance test)
# ---------------------------------------------------------------------------


class TestScriptedCycle:
    def test_full_stop_pick_place_restart(self) -> None:
        """
        Deterministic scripted sequence driven by executor calls only,
        no planner or LLM involvement.
        """
        ex = _make_executor(objects=[_make_object("obj_1")])

        # Conveyor starts stopped by default.
        assert ex._conveyor.running is False

        # 1. Start conveyor.
        r = ex.execute("start_conveyor", {"speed": 0.3})
        assert r["success"] is True
        assert ex._conveyor.running is True

        # 2. Stop conveyor before picking.
        r = ex.execute("stop_conveyor", {})
        assert r["success"] is True
        assert ex._conveyor.running is False

        # 3. Pick target.
        r = ex.execute("pick_target", {"object_id": "obj_1"})
        assert r["success"] is True
        assert ex.holding_object_id == "obj_1"
        assert not ex._workcell_state.has_object("obj_1")

        # 4. Place in bin.
        r = ex.execute("place_in_bin", {"bin_id": "bin_a"})
        assert r["success"] is True
        assert ex._bins.get("bin_a").count == 1
        assert not ex.is_holding

        # 5. Restart conveyor.
        r = ex.execute("start_conveyor", {"speed": 0.3})
        assert r["success"] is True
        assert ex._conveyor.running is True

    def test_cycle_is_repeatable(self) -> None:
        """Running two cycles updates bin counts correctly."""
        ex = _make_executor(objects=[_make_object("obj_1"), _make_object("obj_2")])

        for obj_id in ("obj_1", "obj_2"):
            ex.execute("stop_conveyor", {})
            ex.execute("pick_target", {"object_id": obj_id})
            ex.execute("place_in_bin", {"bin_id": "bin_b"})
            ex.execute("start_conveyor", {"speed": 0.3})

        assert ex._bins.get("bin_b").count == 2
        assert ex._workcell_state.object_count() == 0
