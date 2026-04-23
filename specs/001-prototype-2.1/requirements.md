# Prototype 2.1 Requirements

## Functional Requirements

FR1: Conveyor must move registered objects along the X-axis at a constant configurable speed.

FR2: Conveyor speed must be bounded by configuration.

FR3: Objects must spawn onto the conveyor at a configurable interval.

FR4: Object spawning must support deterministic seeds for repeatable tests.

FR5: The baseline object classes are red cube and blue cylinder.

FR6: The workcell must define bin A and bin B.

FR7: Red cubes must map to bin A.

FR8: Blue cylinders must map to bin B.

FR9: The workcell must define a pick zone.

FR10: Pick-zone detection must report whether an object is eligible for picking.

FR11: The robot may pick an object only when the conveyor is stopped.

FR12: The robot may pick only one object at a time.

FR13: The robot may place a held object only into a known bin.

FR14: Workcell state must include conveyor state, pick-zone state, robot holding state, bins, objects, and current task.

FR15: Workcell state must be serializable as JSON-compatible Python data.

FR16: The executor must provide deterministic handlers for every approved workcell action.

FR17: The orchestrator must refresh workcell state after each executed action.

FR18: The system must support resetting the workcell to a known baseline state.

FR19: The UI must display conveyor state, pick-zone object, robot state, bin counts, current goal, and last action outcome.

## Constraints

C1: All planned actions must pass `SafetyAgent` validation before execution.

C2: Planner output must be strict JSON matching `action-schema.md`.

C3: Executor logic must be deterministic and must not call an LLM.

C4: Foundry Local is the only allowed LLM runtime.

C5: Existing static pick-and-place functionality must not be broken.

C6: Do not modify `PlannerAgent`, `SafetyAgent`, `ExecutorAgent`, `NarratorAgent`, or `Orchestrator` during Phase 1 or Phase 2 unless explicitly required by the task.

C7: Baseline implementation must use stop-pick-place-restart, not dynamic grasping.

## Safety Requirements

SR1: Reject unknown actions.

SR2: Reject actions with missing required parameters.

SR3: Reject actions with extra keys.

SR4: Reject `start_conveyor` when speed is less than or equal to zero.

SR5: Reject `start_conveyor` when speed exceeds the configured maximum.

SR6: Reject `wait` when seconds is less than or equal to zero.

SR7: Reject `wait` when seconds exceeds the configured maximum wait.

SR8: Reject `pick_target` when `object_id` does not exist.

SR9: Reject `pick_target` when the target object is not in the pick zone.

SR10: Reject `pick_target` when the conveyor is running.

SR11: Reject `pick_target` when the robot is already holding an object.

SR12: Reject `place_in_bin` when `bin_id` does not exist.

SR13: Reject `place_in_bin` when the robot is not holding an object.

SR14: Reject an empty action plan when a task is active.
