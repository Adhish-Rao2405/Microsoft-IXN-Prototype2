```
Microsoft IXN Prototype 2.1
Phase 7 Baseline Spec
End-to-End Deterministic Workcell Scenario Tests
```

You are implementing Phase 7 using strict spec-driven development.

DO NOT start by coding.
Start by inspecting the existing interfaces and tests.

---

## 0. CURRENT STATUS

Completed and test-gated:
- Phase 1: simulation primitives
- Phase 2: deterministic workcell read model
- Phase 3: action schema + executor
- Phase 4: safety / validation layer
- Phase 5: deterministic planner
- Phase 6: planning pipeline / orchestrator

Current verified regression:
- Phase 3–6 regression: 191 tests passing

Current intended architecture:

```
State
  → Planner
  → Candidate Plan
  → Safety Validation
  → Validated Plan
  → Executor
```

Phase 7 must NOT change this architecture.

---

## 1. PHASE 7 PURPOSE

Phase 7 is an integration verification phase.

Its job is to prove the complete deterministic stack works end-to-end under realistic but still headless workcell scenarios.

It should answer:

> "Given a valid workcell state, can the system plan, validate, and execute the correct sequence deterministically without bypassing safety or coupling to PyBullet/LLMs?"

Phase 7 is NOT a feature-expansion phase.

---

## 2. ABSOLUTE NON-GOALS

Do NOT add:
- LLM planning
- legacy brain planner integration
- PyBullet
- GUI
- physics simulation
- robot motion/path planning
- collision avoidance
- retries
- fallback planning
- recovery logic
- optimisation
- heuristics
- new action types
- new routing logic
- new safety rules
- new executor semantics
- hidden policy abstractions
- orchestration decision-making

Do NOT modify previous phases unless a real blocking integration bug is proven by a failing test.

If a test can be written using existing public interfaces, do that instead of modifying production code.

---

## 3. HIGH-LEVEL PHASE 7 DELIVERABLES

Create only these files unless a blocking bug requires otherwise:

1. `tests/test_workcell_e2e_scenarios.py`
2. `specs/001-prototype-2.1/phase7-spec.md`
3. `specs/001-prototype-2.1/tasks-phase7.md`

Prefer no production code changes.

If production changes are needed:
- explain the exact failing test
- keep the change minimal
- do not change public behavior from Phases 3–6 unless the existing behavior is objectively broken

---

## 4. FIRST STEP: INTERFACE INSPECTION

Before writing tests, read these files:

- `src/simulation/workcell_state.py`
- `src/planning/planner.py`
- `src/planning/types.py`
- `src/planning/rules.py`
- `src/safety/workcell_safety.py`
- `src/orchestration/pipeline.py`
- `src/orchestration/types.py`
- `src/executor/workcell_executor.py`
- `src/brain/action_schema.py`
- `tests/test_workcell_planner.py`
- `tests/test_workcell_safety.py`
- `tests/test_workcell_executor.py`
- `tests/test_workcell_pipeline.py`

After reading, write down locally:

1. How to construct a valid WorkcellState.
2. How objects are represented.
3. How processed/removed/sorted objects are represented.
4. What fields planner actions use.
5. Whether planner actions are dataclasses or dicts.
6. How safety is called.
7. How safety reports pass/fail.
8. How executor is called.
9. Whether executor mutates a backing state or simply returns a result.
10. How pipeline adapts planner actions to safety/executor.

Do not assume names. Use the existing names.

Known from Phase 6:
- planner emits Action dataclasses
- safety validates action dicts via `validate_action(state, action)`
- executor executes via `execute(action_name, parameters)`
- pipeline preserves planner Action objects in result and adapts only at safety/executor boundary

Confirm this against actual code before proceeding.

---

## 5. PHASE 7 TEST DESIGN PRINCIPLE

Phase 7 tests must be integration tests, not unit tests disguised as integration tests.

Use real components where practical:
- real Planner
- real WorkcellPipeline
- real safety validator / safety function
- real executor where feasible

However:
- do not require PyBullet
- do not require GUI
- do not require external services
- do not require timing or randomness

If the real executor is hard to observe, use a small recording/fake executor for order assertions, but keep at least one test using the real executor if possible.

Do not mock planner and safety for every test. That would duplicate Phase 6. Phase 7 must prove cross-layer compatibility.

---

## 6. FIXTURE STRATEGY

Create fixture helpers inside `tests/test_workcell_e2e_scenarios.py`.

Do not create production fixtures unless necessary.

Recommended helpers:

1. `make_empty_state()` — returns a valid WorkcellState with no objects; includes valid bin definitions if required by safety
2. `make_state_with_objects(objects)` — accepts simple object definitions; returns valid WorkcellState using the real project object/state types
3. `make_stack(executor=None)` — creates Planner(), real safety validator or wrapper, WorkcellPipeline(...), optional executor
4. `action_names(result)` — returns action names/types from candidate or executed actions
5. `action_object_ids(actions)` — extracts object_id values consistently
6. `place_targets(actions)` — extracts target_bin values consistently

Use these helpers to avoid copying schema details across tests.

---

## 7. REQUIRED SCENARIO TESTS

Implement these tests incrementally. After each small group, run the focused test file.

### TEST 1 — Empty Workcell E2E

**Purpose:** Prove empty valid state produces no work and no execution.

Given:
- valid WorkcellState, no plannable objects
- real planner, real pipeline
- executor supplied or recording executor

When: `pipeline.run(state, execute=True)`

Expect:
- `result.status == EMPTY`
- `result.candidate_actions == []`
- `result.validated_actions == []`
- `result.executed_actions == []`
- executor was not called

### TEST 2 — Single Known Object Full Flow

**Purpose:** Prove one normal object travels through planner → safety → executor.

Given:
- one eligible known object (e.g. red if Phase 5 routing uses red)
- real planner, real safety, pipeline
- recording executor or real executor if observable

When: `pipeline.run(state, execute=True)`

Expect:
- `result.status == EXECUTED`
- candidate actions: exactly pick then place
- safety validated both actions
- executor executed both actions in the same order
- no extra actions exist
- place target is the expected bin from Phase 5 routing

> Do not hardcode bin names until you inspect the actual Phase 5 routing table.

### TEST 3 — Multiple Objects Deterministic Order

**Purpose:** Prove Phase 5 canonical ordering is preserved through Phase 6 and execution.

Given:
- multiple eligible objects in deliberately unsorted input order (e.g. obj_9, obj_2, obj_5)

Expect:
- candidate actions grouped by object in canonical planner order
- for each object: pick occurs before place
- validated order == candidate order
- executed order == validated order
- pipeline does not reorder anything

> Do not invent new ordering rules. Use the ordering rule already implemented in Phase 5.

### TEST 4 — Unknown Type Routes to Default Bin E2E

**Purpose:** Prove default/reject bin routing survives the full stack.

Given:
- one eligible object with an unknown type
- valid default/reject bin exists in state/safety context

Expect:
- planner emits pick/place
- place action targets `DEFAULT_BIN` from Phase 5 rules
- safety accepts if the bin exists
- executor receives the place action with that default target
- `status == EXECUTED`

> Do not change routing if this fails. First inspect whether the state fixture includes the default bin expected by safety.

### TEST 5 — Processed Object Is Skipped E2E

**Purpose:** Prove planner eligibility filtering works through full pipeline.

Given:
- one processed/non-plannable object, one eligible object

Expect:
- no candidate/validated/executed action references processed object
- only eligible object appears
- `status == EXECUTED` if eligible object exists

> Use the actual processed/removed/completed field from the WorkcellState object model.

### TEST 6 — Safety Rejection Prevents Execution

**Purpose:** Prove unsafe candidate actions are blocked before executor runs.

Given:
- realistic candidate plan where one action fails safety, or controlled safety wrapper that rejects one action

Expect:
- `result.status == REJECTED`
- `result.rejected_action` is the failing action
- `result.rejection_reason` is preserved
- `result.executed_actions == []`
- executor call count == 0

> This can use a controlled safety wrapper because the purpose is to prove pipeline end-to-end safety gating. But prefer real planner + controlled safety.

### TEST 7 — Full Plan Validation Before Execution

**Purpose:** Prove the system does not validate and execute action-by-action.

Given:
- planner produces A1, A2, A3
- safety accepts A1 and A2
- safety rejects A3
- `execute=True`

Expect:
- A1 and A2 may appear in `result.validated_actions`
- A3 appears as `rejected_action`
- executor receives no actions at all
- `status == REJECTED`

> **This test is critical.** It proves there is no partial execution.

### TEST 8 — Determinism Across Repeated Runs

**Purpose:** Prove repeated equivalent scenarios give identical results.

Given:
- fixture factory creating the same valid state each time
- same planner/safety/pipeline setup

Expect:
- same status, candidate actions, validated actions, executed actions on every run
- no random/time dependence

> Do not reuse a mutated state. Use fresh fixtures.

### TEST 9 — No Legacy LLM Coupling

**Purpose:** Prove deterministic E2E stack does not depend on old LLM planner.

Forbidden references:
- legacy planner module if present
- LLM brain planner
- OpenAI/Foundry client paths
- prompt/planner agent modules

Acceptable approaches: inspect `src/orchestration/pipeline.py` imports; assert forbidden names are absent.

### TEST 10 — No PyBullet Coupling

**Purpose:** Prove Phase 7 E2E tests remain headless and deterministic.

Expect:
- no pybullet imports in new Phase 7 E2E test path
- focused E2E suite runs headlessly

> Do not change existing legacy PyBullet code if it exists elsewhere. This test only protects the deterministic Prototype 2.1 path.

---

## 8. INCREMENTAL IMPLEMENTATION PLAN

Follow this exact sequence.

| Step | Action |
|---|---|
| 1 | Inspect interfaces — read all files in Section 4 |
| 2 | Create empty test file with imports only; run suite, expect no import errors |
| 3 | Add fixture helpers; run suite |
| 4 | Add Tests 1–2; run focused suite |
| 5 | Add Tests 3–5; run focused suite |
| 6 | Add Tests 6–7; run focused suite |
| 7 | Add Tests 8–10; run focused suite |
| 8 | Add spec and task docs |
| 9 | Run full Phase 3–7 regression |
| 10 | Update `tasks-phase7.md` with final result |

---

## 9. PASS/FAIL DECISION RULES

If a Phase 7 test fails:

1. First check the test fixture.
2. Then check whether the test assumption matches real interfaces.
3. Then check whether Phase 6 pipeline is being used correctly.
4. Only then consider production code.

Do NOT fix by:
- weakening tests
- skipping safety
- bypassing executor
- changing planner routing
- adding special-case logic to pipeline
- adding direct mutation in tests

If the failure is due to a fixture missing bins/state fields: fix the fixture.
If the failure is due to safety rejecting an actually invalid action: fix the state setup or expected behavior.
If the failure reveals a true integration mismatch: make the smallest possible production change and rerun Phase 3–7 regression.

---

## 10. WHAT PHASE 7 IS ALLOWED TO ASSERT

Phase 7 may assert:
- action names/types
- action order
- object IDs referenced
- target bin IDs
- pipeline status
- validated action count
- executed action count
- rejection reason
- executor call order
- absence of forbidden imports

Phase 7 should NOT assert:
- internal private helper implementation
- exact source-code formatting
- unnecessary dataclass internals
- hidden implementation details
- performance/timing

---

## 11. EXPECTED FINAL FILES

**Created:**
- `tests/test_workcell_e2e_scenarios.py`
- `specs/001-prototype-2.1/phase7-spec.md`
- `specs/001-prototype-2.1/tasks-phase7.md`

**Unchanged unless blocking bug:**
- `src/planning/*`
- `src/safety/*`
- `src/orchestration/*`
- `src/executor/*`
- `src/simulation/*`

---

## 12. FINAL ACCEPTANCE CRITERIA

Phase 7 is complete only if:

- Focused Phase 7 tests pass.
- Full Phase 3–7 regression passes.
- No previous phase tests regress.
- No LLM coupling is introduced.
- No PyBullet coupling is introduced.
- No production behavior is broadened unnecessarily.
- No new planner/safety/executor responsibilities are added to the pipeline.
- Phase 7 spec docs are created.
- Phase 7 tasks doc records final verification.

---

## 13. FINAL RESPONSE FORMAT

When done, report:

1. Files created
2. Number of Phase 7 tests passed
3. Full regression result
4. Whether production code changed
5. Any boundary issues found
6. Recommended next phase

Do not claim completion without test output.
Do not proceed to Phase 8.
