# Phase 16 — Adversarial Model Output Evaluation

## Project

Microsoft IXN Prototype 2.1

## Phase Goal

Create an adversarial model-output evaluation layer that deliberately feeds unsafe, malformed, incomplete, or hallucinated model responses into the existing model-planner pipeline to prove fail-closed behaviour.

## Absolute Scope Boundary

Phase 16 is adversarial evaluation only.  No safety, executor, planner, or model client changes.

## System Invariants

1. Bad model output must remain bad.
2. Invalid output must not be repaired.
3. Invalid output must not be executed.
4. Unsafe actions must not reach execution.
5. All adversarial tests must use fake clients.
6. Normal tests must not require Foundry Local.
7. Existing parser/validator/safety must remain the enforcement boundary.
8. Evaluation must record failures, not hide them.
9. Zero unsafe executions is the expected success criterion.
10. This phase must not make the model smarter.

## New Files

- `src/experiments/adversarial_cases.py`
- `src/experiments/adversarial_runner.py`
- `src/experiments/run_adversarial.py` (optional CLI)
- `tests/test_adversarial_cases.py`
- `tests/test_adversarial_runner.py`

## Adversarial Cases (minimum 12)

1. `malformed_json`
2. `unknown_action_type`
3. `missing_required_fields`
4. `unsafe_target_coordinates`
5. `unsafe_speed`
6. `unsafe_force`
7. `extra_unexpected_fields`
8. `markdown_wrapped_json`
9. `prose_before_json`
10. `empty_response`
11. `multiple_actions`
12. `wrong_top_level_type`

## Acceptance Gates

- All 12+ adversarial cases exist.
- Runner evaluates all cases using fake clients.
- `unsafe_passes == 0`.
- `summary.json` and `summary.csv` are created.
- Full regression passes.
- Drift audit passes (only expected files changed).
