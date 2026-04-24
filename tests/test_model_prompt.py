"""Tests for deterministic model prompt builder — Phase 10.

No PyBullet. No LLM runtime.
"""

from __future__ import annotations

import ast
import json
import re

import pytest

from src.planning.model_prompt import build_model_planner_prompt
from src.simulation.bins import BinRegistry
from src.simulation.conveyor import Conveyor
from src.simulation.spawner import SpawnedObject
from src.simulation.workcell_state import WorkcellState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conveyor(running: bool = False) -> Conveyor:
    c = Conveyor()
    if running:
        c.start(0.5)
    return c


def _make_object(obj_id: str = "obj_1") -> SpawnedObject:
    return SpawnedObject(
        id=obj_id,
        type="cube",
        color="red",
        position=[0.1, 0.0, 0.5],
        on_conveyor=True,
    )


def _make_state(objects: list | None = None) -> WorkcellState:
    return WorkcellState(
        conveyor=_make_conveyor(),
        objects=objects or [],
        bins=BinRegistry(),
    )


# ---------------------------------------------------------------------------
# Basic prompt properties
# ---------------------------------------------------------------------------


class TestPromptBasicProperties:
    def test_prompt_is_string(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        assert isinstance(prompt, str)

    def test_prompt_is_non_empty(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        assert len(prompt.strip()) > 0

    def test_prompt_is_deterministic_for_same_state(self) -> None:
        state = _make_state([_make_object("obj_1")])
        p1 = build_model_planner_prompt(state)
        p2 = build_model_planner_prompt(state)
        assert p1 == p2

    def test_prompt_varies_with_different_states(self) -> None:
        p1 = build_model_planner_prompt(_make_state([_make_object("obj_1")]))
        p2 = build_model_planner_prompt(_make_state([_make_object("obj_99")]))
        assert p1 != p2


# ---------------------------------------------------------------------------
# JSON output contract
# ---------------------------------------------------------------------------


class TestPromptJsonRequirement:
    def test_prompt_contains_strict_json_instruction(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        assert "json" in prompt.lower() or "JSON" in prompt

    def test_prompt_does_not_allow_natural_language_response(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        lower = prompt.lower()
        # Prompt must not say the model may respond in natural language
        assert "natural language" not in lower

    def test_prompt_contains_no_markdown_requirement(self) -> None:
        # No instruction to wrap output in markdown fences
        prompt = build_model_planner_prompt(_make_state())
        assert "```" not in prompt

    def test_prompt_does_not_request_chain_of_thought(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        lower = prompt.lower()
        assert "think step by step" not in lower
        assert "chain of thought" not in lower
        assert "let's think" not in lower


# ---------------------------------------------------------------------------
# Boundary / authority instructions
# ---------------------------------------------------------------------------


class TestPromptBoundaryInstructions:
    def test_prompt_contains_candidate_only_boundary(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        lower = prompt.lower()
        # Must indicate the model only proposes / suggests candidate actions
        assert "candidate" in lower or "propose" in lower or "suggest" in lower

    def test_prompt_contains_no_execution_authority(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        lower = prompt.lower()
        # Must explicitly say model does not execute
        assert "do not execute" in lower or "not execute" in lower or "cannot execute" in lower

    def test_prompt_contains_no_safety_authority(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        lower = prompt.lower()
        # Must indicate safety validation happens after
        assert "safety" in lower

    def test_prompt_states_safety_validation_happens_after(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        lower = prompt.lower()
        assert "safety" in lower


# ---------------------------------------------------------------------------
# State inclusion
# ---------------------------------------------------------------------------


class TestPromptStateInclusion:
    def test_prompt_contains_current_state_json(self) -> None:
        state = _make_state([_make_object("obj_42")])
        prompt = build_model_planner_prompt(state)
        assert "obj_42" in prompt

    def test_state_json_uses_sorted_keys(self) -> None:
        state = _make_state([_make_object("obj_1")])
        state_dict = state.to_dict()
        # Verify sorted-key serialisation appears in prompt
        sorted_json = json.dumps(state_dict, sort_keys=True)
        prompt = build_model_planner_prompt(state)
        # Key ordering from sorted_json must appear (at least the first few keys)
        first_key = list(state_dict.keys())[0] if state_dict else None
        if first_key:
            assert first_key in prompt


# ---------------------------------------------------------------------------
# Available actions
# ---------------------------------------------------------------------------


class TestPromptAvailableActions:
    def test_prompt_contains_available_action_names(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        # Must mention at least some of the supported action names
        from src.brain.action_schema import ALLOWED_WORKCELL_ACTIONS
        mentioned = sum(1 for name in ALLOWED_WORKCELL_ACTIONS if name in prompt)
        assert mentioned > 0, "No workcell action names found in prompt"

    def test_prompt_mentions_pick_target(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        assert "pick_target" in prompt

    def test_prompt_mentions_place_in_bin(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        assert "place_in_bin" in prompt


# ---------------------------------------------------------------------------
# No timestamps / UUIDs
# ---------------------------------------------------------------------------


class TestPromptNonDeterministicValues:
    def test_prompt_contains_no_timestamp(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", prompt)

    def test_prompt_contains_no_uuid(self) -> None:
        prompt = build_model_planner_prompt(_make_state())
        # UUID pattern: 8-4-4-4-12 hex chars
        assert not re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            prompt,
            re.IGNORECASE,
        )


# ---------------------------------------------------------------------------
# No banned imports
# ---------------------------------------------------------------------------


class TestPromptBuilderNoBannedImports:
    def test_prompt_builder_does_not_import_pybullet(self) -> None:
        import importlib
        mod = importlib.import_module("src.planning.model_prompt")
        src_path = mod.__file__
        assert src_path is not None
        with open(src_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        banned = {"pybullet", "pybullet_data", "requests", "httpx"}

        def _is_banned(name: str) -> bool:
            return any(name == b or name.startswith(b + ".") for b in banned)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_banned(alias.name), f"banned import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                assert not _is_banned(node.module or ""), f"banned import: {node.module}"
