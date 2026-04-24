"""Phase 12 — ModelClient-compatible bridge for FoundryLocalClient.

Adapts the existing ModelClient interface:
    complete(prompt: str) -> str

to the FoundryLocalClient interface:
    complete(system_prompt: str, user_prompt: str) -> str

This module is intentionally thin and must not parse or validate model output.
"""

from __future__ import annotations

from src.planning.foundry_client import FoundryLocalClient

DEFAULT_SYSTEM_PROMPT = (
    "You are a robot planning adapter. Return only strict JSON matching "
    "the allowed action schema. Do not include markdown, prose, "
    "explanation, or code fences."
)


class FoundryModelClient:
    """Bridge that satisfies ModelClient for use with ModelPlanner."""

    def __init__(
        self,
        foundry_client: FoundryLocalClient | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._foundry_client = foundry_client or FoundryLocalClient()
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def complete(self, prompt: str) -> str:
        """Return raw assistant content for *prompt* without transformation."""
        return self._foundry_client.complete(self._system_prompt, prompt)
