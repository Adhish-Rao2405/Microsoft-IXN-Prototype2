# Phase 4 Specification

## Microsoft IXN Prototype 2.1

## Phase 4: Safety and Validation Layer

## Baseline Spec-Driven Development Standard

### Status

Approved implementation spec for Phase 4 only.

### Purpose

Phase 4 introduces a deterministic safety and validation layer that checks whether an explicit action is valid before it is executed against the workcell state.

This layer must not generate actions.
This layer must not modify workcell state.
This layer must not execute actions.

Its job is to answer:

> Is this explicit action allowed right now, given the current workcell state?

This phase sits between:

- Phase 3 action schema / executor
- future planner / LLM phases

It is a gatekeeper, not a planner.

## 1. Scope

### In scope

Phase 4 must implement a validation layer that:

- accepts an explicit action and current workcell state
- checks deterministic safety rules / preconditions
- returns a structured validation result
- can reject invalid or unsafe actions before execution
- remains standalone and unit-testable
- does not mutate state
- does not execute actions
- does not choose alternative actions

### Out of scope

Phase 4 must not implement:

- planner behaviour
- action generation
- action repair
- routing logic
- policy selection
- bin recommendation
- executor logic
- orchestration
- retry strategies
- PyBullet integration
- LLM integration
- UI integration

If the layer starts suggesting what to do next, it is out of scope.

## 2. Design Intent

The Phase 4 layer is a validator, not an actor.

It should answer questions like:

- is `pick_target` valid for this object id?
- is `place_in_bin` valid while holding this object?
- is `start_conveyor` valid if the conveyor is already running?
- is `stop_conveyor` valid if the conveyor is already stopped?

It must not answer questions like:

- what action should happen instead?
- which bin should be used?
- what is the best next move?
- should we auto-correct this plan?

Those belong to later phases.

## 3. Architectural Constraints

### 3.1 Determinism

Validation must be fully deterministic.

Allowed:

- direct checks against current state
- explicit rule evaluation
- structured error reporting

Not allowed:

- wall-clock time
- randomness
- async behaviour
- background checks
- hidden globals
- external service calls

### 3.2 Isolation

The validation layer must be pure domain logic.

Do not import or reference:

- PyBullet
- robot controllers
- planner modules
- agents
- UI
- orchestration
- OpenAI / LLM code

### 3.3 Read-only behaviour

The validator must not mutate any part of:

- workcell state
- bins
- conveyor
- held object state
- action objects

It is a read-only decision-free checker.

### 3.4 No silent repair

The validator must not:

- rewrite actions
- infer missing fields
- fill in defaults based on policy
- choose alternative bins
- choose fallback objects

It may only:

- accept
- reject
- report why

## 4. Required Deliverables

Recommended files:

```text
src/safety/workcell_safety.py
tests/test_workcell_safety.py
specs/001-prototype-2.1/phase4-spec.md
specs/001-prototype-2.1/tasks-phase4.md
```

Code and tests should stay clearly separated from executor and planner code.

## 5. Required Model

Recommended primary objects:

```python
ValidationResult
WorkcellSafetyValidator
```

### Minimum required behaviour

#### `ValidationResult`

Must represent:

- whether action is valid
- one or more machine-readable error codes
- one or more human-readable messages

Recommended fields:

- `is_valid: bool`
- `errors: list[str]`
- optional `messages: list[str]`

It must be JSON-friendly through `to_dict()` if implemented.

#### `WorkcellSafetyValidator`

Must provide deterministic validation of explicit actions against current workcell state.

Recommended API:

```python
class WorkcellSafetyValidator:
    def validate_action(self, state, action) -> ValidationResult: ...
```

Optional:

```python
def validate_plan(self, state, actions) -> list[ValidationResult]: ...
```

Only add plan-level validation if it stays explicit and simple.

## 6. Functional Requirements

### 6.1 Generic validation behaviour

The safety layer must:

- inspect explicit action type
- inspect explicit parameters
- inspect current workcell state
- apply deterministic safety rules
- return structured pass/fail result

The validator must not call the executor.

### 6.2 Required action coverage

Phase 4 must validate all Phase 3 workcell actions:

- `inspect_workcell`
- `start_conveyor`
- `stop_conveyor`
- `wait`
- `pick_target`
- `place_in_bin`
- `reset_workcell`

### 6.3 Required minimum safety rules

#### `inspect_workcell`

Allowed in all normal states unless the schema itself is invalid.

#### `start_conveyor`

Invalid if:

- conveyor is already running

Valid if:

- conveyor exists and is currently stopped

#### `stop_conveyor`

Invalid if:

- conveyor is already stopped

Valid if:

- conveyor exists and is currently running

#### `wait`

Valid as a no-op action provided parameters are schema-valid.
No temporal logic beyond explicit schema checks.

#### `pick_target`

Invalid if:

- no such object exists
- target object is not on conveyor, if your model requires conveyor presence
- executor is already holding another object
- conveyor is running, if your system rule requires stationary picking

Valid if:

- object exists
- no object is currently held
- any required conveyor/pick preconditions are satisfied

#### `place_in_bin`

Invalid if:

- no object is currently held
- target bin does not exist
- held object id does not match the action if explicitly provided
- conveyor state violates the placement precondition, if applicable

Valid if:

- an object is currently held
- target bin exists
- placement preconditions are satisfied

#### `reset_workcell`

Valid unless your model defines an explicit forbidden reset state.
Keep this simple and deterministic.

## 7. Rule Style Requirements

### 7.1 Preconditions only

Phase 4 should focus on preconditions, not predictive planning.

Allowed examples:

- cannot place when not holding
- cannot start already running conveyor
- cannot pick unknown object

Not allowed examples:

- should place in bin A instead
- best recovery action is reset
- wait first, then retry

### 7.2 No policy leakage

Rules must be factual and safety-oriented, not strategic.

Allowed:

- object existence
- holding state
- conveyor running/stopped state
- known bin existence

Not allowed:

- object type to bin mapping
- color-based classification
- sorting rules
- planner policy

### 7.3 Explicit failure reasons

Every invalid action must fail explicitly.

Avoid vague failures like:

- invalid action
- failed

Prefer machine-readable error codes like:

- `object_not_found`
- `already_holding_object`
- `conveyor_already_running`
- `conveyor_already_stopped`
- `bin_not_found`
- `no_object_held`

## 8. Non-Goals

The following are explicitly forbidden in Phase 4.

### 8.1 No action generation

Do not create actions from state.

### 8.2 No action rewriting

Do not mutate incoming action payloads to make them valid.

### 8.3 No action repair

Do not convert invalid actions into safe alternatives.

### 8.4 No plan intelligence

Do not score, rank, optimize, reorder, or suggest plans.

### 8.5 No executor leakage

Do not apply state mutations from validation code.

### 8.6 No planner leakage

Do not choose targets, bins, or recovery strategies.

## 9. Testing Standard

Phase 4 must be test-gated and deterministic.

Required test file:

```text
tests/test_workcell_safety.py
```

Minimum required coverage:

- module isolation
- validation result structure
- action rule tests per action
- pick rules
- place rules
- conveyor rules
- read-only safety
- no hidden intelligence

## 10. Acceptance Criteria

Phase 4 is complete only if all are true:

1. A dedicated safety validator module exists.
2. The validator can validate all Phase 3 workcell actions.
3. The validator returns structured deterministic results.
4. The validator has no banned imports.
5. The validator does not mutate state or actions.
6. The validator does not execute actions.
7. The validator does not suggest alternatives.
8. Invalid actions fail with explicit reasons.
9. All Phase 4 tests pass.
10. The code remains a safety gate, not a planner.

## 11. Definition of Done

Phase 4 is done when:

- the safety validator exists
- tests pass
- invalid actions are rejected cleanly
- valid actions pass cleanly
- no planning or execution behaviour has leaked in
- the layer can safely sit between planner/LLM and executor later

If the validator feels helpful or smart, it is out of scope.

## 12. Guardrails for Codex / VS Code Agent

```text
Implement Phase 4 only: Safety and Validation Layer.

Strict scope:
- Build a deterministic validator for explicit workcell actions against current workcell state
- Return structured validation results
- Add tests in tests/test_workcell_safety.py
- Keep implementation standalone, pure, and unit-testable

Do NOT implement:
- planner logic
- action generation
- action repair
- routing logic
- bin selection logic
- executor logic
- orchestration
- PyBullet integration
- robot behaviour
- LLM or agent logic
- strategy or recommendation fields

Architectural intent:
- This phase is a safety gate, not a planner
- Validator checks explicit preconditions only
- Validator must not mutate state
- Validator must not execute actions
- Validator must not choose alternatives

Constraints:
- Do not modify earlier phases unless there is a blocking bug
- Do not add unnecessary abstractions
- Do not overengineer
- Do not infer future behaviour

Deliverables:
- src/safety/workcell_safety.py
- tests/test_workcell_safety.py

Acceptance target:
- Deterministic validation results
- Explicit pass/fail on all Phase 3 actions
- Explicit failure reasons
- No banned imports
- No planner/executor leakage
```

## 13. tasks.md Style Checklist

See `tasks-phase4.md`.

## 14. Recommended Next-Chat Opener

```text
Continuing Microsoft IXN Prototype 2.1.

Phase 3 is complete and tagged.
Now executing Phase 4 from the Phase 4 spec and tasks.

Implement only:
- src/safety/workcell_safety.py
- tests/test_workcell_safety.py

Strictly follow the phase spec.
Do not modify unrelated files.
Do not add planner logic, action repair, routing, execution, orchestration, or PyBullet logic.
Keep the implementation deterministic, standalone, read-only, and unit-testable.

This phase is a safety gate, not a planner.
```

## 15. Practical Design Guidance

The cleanest shape is:

- `ValidationResult` as a small serialisable value object
- `WorkcellSafetyValidator` as a thin explicit rules class
- one validation method per action type if helpful
- rule checks based only on current state facts

That is enough.

You do not need:

- a policy engine
- a rules DSL
- a recovery framework
- a plan optimizer

Keep it boring.
