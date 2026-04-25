# Phase 17 — Results Aggregation and Dissertation Evidence Pack

## Project

Microsoft IXN Prototype 2.1

## Phase Goal

Aggregate Phase 15 batch results and Phase 16 adversarial results into a
final dissertation-ready evidence pack.

## New Files

- `src/experiments/evidence_pack.py`
- `src/experiments/build_evidence_pack.py` (optional CLI)
- `tests/test_evidence_pack.py`

## Output Files

```text
outputs/evidence_pack/
  evidence_summary.json
  evidence_summary.csv
  adversarial_summary.csv
  dissertation_metrics.md
```

## Acceptance Gates

- `build_evidence_pack()` loads batch + adversarial summaries.
- All four output files are created.
- Unsafe passes explicitly reported; `fail_closed_verified` true when 0.
- Full regression passes.
- Drift audit passes (only expected files changed).
