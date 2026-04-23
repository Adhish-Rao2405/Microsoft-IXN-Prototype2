"""Object spawner – produces red cubes and blue cylinders at a fixed interval."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Supported object classes
# ---------------------------------------------------------------------------

OBJECT_CLASSES: List[Dict[str, str]] = [
    {"type": "cube", "color": "red"},
    {"type": "cylinder", "color": "blue"},
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SpawnedObject:
    """Immutable record for a single spawned object."""

    id: str
    type: str
    color: str
    position: List[float]
    on_conveyor: bool = True

    def to_dict(self) -> dict:
        """Return a JSON-compatible representation."""
        return {
            "id": self.id,
            "type": self.type,
            "color": self.color,
            "position": list(self.position),
            "on_conveyor": self.on_conveyor,
        }


# ---------------------------------------------------------------------------
# Spawner
# ---------------------------------------------------------------------------


class Spawner:
    """
    Standalone object spawner driven by simulated elapsed time.

    The spawner has **no** PyBullet dependency and **no** wall-clock dependency.
    It is designed to be unit-testable in isolation and later integrated into
    the live simulation by an adapter that reads ``pending`` objects and inserts
    them into the PyBullet scene.

    Parameters
    ----------
    interval:
        How many simulated seconds must elapse between spawns.
    spawn_position:
        ``[x, y, z]`` position assigned to every freshly-spawned object.
        Defaults to ``[0.0, 0.0, 0.5]`` (start of a typical conveyor).
    seed:
        Optional integer seed for the internal PRNG.  When the same seed is
        supplied, the spawner always produces the same sequence of object
        classes, making tests fully deterministic.
    """

    def __init__(
        self,
        interval: float = 2.0,
        spawn_position: Optional[List[float]] = None,
        seed: Optional[int] = None,
    ) -> None:
        if interval <= 0:
            raise ValueError(f"interval must be positive, got {interval!r}")
        self._interval = interval
        self._spawn_position: List[float] = list(spawn_position or [0.0, 0.0, 0.5])
        self._rng = random.Random(seed)
        self._elapsed: float = 0.0
        self._counter: int = 0
        self._pending: List[SpawnedObject] = []

    # ------------------------------------------------------------------
    # Public state
    # ------------------------------------------------------------------

    @property
    def interval(self) -> float:
        """Configured spawn interval in simulated seconds."""
        return self._interval

    @property
    def elapsed(self) -> float:
        """Simulated time accumulated since the last spawn (or since init)."""
        return self._elapsed

    @property
    def total_spawned(self) -> int:
        """Total number of objects spawned so far."""
        return self._counter

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def step(self, dt: float) -> List[SpawnedObject]:
        """
        Advance simulated time by *dt* seconds.

        Returns a list of newly-spawned objects (may be empty).  Each call
        to ``step`` can produce at most one object; if the interval would be
        exceeded multiple times by a single large *dt* only one object is
        produced and the remainder carries forward.
        """
        if dt < 0:
            raise ValueError(f"dt must be non-negative, got {dt!r}")
        self._elapsed += dt
        newly_spawned: List[SpawnedObject] = []
        if self._elapsed >= self._interval:
            self._elapsed -= self._interval
            obj = self._spawn_one()
            newly_spawned.append(obj)
            self._pending.append(obj)
        return newly_spawned

    def drain_pending(self) -> List[SpawnedObject]:
        """
        Return all objects that have been spawned but not yet consumed by an
        integration layer, and clear the pending list.
        """
        objects = list(self._pending)
        self._pending.clear()
        return objects

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _spawn_one(self) -> SpawnedObject:
        self._counter += 1
        cls = self._rng.choice(OBJECT_CLASSES)
        return SpawnedObject(
            id=f"obj_{self._counter}",
            type=cls["type"],
            color=cls["color"],
            position=list(self._spawn_position),
            on_conveyor=True,
        )
