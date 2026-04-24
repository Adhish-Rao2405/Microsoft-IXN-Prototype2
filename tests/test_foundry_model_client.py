"""Phase 12 — tests for FoundryModelClient bridge.

Ensures the bridge preserves ModelClient(prompt)->str behavior while delegating
transport to FoundryLocalClient(system_prompt, user_prompt)->str.
"""

from __future__ import annotations

import ast

import pytest

from src.planning.foundry_client import FoundryClientError
from src.planning.foundry_model_client import (
    DEFAULT_SYSTEM_PROMPT,
    FoundryModelClient,
)


class FakeFoundryClient:
    """Duck-typed fake for FoundryLocalClient."""

    def __init__(self, response: str = '{"actions": []}') -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


def test_bridge_exposes_complete_prompt_interface() -> None:
    fake = FakeFoundryClient('{"actions": []}')
    bridge = FoundryModelClient(foundry_client=fake)
    out = bridge.complete("state snapshot")
    assert isinstance(out, str)


def test_bridge_calls_foundry_with_system_and_user_prompt() -> None:
    fake = FakeFoundryClient('{"actions": []}')
    bridge = FoundryModelClient(foundry_client=fake)
    bridge.complete("user prompt body")
    assert len(fake.calls) == 1
    system_prompt, user_prompt = fake.calls[0]
    assert system_prompt == DEFAULT_SYSTEM_PROMPT
    assert user_prompt == "user prompt body"


def test_bridge_returns_raw_assistant_content_unchanged() -> None:
    raw = '{"actions": [{"action": "wait", "parameters": {}}]}'
    fake = FakeFoundryClient(raw)
    bridge = FoundryModelClient(foundry_client=fake)
    assert bridge.complete("x") == raw


def test_bridge_uses_default_strict_system_prompt() -> None:
    fake = FakeFoundryClient('{"actions": []}')
    bridge = FoundryModelClient(foundry_client=fake)
    bridge.complete("prompt")
    system_prompt, _ = fake.calls[0]
    assert system_prompt == DEFAULT_SYSTEM_PROMPT


def test_bridge_accepts_custom_system_prompt() -> None:
    fake = FakeFoundryClient('{"actions": []}')
    custom = "Respond in strict JSON only."
    bridge = FoundryModelClient(foundry_client=fake, system_prompt=custom)
    bridge.complete("prompt")
    system_prompt, _ = fake.calls[0]
    assert system_prompt == custom


def test_bridge_accepts_injected_fake_foundry_client() -> None:
    fake = FakeFoundryClient('{"actions": []}')
    bridge = FoundryModelClient(foundry_client=fake)
    bridge.complete("prompt")
    assert len(fake.calls) == 1


def test_bridge_does_not_parse_valid_json() -> None:
    raw = '{"actions": [{"action": "pick_target", "parameters": {"object_id": "obj_1"}}]}'
    fake = FakeFoundryClient(raw)
    bridge = FoundryModelClient(foundry_client=fake)
    result = bridge.complete("prompt")
    assert isinstance(result, str)
    assert result == raw


def test_bridge_does_not_repair_invalid_json() -> None:
    raw = '{"actions": [BROKEN JSON'
    fake = FakeFoundryClient(raw)
    bridge = FoundryModelClient(foundry_client=fake)
    result = bridge.complete("prompt")
    assert result == raw


def test_bridge_propagates_foundry_client_error() -> None:
    class FailingFoundryClient:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            raise FoundryClientError("boom")

    bridge = FoundryModelClient(foundry_client=FailingFoundryClient())
    with pytest.raises(FoundryClientError):
        bridge.complete("prompt")


def test_bridge_module_has_no_banned_imports() -> None:
    import importlib

    mod = importlib.import_module("src.planning.foundry_model_client")
    src_path = mod.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    banned = {
        "pybullet",
        "pybullet_data",
        "src.executor",
        "src.safety",
        "src.simulation",
        "src.web_ui",
    }

    def _is_banned(name: str) -> bool:
        return any(name == b or name.startswith(b + ".") for b in banned)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not _is_banned(alias.name), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert not _is_banned(node.module or ""), node.module
