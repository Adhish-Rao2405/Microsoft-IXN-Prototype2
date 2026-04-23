# Phase 4 - Safety and Validation Layer

## Phase 4.1 - Create validator module
- [ ] Create `src/safety/workcell_safety.py`
- [ ] Define `ValidationResult`
- [ ] Define `WorkcellSafetyValidator`
- [ ] Keep module pure, deterministic, and read-only

### Requirements
- [ ] No PyBullet imports
- [ ] No planner imports
- [ ] No executor imports unless strictly type-only and safe
- [ ] No hidden globals
- [ ] No state mutation

---

## Phase 4.2 - Implement validation result model
- [ ] Add `is_valid`
- [ ] Add `errors`
- [ ] Add optional human-readable messages
- [ ] Add `to_dict()` if useful

### Requirements
- [ ] JSON-friendly structure only
- [ ] Deterministic ordering of errors/messages
- [ ] No strategy/recommendation fields

---

## Phase 4.3 - Implement validator entrypoint
- [ ] Add `validate_action(state, action)`
- [ ] Dispatch to explicit per-action rule checks
- [ ] Return structured `ValidationResult`

### Requirements
- [ ] No execution
- [ ] No planner behaviour
- [ ] No action rewriting
- [ ] No fallback inference

---

## Phase 4.4 - Add rules for conveyor actions
- [ ] Validate `start_conveyor`
- [ ] Validate `stop_conveyor`
- [ ] Validate `wait`
- [ ] Validate `inspect_workcell`

### Requirements
- [ ] Reject redundant start when already running
- [ ] Reject redundant stop when already stopped
- [ ] Keep `wait` deterministic and simple
- [ ] Keep `inspect_workcell` broadly valid unless schema-invalid

---

## Phase 4.5 - Add rules for manipulation actions
- [ ] Validate `pick_target`
- [ ] Validate `place_in_bin`
- [ ] Validate `reset_workcell`

### Requirements
- [ ] Reject unknown object
- [ ] Reject pick when already holding object
- [ ] Reject place when no object is held
- [ ] Reject unknown bin
- [ ] Keep reset simple and explicit

---

## Phase 4.6 - Add tests
- [ ] Create `tests/test_workcell_safety.py`

### Required test coverage
- [ ] pure import test
- [ ] AST banned-import test
- [ ] validation result structure tests
- [ ] valid/invalid case for every Phase 3 action
- [ ] pick safety tests
- [ ] place safety tests
- [ ] conveyor safety tests
- [ ] validator does not mutate state
- [ ] validator does not mutate actions
- [ ] no hidden intelligence in output

---

## Phase 4.7 - Verification
- [ ] Run Phase 4 tests
- [ ] Confirm no banned imports
- [ ] Confirm validator is read-only
- [ ] Confirm no planner/executor leakage
- [ ] Confirm all acceptance criteria are met
