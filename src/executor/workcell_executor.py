"""Deterministic workcell executor for Prototype 2.1 actions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.workcell_state import WorkcellState


class WorkcellExecutor:
    """Apply explicit workcell actions without planning or inference."""

    def __init__(
        self,
        conveyor: Conveyor,
        bins: BinRegistry,
        workcell_state: WorkcellState,
        max_conveyor_speed: float = 1.0,
        max_wait_seconds: float = 30.0,
    ) -> None:
        self._conveyor = conveyor
        self._bins = bins
        self._workcell_state = workcell_state
        self._max_conveyor_speed = max_conveyor_speed
        self._max_wait_seconds = max_wait_seconds
        self._holding_object_id: Optional[str] = None

    @property
    def holding_object_id(self) -> Optional[str]:
        """The id of the object currently held, or None."""
        return self._holding_object_id

    @property
    def is_holding(self) -> bool:
        """Return True when an object is currently held."""
        return self._holding_object_id is not None

    def execute_plan(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a list of action dicts in order."""
        results: List[Dict[str, Any]] = []
        for act in actions:
            result = self.execute(act["action"], act.get("parameters", {}))
            results.append(result)
        return results

    def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one explicit action and return a result dict."""
        handler = {
            "inspect_workcell": self._do_inspect_workcell,
            "start_conveyor": self._do_start_conveyor,
            "stop_conveyor": self._do_stop_conveyor,
            "wait": self._do_wait,
            "pick_target": self._do_pick_target,
            "place_in_bin": self._do_place_in_bin,
            "reset_workcell": self._do_reset_workcell,
        }.get(action)

        if handler is None:
            return {"action": action, "success": False, "error": f"unknown action: {action!r}"}
        return handler(parameters)

    def _do_inspect_workcell(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "inspect_workcell",
            "success": True,
            "state": self._workcell_state.to_dict(),
        }

    def _do_start_conveyor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        speed = params.get("speed")
        if speed is None:
            return {"action": "start_conveyor", "success": False, "error": "missing parameter: speed"}
        try:
            speed = float(speed)
        except (TypeError, ValueError):
            return {"action": "start_conveyor", "success": False, "error": "speed must be a number"}
        if speed <= 0:
            return {"action": "start_conveyor", "success": False, "error": "speed must be > 0"}
        if speed > self._max_conveyor_speed:
            return {
                "action": "start_conveyor",
                "success": False,
                "error": f"speed {speed} exceeds maximum {self._max_conveyor_speed}",
            }
        self._conveyor.start(speed)
        return {"action": "start_conveyor", "success": True, "speed": speed}

    def _do_stop_conveyor(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        self._conveyor.stop()
        return {"action": "stop_conveyor", "success": True}

    def _do_wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        seconds = params.get("seconds")
        if seconds is None:
            return {"action": "wait", "success": False, "error": "missing parameter: seconds"}
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            return {"action": "wait", "success": False, "error": "seconds must be a number"}
        if seconds <= 0:
            return {"action": "wait", "success": False, "error": "seconds must be > 0"}
        if seconds > self._max_wait_seconds:
            return {
                "action": "wait",
                "success": False,
                "error": f"seconds {seconds} exceeds maximum {self._max_wait_seconds}",
            }
        return {"action": "wait", "success": True, "seconds": seconds}

    def _do_pick_target(self, params: Dict[str, Any]) -> Dict[str, Any]:
        object_id = params.get("object_id")
        if not object_id:
            return {"action": "pick_target", "success": False, "error": "missing parameter: object_id"}
        if not self._workcell_state.has_object(object_id):
            return {"action": "pick_target", "success": False, "error": f"unknown object_id: {object_id!r}"}
        self._holding_object_id = object_id
        self._workcell_state.remove_object(object_id)
        return {"action": "pick_target", "success": True, "object_id": object_id}

    def _do_place_in_bin(self, params: Dict[str, Any]) -> Dict[str, Any]:
        bin_id = params.get("bin_id")
        if not bin_id:
            return {"action": "place_in_bin", "success": False, "error": "missing parameter: bin_id"}
        if not self._bins.is_valid(bin_id):
            return {"action": "place_in_bin", "success": False, "error": f"unknown bin_id: {bin_id!r}"}
        if self._holding_object_id is None:
            return {"action": "place_in_bin", "success": False, "error": "not holding any object"}
        placed_id = self._holding_object_id
        self._bins.increment(bin_id)
        self._holding_object_id = None
        return {"action": "place_in_bin", "success": True, "object_id": placed_id, "bin_id": bin_id}

    def _do_reset_workcell(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        self._conveyor.stop()
        self._holding_object_id = None
        self._bins.reset_all()
        for obj in list(self._workcell_state.list_objects()):
            self._workcell_state.remove_object(obj.id)
        return {"action": "reset_workcell", "success": True}
