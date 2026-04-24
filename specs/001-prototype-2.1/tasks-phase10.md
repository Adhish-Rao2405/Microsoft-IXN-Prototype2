# Phase 10 Task Record — LLM/SLM Planner Adapter Baseline

## Status: COMPLETE

---

## Task 10.1 — Inspect existing planner/action interfaces ✅

- Confirmed `Action` and `Plan` in `src/planning/types.py`.
- `Action(action: str, parameters: dict)` with `to_dict()`.
- `Plan(actions: list[Action])` with `to_dict()` and `plan.actions`.
- `WorkcellPipeline.plan(state)` duck-type contract: returns object with `.actions`.
- `ALLOWED_WORKCELL_ACTIONS`, `WORKCELL_ACTION_SCHEMAS` in `src/brain/action_schema.py`.
- `WorkcellState.to_dict()` in `src/simulation/workcell_state.py`.

---

## Task 10.2 — Write response parser tests ✅

File: `tests/test_model_response.py` — 31 tests.

Covers: valid empty/single/multi, reject non-JSON, reject markdown fences,
reject top-level list, reject missing/extra top-level keys, reject invalid
action items, reject partial acceptance, immutability, determinism, no
banned imports.

---

## Task 10.3 — Write prompt builder tests ✅

File: `tests/test_model_prompt.py` — 20 tests.

Covers: string, non-empty, determinism, state inclusion, JSON requirement,
no markdown, candidate-only boundary, no execution authority, safety mention,
sorted-key state JSON, available action names, no timestamp/UUID, no
PyBullet import.

---

## Task 10.4 — Write model planner tests ✅

File: `tests/test_model_planner.py` — 20 tests.

Covers: client called once, prompt passed, valid/invalid JSON/schema results,
no retry, no state mutation, no safety, no execution, determinism, rejection
reason, pipeline compatibility (empty plan on malformed), no banned imports.

---

## Task 10.5 — Implement model response parser ✅

File: `src/planning/model_response.py`

- `ModelPlanParseResult(actions, accepted, rejection_reason)` — frozen dataclass.
- `parse_model_response_text(text) -> ModelPlanParseResult` — rejects markdown fences first, then JSON parse.
- `parse_model_response_dict(payload) -> ModelPlanParseResult` — strict structural + schema validation.
- No repair. No fuzzy. No defaults. No eval/exec. No PyBullet.

---

## Task 10.6 — Implement deterministic prompt builder ✅

File: `src/planning/model_prompt.py`

- `build_model_planner_prompt(state) -> str` — deterministic.
- Includes state via `state.to_dict()` with `sort_keys=True`.
- Lists all `ALLOWED_WORKCELL_ACTIONS` sorted.
- States candidate-only boundary, no execution, no safety authority, strict JSON.
- No timestamps, no UUIDs, no markdown fences in prompt.

---

## Task 10.7 — Implement model planner adapter ✅

Files:
- `src/planning/model_client.py` — `ModelClient(Protocol)` with `complete(prompt) -> str`.
- `src/planning/model_planner.py` — `ModelPlanner` with `plan(state) -> Plan` and `last_rejection_reason() -> str | None`.

---

## Task 10.8 — Run focused tests ✅

```
python -m pytest tests/test_model_response.py tests/test_model_prompt.py tests/test_model_planner.py -v
```

Result: **71 passed** in 0.58 s.

---

## Task 10.9 — Run full deterministic regression ✅

```
python -m pytest -v --ignore=tests/test_agents.py --ignore=tests/test_integration.py --ignore=tests/test_render_app_screenshots.py --ignore=tests/test_render_screenshots.py
```

Result: **633 passed** in 4.88 s.

---

## Task 10.10 — Document boundaries and non-goals ✅

See `specs/001-prototype-2.1/phase10-spec.md` §8 (Non-goals) and §2 (Threat model).

Key boundary: Phase 10 stops before live Foundry Local integration. No HTTP
client is implemented. No model is loaded or called. Tests use only
`FakeModelClient`.

---

## Summary of files

| File | Action |
|---|---|
| `src/planning/model_response.py` | Created |
| `src/planning/model_prompt.py` | Created |
| `src/planning/model_client.py` | Created |
| `src/planning/model_planner.py` | Created |
| `tests/test_model_response.py` | Created |
| `tests/test_model_prompt.py` | Created |
| `tests/test_model_planner.py` | Created |
| `specs/001-prototype-2.1/phase10-spec.md` | Created |
| `specs/001-prototype-2.1/tasks-phase10.md` | Created |

No existing files modified. Planner/safety/executor/pipeline unchanged.
