# Phase 10 Specification — LLM/SLM Planner Adapter Baseline

## 0. Objective

Introduce the first LLM/SLM planner integration point without allowing the
model to control execution. A strict adapter layer converts model JSON
output into the existing internal `Action` schema. The model only proposes
candidate actions.

---

## 1. Architecture boundary

```
WorkcellState
  → ModelPlanner (LLM adapter)
    → build_model_planner_prompt(state)   [deterministic]
    → ModelClient.complete(prompt)        [injected, swappable]
    → parse_model_response_text(text)     [strict parser]
  → Candidate Plan (tuple[Action, ...])
  → Safety Validator                      [unchanged]
  → Validated Plan
  → Executor                              [unchanged]
  → Evaluation Harness                    [unchanged]
  → Experiment Outputs                    [unchanged]
```

The model does not execute actions, bypass safety, bypass schema
validation, modify state, call tools, or output anything other than
candidate JSON.

---

## 2. Threat model — model output is untrusted

The model is treated as an untrusted input source. All model output:

- Must be valid strict JSON (no prose, no markdown, no code).
- Must conform to the exact workcell action schema.
- Is **candidate only** — not validated, not executed.
- Is passed to the existing safety validator before any execution.
- Is silently rejected (empty plan returned) on any schema violation.

No repair, no fuzzy matching, no default parameter filling, no retry.

---

## 3. Accepted JSON response contract

```json
{
  "actions": [
    {
      "action": "<action_name>",
      "parameters": {}
    }
  ]
}
```

Rules:
- Top-level must be an object/dict.
- Exactly one key: `"actions"`. No extra top-level keys.
- `"actions"` must be a list (may be empty).
- Each action item must be a dict.
- Each action item must contain exactly `"action"` and `"parameters"`.
- `"action"` must be a non-empty string in `ALLOWED_WORKCELL_ACTIONS`.
- `"parameters"` key must be explicitly present and must be a dict.
- Required parameters per `WORKCELL_ACTION_SCHEMAS` must be present and correctly typed.
- No extra parameter keys.

---

## 4. Rejection rules

A response is rejected (accepted=False, actions=(), rejection_reason set) if:

- Text contains backtick sequences (markdown fences).
- Text is not valid JSON.
- JSON is not a top-level dict.
- Top-level dict has keys other than `"actions"`.
- `"actions"` key is missing.
- `"actions"` value is not a list.
- Any action item is not a dict.
- Any action item has keys other than `"action"` and `"parameters"`.
- Any action `"action"` value is missing, null, or empty string.
- Any action `"action"` value is not in `ALLOWED_WORKCELL_ACTIONS`.
- `"parameters"` key is absent from any action item.
- Any action `"parameters"` value is not a dict.
- Any action is missing a required parameter.
- Any action has extra parameter keys.
- **Partial acceptance is forbidden** — one invalid action rejects the entire response.

---

## 5. Prompt builder rules

`build_model_planner_prompt(state: WorkcellState) -> str`:

- Deterministic: same state → same prompt always.
- No timestamps, no UUIDs, no random values.
- Includes state snapshot via `state.to_dict()` with `sort_keys=True`.
- Lists all available action names from `ALLOWED_WORKCELL_ACTIONS` (sorted).
- States model proposes candidate actions only.
- States model does not execute.
- States safety validation happens after model output.
- Requires strict JSON output only.
- Does not include markdown fences in prompt.
- Does not request chain-of-thought.
- Does not permit natural-language response.

---

## 6. ModelClient interface

```python
class ModelClient(Protocol):
    def complete(self, prompt: str) -> str: ...
```

Tests use `FakeModelClient`. No HTTP client is implemented in Phase 10.
No Foundry Local runtime is required.

---

## 7. ModelPlanner adapter contract

```python
class ModelPlanner:
    def __init__(self, client: ModelClient) -> None: ...
    def plan(self, state: WorkcellState) -> Plan: ...
    def last_rejection_reason(self) -> str | None: ...
```

- `plan()` calls `client.complete()` exactly once per invocation.
- Returns `Plan` with candidate `Action` objects on valid response.
- Returns empty `Plan([])` on any invalid response.
- Never raises for malformed model output.
- Never retries.
- Never repairs.
- Never validates safety.
- Never executes actions.
- Never mutates state.
- Never writes files.
- Never imports PyBullet, requests, or httpx.

Pipeline compatibility: `ModelPlanner.plan(state)` returns a `Plan` object
compatible with `WorkcellPipeline` (which calls `plan.actions`).

---

## 8. Non-goals for Phase 10

- No live Foundry Local integration.
- No HTTP client implementation.
- No prompt engineering experiments.
- No performance optimisation.
- No model selection or switching.
- No retry logic.
- No smart repair of model output.
- No changes to safety, executor, or pipeline behaviour.
- No changes to deterministic planner.
- No changes to Phase 8/9 evaluation semantics.

---

## 9. Acceptance criteria

All 30 criteria from the Phase 10 spec prompt are satisfied:

1–8. Response parser: exists, validates strict JSON, rejects prose/markdown/malformed/invalid/partial. ✅
9–13. Prompt builder: exists, deterministic, includes state, candidate-only boundary, prohibits non-JSON. ✅
14–21. ModelPlanner: exists, uses injected client, no network, no retry, no repair, returns empty on invalid, no safety, no execution. ✅
22–25. Existing safety/executor/deterministic planner/pipeline unchanged. ✅
26–30. No PyBullet/GUI/LLM runtime required in tests. ✅

---

## 10. Testing surface

| Test file | Tests |
|---|---|
| `tests/test_model_response.py` | 31 |
| `tests/test_model_prompt.py` | 20 |
| `tests/test_model_planner.py` | 20 |
| **Phase 10 total** | **71** |

Full deterministic regression (Phase 1–10): **633 tests passing**.
