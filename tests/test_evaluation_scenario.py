"""Tests for EvaluationScenario — Phase 8."""

from __future__ import annotations

import pytest

from src.evaluation.scenario import EvaluationScenario


def _valid_scenario(**kwargs) -> EvaluationScenario:
    defaults = dict(
        scenario_id="s001",
        name="Basic test",
        description="A test scenario.",
        objects=[],
        max_steps=5,
        expected_success=True,
        success_conditions=("all_objects_placed",),
        tags=(),
    )
    defaults.update(kwargs)
    return EvaluationScenario(**defaults)


class TestEvaluationScenarioConstruction:
    def test_valid_scenario_constructs(self) -> None:
        s = _valid_scenario()
        assert s.scenario_id == "s001"
        assert s.name == "Basic test"
        assert s.max_steps == 5

    def test_empty_scenario_id_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _valid_scenario(scenario_id="")

    def test_whitespace_only_scenario_id_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _valid_scenario(scenario_id="   ")

    def test_empty_name_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _valid_scenario(name="")

    def test_max_steps_zero_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _valid_scenario(max_steps=0)

    def test_max_steps_negative_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _valid_scenario(max_steps=-1)

    def test_max_steps_positive_accepted(self) -> None:
        s = _valid_scenario(max_steps=1)
        assert s.max_steps == 1


class TestEvaluationScenarioImmutability:
    def test_scenario_is_frozen(self) -> None:
        s = _valid_scenario()
        with pytest.raises((AttributeError, TypeError)):
            s.scenario_id = "modified"  # type: ignore[misc]

    def test_scenario_id_preserved(self) -> None:
        s = _valid_scenario(scenario_id="abc123")
        assert s.scenario_id == "abc123"

    def test_expected_success_is_bool(self) -> None:
        s = _valid_scenario(expected_success=False)
        assert s.expected_success is False


class TestEvaluationScenarioFields:
    def test_success_conditions_stored(self) -> None:
        s = _valid_scenario(success_conditions=("cond_a", "cond_b"))
        assert "cond_a" in s.success_conditions
        assert "cond_b" in s.success_conditions

    def test_tags_default_empty(self) -> None:
        s = _valid_scenario()
        assert len(s.tags) == 0

    def test_tags_stored(self) -> None:
        s = _valid_scenario(tags=("regression", "smoke"))
        assert "regression" in s.tags

    def test_objects_defaults_to_empty(self) -> None:
        s = _valid_scenario(objects=[])
        assert len(s.objects) == 0

    def test_description_stored(self) -> None:
        s = _valid_scenario(description="Detailed desc.")
        assert s.description == "Detailed desc."

    def test_no_callable_fields(self) -> None:
        s = _valid_scenario()
        # No field should be callable (no embedded planner/policy)
        for field_name in ("scenario_id", "name", "description", "max_steps",
                           "expected_success", "success_conditions", "tags", "objects"):
            val = getattr(s, field_name)
            assert not callable(val), f"Field {field_name!r} is callable"
