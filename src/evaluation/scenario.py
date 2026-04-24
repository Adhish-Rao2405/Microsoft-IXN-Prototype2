"""Deterministic evaluation scenario model — Phase 8.

An EvaluationScenario is a frozen, declarative description of a single
experiment run.  It contains no planner logic, no callbacks, no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple


@dataclass(frozen=True)
class EvaluationScenario:
    """Immutable description of a single evaluation scenario.

    Parameters
    ----------
    scenario_id:
        Non-empty unique identifier for traceability.
    name:
        Non-empty human-readable name.
    description:
        Free-text description for dissertation notes.
    objects:
        List of object definitions (dicts or SpawnedObject-compatible) that
        will be used to build the initial WorkcellState in the harness.
    max_steps:
        Maximum number of pipeline steps the harness will run.  Must be >= 1.
    expected_success:
        Declarative label only — does NOT force the outcome.
    success_conditions:
        Tuple of string labels for dissertation traceability.
    tags:
        Optional tuple of string labels for grouping/filtering.
    """

    scenario_id: str
    name: str
    description: str
    objects: Tuple[Any, ...]
    max_steps: int
    expected_success: bool
    success_conditions: Tuple[str, ...]
    tags: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.max_steps, int) or self.max_steps < 1:
            raise ValueError("max_steps must be a positive integer")

    @classmethod
    def create(
        cls,
        scenario_id: str,
        name: str,
        description: str,
        objects: list | tuple,
        max_steps: int,
        expected_success: bool,
        success_conditions: list | tuple,
        tags: list | tuple = (),
    ) -> "EvaluationScenario":
        """Convenience factory that accepts lists and converts to tuples."""
        return cls(
            scenario_id=scenario_id,
            name=name,
            description=description,
            objects=tuple(objects),
            max_steps=max_steps,
            expected_success=expected_success,
            success_conditions=tuple(success_conditions),
            tags=tuple(tags),
        )
