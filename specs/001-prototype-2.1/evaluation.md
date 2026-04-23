# Prototype 2.1 Evaluation

## Acceptance Criteria

Prototype 2.1 is accepted when all of the following are true:

1. A conveyor belt with moving objects exists in the PyBullet workcell.
2. At least two object classes are sortable into at least two bins.
3. The planner outputs strict JSON actions only.
4. The `SafetyAgent` rejects invalid workcell actions.
5. The executor can stop the conveyor, pick an object, place it in the correct bin, and restart the conveyor.
6. The orchestrator can replan after a failed or rejected step.
7. The UI reflects workcell state in real time.
8. At least one end-to-end sorting command succeeds locally using Foundry Local.
9. Unit or integration tests cover schema, state, and workcell safety behavior.

## Baseline Metrics

Recommended metrics:

- Task success rate
- Sorting accuracy
- Plan validity rate
- Safety rejection count
- Average task completion time
- Missed-pick count
- Replan count per task
- Recovery success rate after failure

## Fixed Scenario Candidates

### Scenario 1: Red Cube Baseline

Goal:

- Sort the next red cube into bin A.

Expected result:

- Conveyor stops while the red cube is in the pick zone.
- Robot picks the red cube.
- Robot places it in bin A.
- Conveyor restarts.

### Scenario 2: Blue Cylinder Baseline

Goal:

- Sort the next blue cylinder into bin B.

Expected result:

- Conveyor stops while the blue cylinder is in the pick zone.
- Robot picks the blue cylinder.
- Robot places it in bin B.
- Conveyor restarts.

### Scenario 3: Invalid Pick While Moving

Goal:

- Attempt to pick an object while the conveyor is running.

Expected result:

- Safety validation rejects `pick_target`.
- Narrator reports the reason.
- Orchestrator refreshes state and replans.

### Scenario 4: Missing Object Reference

Goal:

- Attempt to pick a nonexistent object ID.

Expected result:

- Safety validation rejects the action.
- No executor call manipulates the world.

### Scenario 5: Reset and Resume

Goal:

- Reset the workcell and resume sorting.

Expected result:

- Conveyor, robot, objects, bins, and task state return to a known baseline.
- Sorting can continue from a clean state.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Moving grasping is unstable | Use stop-pick-place-restart before dynamic grasping. |
| Planner outputs overcomplicated plans | Keep schema narrow and prompt with bounded examples. |
| State drift causes invalid actions | Refresh state after each action and before execution when needed. |
| UI work delays backend progress | Defer UI surface work until backend workcell logic is stable. |

## Future Extensions

Not required for the baseline, but enabled by this design:

- Pick while conveyor is moving
- Defect detection
- More object classes
- Priority scheduling
- Multi-bin routing
- Camera-driven scene abstraction
- Real hardware bridge
- Benchmarking across local models
