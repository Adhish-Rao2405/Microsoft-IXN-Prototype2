"""Strict JSON action schema – defines the contract between the LLM and the executor."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

# ── Allowed tool definitions ─────────────────────────────────────────

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "move_ee": {
        "description": "Move the end-effector to an XYZ position with optional RPY orientation and speed.",
        "args": {
            "target_xyz": {"type": "list[float]", "length": 3, "required": True},
            "target_rpy": {"type": "list[float]", "length": 3, "required": False},
            "speed": {"type": "float", "required": False, "default": 1.0},
        },
    },
    "open_gripper": {
        "description": "Open the gripper to a specified width (metres, max 0.04).",
        "args": {
            "width": {"type": "float", "required": False, "default": 0.04},
        },
    },
    "close_gripper": {
        "description": "Close the gripper with a given force (newtons).",
        "args": {
            "force": {"type": "float", "required": False, "default": 40.0},
        },
    },
    "pick": {
        "description": "Pick up an object by name. Executes the full approach-descend-close-lift sequence.",
        "args": {
            "object": {"type": "str", "required": True},
        },
    },
    "place": {
        "description": "Place the currently held object at the given XYZ position.",
        "args": {
            "target_xyz": {"type": "list[float]", "length": 3, "required": True},
        },
    },
    "reset": {
        "description": "Return the robot to its neutral position, open gripper, and reset all objects to their original positions.",
        "args": {},
    },
    "describe_scene": {
        "description": "Return a list of all objects in the scene with their positions and colours.",
        "args": {},
    },
}

ALLOWED_TOOLS = set(TOOL_SCHEMAS.keys())

# ── Workcell action schemas (Prototype 2.1) ──────────────────────────
#
# These actions use the {"action": "...", "parameters": {...}} wire format
# as defined in specs/001-prototype-2.1/action-schema.md.
# They are separate from the legacy tool/args schema above.

WORKCELL_ACTION_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "inspect_workcell": {
        "description": "Return the current workcell state snapshot.",
        "required_params": [],
        "optional_params": [],
        "param_types": {},
    },
    "start_conveyor": {
        "description": "Start the conveyor at the given speed (m/s, > 0).",
        "required_params": ["speed"],
        "optional_params": [],
        "param_types": {"speed": float},
    },
    "stop_conveyor": {
        "description": "Stop the conveyor belt.",
        "required_params": [],
        "optional_params": [],
        "param_types": {},
    },
    "wait": {
        "description": "Pause execution for the given number of simulated seconds (> 0).",
        "required_params": ["seconds"],
        "optional_params": [],
        "param_types": {"seconds": float},
    },
    "pick_target": {
        "description": "Pick the object with the given object_id from the pick zone.",
        "required_params": ["object_id"],
        "optional_params": [],
        "param_types": {"object_id": str},
    },
    "place_in_bin": {
        "description": "Place the currently held object into the given bin.",
        "required_params": ["bin_id"],
        "optional_params": [],
        "param_types": {"bin_id": str},
    },
    "reset_workcell": {
        "description": "Reset the workcell to its initial state.",
        "required_params": [],
        "optional_params": [],
        "param_types": {},
    },
}

ALLOWED_WORKCELL_ACTIONS: set = set(WORKCELL_ACTION_SCHEMAS.keys())


def validate_workcell_plan(raw: Any) -> Optional[List[Dict[str, Any]]]:
    """Parse and validate a workcell action plan.

    Accepted shape::

        {"actions": [{"action": "pick_target", "parameters": {"object_id": "obj_1"}}]}

    Returns a list of validated ``{"action": str, "parameters": dict}`` dicts,
    or ``None`` if validation fails.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None

    if not isinstance(raw, dict):
        return None

    actions = raw.get("actions")
    if not isinstance(actions, list) or len(actions) == 0:
        return None

    validated: List[Dict[str, Any]] = []
    for act in actions:
        v = _validate_workcell_action(act)
        if v is None:
            return None
        validated.append(v)

    return validated


def _validate_workcell_action(act: Any) -> Optional[Dict[str, Any]]:
    """Validate a single workcell action dict."""
    if not isinstance(act, dict):
        return None

    # Reject extra top-level keys beyond "action" and "parameters".
    if set(act.keys()) - {"action", "parameters"}:
        return None

    action_name = act.get("action")
    if action_name not in ALLOWED_WORKCELL_ACTIONS:
        return None

    schema = WORKCELL_ACTION_SCHEMAS[action_name]
    parameters = act.get("parameters", {})
    if not isinstance(parameters, dict):
        return None

    # Reject extra parameter keys.
    allowed_keys = set(schema["required_params"]) | set(schema["optional_params"])
    if set(parameters.keys()) - allowed_keys:
        return None

    # Check required parameters are present and of the correct type.
    clean: Dict[str, Any] = {}
    for key in schema["required_params"]:
        if key not in parameters:
            return None
        val = parameters[key]
        expected_type = schema["param_types"].get(key)
        if expected_type is not None:
            if expected_type is float:
                # Accept numeric inputs only; reject string-based coercion.
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    return None
                val = float(val)
            elif expected_type is str:
                if not isinstance(val, str):
                    return None
            elif not isinstance(val, expected_type):
                return None
        clean[key] = val

    return {"action": action_name, "parameters": clean}


def schema_prompt_block() -> str:
    """Return a human-readable description of the schema for the system prompt."""
    lines = ["Available tools (use ONLY these):"]
    for name, info in TOOL_SCHEMAS.items():
        args_desc = ", ".join(
            f"{k}: {v['type']}" + (" (required)" if v.get("required") else " (optional)")
            for k, v in info["args"].items()
        )
        lines.append(f'  - {name}({args_desc}): {info["description"]}')
    return "\n".join(lines)


# ── Validation ───────────────────────────────────────────────────────


def validate_plan(raw: Any) -> Optional[List[Dict[str, Any]]]:
    """Parse and validate a plan/action payload.

    Accepted shapes:
        {"type": "plan", "actions": [...]}
        {"type": "action", "tool": "...", "args": {...}}
        {"tool": "...", "args": {...}}            # shorthand single action

    Returns a list of validated action dicts, or None on failure.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None

    if not isinstance(raw, dict):
        return None

    payload_type = raw.get("type", "action")

    if payload_type == "plan":
        actions = raw.get("actions")
        if not isinstance(actions, list):
            return None
    else:
        actions = [raw]

    validated: List[Dict[str, Any]] = []
    for act in actions:
        v = _validate_single(act)
        if v is None:
            return None  # reject entire plan if one action is invalid
        validated.append(v)

    return validated


def _validate_single(act: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tool = act.get("tool")
    # Handle LLM pattern: {"type": "<tool_name>", "args": {...}} with no "tool"
    if tool is None:
        t = act.get("type", "")
        if t in ALLOWED_TOOLS:
            tool = t
    if tool not in ALLOWED_TOOLS:
        return None
    schema_args = TOOL_SCHEMAS[tool]["args"]
    provided = act.get("args", {})
    if not isinstance(provided, dict):
        return None

    clean_args: Dict[str, Any] = {}
    for arg_name, arg_def in schema_args.items():
        if arg_name in provided:
            val = provided[arg_name]
            # Basic type coercion / checking
            if "list" in arg_def["type"] and isinstance(val, list):
                expected_len = arg_def.get("length")
                if expected_len and len(val) != expected_len:
                    return None
                clean_args[arg_name] = [float(v) for v in val]
            elif arg_def["type"] == "float":
                clean_args[arg_name] = float(val)
            elif arg_def["type"] == "str":
                clean_args[arg_name] = str(val)
            else:
                clean_args[arg_name] = val
        elif arg_def.get("required"):
            return None  # missing required arg
        else:
            clean_args[arg_name] = arg_def.get("default")

    return {"tool": tool, "args": clean_args}
