# Phase 14 — Non-PyBullet Experiment Runner

## Project

Microsoft IXN Prototype 2.1

## Phase Goal

Create a non-PyBullet experiment runner that can execute controlled planner experiments using the existing workcell pipeline.

This phase provides a clean way to run:

- deterministic planner experiments
- model planner experiments
- fixed scenario batches
- exported evaluation results

without modifying the legacy PyBullet `app.py`.

## Current State

Completed:

- Phase 11: `FoundryLocalClient`
- Phase 12: `FoundryModelClient`
- Phase 13: `planner_factory.py`

Important finding from Phase 13:

- `src/app.py` is legacy/PyBullet-coupled.
- Runtime wiring was correctly deferred.
- The new stack already supports dependency injection through `WorkcellPipeline`.

## Target Architecture

```text
Experiment Runner
  → Scenario Input
  → Workcell State
  → Planner Factory
      → Planner()
      OR
      → ModelPlanner(...)
  → Safety
  → Executor
  → Evaluation
  → Export
```

## Absolute Scope Boundary

Phase 14 is experiment runner only.

Do not modify:

* safety rules
* executor behaviour
* deterministic planner logic
* model planner logic
* Foundry client
* Foundry bridge
* planner factory behaviour unless strictly needed for import compatibility
* PyBullet app
* GUI
* evaluation metric semantics
* export schema semantics

Do not add:

* retries
* fallback planner
* JSON repair
* model self-correction
* autonomous loops
* prompt optimisation
* dynamic replanning
* live GUI controls

## System Invariants

1. Experiments are deterministic unless explicitly using model mode.
2. Deterministic mode must not require Foundry Local.
3. Model mode must still treat model output as untrusted.
4. All actions must pass existing validation and safety.
5. Failed model output must fail closed.
6. Runner must not execute raw model output directly.
7. Runner must not import PyBullet or GUI modules.
8. Runner must produce reproducible output files.
9. Runner must be testable without a live model.
10. Runner must not alter existing pipeline behaviour.

## Interface Contract

Create:

```text
src/experiments/experiment_runner.py
```

Required public function:

```python
run_experiment(
    planner_mode: str = "deterministic",
    scenario_name: str = "baseline",
    steps: int = 1,
    output_dir: str | Path = "outputs/experiments",
    model_client = None,
) -> ExperimentResult
```

Create result dataclass:

```python
@dataclass(frozen=True)
class ExperimentResult:
    scenario_name: str
    planner_mode: str
    steps_requested: int
    steps_completed: int
    success: bool
    output_path: Path | None
    errors: tuple[str, ...]
```

## Scenario Contract

Create:

```text
src/experiments/scenarios.py
```

Required function:

```python
create_scenario(name: str)
```

Supported scenarios for Phase 14:

```text
baseline
empty
blocked
```

Scenario requirements:

* Must create valid workcell state objects using existing simulation/state classes.
* Must not require PyBullet.
* Must be deterministic.
* Must be small and fast.

If existing state constructors make these exact names difficult, implement the simplest equivalent scenarios and document them in tests.

## Export Contract

Runner must export results to:

```text
outputs/experiments/
```

Suggested filename format:

```text
{scenario_name}_{planner_mode}_{timestamp_or_counter}.json
```

Exported JSON must include at minimum:

```json
{
  "scenario_name": "baseline",
  "planner_mode": "deterministic",
  "steps_requested": 1,
  "steps_completed": 1,
  "success": true,
  "errors": [],
  "actions": [],
  "evaluations": []
}
```

Use existing export utilities if clean.

If existing export utilities are not compatible, create a minimal local JSON export inside the experiment runner. Do not modify export schema globally.

## Implementation Tasks

## Task 14.1 — Inspect Existing Pipeline and Export Layer

Inspect:

* `src/orchestration/pipeline.py`
* `src/evaluation/*`
* `src/export/*`
* `src/simulation/workcell_state.py`
* `src/planning/planner_factory.py`
* relevant tests from Phases 8–13

Acceptance:

* Understand how to run one pipeline step.
* Understand how evaluation/export currently work.
* No edits yet.

---

## Task 14.2 — Create Experiments Package

Create:

```text
src/experiments/__init__.py
src/experiments/scenarios.py
src/experiments/experiment_runner.py
```

Acceptance:

* Package imports cleanly.
* No PyBullet imports.

---

## Task 14.3 — Implement Scenario Creation

Implement:

```python
create_scenario(name: str)
```

Required scenarios:

1. `baseline`
2. `empty`
3. `blocked`

Rules:

* Unknown scenario raises `ValueError`.
* Each scenario returns a valid state/snapshot compatible with existing planner/pipeline.
* Scenarios must be deterministic.

Acceptance:

* Scenario unit tests can instantiate all scenarios.
* No external services required.

---

## Task 14.4 — Implement `run_experiment`

Implement:

```python
run_experiment(...)
```

Behaviour:

1. Create scenario state.
2. Create planner using `create_planner(planner_mode, model_client=model_client)`.
3. Create/use existing pipeline components.
4. Run for `steps`.
5. Collect actions/evaluation records/errors.
6. Export JSON result.
7. Return `ExperimentResult`.

Failure handling:

* Invalid scenario → controlled `ValueError`.
* Invalid planner mode → controlled `ValueError`.
* Model failure → record error and fail closed.
* Safety/executor failure → record error and fail closed.

Do not silently swallow errors.

Acceptance:

* Deterministic mode can run without Foundry Local.
* Model mode can run with injected fake client.
* Output JSON is created.

---

## Task 14.5 — Add Unit Tests for Scenarios

Create:

```text
tests/test_experiment_scenarios.py
```

Required tests:

1. `baseline` scenario creates valid state.
2. `empty` scenario creates valid state.
3. `blocked` scenario creates valid state.
4. Unknown scenario raises `ValueError`.
5. Scenario creation is deterministic.
6. Scenarios do not import PyBullet/GUI.

---

## Task 14.6 — Add Unit Tests for Experiment Runner

Create:

```text
tests/test_experiment_runner.py
```

Required tests:

1. Deterministic baseline run completes.
2. Deterministic empty run completes or fails closed in controlled way.
3. Deterministic blocked run completes or fails closed in controlled way.
4. Output JSON file is created.
5. Output JSON includes required fields.
6. Invalid scenario raises `ValueError`.
7. Invalid planner mode raises `ValueError`.
8. Model mode works with injected fake client returning valid JSON.
9. Model mode with injected fake client returning invalid JSON fails closed.
10. Model mode does not require live Foundry Local when fake client is injected.
11. Runner does not import PyBullet/GUI.
12. Runner does not modify safety/executor/planner logic.

---

## Task 14.7 — Optional CLI Entrypoint

Only if clean, create:

```text
src/experiments/run_experiment.py
```

Allowed command:

```bash
python -m src.experiments.run_experiment --planner deterministic --scenario baseline --steps 1
```

Optional model command:

```bash
python -m src.experiments.run_experiment --planner model --scenario baseline --steps 1
```

Rules:

* CLI must call `run_experiment()`.
* CLI must not duplicate logic.
* CLI must not import PyBullet.
* CLI must not become interactive.

If CLI is not clean, defer it.

---

## Task 14.8 — Focused Tests

Run:

```bash
python -m pytest tests/test_experiment_scenarios.py tests/test_experiment_runner.py -v
```

Acceptance:

* All Phase 14 focused tests pass.

---

## Task 14.9 — Full Regression

Run the same full regression command used in Phase 13.

Acceptance:

* Existing tests pass.
* Phase 11, 12, and 13 tests still pass.
* New Phase 14 tests pass.

---

## Task 14.10 — Drift Audit

Run:

```bash
git diff --name-only HEAD
git status --short
```

Allowed changes:

* `specs/001-prototype-2.1/phase-14.md`
* `src/experiments/__init__.py`
* `src/experiments/scenarios.py`
* `src/experiments/experiment_runner.py`
* optional `src/experiments/run_experiment.py`
* `tests/test_experiment_scenarios.py`
* `tests/test_experiment_runner.py`

Drift checklist:

* no safety changes
* no executor changes
* no planner logic changes
* no model client changes
* no Foundry bridge changes
* no evaluation semantic changes
* no export semantic changes
* no PyBullet/GUI changes
* no retries
* no fallback planner
* no JSON repair
* no autonomy upgrade

## Acceptance Gates

### Gate 1 — Scenario Layer Exists

* Scenarios can be created deterministically.
* No PyBullet dependency.

### Gate 2 — Runner Exists

* `run_experiment()` runs deterministic experiments.

### Gate 3 — Model Mode Testable

* Model mode works with injected fake client.
* Invalid model output fails closed.

### Gate 4 — Export Exists

* JSON output file is created.
* Required fields are present.

### Gate 5 — Regression Pass

* Focused and full tests pass.

### Gate 6 — Drift Clean

* Only expected files changed.
* No behaviour outside experiment running changed.

## Definition of Done

Phase 14 is complete only when:

1. `src/experiments` package exists.
2. `create_scenario()` supports at least three deterministic scenarios.
3. `run_experiment()` can run deterministic mode.
4. `run_experiment()` can run model mode with fake client.
5. Results are exported to JSON.
6. Invalid model output fails closed.
7. Normal tests do not require Foundry Local.
8. No PyBullet/GUI dependency is introduced.
9. Full regression passes.
10. Drift audit passes.

## Suggested Git Commands

After tests pass:

```bash
git status
git add specs/001-prototype-2.1/phase-14.md
git add src/experiments/__init__.py
git add src/experiments/scenarios.py
git add src/experiments/experiment_runner.py
git add src/experiments/run_experiment.py
git add tests/test_experiment_scenarios.py
git add tests/test_experiment_runner.py
git commit -m "Phase 14: add non-PyBullet experiment runner"
git tag phase-14-experiment-runner
git push origin main --tags
```

Only add files that actually exist.
