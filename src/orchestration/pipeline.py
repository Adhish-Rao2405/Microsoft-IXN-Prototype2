"""Deterministic Phase 6 pipeline/orchestrator for the workcell stack."""

from __future__ import annotations

from typing import Any, Dict

from src.orchestration.errors import PipelineError
from src.orchestration.types import PipelineResult, PipelineStatus


class WorkcellPipeline:
    """Coordinate planner, safety validation, and optional execution."""

    def __init__(self, planner: Any, safety_validator: Any, executor: Any | None = None) -> None:
        self.planner = planner
        self.safety_validator = safety_validator
        self.executor = executor

    def run(self, state: Any, execute: bool = False) -> PipelineResult:
        if self.planner is None:
            raise PipelineError("Planner is required")
        if self.safety_validator is None:
            raise PipelineError("Safety validator is required")
        if execute and self.executor is None:
            raise PipelineError("Execution requested but no executor was provided")

        plan = self.planner.plan(state)
        if plan is None or not hasattr(plan, "actions"):
            raise PipelineError("Planner returned invalid plan")

        candidate_actions = list(plan.actions)
        if not candidate_actions:
            return PipelineResult(status=PipelineStatus.EMPTY)

        validated_actions: list[Any] = []
        for action in candidate_actions:
            validation = self.safety_validator.validate_action(
                state,
                self._action_to_dict(action),
            )
            if not getattr(validation, "is_valid", False):
                return PipelineResult(
                    candidate_actions=candidate_actions,
                    validated_actions=validated_actions,
                    rejected_action=action,
                    rejection_reason=self._rejection_reason(validation),
                    executed_actions=[],
                    status=PipelineStatus.REJECTED,
                )
            validated_actions.append(action)

        if not execute:
            return PipelineResult(
                candidate_actions=candidate_actions,
                validated_actions=validated_actions,
                rejected_action=None,
                rejection_reason=None,
                executed_actions=[],
                status=PipelineStatus.VALIDATED,
            )

        executed_actions: list[Any] = []
        for action in validated_actions:
            self.executor.execute(*self._executor_args(action))
            executed_actions.append(action)

        return PipelineResult(
            candidate_actions=candidate_actions,
            validated_actions=validated_actions,
            rejected_action=None,
            rejection_reason=None,
            executed_actions=executed_actions,
            status=PipelineStatus.EXECUTED,
        )

    def _action_to_dict(self, action: Any) -> Dict[str, Any]:
        if isinstance(action, dict):
            return action
        to_dict = getattr(action, "to_dict", None)
        if callable(to_dict):
            payload = to_dict()
            if isinstance(payload, dict):
                return payload
        action_name = getattr(action, "action", None)
        parameters = getattr(action, "parameters", None)
        if isinstance(action_name, str) and isinstance(parameters, dict):
            return {"action": action_name, "parameters": parameters}
        raise PipelineError("Planner returned invalid plan")

    def _executor_args(self, action: Any) -> tuple[str, Dict[str, Any]]:
        payload = self._action_to_dict(action)
        action_name = payload.get("action")
        parameters = payload.get("parameters", {})
        if not isinstance(action_name, str) or not isinstance(parameters, dict):
            raise PipelineError("Planner returned invalid plan")
        return action_name, dict(parameters)

    def _rejection_reason(self, validation: Any) -> str | None:
        messages = getattr(validation, "messages", None)
        if isinstance(messages, list) and messages:
            first = messages[0]
            if isinstance(first, str):
                return first
        errors = getattr(validation, "errors", None)
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, str):
                return first
        return None