"""Workcell state abstraction – canonical read model for the simulation."""

from __future__ import annotations

from typing import Dict, List, Optional

from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject


class WorkcellState:
    """
    Deterministic, read-oriented workcell state model.

    Aggregates the current state of the three Phase 1 simulation primitives
    (conveyor, tracked objects, bins) into a single queryable snapshot layer.

    This class is a *read model only*.  It does not step the simulation, does
    not route objects, does not assign bins, and does not invoke any planner,
    agent, executor, or LLM logic.

    Parameters
    ----------
    conveyor:
        A ``Conveyor`` instance whose current ``running`` and ``speed``
        properties are used for snapshots.
    objects:
        Mapping of ``object_id → SpawnedObject`` (or any compatible list/dict
        of objects that have ``id``, ``type``, ``color``, ``position``, and
        ``on_conveyor`` attributes).  A copy is taken at construction time.
    bins:
        A ``BinRegistry`` instance whose current state is used for snapshots.
    """

    def __init__(
        self,
        conveyor: Conveyor,
        objects: List[SpawnedObject] | Dict[str, SpawnedObject],
        bins: BinRegistry,
    ) -> None:
        self._conveyor = conveyor
        self._bins = bins

        # Normalise the object input into a keyed dict.
        if isinstance(objects, dict):
            self._objects: Dict[str, SpawnedObject] = dict(objects)
        else:
            self._objects = {obj.id: obj for obj in objects}

    # ------------------------------------------------------------------
    # Object query API
    # ------------------------------------------------------------------

    def get_object(self, object_id: str) -> SpawnedObject:
        """Return the ``SpawnedObject`` for *object_id*.

        Raises
        ------
        KeyError
            If *object_id* is not known.
        """
        try:
            return self._objects[object_id]
        except KeyError:
            raise KeyError(f"Unknown object_id {object_id!r}") from None

    def has_object(self, object_id: str) -> bool:
        """Return ``True`` if *object_id* is currently tracked."""
        return object_id in self._objects

    def list_objects(self) -> List[SpawnedObject]:
        """Return all tracked objects in stable (insertion/id-sorted) order."""
        return [self._objects[k] for k in sorted(self._objects)]

    def object_count(self) -> int:
        """Return the total number of tracked objects."""
        return len(self._objects)

    # ------------------------------------------------------------------
    # Minimal factual mutation helpers
    # ------------------------------------------------------------------

    def register_object(self, obj: SpawnedObject) -> None:
        """Add *obj* to the tracked object set."""
        self._objects[obj.id] = obj

    def remove_object(self, object_id: str) -> None:
        """Remove *object_id* from the tracked set.  No-op if absent."""
        self._objects.pop(object_id, None)

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def conveyor_snapshot(self) -> dict:
        """Return a JSON-friendly snapshot of current conveyor state."""
        return {
            "running": self._conveyor.running,
            "speed": self._conveyor.speed,
        }

    def objects_snapshot(self) -> List[dict]:
        """Return a JSON-friendly list of all tracked objects, sorted by id."""
        return [obj.to_dict() for obj in self.list_objects()]

    def bin_snapshot(self) -> List[dict]:
        """Return a JSON-friendly list of all bin records."""
        return self._bins.to_list()

    def to_dict(self) -> dict:
        """Return a deterministic JSON-friendly whole-system snapshot."""
        return {
            "conveyor": self.conveyor_snapshot(),
            "objects": self.objects_snapshot(),
            "bins": self.bin_snapshot(),
        }
