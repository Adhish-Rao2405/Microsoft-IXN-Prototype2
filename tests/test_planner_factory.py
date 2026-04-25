"""Phase 13 — Unit tests for planner factory.

All 10 required tests. No live Foundry Local required.
No actions executed. Deterministic.
"""

from __future__ import annotations

import ast

import pytest

from src.planning.model_planner import ModelPlanner
from src.planning.planner import Planner
from src.planning.planner_factory import create_planner


class FakeModelClient:
    """Fake client for use with model mode tests (no network)."""

    def complete(self, prompt: str) -> str:
        return '{"actions": []}'


# ---------------------------------------------------------------------------
# 1. Default with no env var returns Planner (deterministic)
# ---------------------------------------------------------------------------


def test_default_no_env_returns_deterministic(monkeypatch):
    monkeypatch.delenv("PLANNER_MODE", raising=False)
    planner = create_planner()
    assert isinstance(planner, Planner)


# ---------------------------------------------------------------------------
# 2. Env PLANNER_MODE=deterministic returns Planner
# ---------------------------------------------------------------------------


def test_env_deterministic_returns_planner(monkeypatch):
    monkeypatch.setenv("PLANNER_MODE", "deterministic")
    planner = create_planner()
    assert isinstance(planner, Planner)


# ---------------------------------------------------------------------------
# 3. Env PLANNER_MODE=model returns ModelPlanner
# ---------------------------------------------------------------------------


def test_env_model_returns_model_planner(monkeypatch):
    monkeypatch.setenv("PLANNER_MODE", "model")
    planner = create_planner(model_client=FakeModelClient())
    assert isinstance(planner, ModelPlanner)


# ---------------------------------------------------------------------------
# 4. Explicit mode="deterministic" returns Planner
# ---------------------------------------------------------------------------


def test_explicit_deterministic_returns_planner(monkeypatch):
    monkeypatch.delenv("PLANNER_MODE", raising=False)
    planner = create_planner(mode="deterministic")
    assert isinstance(planner, Planner)


# ---------------------------------------------------------------------------
# 5. Explicit mode="model" returns ModelPlanner
# ---------------------------------------------------------------------------


def test_explicit_model_returns_model_planner(monkeypatch):
    monkeypatch.delenv("PLANNER_MODE", raising=False)
    planner = create_planner(mode="model", model_client=FakeModelClient())
    assert isinstance(planner, ModelPlanner)


# ---------------------------------------------------------------------------
# 6. Explicit mode overrides environment variable
# ---------------------------------------------------------------------------


def test_explicit_mode_overrides_env(monkeypatch):
    monkeypatch.setenv("PLANNER_MODE", "model")
    # Explicit "deterministic" must win even though env says "model"
    planner = create_planner(mode="deterministic")
    assert isinstance(planner, Planner)


# ---------------------------------------------------------------------------
# 7. Invalid mode raises ValueError
# ---------------------------------------------------------------------------


def test_invalid_mode_raises_value_error(monkeypatch):
    monkeypatch.delenv("PLANNER_MODE", raising=False)
    with pytest.raises(ValueError, match="Invalid planner mode"):
        create_planner(mode="neural_autopilot")


def test_invalid_env_raises_value_error(monkeypatch):
    monkeypatch.setenv("PLANNER_MODE", "turbo_mode")
    with pytest.raises(ValueError, match="Invalid planner mode"):
        create_planner()


# ---------------------------------------------------------------------------
# 8. Model mode accepts injected fake model client
# ---------------------------------------------------------------------------


def test_model_mode_uses_injected_client(monkeypatch):
    monkeypatch.delenv("PLANNER_MODE", raising=False)
    fake = FakeModelClient()
    planner = create_planner(mode="model", model_client=fake)
    assert isinstance(planner, ModelPlanner)
    # Confirm the injected client is actually used (not a new FoundryModelClient)
    assert planner._client is fake


# ---------------------------------------------------------------------------
# 9. Deterministic mode ignores injected fake model client
# ---------------------------------------------------------------------------


def test_deterministic_mode_ignores_model_client(monkeypatch):
    monkeypatch.delenv("PLANNER_MODE", raising=False)
    fake = FakeModelClient()
    planner = create_planner(mode="deterministic", model_client=fake)
    assert isinstance(planner, Planner)
    # No model_client attribute on Planner — confirms it was not injected
    assert not hasattr(planner, "_client")


# ---------------------------------------------------------------------------
# 10. Factory module does not import forbidden modules
# ---------------------------------------------------------------------------


def test_factory_module_has_no_banned_imports():
    import importlib

    mod = importlib.import_module("src.planning.planner_factory")
    src_path = mod.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    banned = {
        "pybullet",
        "pybullet_data",
        "src.safety",
        "src.executor",
        "src.evaluation",
        "src.web_ui",
    }

    def _is_banned(name: str) -> bool:
        return any(name == b or name.startswith(b + ".") for b in banned)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not _is_banned(alias.name), f"banned import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            assert not _is_banned(node.module or ""), f"banned import: {node.module}"
