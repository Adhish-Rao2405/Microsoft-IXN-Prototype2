"""Phase 10 — ModelPlanner adapter.

Wraps a ModelClient to produce candidate Action objects via the prompt
builder and response parser. Does not validate safety. Does not execute.
Does not retry. Does not repair. No network. No PyBullet.
"""

from __future__ import annotations

from src.planning.model_client import ModelClient
from src.planning.model_prompt import build_model_planner_prompt
from src.planning.model_response import parse_model_response_text
from src.planning.types import Plan
from src.simulation.workcell_state import WorkcellState


class ModelPlanner:
    """LLM/SLM planner adapter.

    Converts a WorkcellState snapshot into a candidate Plan by:
    1. Building a deterministic prompt.
    2. Calling the injected ModelClient.
    3. Parsing the raw response into Action objects.
    4. Returning a Plan (possibly empty on rejection).

    The model is not trusted. Safety validation happens downstream.
    """

    def __init__(self, client: ModelClient) -> None:
        self._client = client
        self._last_rejection_reason: str | None = None

    def plan(self, state: WorkcellState) -> Plan:
        """Return a candidate Plan for *state*.

        Returns an empty Plan if the model response is invalid.
        Never raises for malformed model output.
        Never retries.
        Never repairs.
        """
        prompt = build_model_planner_prompt(state)
        response_text = self._client.complete(prompt)
        result = parse_model_response_text(response_text)
        self._last_rejection_reason = result.rejection_reason
        if result.accepted:
            return Plan(list(result.actions))
        return Plan([])

    def last_rejection_reason(self) -> str | None:
        """Return the rejection reason from the most recent plan() call, or None."""
        return self._last_rejection_reason
