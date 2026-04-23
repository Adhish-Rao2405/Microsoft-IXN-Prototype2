"""Deterministic safety validation for explicit workcell actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.brain.action_schema import ALLOWED_WORKCELL_ACTIONS, WORKCELL_ACTION_SCHEMAS


@dataclass
class ValidationResult:
    """Structured validation outcome for one explicit action."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly result representation."""
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "messages": list(self.messages),
        }


class WorkcellSafetyValidator:
    """Read-only precondition validator for workcell actions."""

    def validate_action(self, state: Any, action: Any) -> ValidationResult:
        """Validate one action against current state facts."""
        if not isinstance(action, dict):
            return self._fail("action_must_be_dict", "Action payload must be a dict")

        if set(action.keys()) - {"action", "parameters"}:
            return self._fail("action_has_extra_keys", "Action payload contains extra keys")

        action_name = action.get("action")
        if action_name not in ALLOWED_WORKCELL_ACTIONS:
            return self._fail("unknown_action", f"Unknown action: {action_name!r}")

        parameters = action.get("parameters", {})
        if not isinstance(parameters, dict):
            return self._fail("parameters_must_be_dict", "Action parameters must be a dict")

        schema_errors = self._validate_against_schema(action_name, parameters)
        if schema_errors:
            return self._fail_many(schema_errors)

        if action_name == "inspect_workcell":
            return self._ok()
        if action_name == "start_conveyor":
            return self._validate_start_conveyor(state)
        if action_name == "stop_conveyor":
            return self._validate_stop_conveyor(state)
        if action_name == "wait":
            return self._ok()
        if action_name == "pick_target":
            return self._validate_pick_target(state, parameters)
        if action_name == "place_in_bin":
            return self._validate_place_in_bin(state, parameters)
        if action_name == "reset_workcell":
            return self._ok()

        return self._fail("unknown_action", f"Unknown action: {action_name!r}")

    def validate_plan(self, state: Any, actions: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate each action independently in list order."""
        return [self.validate_action(state, action) for action in actions]

    def _validate_against_schema(self, action_name: str, parameters: Dict[str, Any]) -> List[tuple[str, str]]:
        schema = WORKCELL_ACTION_SCHEMAS[action_name]
        required = list(schema["required_params"])
        optional = list(schema["optional_params"])
        allowed = set(required) | set(optional)
        param_types = schema["param_types"]

        errors: List[tuple[str, str]] = []

        for key in required:
            if key not in parameters:
                errors.append(("missing_required_parameter", f"Missing required parameter: {key}"))

        extra = sorted(set(parameters.keys()) - allowed)
        for key in extra:
            errors.append(("unexpected_parameter", f"Unexpected parameter: {key}"))

        for key in required:
            if key not in parameters:
                continue
            expected_type = param_types.get(key)
            val = parameters[key]
            if expected_type is float:
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    errors.append(("parameter_type_mismatch", f"Parameter {key} must be numeric"))
            elif expected_type is str:
                if not isinstance(val, str):
                    errors.append(("parameter_type_mismatch", f"Parameter {key} must be a string"))
            elif expected_type is not None and not isinstance(val, expected_type):
                errors.append(("parameter_type_mismatch", f"Parameter {key} has wrong type"))

        return errors

    def _validate_start_conveyor(self, state: Any) -> ValidationResult:
        if self._is_conveyor_running(state):
            return self._fail("conveyor_already_running", "Cannot start conveyor while already running")
        return self._ok()

    def _validate_stop_conveyor(self, state: Any) -> ValidationResult:
        if not self._is_conveyor_running(state):
            return self._fail("conveyor_already_stopped", "Cannot stop conveyor while already stopped")
        return self._ok()

    def _validate_pick_target(self, state: Any, parameters: Dict[str, Any]) -> ValidationResult:
        object_id = parameters["object_id"]

        if self._holding_object_id(state) is not None:
            return self._fail("already_holding_object", "Cannot pick while already holding an object")

        if self._is_conveyor_running(state):
            return self._fail("conveyor_must_be_stopped_for_pick", "Cannot pick while conveyor is running")

        obj = self._find_object(state, object_id)
        if obj is None:
            return self._fail("object_not_found", f"Object not found: {object_id!r}")

        if not bool(obj.get("on_conveyor", False)):
            return self._fail("object_not_pickable", f"Object is not available on conveyor: {object_id!r}")

        return self._ok()

    def _validate_place_in_bin(self, state: Any, parameters: Dict[str, Any]) -> ValidationResult:
        if self._holding_object_id(state) is None:
            return self._fail("no_object_held", "Cannot place in bin while no object is held")

        bin_id = parameters["bin_id"]
        if not self._bin_exists(state, bin_id):
            return self._fail("bin_not_found", f"Unknown bin_id: {bin_id!r}")

        return self._ok()

    def _state_dict(self, state: Any) -> Dict[str, Any]:
        if isinstance(state, dict):
            return state
        to_dict = getattr(state, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        return {}

    def _is_conveyor_running(self, state: Any) -> bool:
        data = self._state_dict(state)
        conveyor = data.get("conveyor", {})
        if isinstance(conveyor, dict):
            return bool(conveyor.get("running", False))
        return bool(getattr(getattr(state, "_conveyor", None), "running", False))

    def _holding_object_id(self, state: Any) -> Optional[str]:
        if isinstance(state, dict):
            value = state.get("holding_object_id")
            return value if isinstance(value, str) else None
        value = getattr(state, "holding_object_id", None)
        return value if isinstance(value, str) else None

    def _find_object(self, state: Any, object_id: str) -> Optional[Dict[str, Any]]:
        data = self._state_dict(state)
        objects = data.get("objects", [])
        if isinstance(objects, list):
            for obj in objects:
                if isinstance(obj, dict) and obj.get("id") == object_id:
                    return obj
        return None

    def _bin_exists(self, state: Any, bin_id: str) -> bool:
        data = self._state_dict(state)
        bins = data.get("bins", [])
        if isinstance(bins, list):
            for b in bins:
                if isinstance(b, dict) and b.get("bin_id") == bin_id:
                    return True
        return False

    def _ok(self) -> ValidationResult:
        return ValidationResult(is_valid=True, errors=[], messages=[])

    def _fail(self, code: str, message: str) -> ValidationResult:
        return ValidationResult(is_valid=False, errors=[code], messages=[message])

    def _fail_many(self, errors: List[tuple[str, str]]) -> ValidationResult:
        return ValidationResult(
            is_valid=False,
            errors=[e[0] for e in errors],
            messages=[e[1] for e in errors],
        )
