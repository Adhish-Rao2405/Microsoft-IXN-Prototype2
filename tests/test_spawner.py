"""Tests for src/simulation/spawner.py – Task 1.2."""

from __future__ import annotations

import pytest

from src.simulation.spawner import OBJECT_CLASSES, Spawner, SpawnedObject

# Convenience set of all supported (type, color) pairs for membership checks.
_VALID_CLASSES = {(c["type"], c["color"]) for c in OBJECT_CLASSES}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spawn_n(spawner: Spawner, n: int) -> list[SpawnedObject]:
    """Step the spawner exactly n full intervals and return all objects."""
    results: list[SpawnedObject] = []
    for _ in range(n):
        results.extend(spawner.step(spawner.interval))
    return results


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_no_objects_before_any_step(self) -> None:
        s = Spawner(interval=1.0)
        assert s.total_spawned == 0

    def test_elapsed_zero_at_creation(self) -> None:
        s = Spawner(interval=1.0)
        assert s.elapsed == pytest.approx(0.0)

    def test_pending_empty_at_creation(self) -> None:
        s = Spawner(interval=1.0)
        assert s.drain_pending() == []

    def test_negative_interval_raises(self) -> None:
        with pytest.raises(ValueError):
            Spawner(interval=-1.0)

    def test_zero_interval_raises(self) -> None:
        with pytest.raises(ValueError):
            Spawner(interval=0.0)


# ---------------------------------------------------------------------------
# Spawn timing
# ---------------------------------------------------------------------------


class TestSpawnTiming:
    def test_no_spawn_before_interval(self) -> None:
        s = Spawner(interval=2.0)
        result = s.step(1.9)
        assert result == []
        assert s.total_spawned == 0

    def test_spawn_exactly_at_interval(self) -> None:
        s = Spawner(interval=2.0)
        result = s.step(2.0)
        assert len(result) == 1
        assert s.total_spawned == 1

    def test_spawn_after_interval_exceeded(self) -> None:
        s = Spawner(interval=2.0)
        result = s.step(2.5)
        assert len(result) == 1
        assert s.total_spawned == 1

    def test_remainder_carries_forward(self) -> None:
        """After one spawn the leftover time should count toward the next."""
        s = Spawner(interval=2.0)
        s.step(2.5)  # spawns once; 0.5 s left over
        result = s.step(1.6)  # 0.5 + 1.6 = 2.1 >= 2.0 → another spawn
        assert len(result) == 1
        assert s.total_spawned == 2

    def test_no_double_spawn_in_single_large_step(self) -> None:
        """A single step that covers multiple intervals still spawns at most one."""
        s = Spawner(interval=1.0)
        result = s.step(10.0)
        assert len(result) == 1

    def test_accumulated_partial_steps_trigger_spawn(self) -> None:
        s = Spawner(interval=1.0)
        s.step(0.4)
        s.step(0.4)
        s.step(0.4)  # total 1.2 >= 1.0
        assert s.total_spawned == 1

    def test_partial_steps_do_not_spawn_too_early(self) -> None:
        s = Spawner(interval=1.0)
        s.step(0.3)
        s.step(0.3)
        s.step(0.3)  # total 0.9 < 1.0
        assert s.total_spawned == 0

    def test_negative_dt_raises(self) -> None:
        s = Spawner(interval=1.0)
        with pytest.raises(ValueError):
            s.step(-0.1)


# ---------------------------------------------------------------------------
# Stable sequential IDs
# ---------------------------------------------------------------------------


class TestObjectIDs:
    def test_first_object_id_is_obj_1(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        result = s.step(1.0)
        assert result[0].id == "obj_1"

    def test_ids_are_sequential(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        ids = [s.step(1.0)[0].id for _ in range(5)]
        assert ids == ["obj_1", "obj_2", "obj_3", "obj_4", "obj_5"]

    def test_ids_never_repeat(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        ids = [s.step(1.0)[0].id for _ in range(20)]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Deterministic behavior under the same seed
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_same_sequence(self) -> None:
        s1 = Spawner(interval=1.0, seed=42)
        s2 = Spawner(interval=1.0, seed=42)
        seq1 = [s1.step(1.0)[0].to_dict() for _ in range(10)]
        seq2 = [s2.step(1.0)[0].to_dict() for _ in range(10)]
        assert seq1 == seq2

    def test_different_seeds_produce_different_sequences(self) -> None:
        s1 = Spawner(interval=1.0, seed=1)
        s2 = Spawner(interval=1.0, seed=2)
        seq1 = [s1.step(1.0)[0].type for _ in range(20)]
        seq2 = [s2.step(1.0)[0].type for _ in range(20)]
        # With 20 objects and only two classes the probability that they are
        # identical by chance is (1/2)^19 ≈ 2 × 10⁻⁶ — safe to assert different.
        assert seq1 != seq2

    def test_no_seed_produces_a_valid_sequence(self) -> None:
        """Unseeded spawner must still produce valid objects (just non-deterministic)."""
        s = Spawner(interval=1.0)
        for _ in range(5):
            result = s.step(1.0)
            assert len(result) == 1
            obj = result[0]
            assert (obj.type, obj.color) in _VALID_CLASSES


# ---------------------------------------------------------------------------
# Object class constraints
# ---------------------------------------------------------------------------


class TestObjectClasses:
    def test_all_spawned_objects_are_valid_classes(self) -> None:
        s = Spawner(interval=1.0, seed=7)
        for _ in range(50):
            result = s.step(1.0)
            assert len(result) == 1
            obj = result[0]
            assert (obj.type, obj.color) in _VALID_CLASSES

    def test_only_red_cubes_and_blue_cylinders_appear(self) -> None:
        s = Spawner(interval=1.0, seed=99)
        objects = _spawn_n(s, 100)
        for obj in objects:
            assert obj.type in {"cube", "cylinder"}
            assert obj.color in {"red", "blue"}
            if obj.type == "cube":
                assert obj.color == "red"
            if obj.type == "cylinder":
                assert obj.color == "blue"


# ---------------------------------------------------------------------------
# Object record shape
# ---------------------------------------------------------------------------


class TestObjectRecord:
    def test_spawned_object_has_required_fields(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        obj = s.step(1.0)[0]
        assert hasattr(obj, "id")
        assert hasattr(obj, "type")
        assert hasattr(obj, "color")
        assert hasattr(obj, "position")
        assert hasattr(obj, "on_conveyor")

    def test_on_conveyor_is_true_at_spawn(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        obj = s.step(1.0)[0]
        assert obj.on_conveyor is True

    def test_position_matches_configured_spawn_position(self) -> None:
        s = Spawner(interval=1.0, seed=0, spawn_position=[1.0, 2.0, 3.0])
        obj = s.step(1.0)[0]
        assert obj.position == pytest.approx([1.0, 2.0, 3.0])

    def test_position_is_independent_copy(self) -> None:
        """Mutating the returned position must not affect subsequent spawns."""
        s = Spawner(interval=1.0, seed=0, spawn_position=[0.0, 0.0, 0.5])
        obj = s.step(1.0)[0]
        obj.position[0] = 99.0
        obj2 = s.step(1.0)[0]
        assert obj2.position[0] == pytest.approx(0.0)

    def test_to_dict_returns_json_compatible_dict(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        obj = s.step(1.0)[0]
        d = obj.to_dict()
        assert isinstance(d, dict)
        for key in ("id", "type", "color", "position", "on_conveyor"):
            assert key in d
        assert isinstance(d["position"], list)
        assert isinstance(d["on_conveyor"], bool)


# ---------------------------------------------------------------------------
# Pending queue / drain
# ---------------------------------------------------------------------------


class TestPendingQueue:
    def test_drain_returns_spawned_objects(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        s.step(1.0)
        pending = s.drain_pending()
        assert len(pending) == 1

    def test_drain_clears_the_queue(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        s.step(1.0)
        s.drain_pending()
        assert s.drain_pending() == []

    def test_drain_accumulates_across_steps(self) -> None:
        s = Spawner(interval=1.0, seed=0)
        s.step(1.0)
        s.step(1.0)
        s.step(1.0)
        pending = s.drain_pending()
        assert len(pending) == 3
