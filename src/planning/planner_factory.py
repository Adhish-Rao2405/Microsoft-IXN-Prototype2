"""Phase 13 — Planner selection factory.

Creates a planner instance based on the PLANNER_MODE environment variable
or an explicit mode argument.

Allowed modes:
    deterministic   → Planner (rule-based, stateless)
    model           → ModelPlanner with FoundryModelClient

Default: deterministic (safe, no network dependency).
"""

from __future__ import annotations

import os

from src.planning.planner import Planner
from src.planning.model_planner import ModelPlanner
from src.planning.foundry_model_client import FoundryModelClient

_VALID_MODES = {"deterministic", "model"}
_DEFAULT_MODE = "deterministic"
_ENV_VAR = "PLANNER_MODE"


def get_planner_mode(mode: str | None = None) -> str:
    """Return a validated planner mode string.

    Priority:
        1. *mode* argument (if not None)
        2. PLANNER_MODE environment variable
        3. Default "deterministic"

    Raises:
        ValueError: If the resolved mode is not one of the allowed values.
    """
    resolved = mode if mode is not None else os.environ.get(_ENV_VAR, _DEFAULT_MODE)
    if resolved not in _VALID_MODES:
        raise ValueError(
            f"Invalid planner mode {resolved!r}. "
            f"Allowed values: {sorted(_VALID_MODES)}"
        )
    return resolved


def create_planner(
    mode: str | None = None,
    model_client=None,
):
    """Return a planner appropriate for *mode*.

    Args:
        mode: ``"deterministic"`` or ``"model"``.  ``None`` reads PLANNER_MODE
              from the environment; defaults to ``"deterministic"``.
        model_client: Optional ModelClient-compatible object injected when
                      mode is ``"model"``.  If ``None`` and mode is ``"model"``,
                      a default ``FoundryModelClient()`` is used.
                      Ignored when mode is ``"deterministic"``.

    Returns:
        ``Planner`` for deterministic mode.
        ``ModelPlanner`` for model mode.

    Raises:
        ValueError: If the resolved mode is invalid.
    """
    resolved = get_planner_mode(mode)

    if resolved == "deterministic":
        return Planner()

    # mode == "model"
    client = model_client if model_client is not None else FoundryModelClient()
    return ModelPlanner(client=client)
