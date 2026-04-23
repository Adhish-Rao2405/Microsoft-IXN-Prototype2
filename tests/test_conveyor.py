"""Tests for src/simulation/conveyor.py – Task 1.1."""

from __future__ import annotations

import pytest

from src.simulation.conveyor import Conveyor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conveyor_with_object(
    object_id: str = "obj_1",
    position: list[float] | None = None,
) -> Conveyor:
    c = Conveyor()
    c.register(object_id, position or [0.0, 0.0, 0.5])
    return c


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_not_running_at_creation(self) -> None:
        c = Conveyor()
        assert c.running is False

    def test_speed_zero_at_creation(self) -> None:
        c = Conveyor()
        assert c.speed == 0.0

    def test_no_registered_objects_at_creation(self) -> None:
        c = Conveyor()
        assert c.registered_ids() == []


# ---------------------------------------------------------------------------
# start() / stop()
# ---------------------------------------------------------------------------


class TestStartStop:
    def test_start_sets_running_true(self) -> None:
        c = Conveyor()
        c.start(0.5)
        assert c.running is True

    def test_start_sets_speed(self) -> None:
        c = Conveyor()
        c.start(1.2)
        assert c.speed == pytest.approx(1.2)

    def test_stop_sets_running_false(self) -> None:
        c = Conveyor()
        c.start(0.5)
        c.stop()
        assert c.running is False

    def test_stop_resets_speed_to_zero(self) -> None:
        c = Conveyor()
        c.start(0.5)
        c.stop()
        assert c.speed == pytest.approx(0.0)

    def test_start_with_zero_speed_raises(self) -> None:
        c = Conveyor()
        with pytest.raises(ValueError):
            c.start(0.0)

    def test_start_with_negative_speed_raises(self) -> None:
        c = Conveyor()
        with pytest.raises(ValueError):
            c.start(-1.0)


# ---------------------------------------------------------------------------
# step() – objects move only while running
# ---------------------------------------------------------------------------


class TestStep:
    def test_object_does_not_move_when_stopped(self) -> None:
        c = _make_conveyor_with_object("obj_1", [0.0, 0.0, 0.5])
        c.step(1.0)
        assert c.get_position("obj_1") == pytest.approx([0.0, 0.0, 0.5])

    def test_object_moves_along_x_when_running(self) -> None:
        c = _make_conveyor_with_object("obj_1", [0.0, 0.0, 0.5])
        c.start(1.0)
        c.step(1.0)
        pos = c.get_position("obj_1")
        assert pos[0] == pytest.approx(1.0)

    def test_movement_is_x_axis_only(self) -> None:
        c = _make_conveyor_with_object("obj_1", [0.0, 2.0, 0.5])
        c.start(1.0)
        c.step(1.0)
        pos = c.get_position("obj_1")
        assert pos[1] == pytest.approx(2.0), "Y must not change"
        assert pos[2] == pytest.approx(0.5), "Z must not change"

    def test_movement_scales_with_speed(self) -> None:
        c = _make_conveyor_with_object("obj_1", [0.0, 0.0, 0.0])
        c.start(2.5)
        c.step(0.4)
        assert c.get_position("obj_1")[0] == pytest.approx(1.0)

    def test_movement_scales_with_dt(self) -> None:
        c = _make_conveyor_with_object("obj_1", [0.0, 0.0, 0.0])
        c.start(1.0)
        c.step(0.1)
        c.step(0.1)
        c.step(0.1)
        assert c.get_position("obj_1")[0] == pytest.approx(0.3)

    def test_stop_freezes_motion(self) -> None:
        c = _make_conveyor_with_object("obj_1", [0.0, 0.0, 0.0])
        c.start(1.0)
        c.step(0.5)
        c.stop()
        pos_after_stop = c.get_position("obj_1")[0]
        c.step(1.0)
        assert c.get_position("obj_1")[0] == pytest.approx(pos_after_stop)

    def test_multiple_objects_all_move(self) -> None:
        c = Conveyor()
        c.register("obj_1", [0.0, 0.0, 0.0])
        c.register("obj_2", [1.0, 0.0, 0.0])
        c.start(1.0)
        c.step(1.0)
        assert c.get_position("obj_1")[0] == pytest.approx(1.0)
        assert c.get_position("obj_2")[0] == pytest.approx(2.0)

    def test_step_no_op_with_no_objects(self) -> None:
        c = Conveyor()
        c.start(1.0)
        c.step(1.0)  # must not raise


# ---------------------------------------------------------------------------
# Object registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_register_adds_object(self) -> None:
        c = Conveyor()
        c.register("obj_1", [1.0, 2.0, 3.0])
        assert "obj_1" in c.registered_ids()

    def test_get_position_returns_initial_position(self) -> None:
        c = Conveyor()
        c.register("obj_1", [1.0, 2.0, 3.0])
        assert c.get_position("obj_1") == pytest.approx([1.0, 2.0, 3.0])

    def test_register_copies_position_list(self) -> None:
        """Mutating the caller's list must not affect the stored position."""
        original = [0.0, 0.0, 0.0]
        c = Conveyor()
        c.register("obj_1", original)
        original[0] = 99.0
        assert c.get_position("obj_1")[0] == pytest.approx(0.0)

    def test_get_position_unknown_id_raises(self) -> None:
        c = Conveyor()
        with pytest.raises(KeyError):
            c.get_position("nonexistent")

    def test_unregister_removes_object(self) -> None:
        c = Conveyor()
        c.register("obj_1", [0.0, 0.0, 0.0])
        c.unregister("obj_1")
        assert "obj_1" not in c.registered_ids()

    def test_unregister_unknown_id_does_not_raise(self) -> None:
        c = Conveyor()
        c.unregister("nonexistent")  # must not raise

    def test_unregistered_object_excluded_from_step(self) -> None:
        c = Conveyor()
        c.register("obj_1", [0.0, 0.0, 0.0])
        c.register("obj_2", [0.0, 0.0, 0.0])
        c.unregister("obj_2")
        c.start(1.0)
        c.step(1.0)
        assert c.get_position("obj_1")[0] == pytest.approx(1.0)
        with pytest.raises(KeyError):
            c.get_position("obj_2")
