"""Tests for ExperimentManifest and ExperimentRun — Phase 9."""

from __future__ import annotations

import json

import pytest

from src.evaluation.experiment import ExperimentManifest, ExperimentRun
from src.evaluation.result_schema import EvaluationResult, EvaluationStepRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _manifest(**kwargs) -> ExperimentManifest:
    defaults = dict(
        experiment_id="exp_001",
        name="Baseline experiment",
        description="Phase 9 baseline.",
        scenario_ids=("s001", "s002"),
        planner_name="WorkcellPlanner",
        pipeline_name="WorkcellPipeline",
        version="prototype-2.1",
        tags=(),
    )
    defaults.update(kwargs)
    return ExperimentManifest(**defaults)


def _step() -> EvaluationStepRecord:
    return EvaluationStepRecord(
        step_index=0,
        state_before={},
        candidate_action_count=2,
        validated_action_count=2,
        rejected_action_count=0,
        executed_action_count=2,
        rejection_reasons=(),
        executor_status="executed",
        state_after={},
    )


def _result(scenario_id: str = "s001", scenario_name: str = "Test") -> EvaluationResult:
    return EvaluationResult(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        success=True,
        expected_success=True,
        total_steps=1,
        total_candidate_actions=2,
        total_validated_actions=2,
        total_rejected_actions=0,
        total_executed_actions=2,
        rejection_reasons=(),
        final_status="executed",
        step_records=(_step(),),
        metrics={"rejection_rate": 0.0, "validation_pass_rate": 1.0, "execution_rate": 1.0},
    )


def _run(manifest: ExperimentManifest | None = None) -> ExperimentRun:
    m = manifest or _manifest()
    results = tuple(_result(sid) for sid in m.scenario_ids)
    return ExperimentRun(manifest=m, results=results)


# ---------------------------------------------------------------------------
# ExperimentManifest construction
# ---------------------------------------------------------------------------


class TestExperimentManifestConstruction:
    def test_valid_manifest_constructs(self) -> None:
        m = _manifest()
        assert m.experiment_id == "exp_001"
        assert m.name == "Baseline experiment"
        assert m.version == "prototype-2.1"

    def test_empty_experiment_id_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _manifest(experiment_id="")

    def test_whitespace_only_experiment_id_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _manifest(experiment_id="   ")

    def test_empty_name_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _manifest(name="")

    def test_empty_scenario_ids_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _manifest(scenario_ids=())

    def test_empty_planner_name_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _manifest(planner_name="")

    def test_empty_pipeline_name_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _manifest(pipeline_name="")

    def test_empty_version_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _manifest(version="")

    def test_tags_default_empty(self) -> None:
        m = _manifest()
        assert m.tags == ()

    def test_tags_stored(self) -> None:
        m = _manifest(tags=("regression", "phase9"))
        assert "regression" in m.tags


class TestExperimentManifestImmutability:
    def test_manifest_is_frozen(self) -> None:
        m = _manifest()
        with pytest.raises((AttributeError, TypeError)):
            m.experiment_id = "mutated"  # type: ignore[misc]


class TestExperimentManifestSerialisation:
    def test_to_dict_returns_dict(self) -> None:
        d = _manifest().to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_required_keys(self) -> None:
        d = _manifest().to_dict()
        for key in ("experiment_id", "name", "description", "scenario_ids",
                    "planner_name", "pipeline_name", "version", "tags"):
            assert key in d, f"Missing key: {key}"

    def test_to_dict_is_json_serialisable(self) -> None:
        json.dumps(_manifest().to_dict())

    def test_serialisation_is_deterministic(self) -> None:
        d1 = _manifest().to_dict()
        d2 = _manifest().to_dict()
        assert d1 == d2

    def test_scenario_ids_serialised_as_list(self) -> None:
        d = _manifest(scenario_ids=("a", "b")).to_dict()
        assert isinstance(d["scenario_ids"], list)
        assert d["scenario_ids"] == ["a", "b"]


# ---------------------------------------------------------------------------
# ExperimentRun construction
# ---------------------------------------------------------------------------


class TestExperimentRunConstruction:
    def test_valid_run_constructs(self) -> None:
        r = _run()
        assert r.manifest.experiment_id == "exp_001"
        assert len(r.results) == 2

    def test_run_rejects_empty_results(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            ExperimentRun(manifest=_manifest(), results=())

    def test_run_rejects_result_order_mismatch(self) -> None:
        m = _manifest(scenario_ids=("s001", "s002"))
        results = (
            _result("s002"),  # wrong order
            _result("s001"),
        )
        with pytest.raises((ValueError, TypeError)):
            ExperimentRun(manifest=m, results=results)

    def test_run_rejects_duplicate_scenario_ids_in_manifest(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            _manifest(scenario_ids=("s001", "s001"))

    def test_run_rejects_wrong_number_of_results(self) -> None:
        m = _manifest(scenario_ids=("s001", "s002"))
        with pytest.raises((ValueError, TypeError)):
            ExperimentRun(manifest=m, results=(_result("s001"),))


class TestExperimentRunSerialisation:
    def test_to_dict_returns_dict(self) -> None:
        assert isinstance(_run().to_dict(), dict)

    def test_to_dict_has_required_keys(self) -> None:
        d = _run().to_dict()
        assert "manifest" in d
        assert "results" in d

    def test_to_dict_is_json_serialisable(self) -> None:
        json.dumps(_run().to_dict())

    def test_serialisation_is_deterministic(self) -> None:
        d1 = _run().to_dict()
        d2 = _run().to_dict()
        assert d1 == d2

    def test_results_serialised_as_list(self) -> None:
        d = _run().to_dict()
        assert isinstance(d["results"], list)
