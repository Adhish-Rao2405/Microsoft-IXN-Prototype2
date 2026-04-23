"""Planning-layer error types."""

from __future__ import annotations


class PlanningError(Exception):
    """Raised when the planner receives an invalid state it cannot plan against."""
