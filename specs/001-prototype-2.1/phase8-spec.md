# Phase 8 Specification

## Microsoft IXN Prototype 2.1

## Phase 8: Deterministic Evaluation / Experiment Harness

---

## 0. Current Status

Completed and test-gated before this phase:
- Phase 1: simulation primitives
- Phase 2: deterministic workcell read model
- Phase 3: action schema + executor
- Phase 4: safety / validation layer
- Phase 5: deterministic planner
- Phase 6: planning pipeline / orchestrator
- Phase 7: deterministic end-to-end scenario tests

Verified regression before Phase 8: 233 tests passing.

---

## 1. Phase 8 Purpose

Phase 8 creates the first deterministic evaluation / experiment harness.

It runs predefined workcell scenarios through the existing deterministic planning pipeline and records measurable experiment outcomes.

This harness is the foundation for dissertation evidence generation and for later comparison against future LLM/SLM planners.

**Phase 8 introduces no new intelligence.** It observes and records.

---

## 2. Architecture Under Test

```
Scenario Definition
  → Initial Workcell State
  → Existing Planning Pipeline (Phase 6)
  → Existing Safety Validation (Phase 4)
  → Existing Executor (Phase 3)
  → Evaluation Result Record
  → Optional JSON export
```

The architecture from Phases 1–7 is unchanged.

---

## 3. Absolute Non-Goals

Do NOT add:
- LLM planning
- PyBullet
- GUI
- physics simulation
- robot motion/path planning
- collision avoidance
- retries or fallback planning
- recovery logic
- optimisation or heuristics
- new action types
- new routing logic
- new safety rules
- new executor semantics
- hidden policy abstractions
- orchestration decision-making

Do NOT modify planner/safety/executor unless a real blocking integration bug is proven by a failing test.

---

## 4. Responsibility Boundary

The harness **observes and records**. It must not:

- decide better actions
- retry failed actions
- reinterpret planner output
- bypass safety
- bypass executor
- mutate scenarios unexpectedly

---

## 5. New Files Created

| File | Purpose |
|---|---|
| `src/evaluation/__init__.py` | Package exports |
| `src/evaluation/scenario.py` | `EvaluationScenario` frozen dataclass |
| `src/evaluation/result_schema.py` | `EvaluationStepRecord`, `EvaluationResult` |
| `src/evaluation/metrics.py` | Pure `compute_metrics()` function |
| `src/evaluation/harness.py` | `EvaluationHarness`, `result_to_json_dict()` |
| `tests/test_evaluation_scenario.py` | Scenario construction/validation tests |
| `tests/test_evaluation_result_schema.py` | Result schema + JSON serialisation tests |
| `tests/test_evaluation_metrics.py` | Metric formula + determinism tests |
| `tests/test_evaluation_harness.py` | Harness behaviour tests (fake pipelines) |

---

## 6. Scenario Model

`EvaluationScenario` is a frozen dataclass:

```python
@dataclass(frozen=True)
class EvaluationScenario:
    scenario_id: str          # non-empty; unique identifier
    name: str                 # non-empty; human-readable
    description: str          # free text
    objects: Tuple[Any, ...]  # initial object definitions
    max_steps: int            # >= 1
    expected_success: bool    # declarative label only — does NOT force outcome
    success_conditions: Tuple[str, ...]  # dissertation traceability labels
    tags: Tuple[str, ...] = ()
```

Rules:
- `scenario_id` and `name` must be non-empty strings.
- `max_steps` must be >= 1.
- No callable fields; no planner logic; no randomness.

---

## 7. Result Schema

`EvaluationStepRecord` — per-step pipeline snapshot:

| Field | Type | Description |
|---|---|---|
| `step_index` | `int` | Zero-based step number |
| `state_before` | serialisable | Workcell state snapshot before pipeline |
| `candidate_action_count` | `int` | Actions proposed by planner |
| `validated_action_count` | `int` | Actions that passed safety |
| `rejected_action_count` | `int` | Actions that failed safety (0 or 1) |
| `executed_action_count` | `int` | Actions successfully executed |
| `rejection_reasons` | `Tuple[str,...]` | Reasons for rejection (empty if none) |
| `executor_status` | `str` | Pipeline status string |
| `state_after` | serialisable | Workcell state snapshot after pipeline |

`EvaluationResult` — aggregated scenario outcome. All fields JSON-serialisable. Exposed via `to_dict()`.

---

## 8. Metrics

`compute_metrics(result) -> dict` — pure function, no IO, no timing, no randomness.

| Metric | Formula |
|---|---|
| `scenario_success` | `result.success` |
| `total_steps` | `result.total_steps` |
| `total_candidate_actions` | direct |
| `total_validated_actions` | direct |
| `total_rejected_actions` | direct |
| `total_executed_actions` | direct |
| `rejection_rate` | `rejected / candidate` if `candidate > 0` else `0.0` |
| `validation_pass_rate` | `validated / candidate` if `candidate > 0` else `0.0` |
| `execution_rate` | `executed / validated` if `validated > 0` else `0.0` |

---

## 9. Harness Behaviour

`EvaluationHarness(pipeline)`:

- `run_scenario(scenario) → EvaluationResult`
- `run_many(scenarios) → tuple[EvaluationResult, ...]`

Loop behaviour:
1. Run up to `scenario.max_steps` pipeline steps.
2. At each step: snapshot state → run pipeline → record counts/reasons → snapshot state.
3. Stop early if pipeline returns `EMPTY` or `REJECTED` (terminal statuses).
4. Never retry. Never modify the plan. Never bypass safety.

Success definition:
- `True` if all steps completed without `REJECTED` terminal status.
- `False` if pipeline returned `REJECTED`.

---

## 10. Acceptance Criteria

Phase 8 is complete when:

1. Evaluation scenario schema exists and is validated.
2. Evaluation result schema exists and is JSON-serialisable.
3. Deterministic metrics exist (pure functions, no IO).
4. Harness can run one scenario.
5. Harness can run multiple scenarios in order.
6. Results are JSON-serialisable via `to_dict()` / `result_to_json_dict()`.
7. Tests prove deterministic repeatability.
8. Tests prove no retry/smart recovery.
9. Tests prove `max_steps` is respected.
10. Tests prove early terminal stop works.
11. Tests prove ordering preserved in batch runs.
12. Phase 1–7 regression still passes.
13. New Phase 8 tests pass.
14. No LLM code added.
15. No PyBullet dependency added.
16. No planner/safety/executor behaviour changed.
