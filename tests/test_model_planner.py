"""Tests for ModelPlanner adapter — Phase 10.

Uses FakeModelClient. No PyBullet. No real LLM.
"""

from __future__ import annotations

import ast
import json

import pytest

from src.planning.model_planner import ModelPlanner
from src.planning.types import Action, Plan
from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeModelClient:
    """Records calls and returns a fixed response string."""

    def __init__(self, response: str = '{"actions": []}') -> None:
        self._response = response
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self._response


def _make_state() -> WorkcellState:
    return WorkcellState(
        conveyor=Conveyor(),
        objects=[],
        bins=BinRegistry(),
    )


def _valid_pick_response() -> str:
    return json.dumps({"actions": [{"action": "pick_target", "parameters": {"object_id": "obj_1"}}]})


def _valid_empty_response() -> str:
    return json.dumps({"actions": []})


def _invalid_json_response() -> str:
    return "move the cube to the bin"


def _invalid_schema_response() -> str:
    return json.dumps({"actions": [{"action": "fly_away", "parameters": {}}]})


# ---------------------------------------------------------------------------
# Basic planner behaviour
# ---------------------------------------------------------------------------


class TestModelPlannerBasic:
    def test_planner_calls_client_once(self) -> None:
        client = FakeModelClient(_valid_empty_response())
        planner = ModelPlanner(client)
        planner.plan(_make_state())
        assert len(client.calls) == 1

    def test_planner_passes_prompt_to_client(self) -> None:
        client = FakeModelClient(_valid_empty_response())
        planner = ModelPlanner(client)
        planner.plan(_make_state())
        assert len(client.calls[0]) > 0

    def test_planner_returns_plan_for_valid_response(self) -> None:
        client = FakeModelClient(_valid_pick_response())
        planner = ModelPlanner(client)
        result = planner.plan(_make_state())
        assert isinstance(result, Plan)
        assert len(result.actions) == 1
        assert result.actions[0].action == "pick_target"

    def test_planner_returns_empty_plan_for_invalid_json(self) -> None:
        client = FakeModelClient(_invalid_json_response())
        planner = ModelPlanner(client)
        result = planner.plan(_make_state())
        assert isinstance(result, Plan)
        assert len(result.actions) == 0

    def test_planner_returns_empty_plan_for_invalid_schema(self) -> None:
        client = FakeModelClient(_invalid_schema_response())
        planner = ModelPlanner(client)
        result = planner.plan(_make_state())
        assert isinstance(result, Plan)
        assert len(result.actions) == 0

    def test_planner_returns_plan_type(self) -> None:
        client = FakeModelClient(_valid_empty_response())
        planner = ModelPlanner(client)
        result = planner.plan(_make_state())
        assert isinstance(result, Plan)
        assert hasattr(result, "actions")


# ---------------------------------------------------------------------------
# No retry
# ---------------------------------------------------------------------------


class TestModelPlannerNoRetry:
    def test_planner_does_not_retry_after_invalid_response(self) -> None:
        client = FakeModelClient(_invalid_json_response())
        planner = ModelPlanner(client)
        planner.plan(_make_state())
        # Client called exactly once — no retry
        assert len(client.calls) == 1

    def test_planner_does_not_retry_after_schema_rejection(self) -> None:
        client = FakeModelClient(_invalid_schema_response())
        planner = ModelPlanner(client)
        planner.plan(_make_state())
        assert len(client.calls) == 1


# ---------------------------------------------------------------------------
# No state mutation
# ---------------------------------------------------------------------------


class TestModelPlannerNoStateMutation:
    def test_planner_does_not_mutate_state(self) -> None:
        from src.simulation.spawner import SpawnedObject
        state = WorkcellState(
            conveyor=Conveyor(),
            objects=[SpawnedObject(id="obj_1", type="cube", color="red",
                                   position=[0.0, 0.0, 0.0], on_conveyor=True)],
            bins=BinRegistry(),
        )
        snapshot_before = state.to_dict()
        client = FakeModelClient(_valid_pick_response())
        ModelPlanner(client).plan(state)
        assert state.to_dict() == snapshot_before


# ---------------------------------------------------------------------------
# No safety validation
# ---------------------------------------------------------------------------


class TestModelPlannerNoSafety:
    def test_planner_does_not_validate_safety_itself(self) -> None:
        """Model planner must return unsafe-but-schema-valid actions as candidates.

        Safety rejection is the pipeline's responsibility.
        A schema-valid action for a non-existent object is still returned as a candidate.
        """
        # pick_target with object_id that does not exist in an empty state
        response = json.dumps({
            "actions": [{"action": "pick_target", "parameters": {"object_id": "ghost_obj"}}]
        })
        client = FakeModelClient(response)
        planner = ModelPlanner(client)
        result = planner.plan(_make_state())
        # Planner should return the candidate — safety is not its job
        assert len(result.actions) == 1
        assert result.actions[0].action == "pick_target"

    def test_planner_does_not_execute_actions(self) -> None:
        """Planner must only call client.complete — no executor calls."""
        client = FakeModelClient(_valid_pick_response())
        planner = ModelPlanner(client)
        planner.plan(_make_state())
        # If we got here without a real executor, the planner did not execute
        assert len(client.calls) == 1  # only the LLM client was called


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestModelPlannerDeterminism:
    def test_planner_is_deterministic_for_same_state_and_same_client_response(self) -> None:
        state = _make_state()
        client = FakeModelClient(_valid_pick_response())
        p1 = ModelPlanner(client).plan(state)
        client2 = FakeModelClient(_valid_pick_response())
        p2 = ModelPlanner(client2).plan(state)
        assert p1 == p2


# ---------------------------------------------------------------------------
# Rejection reason
# ---------------------------------------------------------------------------


class TestModelPlannerRejectionReason:
    def test_planner_exposes_rejection_reason_after_invalid_response(self) -> None:
        client = FakeModelClient(_invalid_json_response())
        planner = ModelPlanner(client)
        planner.plan(_make_state())
        reason = planner.last_rejection_reason()
        assert reason is not None

    def test_planner_rejection_reason_is_none_after_valid_response(self) -> None:
        client = FakeModelClient(_valid_pick_response())
        planner = ModelPlanner(client)
        planner.plan(_make_state())
        assert planner.last_rejection_reason() is None

    def test_planner_rejection_reason_is_none_before_any_plan(self) -> None:
        client = FakeModelClient(_valid_empty_response())
        planner = ModelPlanner(client)
        assert planner.last_rejection_reason() is None


# ---------------------------------------------------------------------------
# Pipeline compatibility
# ---------------------------------------------------------------------------


class TestModelPlannerPipelineCompatibility:
    def test_planner_can_be_used_with_existing_pipeline_interface(self) -> None:
        """ModelPlanner must satisfy the pipeline's planner duck-type: plan(state) -> Plan."""
        from src.orchestration.pipeline import WorkcellPipeline
        from src.safety.workcell_safety import WorkcellSafetyValidator

        client = FakeModelClient(_valid_empty_response())
        planner = ModelPlanner(client)
        safety = WorkcellSafetyValidator()
        pipeline = WorkcellPipeline(planner=planner, safety_validator=safety)

        result = pipeline.run(_make_state(), execute=False)
        # Empty actions → EMPTY status
        from src.orchestration.types import PipelineStatus
        assert result.status == PipelineStatus.EMPTY

    def test_malformed_response_never_reaches_executor(self) -> None:
        """When model emits malformed JSON, pipeline produces no executed actions."""
        from src.orchestration.pipeline import WorkcellPipeline
        from src.orchestration.types import PipelineStatus

        class FakeSafety:
            def validate_action(self, state, action):
                from src.orchestration.types import PipelineStatus  # noqa
                # This should never be called if plan is empty
                raise AssertionError("Safety should not be called for empty plan")

        client = FakeModelClient(_invalid_json_response())
        planner = ModelPlanner(client)
        pipeline = WorkcellPipeline(planner=planner, safety_validator=FakeSafety())
        result = pipeline.run(_make_state(), execute=False)
        assert result.status == PipelineStatus.EMPTY
        assert result.executed_actions == [] or result.executed_actions is None or len(list(result.executed_actions)) == 0


# ---------------------------------------------------------------------------
# No banned imports
# ---------------------------------------------------------------------------


class TestModelPlannerNoBannedImports:
    def _parse_module(self, module_name: str) -> ast.Module:
        import importlib
        mod = importlib.import_module(module_name)
        src_path = mod.__file__
        assert src_path is not None
        with open(src_path, encoding="utf-8") as f:
            return ast.parse(f.read()), src_path

    def _check_no_banned(self, module_name: str, banned: set[str]) -> None:
        import importlib
        mod = importlib.import_module(module_name)
        src_path = mod.__file__
        assert src_path is not None
        with open(src_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())

        def _is_banned(name: str) -> bool:
            return any(name == b or name.startswith(b + ".") for b in banned)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_banned(alias.name), f"banned import in {module_name}: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                assert not _is_banned(node.module or ""), f"banned import in {module_name}: {node.module}"

    def test_model_planner_module_has_no_pybullet_import(self) -> None:
        self._check_no_banned("src.planning.model_planner", {"pybullet", "pybullet_data"})

    def test_model_planner_module_has_no_requests_or_httpx_import(self) -> None:
        self._check_no_banned("src.planning.model_planner", {"requests", "httpx"})

    def test_model_planner_module_has_no_file_io(self) -> None:
        import importlib
        mod = importlib.import_module("src.planning.model_planner")
        src_path = mod.__file__
        assert src_path is not None
        with open(src_path, encoding="utf-8") as f:
            source = f.read()
        # No open() calls, no pathlib writes
        assert "open(" not in source
        assert ".write(" not in source
        assert "write_text(" not in source
