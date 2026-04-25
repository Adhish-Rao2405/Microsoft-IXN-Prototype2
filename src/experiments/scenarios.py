"""Phase 14 — Deterministic experiment scenarios.

Each scenario returns a WorkcellState constructed from existing simulation
primitives.  No PyBullet dependency.  All scenarios are deterministic.
"""

from __future__ import annotations

from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState

_SUPPORTED_SCENARIOS = ("baseline", "empty", "blocked")


def create_scenario(name: str) -> WorkcellState:
    """Return a deterministic WorkcellState for the named scenario.

    Scenarios:
        baseline  — one plannable red cube on the conveyor, conveyor stopped.
        empty     — no objects present.
        blocked   — one object with an unknown/unrouteable color (neither
                    "red" nor "blue"), causing the deterministic planner to
                    produce no actions.

    Args:
        name: One of ``"baseline"``, ``"empty"``, ``"blocked"``.

    Raises:
        ValueError: For any unrecognised scenario name.
    """
    if name == "baseline":
        return _baseline()
    if name == "empty":
        return _empty()
    if name == "blocked":
        return _blocked()
    raise ValueError(
        f"Unknown scenario {name!r}. Supported: {_SUPPORTED_SCENARIOS}"
    )


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------


def _baseline() -> WorkcellState:
    """One red cube on a stopped conveyor; deterministic planner should act."""
    return WorkcellState(
        conveyor=Conveyor(),
        objects=[
            SpawnedObject(
                id="obj_1",
                type="cube",
                color="red",
                position=[0.3, 0.0, 0.1],
                on_conveyor=True,
            )
        ],
        bins=BinRegistry(),
    )


def _empty() -> WorkcellState:
    """No objects; deterministic planner produces an empty plan."""
    return WorkcellState(
        conveyor=Conveyor(),
        objects=[],
        bins=BinRegistry(),
    )


def _blocked() -> WorkcellState:
    """Object not on conveyor (already picked or removed); planner skips it.

    is_plannable_object() requires on_conveyor=True, so this scenario
    produces an empty plan from the deterministic planner — a realistic
    'workcell blocked / nothing actionable' state.
    """
    return WorkcellState(
        conveyor=Conveyor(),
        objects=[
            SpawnedObject(
                id="obj_blocked",
                type="cube",
                color="red",
                position=[0.3, 0.0, 0.1],
                on_conveyor=False,      # not plannable — planner emits no actions
            )
        ],
        bins=BinRegistry(),
    )
