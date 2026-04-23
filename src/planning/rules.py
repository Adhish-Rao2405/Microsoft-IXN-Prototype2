"""Deterministic planning rules.

All policy is explicit and table-driven.  There is no dynamic routing,
no learned routing, and no hidden defaults beyond those declared here.

Routing is based on object *color* (the SpawnedObject field), not object
*type* (which is the structural form: cube/cylinder).
"""

from __future__ import annotations

from typing import Any, List

from src.planning.types import Action

# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

BIN_ROUTING: dict[str, str] = {
    "red": "bin_a",
    "blue": "bin_b",
}

DEFAULT_BIN: str = "bin_a"


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def is_plannable_object(obj: Any) -> bool:
    """Return True if the object is eligible for pick+place planning.

    An object is plannable only when it is on the conveyor and available
    for picking.  Objects that have been removed from state, or whose
    on_conveyor flag is False, are skipped.
    """
    return bool(getattr(obj, "on_conveyor", False))


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def sort_plannable_objects(objects: List[Any]) -> List[Any]:
    """Return objects sorted by id in ascending lexical order.

    This is the canonical deterministic ordering rule.  It is stable and
    repeatable regardless of input list order.
    """
    return sorted(objects, key=lambda o: o.id)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def resolve_target_bin(color: str) -> str:
    """Map object color to a target bin_id using the routing table.

    Falls back to DEFAULT_BIN for unrecognised colors.
    Never guesses or infers beyond the explicit table.
    """
    return BIN_ROUTING.get(color, DEFAULT_BIN)


# ---------------------------------------------------------------------------
# Action builders
# ---------------------------------------------------------------------------


def make_pick_action(object_id: str) -> Action:
    """Return a pick_target action for the given object_id."""
    return Action(action="pick_target", parameters={"object_id": object_id})


def make_place_action(bin_id: str) -> Action:
    """Return a place_in_bin action for the given bin_id."""
    return Action(action="place_in_bin", parameters={"bin_id": bin_id})
