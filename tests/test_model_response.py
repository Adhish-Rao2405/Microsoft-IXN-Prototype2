"""Tests for model response parsing — Phase 10.

All tests use existing workcell action schema only.
No PyBullet. No LLM runtime.
"""

from __future__ import annotations

import ast
import json

import pytest

from src.planning.model_response import ModelPlanParseResult, parse_model_response_dict, parse_model_response_text
from src.planning.types import Action


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_pick() -> dict:
    return {"action": "pick_target", "parameters": {"object_id": "obj_1"}}


def _valid_place() -> dict:
    return {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}}


def _valid_stop() -> dict:
    return {"action": "stop_conveyor", "parameters": {}}


def _valid_reset() -> dict:
    return {"action": "reset_workcell", "parameters": {}}


# ---------------------------------------------------------------------------
# Valid parses
# ---------------------------------------------------------------------------


class TestParseValidResponses:
    def test_parses_valid_empty_action_list(self) -> None:
        result = parse_model_response_text('{"actions": []}')
        assert result.accepted is True
        assert result.actions == ()

    def test_parses_valid_single_action(self) -> None:
        payload = {"actions": [_valid_pick()]}
        result = parse_model_response_text(json.dumps(payload))
        assert result.accepted is True
        assert len(result.actions) == 1
        a = result.actions[0]
        assert isinstance(a, Action)
        assert a.action == "pick_target"
        assert a.parameters == {"object_id": "obj_1"}

    def test_parses_valid_multiple_actions(self) -> None:
        payload = {"actions": [_valid_stop(), _valid_pick(), _valid_place()]}
        result = parse_model_response_text(json.dumps(payload))
        assert result.accepted is True
        assert len(result.actions) == 3
        assert result.actions[0].action == "stop_conveyor"
        assert result.actions[1].action == "pick_target"
        assert result.actions[2].action == "place_in_bin"

    def test_parse_dict_valid(self) -> None:
        payload = {"actions": [_valid_reset()]}
        result = parse_model_response_dict(payload)
        assert result.accepted is True
        assert result.actions[0].action == "reset_workcell"


# ---------------------------------------------------------------------------
# Rejection: non-JSON / malformed text
# ---------------------------------------------------------------------------


class TestParseRejectsNonJson:
    def test_rejects_non_json_text(self) -> None:
        result = parse_model_response_text("move the item to the bin")
        assert result.accepted is False
        assert result.actions == ()
        assert result.rejection_reason is not None

    def test_rejects_markdown_fenced_json(self) -> None:
        fenced = "```json\n{\"actions\": []}\n```"
        result = parse_model_response_text(fenced)
        assert result.accepted is False
        assert result.actions == ()
        assert result.rejection_reason is not None

    def test_rejects_markdown_fenced_no_lang(self) -> None:
        fenced = "```\n{\"actions\": []}\n```"
        result = parse_model_response_text(fenced)
        assert result.accepted is False

    def test_rejects_empty_string(self) -> None:
        result = parse_model_response_text("")
        assert result.accepted is False

    def test_rejects_whitespace_only(self) -> None:
        result = parse_model_response_text("   ")
        assert result.accepted is False


# ---------------------------------------------------------------------------
# Rejection: structural
# ---------------------------------------------------------------------------


class TestParseRejectsWrongStructure:
    def test_rejects_top_level_list(self) -> None:
        result = parse_model_response_text('[{"action": "pick_target", "parameters": {}}]')
        assert result.accepted is False
        assert result.actions == ()

    def test_rejects_missing_actions_key(self) -> None:
        result = parse_model_response_dict({"command": [_valid_pick()]})
        assert result.accepted is False

    def test_rejects_actions_not_list(self) -> None:
        result = parse_model_response_dict({"actions": "pick_target"})
        assert result.accepted is False

    def test_rejects_extra_top_level_keys(self) -> None:
        result = parse_model_response_dict({"actions": [], "model": "gpt4"})
        assert result.accepted is False

    def test_rejects_non_dict_payload(self) -> None:
        result = parse_model_response_dict([_valid_pick()])  # type: ignore[arg-type]
        assert result.accepted is False


# ---------------------------------------------------------------------------
# Rejection: action item level
# ---------------------------------------------------------------------------


class TestParseRejectsActionItem:
    def test_rejects_action_item_not_dict(self) -> None:
        result = parse_model_response_dict({"actions": ["pick_target"]})
        assert result.accepted is False

    def test_rejects_missing_action_name(self) -> None:
        result = parse_model_response_dict({"actions": [{"parameters": {}}]})
        assert result.accepted is False

    def test_rejects_empty_action_name(self) -> None:
        result = parse_model_response_dict({"actions": [{"action": "", "parameters": {}}]})
        assert result.accepted is False

    def test_rejects_null_action_name(self) -> None:
        result = parse_model_response_dict({"actions": [{"action": None, "parameters": {}}]})
        assert result.accepted is False

    def test_rejects_parameters_missing(self) -> None:
        result = parse_model_response_dict({"actions": [{"action": "stop_conveyor"}]})
        assert result.accepted is False

    def test_rejects_parameters_not_dict(self) -> None:
        result = parse_model_response_dict(
            {"actions": [{"action": "stop_conveyor", "parameters": "fast"}]}
        )
        assert result.accepted is False

    def test_rejects_invalid_internal_action_schema(self) -> None:
        result = parse_model_response_dict(
            {"actions": [{"action": "fly_away", "parameters": {}}]}
        )
        assert result.accepted is False

    def test_rejects_partial_acceptance_when_one_action_invalid(self) -> None:
        # First action valid, second invalid → entire result rejected
        payload = {
            "actions": [
                _valid_stop(),
                {"action": "unknown_action", "parameters": {}},
            ]
        }
        result = parse_model_response_dict(payload)
        assert result.accepted is False
        assert result.actions == ()

    def test_rejects_action_with_extra_item_keys(self) -> None:
        result = parse_model_response_dict(
            {"actions": [{"action": "stop_conveyor", "parameters": {}, "extra": "field"}]}
        )
        assert result.accepted is False

    def test_rejects_missing_required_parameter(self) -> None:
        # pick_target requires object_id
        result = parse_model_response_dict(
            {"actions": [{"action": "pick_target", "parameters": {}}]}
        )
        assert result.accepted is False


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------


class TestParseResultContract:
    def test_parse_result_is_immutable(self) -> None:
        result = parse_model_response_text('{"actions": []}')
        with pytest.raises((AttributeError, TypeError)):
            result.accepted = False  # type: ignore[misc]

    def test_repeated_parse_same_input_is_deterministic(self) -> None:
        text = json.dumps({"actions": [_valid_pick()]})
        r1 = parse_model_response_text(text)
        r2 = parse_model_response_text(text)
        assert r1.accepted == r2.accepted
        assert r1.actions == r2.actions
        assert r1.rejection_reason == r2.rejection_reason

    def test_accepted_false_has_empty_actions(self) -> None:
        result = parse_model_response_text("not json")
        assert result.accepted is False
        assert result.actions == ()

    def test_accepted_true_has_none_rejection_reason(self) -> None:
        result = parse_model_response_text('{"actions": []}')
        assert result.accepted is True
        assert result.rejection_reason is None

    def test_accepted_false_has_non_none_rejection_reason(self) -> None:
        result = parse_model_response_text("not json")
        assert result.rejection_reason is not None


# ---------------------------------------------------------------------------
# No banned imports
# ---------------------------------------------------------------------------


class TestParserNoBannedImports:
    def _check_module(self, module_name: str) -> None:
        import importlib
        mod = importlib.import_module(module_name)
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

    def test_parser_does_not_import_pybullet(self) -> None:
        self._check_module("src.planning.model_response")

    def test_parser_does_not_execute_code_like_strings(self) -> None:
        # Verify no eval/exec calls in parser module
        import importlib
        mod = importlib.import_module("src.planning.model_response")
        src_path = mod.__file__
        assert src_path is not None
        with open(src_path, encoding="utf-8") as f:
            source = f.read()
        assert "eval(" not in source
        assert "exec(" not in source
