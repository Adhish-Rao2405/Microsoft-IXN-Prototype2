# Phase 13 — Planner Selection Mechanism

## Project

Microsoft IXN Prototype 2.1

## Phase Goal

Introduce a controlled planner-selection mechanism so the system can manually choose between:

1. `DeterministicPlanner`
2. `ModelPlanner` using `FoundryModelClient`

This phase activates selection only. It must not improve, modify, or reinterpret planning behaviour.

## Current Architecture

```text
State → Planner → Safety → Executor → Evaluation → Export
```

## Target Phase 13 Architecture

```text
State
  → Selected Planner
      → DeterministicPlanner
      OR
      → ModelPlanner(client=FoundryModelClient)
  → Safety
  → Executor
  → Evaluation
  → Export
```

## Absolute Scope Boundary

Phase 13 is planner selection only.

Do not modify:

* `DeterministicPlanner` planning logic
* `ModelPlanner` parsing / validation logic
* safety rules
* executor behaviour
* evaluation metrics
* export format
* simulation logic
* GUI / PyBullet logic
* Foundry client behaviour
* Foundry bridge behaviour

Do not add:

* retries
* fallback planner
* automatic switching
* self-correction
* JSON repair
* prompt improvement
* hidden intelligence
* agent loops
* model-output execution bypass

## System Invariants

These must remain true:

1. Planner mode is manually selected.
2. Default mode is deterministic.
3. Invalid planner mode fails explicitly.
4. Model output remains untrusted.
5. Model output still goes through existing validation.
6. Safety remains the final gate before execution.
7. Executor only receives validated and safety-checked actions.
8. No planner may bypass safety.
9. No planner may bypass evaluation/export pipeline.
10. Failed model output must fail closed exactly as before.
11. Phase 13 must not require Foundry Local for normal tests.

## Configuration Contract

Use environment variable:

```text
PLANNER_MODE
```

Allowed values:

```text
deterministic
model
```

Default:

```text
deterministic
```

Invalid values must raise a controlled error.

## Interface Contract

Create:

```text
src/planning/planner_factory.py
```

Required public function:

```python
create_planner(mode: str | None = None)
```

Behaviour:

* If `mode is None`, read `PLANNER_MODE` from environment.
* If environment variable is missing, default to `"deterministic"`.
* If mode is `"deterministic"`, return `DeterministicPlanner()`.
* If mode is `"model"`, return `ModelPlanner(client=FoundryModelClient())`.
* If mode is invalid, raise `ValueError`.

Optional helper:

```python
get_planner_mode(mode: str | None = None) -> str
```

This may be used to centralise validation.

## Dependency Contract

`planner_factory.py` may import:

* `os`
* deterministic planner module
* `ModelPlanner`
* `FoundryModelClient`

It must not import:

* safety
* executor
* evaluation
* export
* PyBullet
* GUI
* simulation runtime

## Implementation Tasks

## Task 13.1 — Inspect Planner Instantiation Points

Search for where planners are currently created.

Inspect likely files:

* `src/planning/model_planner.py`
* `src/planning/deterministic_planner.py`
* any runner / app / orchestrator files
* tests that instantiate planners directly

Do not edit yet.

Acceptance:

* Identify whether there is a clean runtime insertion point.
* Identify whether factory can be added without rewiring app logic.
* No behaviour changed.

---

## Task 13.2 — Create Planner Factory

Create:

```text
src/planning/planner_factory.py
```

Implement:

```python
create_planner(mode: str | None = None)
```

Expected behaviour:

```text
mode=None + no env var        → DeterministicPlanner
mode=None + env deterministic → DeterministicPlanner
mode=None + env model         → ModelPlanner with FoundryModelClient
mode="deterministic"          → DeterministicPlanner
mode="model"                  → ModelPlanner with FoundryModelClient
mode invalid                  → ValueError
```

Acceptance:

* Factory exists.
* Default is deterministic.
* Invalid mode fails explicitly.
* No planner internals changed.

---

## Task 13.3 — Add Dependency Injection Support if Needed

Only if necessary, allow custom clients for tests.

Preferred function shape:

```python
create_planner(
    mode: str | None = None,
    model_client = None,
)
```

Rules:

* `model_client` is only used when mode is `"model"`.
* If model mode and `model_client is None`, use `FoundryModelClient()`.
* Deterministic mode must ignore `model_client`.

Acceptance:

* Tests can create a model planner without real Foundry Local.
* Normal model mode still uses `FoundryModelClient`.
* No live model required in tests.

---

## Task 13.4 — Add Factory Unit Tests

Create:

```text
tests/test_planner_factory.py
```

Required tests:

1. Default with no env var returns `DeterministicPlanner`.
2. Env `PLANNER_MODE=deterministic` returns `DeterministicPlanner`.
3. Env `PLANNER_MODE=model` returns `ModelPlanner`.
4. Explicit `mode="deterministic"` returns `DeterministicPlanner`.
5. Explicit `mode="model"` returns `ModelPlanner`.
6. Explicit mode overrides environment variable.
7. Invalid mode raises `ValueError`.
8. Model mode accepts injected fake model client.
9. Deterministic mode ignores injected fake model client.
10. Factory module does not import safety/executor/evaluation/export/PyBullet/GUI.

Acceptance:

* Tests are deterministic.
* Tests do not require Foundry Local.
* Tests do not execute actions.

---

## Task 13.5 — Add Planner Selection Compatibility Tests

Extend existing planner tests or create:

```text
tests/test_planner_selection.py
```

Required tests:

### Deterministic path

* Create planner via factory in deterministic mode.
* Run same style of planning call already used by existing deterministic tests.
* Confirm result type/behaviour matches existing deterministic planner expectations.

### Model path, valid output

* Create planner via factory in model mode using injected fake client.
* Fake client returns valid raw JSON action.
* Confirm existing `ModelPlanner` parser/validation accepts it.

### Model path, invalid output

* Create planner via factory in model mode using injected fake client.
* Fake client returns invalid/malformed output.
* Confirm existing failure behaviour is preserved.

Acceptance:

* Selection changes which planner is created only.
* Validation still belongs to existing planner path.
* Invalid model output still fails closed.
* No live Foundry Local call.

---

## Task 13.6 — Wire Runtime Only if Clean

Search for a clean runtime planner creation point.

Allowed:

```python
from src.planning.planner_factory import create_planner

planner = create_planner()
```

Only replace direct planner construction if:

* there is one obvious runtime entry point
* the change does not alter tests unexpectedly
* the change does not introduce GUI/PyBullet coupling into factory

Forbidden:

* do not rewrite app architecture
* do not build a new CLI
* do not change executor pipeline
* do not change evaluation pipeline

If no clean insertion point exists:

* leave factory tested and ready
* document that runtime wiring is deferred

Acceptance:

* Either clean runtime hook added, or explicitly deferred.
* No forced integration.

---

## Task 13.7 — Focused Test Pass

Run:

```bash
python -m pytest tests/test_planner_factory.py tests/test_planner_selection.py -v
```

If `test_planner_selection.py` was not created, run the relevant modified planner test file instead.

Acceptance:

* New Phase 13 tests pass.
* Existing planner tests still pass.

---

## Task 13.8 — Full Regression Pass

Run the same full regression command used in Phase 12.

If the project has known heavy/manual tests, use the same ignore list as Phase 12 and report it exactly.

Acceptance:

* Existing tests pass.
* Phase 11 and Phase 12 tests still pass.
* New Phase 13 tests pass.

---

## Task 13.9 — Drift Audit

Run:

```bash
git diff --name-only HEAD
git status --short
```

Check modified files.

Allowed changes:

* `specs/001-prototype-2.1/phase-13.md`
* `src/planning/planner_factory.py`
* `tests/test_planner_factory.py`
* optional `tests/test_planner_selection.py`
* optional clean runtime entry-point file, only if justified

Unexpected changes must be reverted unless explicitly required.

Drift checklist:

* no safety changes
* no executor changes
* no evaluation/export changes
* no deterministic planner logic changes
* no model planner logic changes
* no Foundry client changes
* no Foundry bridge changes
* no retries
* no fallback planner
* no JSON repair
* no autonomous loop
* no GUI/PyBullet changes

## Acceptance Gates

### Gate 1 — Factory Exists

* `planner_factory.py` exists.
* `create_planner()` works.

### Gate 2 — Configuration Works

* `PLANNER_MODE` controls planner type.
* Default is deterministic.
* Invalid mode fails explicitly.

### Gate 3 — Model Path Uses Bridge

* Model mode creates `ModelPlanner(client=FoundryModelClient())`.
* Tests can inject fake client.

### Gate 4 — Validation Boundary Preserved

* Valid model output passes through existing validation.
* Invalid output fails closed.
* No schema validation added to factory.

### Gate 5 — Regression Pass

* Focused tests pass.
* Full regression passes.

### Gate 6 — Drift Audit Pass

* Only expected files changed.
* No autonomy or behaviour upgrades added.

## Definition of Done

Phase 13 is complete only when:

1. `create_planner()` exists.
2. `PLANNER_MODE` supports deterministic and model modes.
3. Default planner mode is deterministic.
4. Invalid mode raises explicit error.
5. Model mode uses `ModelPlanner` with `FoundryModelClient`.
6. Tests can inject a fake model client.
7. Deterministic behaviour remains unchanged.
8. Model output remains untrusted.
9. Invalid model output still fails closed.
10. Normal tests do not require Foundry Local.
11. Full regression passes.
12. Drift audit passes.

## Suggested Git Commands

After tests pass:

```bash
git status
git add specs/001-prototype-2.1/phase-13.md
git add src/planning/planner_factory.py
git add tests/test_planner_factory.py
git add tests/test_planner_selection.py
git commit -m "Phase 13: add planner selection mechanism"
git tag phase-13-planner-selection
git push origin main --tags
```

Only add files that actually exist.
