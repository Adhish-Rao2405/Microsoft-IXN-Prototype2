# Microsoft IXN Prototype 2.1

## Overview

Prototype 2.1 extends Microsoft-IXN-Prototype2 into a dynamic conveyor sorting workcell.

The system:

- Uses the existing local multi-agent architecture: planner, safety validator, executor, and narrator.
- Operates on a structured workcell state.
- Executes only validated structured actions.
- Simulates moving objects on a conveyor in PyBullet.
- Sorts supported object classes into configured bins.
- Runs locally with Foundry Local and local Python runtime only.

## Goal

Build a local, safety-constrained, multi-agent robotic workcell that can sort conveyor objects with deterministic execution and inspectable agent decisions.

## Baseline Behavior

The baseline sorting loop is:

1. Object moves along the conveyor.
2. Workcell state reports object position and pick-zone occupancy.
3. Planner proposes a structured action plan.
4. Safety validates the plan before execution.
5. Executor stops the conveyor, picks the target, places it in the target bin, and restarts the conveyor.
6. Orchestrator refreshes state before continuing.

## Build Constraints

- Do not replace the existing agent architecture.
- Do not add cloud LLM services.
- Do not let LLM output directly manipulate simulation state.
- Do not attempt moving-object grasping in the baseline.
- Implement one phase at a time.
