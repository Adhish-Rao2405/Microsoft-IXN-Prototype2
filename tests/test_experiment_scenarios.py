"""Phase 14 — Unit tests for experiment scenarios.

6 required tests. No PyBullet. No live model.
"""

from __future__ import annotations

import ast

import pytest

from src.experiments.scenarios import create_scenario
from src.simulation.workcell_state import WorkcellState


def test_baseline_creates_valid_state():
    state = create_scenario("baseline")
    assert isinstance(state, WorkcellState)
    objects = state.list_objects()
    assert len(objects) == 1
    assert objects[0].on_conveyor is True


def test_empty_creates_valid_state():
    state = create_scenario("empty")
    assert isinstance(state, WorkcellState)
    assert state.list_objects() == []


def test_blocked_creates_valid_state():
    state = create_scenario("blocked")
    assert isinstance(state, WorkcellState)
    objects = state.list_objects()
    assert len(objects) == 1
    # The blocked scenario has on_conveyor=False — not plannable
    assert objects[0].on_conveyor is False


def test_unknown_scenario_raises_value_error():
    with pytest.raises(ValueError, match="Unknown scenario"):
        create_scenario("nonexistent_scenario")


def test_scenario_creation_is_deterministic():
    s1 = create_scenario("baseline")
    s2 = create_scenario("baseline")
    assert s1.to_dict() == s2.to_dict()


def test_scenarios_module_has_no_pybullet_import():
    import importlib

    mod = importlib.import_module("src.experiments.scenarios")
    src_path = mod.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "pybullet" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            assert "pybullet" not in (node.module or "")
