# Phase 9 Task Record — Experiment Output Layer

## Status: COMPLETE

## Test counts

| Suite | Tests | Status |
|---|---|---|
| `tests/test_evaluation_experiment.py` | 26 | ✅ All passing |
| `tests/test_evaluation_exporters.py` | 45 | ✅ All passing |
| **Phase 9 subtotal** | **71** | ✅ |
| **Phase 1–9 regression (excl. pybullet)** | **562** | ✅ |

## Modules created

| Module | Purpose |
|---|---|
| `src/evaluation/experiment.py` | `ExperimentManifest`, `ExperimentRun` frozen dataclasses |
| `src/evaluation/exporters.py` | Pure conversion functions + IO: JSON, CSV, Markdown |

`src/evaluation/__init__.py` updated to export all Phase 9 symbols.

## Test files created

- `tests/test_evaluation_experiment.py` — 26 tests covering construction,
  validation, immutability, and serialisation of `ExperimentManifest` and
  `ExperimentRun`.
- `tests/test_evaluation_exporters.py` — 45 tests covering pure conversion
  functions, all three IO writers, `write_experiment_outputs`, and AST-based
  banned-import checks.

## Key design decisions

- `ExperimentManifest.to_dict()` returns keys in alphabetical order for
  deterministic JSON output.
- `write_experiment_json` uses `sort_keys=True, indent=2`.
- `write_summary_csv` uses `newline=""` and fixed `_CSV_COLUMNS` order.
- `write_markdown_report` omits all timestamps; rejection reasons sorted
  alphabetically.
- `write_experiment_outputs` returns `(json_path, csv_path, md_path)` in
  fixed order per spec.
- No timestamp, UUID, or non-deterministic value appears in any output.
- AST checks verify no pybullet / LLM imports enter the new modules.
