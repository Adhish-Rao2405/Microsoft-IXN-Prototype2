"""Phase 13 — Planner selection compatibility tests.

Confirms that the factory-created planners behave identically to
directly-instantiated planners through the existing plan/validate path.
No live Foundry Local required. No actions executed.
"""

from __future__ import annotations

import json

from src.planning.planner import Planner
from src.planning.model_planner import ModelPlanner
from src.planning.planner_factory import create_planner
from src.planning.types import Plan
from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_empty_state() -> WorkcellState:
    return WorkcellState(conveyor=Conveyor(), objects=[], bins=BinRegistry())


def _make_state_with_object() -> WorkcellState:
    return WorkcellState(
        conveyor=Conveyor(),
        objects=[
            SpawnedObject(
                id="obj_1",
                type="cube",
                color="red",
                position=[0.0, 0.0, 0.0],
                on_conveyor=True,
            )
        ],
        bins=BinRegistry(),
    )


class FakeFoundryClient:
    """Fake low-level Foundry transport — no network."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


# ---------------------------------------------------------------------------
# Deterministic path
# ---------------------------------------------------------------------------


class TestDeterministicSelection:
    def test_factory_deterministic_returns_planner_type(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        planner = create_planner(mode="deterministic")
        assert isinstance(planner, Planner)

    def test_factory_deterministic_returns_plan_for_empty_state(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        planner = create_planner(mode="deterministic")
        result = planner.plan(_make_empty_state())
        assert isinstance(result, Plan)
        assert len(result.actions) == 0

    def test_factory_deterministic_returns_plan_for_state_with_object(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        planner = create_planner(mode="deterministic")
        result = planner.plan(_make_state_with_object())
        assert isinstance(result, Plan)
        assert len(result.actions) > 0

    def test_factory_deterministic_matches_direct_instantiation(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        state = _make_state_with_object()
        factory_plan = create_planner(mode="deterministic").plan(state)
        direct_plan = Planner().plan(state)
        assert factory_plan == direct_plan

    def test_factory_default_env_deterministic_matches_direct(self, monkeypatch):
        monkeypatch.setenv("PLANNER_MODE", "deterministic")
        state = _make_empty_state()
        factory_plan = create_planner().plan(state)
        direct_plan = Planner().plan(state)
        assert factory_plan == direct_plan


# ---------------------------------------------------------------------------
# Model path — valid output
# ---------------------------------------------------------------------------


class TestModelSelectionValidOutput:
    def _valid_json(self) -> str:
        return json.dumps({
            "actions": [{"action": "pick_target", "parameters": {"object_id": "obj_1"}}]
        })

    def test_factory_model_returns_model_planner_type(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        fake = FakeFoundryClient(self._valid_json())
        from src.planning.foundry_model_client import FoundryModelClient
        bridge = FoundryModelClient(foundry_client=fake)
        planner = create_planner(mode="model", model_client=bridge)
        assert isinstance(planner, ModelPlanner)

    def test_model_selection_accepts_valid_json_via_existing_parser(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        fake = FakeFoundryClient(self._valid_json())
        from src.planning.foundry_model_client import FoundryModelClient
        bridge = FoundryModelClient(foundry_client=fake)
        planner = create_planner(mode="model", model_client=bridge)
        result = planner.plan(_make_empty_state())
        assert isinstance(result, Plan)
        assert len(result.actions) == 1
        assert result.actions[0].action == "pick_target"

    def test_model_selection_with_env_var_uses_injected_client(self, monkeypatch):
        monkeypatch.setenv("PLANNER_MODE", "model")
        fake = FakeFoundryClient(self._valid_json())
        from src.planning.foundry_model_client import FoundryModelClient
        bridge = FoundryModelClient(foundry_client=fake)
        planner = create_planner(model_client=bridge)
        result = planner.plan(_make_empty_state())
        assert isinstance(result, Plan)
        assert len(result.actions) == 1

    def test_model_selection_calls_foundry_client_once(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        fake = FakeFoundryClient(self._valid_json())
        from src.planning.foundry_model_client import FoundryModelClient
        bridge = FoundryModelClient(foundry_client=fake)
        planner = create_planner(mode="model", model_client=bridge)
        planner.plan(_make_empty_state())
        assert len(fake.calls) == 1


# ---------------------------------------------------------------------------
# Model path — invalid output
# ---------------------------------------------------------------------------


class TestModelSelectionInvalidOutput:
    def test_invalid_json_fails_closed_via_factory(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        fake = FakeFoundryClient("not valid JSON at all")
        from src.planning.foundry_model_client import FoundryModelClient
        bridge = FoundryModelClient(foundry_client=fake)
        planner = create_planner(mode="model", model_client=bridge)
        result = planner.plan(_make_empty_state())
        assert isinstance(result, Plan)
        assert len(result.actions) == 0

    def test_invalid_schema_fails_closed_via_factory(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        bad = json.dumps({"actions": [{"action": "fire_missiles", "parameters": {}}]})
        fake = FakeFoundryClient(bad)
        from src.planning.foundry_model_client import FoundryModelClient
        bridge = FoundryModelClient(foundry_client=fake)
        planner = create_planner(mode="model", model_client=bridge)
        result = planner.plan(_make_empty_state())
        assert isinstance(result, Plan)
        assert len(result.actions) == 0

    def test_invalid_output_sets_rejection_reason(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        fake = FakeFoundryClient("garbage")
        from src.planning.foundry_model_client import FoundryModelClient
        bridge = FoundryModelClient(foundry_client=fake)
        planner = create_planner(mode="model", model_client=bridge)
        planner.plan(_make_empty_state())
        assert planner.last_rejection_reason() is not None

    def test_no_retry_on_invalid_output(self, monkeypatch):
        monkeypatch.delenv("PLANNER_MODE", raising=False)
        fake = FakeFoundryClient("bad json")
        from src.planning.foundry_model_client import FoundryModelClient
        bridge = FoundryModelClient(foundry_client=fake)
        planner = create_planner(mode="model", model_client=bridge)
        planner.plan(_make_empty_state())
        assert len(fake.calls) == 1  # no retry
