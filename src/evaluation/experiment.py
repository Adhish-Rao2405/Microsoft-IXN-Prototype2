"""Phase 9 — Experiment model.

Immutable dataclasses for grouping a set of EvaluationResult objects under
a named, versioned experiment manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from src.evaluation.result_schema import EvaluationResult


@dataclass(frozen=True)
class ExperimentManifest:
    """Immutable descriptor for an experiment run."""

    experiment_id: str
    name: str
    description: str
    scenario_ids: Tuple[str, ...]
    planner_name: str
    pipeline_name: str
    version: str = "prototype-2.1"
    tags: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.experiment_id or not self.experiment_id.strip():
            raise ValueError("experiment_id must be a non-empty, non-whitespace string")
        if not self.name or not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.scenario_ids:
            raise ValueError("scenario_ids must not be empty")
        if not self.planner_name or not self.planner_name.strip():
            raise ValueError("planner_name must be non-empty")
        if not self.pipeline_name or not self.pipeline_name.strip():
            raise ValueError("pipeline_name must be non-empty")
        if not self.version or not self.version.strip():
            raise ValueError("version must be non-empty")
        if len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ValueError("scenario_ids must not contain duplicates")

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "experiment_id": self.experiment_id,
            "name": self.name,
            "pipeline_name": self.pipeline_name,
            "planner_name": self.planner_name,
            "scenario_ids": list(self.scenario_ids),
            "tags": list(self.tags),
            "version": self.version,
        }


@dataclass(frozen=True)
class ExperimentRun:
    """Immutable container binding a manifest to its evaluation results."""

    manifest: ExperimentManifest
    results: Tuple[EvaluationResult, ...]

    def __post_init__(self) -> None:
        if not self.results:
            raise ValueError("results must not be empty")
        expected = list(self.manifest.scenario_ids)
        actual = [r.scenario_id for r in self.results]
        if actual != expected:
            raise ValueError(
                f"results scenario_ids {actual} do not match manifest.scenario_ids {expected}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "results": [r.to_dict() for r in self.results],
        }
