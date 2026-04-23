# Phase 5 Specification

## Microsoft IXN Prototype 2.1

## Phase 5: Deterministic Planner

### Status

Approved implementation spec for Phase 5 only.

---

## 1. Purpose

Introduce a deterministic decision-making layer that converts workcell state → action sequence, without executing actions.

This layer defines *what should happen*, not *how it is applied*.

---

## 2. Architectural Position

```
State (Read Model)
      ↓
Planner  ← (Phase 5)
      ↓
Action Schema (validated structure)
      ↓
Safety Layer (rule validation)
      ↓
Executor (state mutation)
```

---

## 3. Core Responsibilities

The planner must:

- Read workcell state (immutable input)
- Apply explicit rule-based logic
- Output a finite ordered list of actions
- Ensure all actions conform to the Phase 3 action schema
- Ensure all outputs are valid candidates for safety validation

---

## 4. Non-Responsibilities (Hard Boundaries)

The planner must NOT:

- Execute actions
- Modify system state
- Access simulation internals (physics, PyBullet)
- Bypass safety layer
- Generate probabilistic or heuristic outputs
- Use LLMs or learned policies
- Maintain hidden internal state between calls

---

## 5. Determinism Requirements

Planner must be a pure function:

- Same input state → same output plan
- No randomness, no time-based variation, no ordering ambiguity

If multiple valid plans exist, selection must follow **fixed priority ordering rules**.

---

## 6. Inputs

Primary input: `WorkcellState` read model (Phase 2).

Planner may only inspect:

- object records (id, color, on_conveyor)
- conveyor read state
- bin read state

Planner must not require hidden inputs beyond what the read model exposes.

---

## 7. Outputs

```python
Plan(actions=[...])
```

Where each action conforms to Phase 3 action schema:

```python
{"action": "pick_target", "parameters": {"object_id": "obj_1"}}
{"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}}
```

Constraints:

- Strictly conforms to Phase 3 Action Schema
- Serialisable
- Fully explicit (no inferred steps)

---

## 8. Planning Model

- Stateless
- Single-pass rule evaluation
- No search trees
- No backtracking
- No optimisation layer

---

## 9. Planning Rules (Baseline)

### Object Eligibility

An object is plannable only if `on_conveyor == True`.

### Bin Routing (table-driven)

```python
BIN_ROUTING = {
    "red": "bin_a",
    "blue": "bin_b",
}
DEFAULT_BIN = "bin_a"
```

Resolution: `target_bin = BIN_ROUTING.get(object.color, DEFAULT_BIN)`

No dynamic routing. No learned routing. No capacity optimisation.

### Object Ordering

```python
sorted(objects, key=lambda o: o.id)   # ascending lexical
```

Fixed and documented. Stable across runs.

### Plan Composition

For each eligible object (in canonical order):

```python
[pick_target(object_id), place_in_bin(bin_id)]
```

Final plan: `concat(subplans in canonical order)`.

---

## 10. Failure Modes

### No objects

```python
Plan(actions=[])   # not an error
```

### Unknown object color

Route to `DEFAULT_BIN`. Not an error.

### Invalid state

```python
raise PlanningError("Invalid state: <reason>")
```

Examples: `state is None`, object missing id, object missing color, duplicate object IDs.

---

## 11. Interface Definition

```python
class Planner:
    def plan(self, state: WorkcellState) -> Plan:
        ...
```

Stateless class. No side effects. No caching.

---

## 12. File Structure

```
src/planning/
    __init__.py
    planner.py     # Planner class, plan() orchestration
    rules.py       # routing table, eligibility, ordering, action builders
    types.py       # Action, Plan value types
    errors.py      # PlanningError

tests/
    test_workcell_planner.py
```

---

## 13. Implementation Notes

### Routing must be table-driven

```python
# Good
BIN_ROUTING.get(object.color, DEFAULT_BIN)

# Bad
if object.color.startswith("r"):
```

### Do not mix validation and planning

Planner may reject malformed input. It must not replicate Phase 4 safety semantics.

### Do not reach into executor

```python
# Bad
from src.executor.workcell_executor import WorkcellExecutor
executor.can_pick(...)
```

---

## 14. Acceptance Criteria

Phase 5 is complete when:

1. Planner produces valid plans for all test states
2. Output is deterministic across repeated runs
3. No coupling exists with executor or simulation
4. Safety layer can validate all outputs without translation
5. All Phase 5 tests pass
6. Module has no banned imports (no PyBullet, no executor, no agents)

---

## 15. Explicit Non-Goals

Do NOT implement:

- path planning
- optimisation
- scheduling
- concurrency
- collision avoidance
- learning systems
- heuristics
- cost functions

---

## 16. Design Philosophy

This planner is intentionally:

- **dumb**
- **predictable**
- **transparent**

It exists to prove architecture separation and enable safe layering.
If it "feels smart", it is incorrect.

---

## 17. Invariants

These must remain true for every successful planning call:

- Planner is side-effect free
- Output action order is deterministic
- Every object appears at most once in planning output
- Every place action corresponds to a preceding pick action for the same object
- No action references nonexistent objects
- No action references invalid bins

---

## 18. Future Extension Points (NOT NOW)

Reserved for later phases:

- heuristic planner
- search-based planner
- LLM planner
- hybrid safety-aware planning
