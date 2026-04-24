"""Phase 10 — Model response contract.

Strict parser from raw model text/dict to internal Action objects.
No repair. No fuzzy matching. No guessing. No network. No PyBullet.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from src.brain.action_schema import ALLOWED_WORKCELL_ACTIONS, WORKCELL_ACTION_SCHEMAS
from src.planning.types import Action


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelPlanParseResult:
    """Immutable result of parsing a model response."""

    actions: Tuple[Action, ...]
    accepted: bool
    rejection_reason: str | None


# ---------------------------------------------------------------------------
# Private validation helpers
# ---------------------------------------------------------------------------


def _reject(reason: str) -> ModelPlanParseResult:
    return ModelPlanParseResult(actions=(), accepted=False, rejection_reason=reason)


def _accept(actions: Tuple[Action, ...]) -> ModelPlanParseResult:
    return ModelPlanParseResult(actions=actions, accepted=True, rejection_reason=None)


def _parse_single_action(item: Any) -> Action | None:
    """Return an Action if *item* is valid, else None. No repair."""
    if not isinstance(item, dict):
        return None

    # Reject extra keys beyond "action" and "parameters"
    if set(item.keys()) - {"action", "parameters"}:
        return None

    action_name = item.get("action")
    if not isinstance(action_name, str) or not action_name:
        return None

    if action_name not in ALLOWED_WORKCELL_ACTIONS:
        return None

    # "parameters" key must be explicitly present and must be a dict
    if "parameters" not in item:
        return None
    parameters = item["parameters"]
    if not isinstance(parameters, dict):
        return None

    schema = WORKCELL_ACTION_SCHEMAS[action_name]

    # Reject extra parameter keys
    allowed_keys = set(schema["required_params"]) | set(schema["optional_params"])
    if set(parameters.keys()) - allowed_keys:
        return None

    # Validate required parameters
    clean: dict[str, Any] = {}
    for key in schema["required_params"]:
        if key not in parameters:
            return None
        val = parameters[key]
        expected_type = schema["param_types"].get(key)
        if expected_type is not None:
            if expected_type is float:
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    return None
                val = float(val)
            elif expected_type is str:
                if not isinstance(val, str):
                    return None
            elif not isinstance(val, expected_type):
                return None
        clean[key] = val

    return Action(action=action_name, parameters=clean)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_model_response_dict(payload: Mapping[str, Any]) -> ModelPlanParseResult:
    """Parse and validate a model response already decoded from JSON.

    Returns ModelPlanParseResult with accepted=True only if every action
    is valid per the existing workcell action schema. Partial acceptance
    is forbidden — one invalid action rejects the entire response.
    """
    if not isinstance(payload, dict):
        return _reject("top_level_not_dict")

    # Strict top-level: only "actions" key allowed
    if set(payload.keys()) - {"actions"}:
        return _reject("extra_top_level_keys")

    if "actions" not in payload:
        return _reject("missing_actions_key")

    raw_actions = payload["actions"]
    if not isinstance(raw_actions, list):
        return _reject("actions_not_list")

    actions: list[Action] = []
    for item in raw_actions:
        action = _parse_single_action(item)
        if action is None:
            return _reject("invalid_action_item")
        actions.append(action)

    return _accept(tuple(actions))


def parse_model_response_text(response_text: str) -> ModelPlanParseResult:
    """Parse raw model response text (must be strict JSON, no markdown).

    Returns ModelPlanParseResult. Rejects markdown fences, prose, and
    any text that is not strict JSON.
    """
    if not isinstance(response_text, str) or not response_text.strip():
        return _reject("empty_or_non_string_response")

    # Reject markdown fences before attempting JSON parse
    if "```" in response_text:
        return _reject("markdown_fenced_response")

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        return _reject(f"json_decode_error: {exc.msg}")

    return parse_model_response_dict(payload)
