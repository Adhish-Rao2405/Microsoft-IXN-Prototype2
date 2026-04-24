# Phase 8 Task List

## Title

Deterministic Evaluation / Experiment Harness

## Objective

Create the first deterministic experiment harness that runs predefined workcell
scenarios through the existing planning pipeline and records measurable outcomes
for dissertation evidence generation.

## Tasks

### 1. Inspect existing interfaces

Read:
- `src/orchestration/pipeline.py` and `types.py`
- `src/simulation/workcell_state.py`
- `src/planning/types.py`
- `src/evaluation/` (once created)
- Existing Phase 3–7 tests for API patterns

### 2. Write tests first

Create before any production code:
- `tests/test_evaluation_scenario.py`
- `tests/test_evaluation_result_schema.py`
- `tests/test_evaluation_metrics.py`
- `tests/test_evaluation_harness.py`

Confirm import errors (expected failures) before implementing.

### 3. Implement evaluation package

Create in order:
1. `src/evaluation/__init__.py`
2. `src/evaluation/scenario.py`
3. `src/evaluation/result_schema.py`
4. `src/evaluation/metrics.py`
5. `src/evaluation/harness.py`

### 4. Run focused Phase 8 suites

```
python -m pytest tests/test_evaluation_scenario.py -v
python -m pytest tests/test_evaluation_result_schema.py -v
python -m pytest tests/test_evaluation_metrics.py -v
python -m pytest tests/test_evaluation_harness.py -v
```

### 5. Run full Phase 3–8 regression

```
python -m pytest tests/test_action_schema.py tests/test_workcell_executor.py \
  tests/test_workcell_safety.py tests/test_workcell_planner.py \
  tests/test_workcell_pipeline.py tests/test_workcell_e2e_scenarios.py \
  tests/test_evaluation_scenario.py tests/test_evaluation_result_schema.py \
  tests/test_evaluation_metrics.py tests/test_evaluation_harness.py -q
```

### 6. Record completion

Update this file with final test counts and regression result.

## Completion Record

Status: Complete

Focused Phase 8 results:
- `test_evaluation_scenario.py`: 16 passed
- `test_evaluation_result_schema.py`: 17 passed
- `test_evaluation_metrics.py`: 19 passed
- `test_evaluation_harness.py`: 35 passed
- Total Phase 8: 87 passed

Full Phase 3–8 regression: 320 passed in 1.44s

Production code changes required: None

No LLM code introduced: confirmed

No PyBullet dependency introduced: confirmed (AST-verified in harness test)

Files created:
- `src/evaluation/__init__.py`
- `src/evaluation/scenario.py`
- `src/evaluation/result_schema.py`
- `src/evaluation/metrics.py`
- `src/evaluation/harness.py`
- `tests/test_evaluation_scenario.py`
- `tests/test_evaluation_result_schema.py`
- `tests/test_evaluation_metrics.py`
- `tests/test_evaluation_harness.py`
- `specs/001-prototype-2.1/phase8-spec.md`
- `specs/001-prototype-2.1/tasks-phase8.md`

Boundary issues found:
- None. The existing PipelineResult public interface (candidate_actions,
  validated_actions, executed_actions, rejected_action, rejection_reason,
  status) was sufficient for all harness observation needs without any
  production code changes.
