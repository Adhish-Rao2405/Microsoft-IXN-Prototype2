# Prototype 2.1 Spec Pack

This directory contains the implementation baseline for Microsoft IXN Prototype 2.1: a local multi-agent PyBullet workcell for conveyor-based object sorting.

## Documents

- [overview.md](overview.md): Purpose, scope, architecture, behavior, and failure handling.
- [requirements.md](requirements.md): Functional requirements, non-functional requirements, safety rules, and sorting logic.
- [action-schema.md](action-schema.md): Approved planner actions and executor contract.
- [workcell-state.md](workcell-state.md): Structured workcell state schema and refresh requirements.
- [tasks.md](tasks.md): Phase-by-phase implementation plan and acceptance checklist.
- [phase7-spec.md](phase7-spec.md): Phase 7 deterministic end-to-end integration test scope and acceptance criteria.
- [tasks-phase7.md](tasks-phase7.md): Phase 7 implementation checklist and regression record.
- [evaluation.md](evaluation.md): Acceptance criteria, metrics, fixed scenarios, risks, and future extensions.

## Baseline Goal

Build a deterministic stop-pick-place-restart conveyor sorting loop where local agents plan, validate, execute, and explain safe workcell actions without cloud services.
