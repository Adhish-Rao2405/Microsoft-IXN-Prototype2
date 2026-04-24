# Phase 7 Task List

## Title

End-to-End Deterministic Workcell Scenario Tests

## Objective

Verify that the deterministic workcell stack works end to end without introducing new intelligence or new runtime dependencies.

## Tasks

### 1. Read the real deterministic stack

Read the actual implementation and tests for:

- Workcell state construction
- Planner
- Safety validation
- Orchestration or pipeline
- Executor

Do not assume API names or field shapes.

### 2. Create the Phase 7 spec

Create:

- `specs/001-prototype-2.1/phase7-spec.md`

Document:

- Purpose
- Architecture under test
- Non-goals
- Required scenario coverage
- Acceptance criteria

### 3. Create deterministic end-to-end scenario tests

Create:

- `tests/test_workcell_e2e_scenarios.py`

Use the real deterministic stack where practical.

Prefer meaningful integration over heavy mocking.

### 4. Keep production changes minimal

- Prefer no production-code changes.
- Only fix production code if a failing scenario test proves a real integration bug.
- Do not broaden planner, safety, executor, or orchestration behavior during Phase 7.

### 5. Prove the required scenarios

Cover:

- Empty workcell
- Single object full flow
- Multiple objects deterministic order
- Unknown type default or reject routing if supported
- Processed object skipped
- Safety rejection prevents execution
- Full-plan validation before execution
- Determinism across repeated runs
- No legacy LLM coupling
- No PyBullet coupling

### 6. Run focused regression

Run the relevant deterministic workcell regression tests after Phase 7 changes.

Record the final regression result in this file once Phase 7 is complete.

## Completion Record

Status: Complete

Focused regression result: 42 passed (tests/test_workcell_e2e_scenarios.py)

Full Phase 3–7 regression result: 233 passed in 1.10s

Production code changes required: None
