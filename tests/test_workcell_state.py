"""Tests for src/simulation/workcell_state.py – Phase 2."""

from __future__ import annotations

import pytest

from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_conveyor(running: bool = False, speed: float = 0.0) -> Conveyor:
    c = Conveyor()
    if running:
        c.start(speed if speed > 0 else 1.0)
    return c


def _make_object(obj_id: str = "obj_1", on_conveyor: bool = True) -> SpawnedObject:
    return SpawnedObject(
        id=obj_id,
        type="cube",
        color="red",
        position=[0.1, 0.0, 0.5],
        on_conveyor=on_conveyor,
    )


def _make_bins() -> BinRegistry:
    return BinRegistry()


def _make_state(
    objects: list[SpawnedObject] | None = None,
    conveyor: Conveyor | None = None,
    bins: BinRegistry | None = None,
) -> WorkcellState:
    return WorkcellState(
        conveyor=conveyor or _make_conveyor(),
        objects=objects or [],
        bins=bins or _make_bins(),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_can_construct_with_empty_objects(self) -> None:
        ws = _make_state()
        assert ws.object_count() == 0

    def test_can_construct_with_list_of_objects(self) -> None:
        objs = [_make_object("obj_1"), _make_object("obj_2")]
        ws = _make_state(objects=objs)
        assert ws.object_count() == 2

    def test_can_construct_with_dict_of_objects(self) -> None:
        objs = {"obj_1": _make_object("obj_1"), "obj_2": _make_object("obj_2")}
        ws = WorkcellState(
            conveyor=_make_conveyor(),
            objects=objs,
            bins=_make_bins(),
        )
        assert ws.object_count() == 2

    def test_construction_does_not_mutate_input_list(self) -> None:
        obj = _make_object("obj_1")
        source = [obj]
        ws = _make_state(objects=source)
        source.clear()
        assert ws.object_count() == 1

    def test_construction_does_not_mutate_input_dict(self) -> None:
        obj = _make_object("obj_1")
        source = {"obj_1": obj}
        ws = WorkcellState(
            conveyor=_make_conveyor(),
            objects=source,
            bins=_make_bins(),
        )
        source.clear()
        assert ws.object_count() == 1


# ---------------------------------------------------------------------------
# Object lookup
# ---------------------------------------------------------------------------


class TestObjectLookup:
    def test_get_object_returns_correct_object(self) -> None:
        obj = _make_object("obj_1")
        ws = _make_state(objects=[obj])
        result = ws.get_object("obj_1")
        assert result.id == "obj_1"

    def test_get_object_unknown_id_raises_key_error(self) -> None:
        ws = _make_state()
        with pytest.raises(KeyError):
            ws.get_object("nonexistent")

    def test_get_object_empty_string_raises_key_error(self) -> None:
        ws = _make_state()
        with pytest.raises(KeyError):
            ws.get_object("")

    def test_has_object_true_for_known_id(self) -> None:
        ws = _make_state(objects=[_make_object("obj_1")])
        assert ws.has_object("obj_1") is True

    def test_has_object_false_for_unknown_id(self) -> None:
        ws = _make_state()
        assert ws.has_object("obj_99") is False

    def test_has_object_false_after_removal(self) -> None:
        ws = _make_state(objects=[_make_object("obj_1")])
        ws.remove_object("obj_1")
        assert ws.has_object("obj_1") is False


# ---------------------------------------------------------------------------
# Object listing
# ---------------------------------------------------------------------------


class TestObjectListing:
    def test_list_objects_empty(self) -> None:
        ws = _make_state()
        assert ws.list_objects() == []

    def test_list_objects_returns_all(self) -> None:
        objs = [_make_object("obj_1"), _make_object("obj_2"), _make_object("obj_3")]
        ws = _make_state(objects=objs)
        ids = [o.id for o in ws.list_objects()]
        assert set(ids) == {"obj_1", "obj_2", "obj_3"}

    def test_list_objects_order_is_stable(self) -> None:
        """Listing must return a deterministic sorted order regardless of insertion."""
        objs = [_make_object("obj_3"), _make_object("obj_1"), _make_object("obj_2")]
        ws = _make_state(objects=objs)
        ids = [o.id for o in ws.list_objects()]
        assert ids == sorted(ids)

    def test_object_count_matches_list_length(self) -> None:
        objs = [_make_object(f"obj_{i}") for i in range(5)]
        ws = _make_state(objects=objs)
        assert ws.object_count() == len(ws.list_objects())


# ---------------------------------------------------------------------------
# Minimal mutation helpers
# ---------------------------------------------------------------------------


class TestMutationHelpers:
    def test_register_object_adds_to_state(self) -> None:
        ws = _make_state()
        ws.register_object(_make_object("obj_1"))
        assert ws.has_object("obj_1")

    def test_register_object_replaces_existing(self) -> None:
        obj_v1 = SpawnedObject(id="obj_1", type="cube", color="red",
                               position=[0.0, 0.0, 0.0], on_conveyor=True)
        obj_v2 = SpawnedObject(id="obj_1", type="cylinder", color="blue",
                               position=[1.0, 0.0, 0.0], on_conveyor=False)
        ws = _make_state(objects=[obj_v1])
        ws.register_object(obj_v2)
        assert ws.get_object("obj_1").type == "cylinder"

    def test_remove_object_removes_it(self) -> None:
        ws = _make_state(objects=[_make_object("obj_1")])
        ws.remove_object("obj_1")
        assert not ws.has_object("obj_1")
        assert ws.object_count() == 0

    def test_remove_unknown_object_does_not_raise(self) -> None:
        ws = _make_state()
        ws.remove_object("nonexistent")  # must not raise


# ---------------------------------------------------------------------------
# Conveyor snapshot
# ---------------------------------------------------------------------------


class TestConveyorSnapshot:
    def test_conveyor_snapshot_stopped(self) -> None:
        ws = _make_state(conveyor=_make_conveyor(running=False))
        snap = ws.conveyor_snapshot()
        assert snap["running"] is False
        assert snap["speed"] == 0.0

    def test_conveyor_snapshot_running(self) -> None:
        c = _make_conveyor(running=True, speed=0.5)
        ws = _make_state(conveyor=c)
        snap = ws.conveyor_snapshot()
        assert snap["running"] is True
        assert snap["speed"] == pytest.approx(0.5)

    def test_conveyor_snapshot_reflects_live_state(self) -> None:
        """Snapshot must reflect the conveyor's current state at call time."""
        c = _make_conveyor(running=False)
        ws = _make_state(conveyor=c)
        assert ws.conveyor_snapshot()["running"] is False
        c.start(1.0)
        assert ws.conveyor_snapshot()["running"] is True

    def test_conveyor_snapshot_has_required_keys(self) -> None:
        snap = _make_state().conveyor_snapshot()
        assert "running" in snap
        assert "speed" in snap


# ---------------------------------------------------------------------------
# Bin snapshot
# ---------------------------------------------------------------------------


class TestBinSnapshot:
    def test_bin_snapshot_contains_both_bins(self) -> None:
        ws = _make_state()
        ids = {entry["bin_id"] for entry in ws.bin_snapshot()}
        assert ids == {"bin_a", "bin_b"}

    def test_bin_snapshot_reflects_current_counts(self) -> None:
        bins = _make_bins()
        bins.increment("bin_a")
        bins.increment("bin_a")
        ws = _make_state(bins=bins)
        snap = {entry["bin_id"]: entry for entry in ws.bin_snapshot()}
        assert snap["bin_a"]["count"] == 2
        assert snap["bin_b"]["count"] == 0

    def test_bin_snapshot_reflects_live_bin_state(self) -> None:
        bins = _make_bins()
        ws = _make_state(bins=bins)
        assert ws.bin_snapshot()[0]["count"] == 0 or True  # initial
        bins.increment("bin_a")
        snap = {e["bin_id"]: e for e in ws.bin_snapshot()}
        assert snap["bin_a"]["count"] == 1

    def test_bin_snapshot_entries_have_required_keys(self) -> None:
        for entry in _make_state().bin_snapshot():
            assert "bin_id" in entry
            assert "position" in entry
            assert "count" in entry

    def test_bin_snapshot_is_sorted(self) -> None:
        ids = [e["bin_id"] for e in _make_state().bin_snapshot()]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Objects snapshot
# ---------------------------------------------------------------------------


class TestObjectsSnapshot:
    def test_objects_snapshot_empty(self) -> None:
        ws = _make_state()
        assert ws.objects_snapshot() == []

    def test_objects_snapshot_contains_all_objects(self) -> None:
        objs = [_make_object("obj_1"), _make_object("obj_2")]
        ws = _make_state(objects=objs)
        ids = {e["id"] for e in ws.objects_snapshot()}
        assert ids == {"obj_1", "obj_2"}

    def test_objects_snapshot_is_sorted_by_id(self) -> None:
        objs = [_make_object("obj_3"), _make_object("obj_1"), _make_object("obj_2")]
        ws = _make_state(objects=objs)
        ids = [e["id"] for e in ws.objects_snapshot()]
        assert ids == sorted(ids)

    def test_objects_snapshot_entries_have_required_keys(self) -> None:
        ws = _make_state(objects=[_make_object("obj_1")])
        for entry in ws.objects_snapshot():
            for key in ("id", "type", "color", "position", "on_conveyor"):
                assert key in entry

    def test_objects_snapshot_contains_only_json_primitives(self) -> None:
        ws = _make_state(objects=[_make_object("obj_1")])
        for entry in ws.objects_snapshot():
            for v in entry.values():
                assert isinstance(v, (str, int, float, bool, list, dict, type(None)))


# ---------------------------------------------------------------------------
# Whole-system to_dict snapshot
# ---------------------------------------------------------------------------


class TestToDict:
    def test_to_dict_has_top_level_sections(self) -> None:
        snap = _make_state().to_dict()
        assert "conveyor" in snap
        assert "objects" in snap
        assert "bins" in snap

    def test_to_dict_no_extra_top_level_keys(self) -> None:
        snap = _make_state().to_dict()
        assert set(snap.keys()) == {"conveyor", "objects", "bins"}

    def test_to_dict_conveyor_section_correct(self) -> None:
        c = _make_conveyor(running=True, speed=2.0)
        snap = _make_state(conveyor=c).to_dict()
        assert snap["conveyor"]["running"] is True
        assert snap["conveyor"]["speed"] == pytest.approx(2.0)

    def test_to_dict_objects_section_correct(self) -> None:
        objs = [_make_object("obj_1")]
        snap = _make_state(objects=objs).to_dict()
        assert len(snap["objects"]) == 1
        assert snap["objects"][0]["id"] == "obj_1"

    def test_to_dict_bins_section_correct(self) -> None:
        bins = _make_bins()
        bins.increment("bin_b")
        snap = _make_state(bins=bins).to_dict()
        by_id = {e["bin_id"]: e for e in snap["bins"]}
        assert by_id["bin_b"]["count"] == 1

    def test_to_dict_is_deterministic(self) -> None:
        """Same input must produce identical snapshots."""
        objs = [_make_object("obj_1"), _make_object("obj_2")]
        ws = _make_state(objects=objs)
        assert ws.to_dict() == ws.to_dict()

    def test_to_dict_contains_only_json_friendly_types(self) -> None:
        def _assert_json_friendly(obj: object, path: str = "root") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    _assert_json_friendly(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    _assert_json_friendly(v, f"{path}[{i}]")
            else:
                assert isinstance(obj, (str, int, float, bool, type(None))), (
                    f"Non-JSON value at {path}: {type(obj)}"
                )

        objs = [_make_object("obj_1")]
        ws = _make_state(objects=objs)
        _assert_json_friendly(ws.to_dict())


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------


class TestIsolation:
    def test_no_pybullet_import(self) -> None:
        import ast
        import pathlib

        src = pathlib.Path(
            "src/simulation/workcell_state.py"
        ).read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "pybullet" not in alias.name.lower()
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "pybullet" not in node.module.lower()

    def test_no_planner_or_agent_import(self) -> None:
        import ast
        import pathlib

        src = pathlib.Path(
            "src/simulation/workcell_state.py"
        ).read_text()
        tree = ast.parse(src)
        forbidden = ("planner", "agent", "executor", "web_ui", "openai", "foundry")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for f in forbidden:
                        assert f not in alias.name.lower()
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for f in forbidden:
                        assert f not in node.module.lower()
