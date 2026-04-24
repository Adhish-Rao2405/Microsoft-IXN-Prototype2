# Phase 6 — Planning Pipeline / Orchestrator

## Phase 6.1 — Inspect existing interfaces
- [x] Read `src/planning/planner.py`
- [x] Read `src/planning/types.py`
- [x] Read `src/safety/workcell_safety.py`
- [x] Read `src/executor/workcell_executor.py`
- [x] Read `src/brain/action_schema.py`
- [x] Align orchestration behavior to real method names and payload shapes

## Phase 6.2 — Define orchestration types
- [x] Create `src/orchestration/__init__.py`
- [x] Create `src/orchestration/errors.py`
- [x] Create `src/orchestration/types.py`
- [x] Define `PipelineError`
- [x] Define `PipelineExecutionError`
- [x] Define `PipelineStatus`
- [x] Define frozen `PipelineResult`

## Phase 6.3 — Write tests
- [x] Create `tests/test_workcell_pipeline.py`
- [x] Add module isolation and banned-import coverage
- [x] Add empty-plan coverage
- [x] Add validate-only flow coverage
- [x] Add execute-mode coverage
- [x] Add safety-rejection coverage
- [x] Add planner interaction coverage
- [x] Add malformed output and error propagation coverage
- [x] Add determinism coverage

## Phase 6.4 — Implement pipeline
- [x] Create `src/orchestration/pipeline.py`
- [x] Preserve planner action order
- [x] Validate full plan before any execution
- [x] Stop on first safety rejection
- [x] Preserve safety rejection reason
- [x] Keep planner output unchanged in the result
- [x] Require executor only for `execute=True`
- [x] Keep planner, safety, and executor responsibilities separate

## Phase 6.5 — Run tests
- [x] Run `tests/test_workcell_pipeline.py`
- [x] Confirm focused Phase 6 suite passes

## Phase 6.6 — Regression
- [x] Run Phase 3–6 regression command
- [x] Confirm no regressions in schema, executor, safety, planner, or pipeline

## Phase 6.7 — Document final status
- [x] Add `specs/001-prototype-2.1/phase6-spec.md`
- [x] Add `specs/001-prototype-2.1/tasks-phase6.md`
- [x] Update final status after regression completes