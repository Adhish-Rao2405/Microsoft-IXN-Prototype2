"""Planning-side value types.

Action uses the field name ``action`` (not ``type``) to align exactly with the
Phase 3 workcell action schema wire format: {"action": "...", "parameters": {...}}.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Action:
    """A single fully-explicit workcell action."""

    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "parameters": dict(self.parameters)}


@dataclass
class Plan:
    """An ordered list of explicit actions."""

    actions: List[Action] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"actions": [a.to_dict() for a in self.actions]}

    def __len__(self) -> int:
        return len(self.actions)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Plan):
            return NotImplemented
        return self.to_dict() == other.to_dict()
