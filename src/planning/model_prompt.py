"""Phase 10 — Deterministic prompt builder for model planner.

Converts a WorkcellState snapshot into a stable instruction prompt.
Deterministic for the same state. No timestamps. No UUIDs. No network.
No PyBullet.
"""

from __future__ import annotations

import json

from src.brain.action_schema import ALLOWED_WORKCELL_ACTIONS, WORKCELL_ACTION_SCHEMAS
from src.simulation.workcell_state import WorkcellState

# Fixed action list (sorted for determinism).
_SORTED_ACTIONS = sorted(ALLOWED_WORKCELL_ACTIONS)


def _build_action_list_text() -> str:
    """Return a stable description of all available actions."""
    lines: list[str] = []
    for name in _SORTED_ACTIONS:
        schema = WORKCELL_ACTION_SCHEMAS[name]
        required = schema.get("required_params", [])
        desc = schema.get("description", "")
        if required:
            params_str = ", ".join(f"{p}: {schema['param_types'].get(p, 'any')}" for p in required)
            lines.append(f"  - {name}({params_str}): {desc}")
        else:
            lines.append(f"  - {name}(): {desc}")
    return "\n".join(lines)


_ACTION_LIST_TEXT = _build_action_list_text()

_PROMPT_TEMPLATE = """\
You are a planner that proposes candidate workcell actions.

BOUNDARIES:
- You do not execute actions.
- You do not validate safety.
- You only output JSON.
- Safety validation happens after your output.
- Propose candidate actions only.

OUTPUT FORMAT:
Respond with strict JSON only. No markdown. No prose. No comments. No code.

{{
  "actions": [
    {{
      "action": "<action_name>",
      "parameters": {{}}
    }}
  ]
}}

AVAILABLE ACTIONS:
{action_list}

CURRENT WORKCELL STATE:
{state_json}
"""


def build_model_planner_prompt(state: WorkcellState) -> str:
    """Return a deterministic prompt for the given WorkcellState.

    Same state always produces the same prompt string.
    No timestamps, no UUIDs, no random values.
    """
    state_json = json.dumps(state.to_dict(), sort_keys=True, indent=2)
    return _PROMPT_TEMPLATE.format(
        action_list=_ACTION_LIST_TEXT,
        state_json=state_json,
    )
