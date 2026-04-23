# Prototype 2.1 Tasks

## Build Order

Implement phases in this order:

1. Conveyor simulation
2. Object spawning
3. Workcell state abstraction
4. Executor updates
5. Safety rules
6. Planner prompt update
7. Replanning loop
8. UI updates

Do not modify planner or agent orchestration early. Phase 1 and Phase 2 should be simulation and state work only.
Do not modify web UI files before Phase 7.
Do not modify planner or orchestrator before their listed phases.
Standalone simulation and state components must be unit-testable before live PyBullet integration.

## Phase 1 - Conveyor Simulation

### Task 1.1: Create conveyor simulation

Files:

- `src/simulation/conveyor.py`
- `tests/test_conveyor.py`

Requirements:

- Move registered objects along the X-axis at constant speed.
- Support `start(speed)`.
- Support `stop()`.
- Support `step(dt)`.
- Expose current `running` and `speed` state.
- Do not depend on LLMs or agents.
- Do not modify planner, safety agent, executor agent, narrator agent, or orchestrator.
- Implementation should be standalone and unit-testable before any integration into the live PyBullet scene.

Done when:

- Unit tests prove objects move only while the conveyor is running.

### Task 1.2: Create object spawner

Files:

- `src/simulation/spawner.py`
- `tests/test_spawner.py`

Requirements:

- Spawn red cubes and blue cylinders.
- Spawn at a configurable interval.
- Produce stable object IDs such as `obj_1`.
- Support deterministic seed input.
- Do not integrate with planner or agents yet.
- Implementation should be standalone and unit-testable before any integration into the live PyBullet scene.

Done when:

- Unit tests prove spawn timing, IDs, and deterministic behavior.

### Task 1.3: Create bin definitions

Files:

- `src/simulation/bins.py`
- `tests/test_bins.py`

Requirements:

- Define bin A and bin B positions.
- Track count per bin.
- Provide lookup by `bin_id`.

Done when:

- Unit tests prove known bins resolve and unknown bins fail cleanly.

## Phase 2 - Workcell State

### Task 2.1: Create sorting rules

Files:

- `src/brain/sorting_rules.py`
- `tests/test_sorting_rules.py`

Requirements:

- Map red cube to bin A.
- Map blue cylinder to bin B.
- Return `None` or a clear failure for unsupported object classes.

Done when:

- Unit tests prove baseline mappings.

### Task 2.2: Create workcell state abstraction

Files:

- `src/brain/workcell_state.py`
- `tests/test_workcell_state.py`

Requirements:

- Return JSON-compatible state.
- Include task, conveyor, pick zone, robot, bins, and objects.
- Include each object's `id`, `type`, `color`, `position`, `on_conveyor`, and `target_bin`.
- Do not call an LLM.
- `workcell_state.py` must construct state only and must not mutate simulation state.
- `workcell_state.py` may read from simulation registries or scene adapters but must not own simulation updates.

Done when:

- Unit tests prove state output matches the required shape.

### Task 2.3: Implement pick-zone detection

Files:

- `src/brain/workcell_state.py`
- `tests/test_workcell_state.py`

Requirements:

- Detect when an object is inside the configured pick zone.
- Return `occupied: true` and `object_id` when an eligible object is present.
- Return `occupied: false` and `object_id: null` otherwise.

Done when:

- Unit tests cover inside, outside, and empty pick-zone cases.

## Phase 3 - Executor Updates

### Task 3.1: Extend action schema

Files:

- `src/brain/action_schema.py`
- `tests/test_action_schema.py`

Requirements:

- Add only actions listed in `action-schema.md`.
- Enforce required parameters.
- Reject extra keys.

Done when:

- Schema tests pass for valid and invalid workcell actions.

### Task 3.2: Add conveyor control actions

Files:

- `src/executor/action_executor.py`
- `tests/test_executor.py`

Requirements:

- Implement `inspect_workcell`.
- Implement `start_conveyor`.
- Implement `stop_conveyor`.
- Implement `wait`.
- Keep execution deterministic.

Done when:

- Tests prove each action dispatches to deterministic simulation logic.

### Task 3.3: Add object and bin actions

Files:

- `src/executor/action_executor.py`
- `tests/test_executor.py`

Requirements:

- Implement `pick_target`.
- Implement `place_in_bin`.
- Implement `reset_workcell`.
- Resolve object IDs and bin IDs through workcell state or simulation registries.
- Use a deterministic scripted sequence: stop conveyor -> pick target -> place in bin -> restart conveyor.
- This scripted flow must work via executor calls only, without planner or LLM involvement.

Done when:

- A scripted stop-pick-place-restart flow works without LLM involvement.

## Phase 3 Checkpoint

Do not proceed to Phase 4 until the workcell supports a deterministic end-to-end stop-pick-place-restart cycle without using any LLM, planner, or agent orchestration.

## Phase 4 - Safety Rules

### Task 4.1: Add workcell safety validation

Files:

- `src/agents/safety_agent.py`
- `tests/test_safety_workcell.py`

Requirements:

- Reject unknown actions.
- Reject missing or extra parameters.
- Reject invalid object IDs.
- Reject invalid bin IDs.
- Reject invalid conveyor speed.
- Reject invalid wait duration.
- Reject picking while conveyor is running.
- Reject picking when target is outside the pick zone.
- Reject picking while already holding an object.
- Reject placing while not holding an object.
- Reject starting the conveyor during an active grasp or place sequence if the executor exposes a busy state.

Done when:

- Tests cover every safety requirement in `requirements.md`.

## Phase 5 - Planner Prompt

### Task 5.1: Update planner prompt for workcell actions

Files:

- `src/brain/planner.py`
- `tests/test_planner.py`

Requirements:

- Include allowed actions from `action-schema.md`.
- Require strict JSON only.
- Keep examples short.
- Preserve existing local Foundry behavior.

Done when:

- Planner parsing tests still pass and workcell action examples parse correctly.

## Phase 6 - Replanning

### Task 6.1: Refresh state after each action

Files:

- `src/agents/orchestrator.py`
- `tests/test_replanning.py`

Requirements:

- Refresh workcell state after every executed action.
- Stop executing queued actions when refreshed state invalidates the next action.

Done when:

- Tests prove stale plans do not continue after state drift.

### Task 6.2: Replan after failure

Files:

- `src/agents/orchestrator.py`
- `tests/test_replanning.py`

Requirements:

- Trigger planner again after a rejected or failed action.
- Track replan count for the current task.
- Cap replanning attempts per task to avoid infinite loops.

Done when:

- Tests prove at least one failed step triggers replanning.

## Phase 7 - UI Updates

### Task 7.1: Add workcell state API and WebSocket update

Files:

- `src/web_ui.py`
- `tests/test_web_ui.py`

Requirements:

- Expose latest workcell state to the UI.
- Broadcast workcell state changes over WebSocket.
- Preserve existing health, command, voice, model, and camera behavior.

Done when:

- Backend tests prove workcell state is available without requiring Foundry Local.

### Task 7.2: Add workcell UI panel

Files:

- `src/static/index.html`
- `src/static/style.css`
- `src/static/app.js`

Requirements:

- Display conveyor running or stopped state.
- Display pick-zone object.
- Display robot busy or idle state.
- Display bin counts.
- Display current goal.
- Display last action outcome.
- UI must degrade gracefully if no workcell state has been published yet.

Done when:

- Browser UI reflects workcell state without blocking command execution.

## Phase 8 - Evaluation

### Task 8.1: Add baseline scenarios

Files:

- `tests/test_replanning.py`
- Optional `docs/evaluation-prototype-2.1.md`

Requirements:

- Cover red cube to bin A.
- Cover blue cylinder to bin B.
- Cover invalid pick while conveyor is running.
- Cover missing object reference.
- Cover reset and resume.

Done when:

- Repeatable scenario tests exist for report and demo use.
