"""Phase 16 — Unit tests for adversarial_cases.

7 required tests.  No PyBullet.  No live Foundry Local.
"""

from __future__ import annotations

import ast

import pytest

from src.experiments.adversarial_cases import AdversarialCase, get_adversarial_cases

_REQUIRED_CASE_NAMES = {
    "malformed_json",
    "unknown_action_type",
    "missing_required_fields",
    "unsafe_target_coordinates",
    "unsafe_speed",
    "unsafe_force",
    "extra_unexpected_fields",
    "markdown_wrapped_json",
    "prose_before_json",
    "empty_response",
    "multiple_actions",
    "wrong_top_level_type",
}


def test_returns_tuple_of_cases():
    cases = get_adversarial_cases()
    assert isinstance(cases, tuple)
    assert len(cases) >= 12
    for case in cases:
        assert isinstance(case, AdversarialCase)


def test_includes_all_required_case_names():
    names = {c.name for c in get_adversarial_cases()}
    missing = _REQUIRED_CASE_NAMES - names
    assert not missing, f"Missing required cases: {missing}"


def test_case_names_are_unique():
    names = [c.name for c in get_adversarial_cases()]
    assert len(names) == len(set(names)), "Duplicate case names found"


def test_every_case_has_non_empty_description():
    for case in get_adversarial_cases():
        assert isinstance(case.description, str)
        assert case.description.strip(), f"Case {case.name!r} has empty description"


def test_every_case_has_response_text_field():
    for case in get_adversarial_cases():
        # response_text exists and is a string (may be empty — that's valid for empty_response case)
        assert isinstance(case.response_text, str), (
            f"Case {case.name!r}: response_text must be a str"
        )


def test_cases_are_deterministic():
    c1 = get_adversarial_cases()
    c2 = get_adversarial_cases()
    assert c1 == c2


def test_module_has_no_pybullet_import():
    import importlib

    mod = importlib.import_module("src.experiments.adversarial_cases")
    src_path = mod.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "pybullet" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            assert "pybullet" not in (node.module or "")
