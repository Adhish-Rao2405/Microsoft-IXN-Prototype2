# Phase 6 Specification

## Microsoft IXN Prototype 2.1

## Phase 6: Planning Pipeline / Orchestrator

### Status

Approved implementation spec for Phase 6 only.

---

## 1. Purpose

Phase 6 adds a deterministic orchestration layer that coordinates:

```text
WorkcellState
  → Planner
  → Candidate Plan
  → Safety Validation
  → Validated Plan
  → Optional Execution
```

The orchestrator controls flow only. It does not make planning decisions, apply safety rules, execute domain logic internally, or mutate the read model directly.

---

## 2. Architecture

```text
State → Planner → Candidate Plan → Safety → Validated Plan → Executor
```

The pipeline must preserve this separation. Forbidden drift:

```text
State → Orchestrator decides + validates + executes
```

---

## 3. Public Interface

```python
class WorkcellPipeline:
    def __init__(self, planner, safety_validator, executor=None):
        ...

    def run(self, state, execute: bool = False) -> PipelineResult:
        ...
```

Constructor contract:

```python
WorkcellPipeline(
    planner=Planner(),
    safety_validator=WorkcellSafetyValidator(),
    executor=WorkcellExecutor(...) | None,
)
```

If `execute=True` and no executor is present, the pipeline must raise:

```python
PipelineError("Execution requested but no executor was provided")
```

---

## 4. Result Contract

```python
@dataclass(frozen=True)
class PipelineResult:
    candidate_actions: list
    validated_actions: list
    rejected_action: object | None
    rejection_reason: str | None
    executed_actions: list
    status: PipelineStatus
```

```python
class PipelineStatus(Enum):
    EMPTY = "empty"
    VALIDATED = "validated"
    EXECUTED = "executed"
    REJECTED = "rejected"
```

Meaning:

- `candidate_actions`: planner output before safety.
- `validated_actions`: planner actions that passed safety.
- `rejected_action`: first action rejected by safety, if any.
- `rejection_reason`: preserved safety rejection reason.
- `executed_actions`: actions actually sent to the executor.
- `status`: final orchestration outcome.

---

## 5. Mode Behavior

### Validate-only mode

```python
pipeline.run(state, execute=False)
```

Behavior:

- planner runs once
- safety validates planner output in order
- executor is never called
- returns `EMPTY`, `VALIDATED`, or `REJECTED`

### Execute mode

```python
pipeline.run(state, execute=True)
```

Behavior:

- planner runs once
- safety validates the entire candidate plan first
- executor is called only if all actions validate
- returns `EMPTY`, `EXECUTED`, or `REJECTED`

---

## 6. Safety Semantics

### Sequential validation

Actions must be validated in planner order. The pipeline must not sort, batch-reorder, or group actions.

### Stop on first rejection

If safety rejects an action:

- stop immediately
- preserve already validated actions
- store the rejected action
- preserve the safety rejection reason
- do not validate later actions
- do not execute anything

### No partial execution

Baseline Phase 6 forbids partial execution. The pipeline must validate the full plan before sending any action to the executor.

---

## 7. Execution Semantics

Execution order:

1. planner produces a full candidate plan
2. safety validates the full candidate plan
3. executor receives validated actions in the exact same order

The pipeline may call executor entrypoints only through the executor abstraction. It must not recreate execution logic or mutate workcell state directly.

---

## 8. Failure Modes

### Empty plan

If the planner returns zero actions:

```python
PipelineResult(
    candidate_actions=[],
    validated_actions=[],
    rejected_action=None,
    rejection_reason=None,
    executed_actions=[],
    status=PipelineStatus.EMPTY,
)
```

### Planning failure

`PlanningError` propagates unchanged. Planning failures belong to the planner layer.

### Malformed planner output

If the planner returns `None` or an object without `.actions`, raise:

```python
PipelineError("Planner returned invalid plan")
```

### Safety rejection

Safety rejection is represented as `PipelineResult(status=REJECTED)`, not as a pipeline misuse exception.

### Pipeline misuse

Orchestration misuse raises `PipelineError`, for example:

- missing planner
- missing safety validator
- execute mode requested without executor

---

## 9. Non-Goals

The pipeline must not:

- create new actions
- alter planner actions
- infer missing parameters
- silently skip invalid actions
- weaken or override safety decisions
- mutate `WorkcellState`
- inspect simulator internals
- call PyBullet directly
- use LLM logic
- retry failed actions
- repair broken plans
- introduce heuristics
- introduce fallback planning
- decide object priority
- perform optimisation
- perform path planning
- decide bin routing
- handle business/domain policy directly

---

## 10. Dependency Rules

Allowed imports for the orchestration layer:

- `src.planning`
- `src.safety`
- `src.executor`
- standard library support modules

Forbidden imports:

- `pybullet`
- `pybullet_data`
- `random`
- `time`
- `datetime`
- simulation internals that bypass the read model
- legacy LLM planner modules
- `openai`

---

## 11. File Structure

```text
src/orchestration/
    __init__.py
    errors.py
    types.py
    pipeline.py

tests/
    test_workcell_pipeline.py
```

This layer must remain separate from planning, safety, execution, and simulation packages.

---

## 12. Acceptance Criteria

Phase 6 is complete when:

1. `test_workcell_pipeline.py` exists.
2. All Phase 6 tests pass.
3. Phase 3, 4, 5, and 6 regression tests pass together.
4. The pipeline does not import simulator internals.
5. The pipeline does not import the legacy LLM planner.
6. The pipeline does not create or rewrite planner actions.
7. Safety validates the full plan before executor receives any action.
8. The executor never runs after safety rejection.
9. Validate-only mode works without an executor.
10. Execution mode requires an executor.
11. Spec and task docs are present.