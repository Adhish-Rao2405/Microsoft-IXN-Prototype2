# Phase 5 — Deterministic Planner

## Phase 5.1 — Create planning module
- [x] Create `src/planning/__init__.py`
- [x] Create `src/planning/errors.py` — `PlanningError`
- [x] Create `src/planning/types.py` — `Action`, `Plan`
- [x] Create `src/planning/rules.py` — routing table, predicates, builders
- [x] Create `src/planning/planner.py` — `Planner` class

### Requirements
- [x] No PyBullet imports
- [x] No executor imports
- [x] No agent imports
- [x] No safety layer imports
- [x] No hidden globals
- [x] No state mutation

---

## Phase 5.2 — Implement Action and Plan types
- [x] `Action` with `action: str` and `parameters: dict`
- [x] `Plan` with `actions: list[Action]`
- [x] `to_dict()` on both (Phase 3 wire format)
- [x] `Plan.__eq__` for determinism testing

### Requirements
- [x] JSON-serialisable
- [x] No strategy/recommendation fields
- [x] Wire format aligns with Phase 3 schema (`action` key, not `type`)

---

## Phase 5.3 — Implement planning rules
- [x] `BIN_ROUTING` table (`red → bin_a`, `blue → bin_b`)
- [x] `DEFAULT_BIN = "bin_a"` (valid registry bin)
- [x] `is_plannable_object(obj)` — checks `on_conveyor`
- [x] `sort_plannable_objects(objects)` — ascending `id` sort
- [x] `resolve_target_bin(color)` — table lookup with default
- [x] `make_pick_action(object_id)` — returns `Action`
- [x] `make_place_action(bin_id)` — returns `Action`

### Requirements
- [x] Routing is explicit, not inferred
- [x] Default bin is a valid registered bin
- [x] Sorting is stable and canonical

---

## Phase 5.4 — Implement Planner class
- [x] `plan(state) -> Plan`
- [x] Validate state is not None
- [x] Validate state has `list_objects()`
- [x] Validate objects have required fields (`id`, `color`)
- [x] Detect and reject duplicate object IDs
- [x] Filter eligible objects (`is_plannable_object`)
- [x] Sort eligible objects (`sort_plannable_objects`)
- [x] Generate `pick_target` + `place_in_bin` subplan per object
- [x] Return `Plan(actions=[...])`

### Requirements
- [x] Stateless between calls
- [x] No execution
- [x] No planner behaviour beyond stated rules
- [x] No action rewriting
- [x] No fallback inference

---

## Phase 5.5 — Write tests (test-first)
- [x] Create `tests/test_workcell_planner.py`

### Required test coverage (all 10 baseline cases)
- [x] Test 1: Empty state returns empty plan
- [x] Test 2: Single known object → pick then place (correct bin)
- [x] Test 3: Unknown color → default bin routing
- [x] Test 4: Multiple objects → deterministic ascending-id ordering
- [x] Test 5: Ineligible object (`on_conveyor=False`) skipped
- [x] Test 6: Determinism across repeated calls
- [x] Test 7: Planner does not mutate input state
- [x] Test 8: Invalid state raises `PlanningError`
- [x] Test 9: Duplicate object IDs raise `PlanningError`
- [x] Test 10: All emitted actions pass Phase 3 schema validation

### Additional coverage
- [x] Module isolation (pure import test, AST banned-import test)
- [x] Rules: routing table, eligibility predicate, sorting, action builders

---

## Phase 5.6 — Verification
- [x] Run Phase 5 tests — 51 passed in 0.43s
- [x] Confirm no banned imports (AST test passes)
- [x] Confirm planner is stateless and read-only (Tests 6, 7)
- [x] Confirm no executor/agent/safety leakage
- [x] Confirm all 10 acceptance criteria met
