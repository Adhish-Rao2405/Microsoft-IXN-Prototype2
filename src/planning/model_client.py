"""Phase 10 — Model client protocol.

Defines the interface for any LLM/SLM client used by ModelPlanner.
No network calls. No Foundry Local dependency. Tests use FakeModelClient.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ModelClient(Protocol):
    """Minimal interface for a model completion client."""

    def complete(self, prompt: str) -> str:
        """Send *prompt* and return the raw response text."""
        ...
