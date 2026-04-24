"""Deterministic evaluation harness — Phase 8.

Runs predefined EvaluationScenario objects through an existing deterministic
WorkcellPipeline and records measurable experiment outcomes.

The harness observes and records.  It does not:
- retry rejected actions
- reinterpret planner output
- bypass safety
- bypass executor
- create alternative plans
- add decision-making logic
"""

from __future__ import annotations

from typing import Any, Iterable

from src.evaluation.metrics import compute_metrics
from src.evaluation.result_schema import EvaluationResult, EvaluationStepRecord
from src.evaluation.scenario import EvaluationScenario
from src.orchestration.types import PipelineStatus

# Terminal statuses: the harness stops early when one of these is returned.
# EXECUTED is a non-terminal success — the harness continues until max_steps.
_TERMINAL_STATUSES = frozenset({PipelineStatus.EMPTY, PipelineStatus.REJECTED})

# Final status string when all steps completed without rejection/error.
_STATUS_SUCCESS = "executed"
_STATUS_REJECTED = "rejected"
_STATUS_EMPTY = "empty"
_STATUS_VALIDATED = "validated"


def _status_str(status: Any) -> str:
    """Convert a PipelineStatus (or duck-type) to a canonical string."""
    if isinstance(status, PipelineStatus):
        return status.value
    return str(getattr(status, "value", status))


def _is_terminal(status: Any) -> bool:
    """Return True if *status* should halt the harness loop early."""
    if isinstance(status, PipelineStatus):
        return status in _TERMINAL_STATUSES
    # Duck-type fallback for fake pipelines in tests
    value = getattr(status, "value", status)
    return value in {"empty", "rejected"}


def _state_snapshot(state: Any) -> Any:
    """Return a JSON-serialisable snapshot of *state*.

    Uses WorkcellState.to_dict() when available; falls back to a minimal
    descriptive dict for plain-dict states or test stubs.
    """
    to_dict = getattr(state, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(state, dict):
        return state
    return {}


def _count_rejected(pipeline_result: Any) -> int:
    """Return the number of rejected actions from a pipeline result."""
    rejected = getattr(pipeline_result, "rejected_action", None)
    return 1 if rejected is not None else 0


def _rejection_reasons(pipeline_result: Any) -> tuple[str, ...]:
    """Extract rejection reasons from a pipeline result."""
    reason = getattr(pipeline_result, "rejection_reason", None)
    if isinstance(reason, str) and reason:
        return (reason,)
    return ()


def result_to_json_dict(result: EvaluationResult) -> dict:
    """Return a JSON-serialisable dict representation of *result*.

    This is a pure helper.  Only a runner script should write this to disk.
    """
    return result.to_dict()


class EvaluationHarness:
    """Run evaluation scenarios through a deterministic pipeline.

    Parameters
    ----------
    pipeline:
        An existing WorkcellPipeline (or duck-type with a ``run(state, execute)``
        method that returns a PipelineResult-compatible object).
    """

    def __init__(self, pipeline: Any) -> None:
        self.pipeline = pipeline

    def run_scenario(self, scenario: EvaluationScenario) -> EvaluationResult:
        """Run *scenario* through the pipeline and return an EvaluationResult.

        The harness runs up to ``scenario.max_steps`` pipeline steps.
        It stops early when the pipeline returns a terminal status
        (EMPTY or REJECTED).

        It never retries, never creates alternative actions, and never
        bypasses safety or the executor.
        """
        step_records: list[EvaluationStepRecord] = []
        total_candidate = 0
        total_validated = 0
        total_rejected = 0
        total_executed = 0
        all_rejection_reasons: list[str] = []
        final_status_str = _STATUS_EMPTY
        success = True

        # Build the state for this scenario.  For Phase 8 the harness accepts
        # the scenario's objects list directly and passes it to the pipeline.
        # When connected to a real WorkcellState in later phases, a factory
        # adapter would be used here.
        state = _scenario_state(scenario)

        for step_index in range(scenario.max_steps):
            state_before_snapshot = _state_snapshot(state)

            pipeline_result = self.pipeline.run(state, execute=True)

            state_after_snapshot = _state_snapshot(state)

            status = getattr(pipeline_result, "status", None)
            final_status_str = _status_str(status)

            candidate_actions = getattr(pipeline_result, "candidate_actions", []) or []
            validated_actions = getattr(pipeline_result, "validated_actions", []) or []
            executed_actions = getattr(pipeline_result, "executed_actions", []) or []
            step_rejected_count = _count_rejected(pipeline_result)
            step_reasons = _rejection_reasons(pipeline_result)

            step_candidate = len(candidate_actions)
            step_validated = len(validated_actions)
            step_executed = len(executed_actions)

            total_candidate += step_candidate
            total_validated += step_validated
            total_rejected += step_rejected_count
            total_executed += step_executed
            all_rejection_reasons.extend(step_reasons)

            record = EvaluationStepRecord(
                step_index=step_index,
                state_before=state_before_snapshot,
                candidate_action_count=step_candidate,
                validated_action_count=step_validated,
                rejected_action_count=step_rejected_count,
                executed_action_count=step_executed,
                rejection_reasons=tuple(step_reasons),
                executor_status=final_status_str,
                state_after=state_after_snapshot,
            )
            step_records.append(record)

            if _is_terminal(status):
                if final_status_str == _STATUS_REJECTED:
                    success = False
                break

        total_steps = len(step_records)

        result = EvaluationResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            success=success,
            expected_success=scenario.expected_success,
            total_steps=total_steps,
            total_candidate_actions=total_candidate,
            total_validated_actions=total_validated,
            total_rejected_actions=total_rejected,
            total_executed_actions=total_executed,
            rejection_reasons=tuple(all_rejection_reasons),
            final_status=final_status_str,
            step_records=tuple(step_records),
            metrics=compute_metrics(
                # Build a provisional result for metrics (reuses this result's counts)
                EvaluationResult(
                    scenario_id=scenario.scenario_id,
                    scenario_name=scenario.name,
                    success=success,
                    expected_success=scenario.expected_success,
                    total_steps=total_steps,
                    total_candidate_actions=total_candidate,
                    total_validated_actions=total_validated,
                    total_rejected_actions=total_rejected,
                    total_executed_actions=total_executed,
                    rejection_reasons=tuple(all_rejection_reasons),
                    final_status=final_status_str,
                    step_records=tuple(step_records),
                    metrics={},
                )
            ),
        )
        return result

    def run_many(
        self,
        scenarios: Iterable[EvaluationScenario],
    ) -> tuple[EvaluationResult, ...]:
        """Run multiple scenarios in order and return results as an ordered tuple."""
        return tuple(self.run_scenario(s) for s in scenarios)


def _scenario_state(scenario: EvaluationScenario) -> Any:
    """Build the initial state object for a scenario.

    For Phase 8 deterministic harness tests the pipeline fakes accept any
    state object.  When integrating with the real WorkcellState the caller
    should build the state externally and pass it in, or this function should
    be replaced with a real factory.

    Returns the scenario itself as a minimal state carrier so that pipelines
    that call state.to_dict() or ignore state entirely both work.
    """
    return _ScenarioStateProxy(scenario)


class _ScenarioStateProxy:
    """Minimal state proxy passed to the pipeline.

    Carries the scenario's object list so the pipeline can read it.
    Provides to_dict() for snapshot purposes.
    """

    def __init__(self, scenario: EvaluationScenario) -> None:
        self._scenario = scenario

    def to_dict(self) -> dict:
        return {
            "scenario_id": self._scenario.scenario_id,
            "objects": list(self._scenario.objects),
            "step": "initial",
        }
