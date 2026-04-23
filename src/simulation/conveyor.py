"""Conveyor belt simulation – moves registered objects along the X-axis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class _ObjectState:
    """Tracks the mutable position of a registered object."""

    position: List[float]  # [x, y, z]


class Conveyor:
    """
    Standalone conveyor simulation.

    Objects are registered with an initial position.  While the conveyor is
    running, each call to ``step(dt)`` advances every registered object along
    the positive X-axis by ``speed * dt`` metres.

    This class has no dependency on PyBullet or any agent/planner module.
    It is designed to be unit-testable in isolation and later integrated into
    the live simulation by an adapter that reads positions back from
    ``get_position`` and writes them to PyBullet body transforms.
    """

    def __init__(self) -> None:
        self._objects: Dict[str, _ObjectState] = {}
        self._running: bool = False
        self._speed: float = 0.0

    # ------------------------------------------------------------------
    # Public state properties
    # ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        """``True`` while the conveyor is moving."""
        return self._running

    @property
    def speed(self) -> float:
        """Current belt speed in metres per second (0.0 when stopped)."""
        return self._speed

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def start(self, speed: float) -> None:
        """Start the belt at *speed* metres per second (must be > 0)."""
        if speed <= 0:
            raise ValueError(f"speed must be positive, got {speed!r}")
        self._speed = speed
        self._running = True

    def stop(self) -> None:
        """Stop the belt.  Registered object positions are frozen."""
        self._running = False
        self._speed = 0.0

    def step(self, dt: float) -> None:
        """
        Advance the simulation by *dt* seconds.

        If the conveyor is running every registered object is moved along the
        positive X-axis by ``speed * dt``.  If the conveyor is stopped this
        is a no-op.
        """
        if not self._running:
            return
        dx = self._speed * dt
        for state in self._objects.values():
            state.position[0] += dx

    # ------------------------------------------------------------------
    # Object registry
    # ------------------------------------------------------------------

    def register(self, object_id: str, position: List[float]) -> None:
        """
        Register *object_id* with an initial *position* ``[x, y, z]``.

        A copy of the position list is stored so that the caller's list is
        not mutated.
        """
        self._objects[object_id] = _ObjectState(position=list(position))

    def unregister(self, object_id: str) -> None:
        """Remove *object_id* from the conveyor registry."""
        self._objects.pop(object_id, None)

    def get_position(self, object_id: str) -> List[float]:
        """Return the current ``[x, y, z]`` position of *object_id*."""
        try:
            return list(self._objects[object_id].position)
        except KeyError:
            raise KeyError(f"Object {object_id!r} is not registered on the conveyor")

    def registered_ids(self) -> List[str]:
        """Return a list of all currently registered object IDs."""
        return list(self._objects.keys())
