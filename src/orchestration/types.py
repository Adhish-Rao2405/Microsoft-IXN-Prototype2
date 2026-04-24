"""Result types for the deterministic workcell pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class PipelineStatus(Enum):
    EMPTY = "empty"
    VALIDATED = "validated"
    EXECUTED = "executed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PipelineResult:
    candidate_actions: List[Any] = field(default_factory=list)
    validated_actions: List[Any] = field(default_factory=list)
    rejected_action: Optional[Any] = None
    rejection_reason: Optional[str] = None
    executed_actions: List[Any] = field(default_factory=list)
    status: PipelineStatus = PipelineStatus.EMPTY