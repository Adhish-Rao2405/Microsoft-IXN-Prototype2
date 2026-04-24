# Phase 9 Specification — Experiment Output Layer

## 0. Overview

Phase 9 turns `EvaluationResult` objects (Phase 8) into repeatable,
dissertation-ready artefacts. This phase is about **evidence capture**, not
new intelligence.

### Deliverables

| Module | Contents |
|---|---|
| `src/evaluation/experiment.py` | `ExperimentManifest`, `ExperimentRun` |
| `src/evaluation/exporters.py` | Pure conversion functions + IO helpers |

### Output artefacts (fixed names)

| File | Format |
|---|---|
| `experiment_result.json` | Full experiment run as sorted-key JSON |
| `summary.csv` | One row per scenario; fixed column order |
| `report.md` | Human-readable Markdown report |

---

## 1. Architecture invariants

- No LLM dependency.
- No PyBullet dependency.
- No non-deterministic output — no timestamps, no UUIDs, no wall-clock values.
- All output is written UTF-8.
- `write_experiment_outputs` returns exactly three paths in deterministic
  order: `(experiment_result.json, summary.csv, report.md)`.
- Output directory structure is flat — all three files directly in `output_dir`.
- `EvaluationResult.metrics` contains the pre-computed metrics dict from
  `compute_metrics()`. Exporters use those values directly; they do not recompute.

---

## 2. Data models

### `ExperimentManifest`

```python
@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str      # non-empty, non-whitespace
    name: str               # non-empty
    description: str
    scenario_ids: tuple[str, ...]  # non-empty; no duplicates
    planner_name: str       # non-empty
    pipeline_name: str      # non-empty
    version: str = "prototype-2.1"  # non-empty
    tags: tuple[str, ...] = ()
```

Validation (`__post_init__`):
- `experiment_id`: non-empty, non-whitespace
- `name`, `planner_name`, `pipeline_name`, `version`: non-empty
- `scenario_ids`: non-empty, no duplicate values

`to_dict()` returns a JSON-serialisable dict with keys sorted.
`scenario_ids` and `tags` serialised as lists.

### `ExperimentRun`

```python
@dataclass(frozen=True)
class ExperimentRun:
    manifest: ExperimentManifest
    results: tuple[EvaluationResult, ...]
```

Validation (`__post_init__`):
- `results` is non-empty.
- `[r.scenario_id for r in results]` equals `list(manifest.scenario_ids)` exactly
  (same order, same count).

`to_dict()` returns `{"manifest": ..., "results": [...]}`.

---

## 3. Exporter functions

### Pure conversion

| Function | Signature | Returns |
|---|---|---|
| `manifest_to_dict` | `(manifest) -> dict` | JSON-compatible dict |
| `experiment_run_to_dict` | `(run) -> dict` | JSON-compatible dict |
| `result_to_summary_row` | `(result, *, experiment_id) -> dict` | Row with all CSV columns |
| `results_to_summary_rows` | `(results, *, experiment_id) -> list[dict]` | Rows in input order |

### CSV columns (exact order, do not change)

```
experiment_id, scenario_id, scenario_name, success, expected_success,
final_status, total_steps, total_candidate_actions, total_validated_actions,
total_rejected_actions, total_executed_actions, rejection_rate,
validation_pass_rate, execution_rate, rejection_reasons
```

`rejection_reasons` is a `|`-joined string of the rejection reasons tuple.

### IO functions

| Function | Output file | Description |
|---|---|---|
| `write_experiment_json(output_dir, run) -> Path` | `experiment_result.json` | `sort_keys=True, indent=2` |
| `write_summary_csv(output_dir, run) -> Path` | `summary.csv` | Fixed column order; `newline=""` |
| `write_markdown_report(output_dir, run) -> Path` | `report.md` | See §4 |
| `write_experiment_outputs(output_dir, run) -> tuple[Path, ...]` | all three | Returns `(json, csv, md)` |

All IO functions:
- Create `output_dir` if it does not exist (`mkdir(parents=True, exist_ok=True)`).
- Overwrite existing files silently.
- Write UTF-8.
- Return the `Path` to the created file.

---

## 4. Markdown report format

```
# Experiment Report: <name>

## Metadata
- **Experiment ID**: …
- **Name**: …
- **Description**: …
- **Planner**: …
- **Pipeline**: …
- **Version**: …
- **Tags**: …  (omit line when empty)

## Summary
- **Scenarios**: N
- **Passed**: N
- **Failed**: N
- **Pass rate**: 0.0000

## Scenario Results
| scenario_id | scenario_name | success | final_status | rejection_rate |
|---|---|---|---|---|
| … | … | … | … | … |

## Rejection Reasons
- `<reason>` (count)        ← one line per unique reason, sorted
   OR
No rejected actions recorded.

## Notes
This report is generated deterministically from evaluation results.
No timestamps or non-deterministic values are included.
```

---

## 5. Testing surface

| Test file | Count |
|---|---|
| `tests/test_evaluation_experiment.py` | 26 |
| `tests/test_evaluation_exporters.py` | 45 |
| **Phase 9 total** | **71** |

All Phase 9 tests pass in isolation and within the full regression suite.
No PyBullet or LLM imports in `experiment.py` or `exporters.py` (verified
by AST check in `TestExportersNoBannedImports`).
