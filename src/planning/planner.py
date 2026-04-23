"""Deterministic rule-based planner for Prototype 2.1.

Converts a WorkcellState read model into an ordered list of explicit actions.
Pure and stateless: the same input always produces the same output.

Architectural position:
    State (read model) → Planner → Action Schema → Safety → Executor

This module must not:
    - execute actions
    - mutate state
    - access PyBullet or simulation internals
    - bypass the safety layer
    - use LLMs or learned policies
    - maintain hidden state between calls
"""

from __future__ import annotations

from typing import Any

from src.planning.errors import PlanningError
from src.planning.rules import (
    is_plannable_object,
    make_pick_action,
    make_place_action,
    resolve_target_bin,
    sort_plannable_objects,
)
from src.planning.types import Action, Plan


class Planner:
    """Deterministic rule-based planner.

    Stateless class.  Every call to ``plan()`` is independent.
    """

    def plan(self, state: Any) -> Plan:
        """Convert workcell state into an explicit ordered action plan.

        Parameters
        ----------
        state:
            A WorkcellState read model (Phase 2).  Must expose
            ``list_objects() -> List[SpawnedObject]``.

        Returns
        -------
        Plan
            An ordered list of pick_target / place_in_bin actions.
            Returns an empty plan when no eligible objects exist.

        Raises
        ------
        PlanningError
            When the state is None, missing required interface, contains
            objects with missing required fields, or contains duplicate IDs.
        """
        if state is None:
            raise PlanningError("Invalid state: state is None")

        try:
            objects = state.list_objects()
        except AttributeError:
            raise PlanningError("Invalid state: missing list_objects()")

        self._validate_objects(objects)

        eligible = [o for o in objects if is_plannable_object(o)]
        ordered = sort_plannable_objects(eligible)

        actions: list[Action] = []
        for obj in ordered:
            target_bin = resolve_target_bin(obj.color)
            actions.append(make_pick_action(obj.id))
            actions.append(make_place_action(target_bin))

        return Plan(actions=actions)

    def _validate_objects(self, objects: Any) -> None:
        """Validate structural integrity of the object list."""
        seen_ids: set[str] = set()
        for obj in objects:
            obj_id = getattr(obj, "id", None)
            if obj_id is None:
                raise PlanningError("Invalid state: object missing id field")
            if not hasattr(obj, "color"):
                raise PlanningError(
                    f"Invalid state: object {obj_id!r} missing color field"
                )
            if obj_id in seen_ids:
                raise PlanningError(
                    f"Invalid state: duplicate object_id {obj_id!r}"
                )
            seen_ids.add(obj_id)
