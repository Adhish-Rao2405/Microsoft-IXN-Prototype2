"""Phase 11 — Optional live integration smoke test for FoundryLocalClient.

This test only runs when RUN_FOUNDRY_INTEGRATION=1 is set.
Normal pytest runs skip it entirely.

Allowed:
- Call local Foundry endpoint.
- Ask for a minimal strict JSON response.
- Assert that a string response is returned.

Forbidden:
- Do not execute returned actions.
- Do not require model correctness.
- Do not make this part of normal test pass.
"""

from __future__ import annotations

import os

import pytest

from src.planning.foundry_client import FoundryLocalClient

_REQUIRES_LIVE = pytest.mark.skipif(
    os.environ.get("RUN_FOUNDRY_INTEGRATION") != "1",
    reason="Set RUN_FOUNDRY_INTEGRATION=1 to run live Foundry Local tests",
)

_SYSTEM_PROMPT = (
    "You are a strict JSON responder. "
    "Reply only with valid JSON matching: "
    '{"actions": [{"action": "wait", "parameters": {"duration": 1.0}}]}'
)
_USER_PROMPT = "Respond with the example JSON exactly."


@_REQUIRES_LIVE
def test_live_foundry_returns_string():
    """Smoke test: Foundry Local endpoint returns a non-empty string."""
    client = FoundryLocalClient(timeout_seconds=30.0)
    result = client.complete(_SYSTEM_PROMPT, _USER_PROMPT)
    assert isinstance(result, str)
    assert len(result) > 0


@_REQUIRES_LIVE
def test_live_foundry_does_not_execute_output():
    """Returned content is a raw string — never executed by this client."""
    client = FoundryLocalClient(timeout_seconds=30.0)
    result = client.complete(_SYSTEM_PROMPT, _USER_PROMPT)
    # Verify the client returned a string, not an executed action or side-effect.
    assert isinstance(result, str)
