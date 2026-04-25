# Phase 15 — Experiment Batch Runner and Comparative Metrics

## Project

Microsoft IXN Prototype 2.1

## Phase Goal

Create a batch experiment runner that executes multiple scenarios across planner modes and produces comparison-ready JSON/CSV outputs.

This phase turns the Phase 14 single-run experiment layer into reproducible evaluation evidence.

## Current State

Completed:

- Phase 13: planner factory
- Phase 14: non-PyBullet `run_experiment()`

Current evidence flow:

```text
planner_mode → scenario → pipeline → result JSON
```

Target evidence flow:

```text
planner_modes × scenarios × runs
  → run_experiment()
  → per-run JSON
  → batch summary JSON
  → batch summary CSV
  → comparison metrics
```

## Absolute Scope Boundary

Phase 15 is batch evaluation only.

Do not modify:

* safety rules
* executor behaviour
* deterministic planner logic
* model planner logic
* Foundry client
* Foundry bridge
* planner factory semantics
* experiment runner semantics unless strictly needed for batch metadata
* PyBullet app
* GUI
* simulation physics
* evaluation meaning

Do not add:

* retries
* fallback planner
* JSON repair
* model self-correction
* prompt optimisation
* autonomous loops
* dynamic replanning
* live GUI controls
* model ranking
* automatic model selection

## System Invariants

1. Batch runner calls `run_experiment()`.
2. Batch runner does not duplicate pipeline logic.
3. Batch runner does not execute raw model output.
4. Model output remains untrusted.
5. Invalid model output still fails closed.
6. Deterministic mode remains the default baseline.
7. Normal tests do not require Foundry Local.
8. Model mode must be testable with injected fake clients.
9. Batch outputs must be reproducible and machine-readable.
10. Comparative metrics must be descriptive only, not optimisation logic.

## Interface Contract

Create:

```text
src/experiments/batch_runner.py
```

Required dataclass:

```python
@dataclass(frozen=True)
class BatchExperimentResult:
    batch_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    output_dir: Path
    summary_json_path: Path
    summary_csv_path: Path
```

Required public function:

```python
run_batch_experiment(
    batch_name: str = "phase15_batch",
    planner_modes: tuple[str, ...] = ("deterministic",),
    scenario_names: tuple[str, ...] = ("baseline", "empty", "blocked"),
    runs_per_case: int = 1,
    steps: int = 1,
    output_dir: str | Path = "outputs/experiments/batches",
    model_client = None,
) -> BatchExperimentResult
```

## Output Contract

For each batch, create a batch directory:

```text
outputs/experiments/batches/{batch_name}/
```

Required outputs:

```text
runs/
summary.json
summary.csv
```

### Per-run JSON

Per-run JSON files should be produced by the existing Phase 14 runner.

Batch runner should not replace them.

### `summary.json`

Must include:

```json
{
  "batch_name": "phase15_batch",
  "total_runs": 3,
  "successful_runs": 3,
  "failed_runs": 0,
  "cases": [
    {
      "run_id": "deterministic_baseline_001",
      "planner_mode": "deterministic",
      "scenario_name": "baseline",
      "run_index": 1,
      "steps_requested": 1,
      "steps_completed": 1,
      "success": true,
      "output_path": "outputs/...",
      "error_count": 0,
      "errors": []
    }
  ],
  "metrics": {
    "success_rate": 1.0,
    "failure_rate": 0.0,
    "success_by_planner": {
      "deterministic": 1.0
    },
    "success_by_scenario": {
      "baseline": 1.0
    }
  }
}
```

### `summary.csv`

Must include columns:

```text
batch_name
run_id
planner_mode
scenario_name
run_index
steps_requested
steps_completed
success
error_count
output_path
errors
```

## Metrics Contract

Implement descriptive metrics only:

* total runs
* successful runs
* failed runs
* success rate
* failure rate
* success rate by planner
* success rate by scenario
* average steps completed by planner
* average steps completed by scenario

Do not implement:

* optimisation
* automatic selection
* scoring that changes execution
* model ranking for runtime use

## Implementation Tasks

## Task 15.1 — Inspect Phase 14 Runner Output

Inspect:

* `src/experiments/experiment_runner.py`
* `tests/test_experiment_runner.py`
* generated JSON shape if needed

Acceptance:

* Understand `ExperimentResult`.
* Understand exported JSON format.
* No edits yet.

---

## Task 15.2 — Create Batch Runner

Create:

```text
src/experiments/batch_runner.py
```

Implement:

```python
run_batch_experiment(...)
```

Behaviour:

1. Create batch output directory.
2. Create `runs/` subdirectory.
3. Loop over planner modes.
4. Loop over scenario names.
5. Loop over run index.
6. Call `run_experiment()` for each case.
7. Collect results.
8. Write `summary.json`.
9. Write `summary.csv`.
10. Return `BatchExperimentResult`.

Acceptance:

* Batch runner delegates single runs to Phase 14.
* No duplicate pipeline logic.
* No PyBullet/GUI imports.

---

## Task 15.3 — Implement Metrics Helper

Inside `batch_runner.py`, or separate file only if cleaner, implement descriptive metric generation.

Suggested internal function:

```python
_build_metrics(cases: list[dict]) -> dict
```

Acceptance:

* Handles empty case list safely.
* Computes success/failure rates.
* Computes grouped success rates.
* Computes grouped average steps completed.

---

## Task 15.4 — Add Batch Runner Tests

Create:

```text
tests/test_batch_runner.py
```

Required tests: 21 (see spec for full list).

Acceptance:

* Tests are deterministic.
* Tests do not require live Foundry Local.
* Temporary directories are used for outputs.

---

## Task 15.5 — Optional CLI Entrypoint

Only if clean, create:

```text
src/experiments/run_batch.py
```

---

## Task 15.6 — Focused Tests

Run:

```bash
python -m pytest tests/test_batch_runner.py -v
```

---

## Task 15.7 — Full Regression

Run the same full regression command used in Phase 14.

---

## Task 15.8 — Drift Audit

Allowed changes:

* `specs/001-prototype-2.1/phase-15.md`
* `src/experiments/batch_runner.py`
* optional `src/experiments/run_batch.py`
* `tests/test_batch_runner.py`
