# Phase 11 — Foundry Local Client Adapter

## Project

Microsoft IXN Prototype 2.1

## Phase Goal

Implement a strict Foundry Local HTTP client adapter for real local model inference.

This phase connects the system to a real OpenAI-compatible Foundry Local endpoint, but it must not increase autonomy, change planning behaviour, bypass safety, or modify executor behaviour.

## Current Architecture

```text
State → Planner / ModelAdapter → Safety → Executor → Evaluation → Export
```

## Target Phase 11 Architecture

```text
State
  → ModelAdapter
  → FoundryLocalClient
  → raw assistant content
  → ModelAdapter parser / validator
  → Safety
  → Executor
  → Evaluation
  → Export
```

## Absolute Scope Boundary

Phase 11 is adapter-only.

Do not modify:

* deterministic planner logic
* safety rules
* executor behaviour
* evaluation metrics
* export format
* simulation logic
* GUI / PyBullet integration

Do not add:

* retries
* autonomous loops
* self-correction
* JSON repair
* fallback planning
* extra intelligence
* action execution from the client
* schema validation inside the client

## System Invariants

These must always remain true:

1. Model output is untrusted.
2. Model output must never bypass schema validation.
3. Model output must never be executed directly.
4. Foundry client failures must fail closed.
5. A failed model call must not mutate system state.
6. The client must not know about safety, executor, PyBullet, GUI, or evaluation.
7. The client must return raw assistant content only.
8. Invalid model output must remain invalid.
9. No retries are permitted in this phase.
10. No hidden fallback logic is permitted.

## Interface Contract

### `FoundryLocalClient`

Suggested file:

```text
src/planning/foundry_client.py
```

Required public method:

```python
complete(system_prompt: str, user_prompt: str) -> str
```

### Inputs

* `system_prompt: str`
* `user_prompt: str`

### Output

* raw assistant content as `str`

### Forbidden Responsibilities

The client must not:

* parse JSON actions
* validate action schema
* repair malformed JSON
* execute actions
* call safety
* call executor
* infer missing fields
* add default actions
* perform retries

## Configuration Contract

Environment variables:

```text
FOUNDRY_LOCAL_BASE_URL
FOUNDY_LOCAL_BASE_URL
FOUNDRY_LOCAL_MODEL
```

Priority:

1. `FOUNDRY_LOCAL_BASE_URL`
2. `FOUNDY_LOCAL_BASE_URL`
3. default `http://127.0.0.1:8000`

Model:

1. `FOUNDRY_LOCAL_MODEL`
2. default `"local-model"`

Endpoint:

```text
/v1/chat/completions
```

Full URL:

```text
{base_url}/v1/chat/completions
```

## Request Contract

The client must send:

```json
{
  "model": "local-model",
  "messages": [
    {
      "role": "system",
      "content": "<system_prompt>"
    },
    {
      "role": "user",
      "content": "<user_prompt>"
    }
  ],
  "temperature": 0,
  "max_completion_tokens": 256
}
```

Use `max_completion_tokens`, not `max_tokens`.

Default timeout:

```text
5 seconds
```

## Response Contract

Expected response shape:

```json
{
  "choices": [
    {
      "message": {
        "content": "<assistant_content>"
      }
    }
  ]
}
```

The client must return only:

```text
assistant_content
```

No parsing.
No schema validation.
No repair.

## Error Contract

Create typed exceptions:

```python
FoundryClientError
FoundryConnectionError
FoundryTimeoutError
FoundryHTTPStatusError
FoundryMalformedResponseError
FoundryEmptyResponseError
```

The client must raise controlled typed errors for:

* connection failure
* timeout
* non-200 HTTP status
* malformed JSON
* missing `choices`
* empty `choices`
* missing `message`
* missing `content`
* empty content

Raw HTTP/library exceptions must not leak upward.

## Implementation Tasks

### Task 11.1 — Inspect Current Adapter Boundary

Before writing implementation code:

* Inspect existing planning/model adapter files.
* Identify where raw model text is expected.
* Identify whether `src/planning/model_client.py` already exists.
* Do not change behaviour during inspection.

Acceptance:

* Current boundary is understood.
* No unrelated code changes.

---

### Task 11.2 — Implement `FoundryLocalClient`

Create:

```text
src/planning/foundry_client.py
```

Implement:

```python
FoundryLocalClient(
    base_url: str | None = None,
    model: str | None = None,
    timeout_seconds: float = 5.0,
    max_completion_tokens: int = 256,
)
```

And:

```python
complete(system_prompt: str, user_prompt: str) -> str
```

Acceptance:

* Resolves base URL correctly.
* Resolves model correctly.
* Builds correct OpenAI-compatible request.
* Sends POST request to `/v1/chat/completions`.
* Returns raw assistant content only.
* Does not import safety, executor, simulation, PyBullet, GUI, evaluation, or export modules.

---

### Task 11.3 — Implement Typed Failure Handling

Add exception classes in the same module unless project structure suggests a better existing location.

Acceptance:

* All network and response failures are converted into typed client errors.
* No raw requests/urllib exceptions leak upward.
* Failures are explicit and testable.

---

### Task 11.4 — Unit Test the Client with Mocked HTTP

Create:

```text
tests/test_foundry_client.py
```

Tests must not require Foundry Local to be running.

Required tests:

1. Uses default base URL when no env var is set.
2. Uses `FOUNDRY_LOCAL_BASE_URL` when present.
3. Uses `FOUNDY_LOCAL_BASE_URL` alias when preferred env var is absent.
4. Preferred env var overrides alias.
5. Uses `FOUNDRY_LOCAL_MODEL` when present.
6. Uses default model otherwise.
7. Sends request to `/v1/chat/completions`.
8. Sends `temperature: 0`.
9. Sends `max_completion_tokens`.
10. Sends system and user messages correctly.
11. Extracts assistant message content correctly.
12. Raises `FoundryTimeoutError` on timeout.
13. Raises `FoundryConnectionError` on connection failure.
14. Raises `FoundryHTTPStatusError` on HTTP 500.
15. Raises `FoundryMalformedResponseError` on invalid JSON.
16. Raises `FoundryMalformedResponseError` when `choices` is missing.
17. Raises `FoundryMalformedResponseError` when `choices` is empty.
18. Raises `FoundryMalformedResponseError` when `message` is missing.
19. Raises `FoundryMalformedResponseError` when `content` is missing.
20. Raises `FoundryEmptyResponseError` when content is empty.
21. Does not parse JSON action content.
22. Does not repair invalid JSON action content.

Acceptance:

* Tests use mocked HTTP only.
* Tests are deterministic.
* Tests do not depend on a live model.

---

### Task 11.5 — Integrate via Dependency Injection Only

If an existing `ModelAdapter` or `model_client.py` abstraction exists, wire `FoundryLocalClient` through dependency injection.

Allowed:

* Add optional client injection.
* Preserve fake/mock clients.
* Preserve deterministic planner tests.
* Preserve existing model adapter parsing and validation path.

Forbidden:

* Do not rewrite planner logic.
* Do not rewrite safety logic.
* Do not rewrite executor logic.
* Do not modify evaluation/export.

Acceptance:

* Existing tests still pass.
* Existing mock/fake client tests still pass.
* Foundry client can be used as a real client without changing downstream safety.

---

### Task 11.6 — Optional Live Integration Smoke Test

Optional file:

```text
tests/test_foundry_integration.py
```

This test must be skipped unless:

```text
RUN_FOUNDRY_INTEGRATION=1
```

Allowed:

* Call local Foundry endpoint.
* Ask for a minimal strict JSON response.
* Assert that a string response is returned.

Forbidden:

* Do not execute returned actions.
* Do not require model correctness.
* Do not make this part of normal test pass.

Acceptance:

* Normal `pytest` does not require Foundry Local.
* Live integration is opt-in only.

---

### Task 11.7 — Full Regression Test Pass

Run:

```bash
python -m pytest -v
```

Acceptance:

* All existing tests pass.
* All new Phase 11 unit tests pass.
* No unrelated tests are modified to force a pass.

---

### Task 11.8 — Drift Audit

Check that Phase 11 did not introduce:

* executor changes
* safety rule changes
* deterministic planner changes
* evaluation changes
* export changes
* PyBullet coupling
* GUI coupling
* retries
* autonomous loops
* fallback intelligence
* JSON repair
* model-output execution bypass

Acceptance:

* Phase remains client-adapter only.

## Phase Acceptance Gates

### Gate 1 — Client Exists

* `FoundryLocalClient` implemented.
* Typed exceptions implemented.
* No integration yet required.

### Gate 2 — Client Unit Tests Pass

* Mocked HTTP tests pass.
* No live server required.

### Gate 3 — Adapter Boundary Preserved

* Existing model adapter path still treats model output as untrusted.
* Existing validation still owns schema enforcement.

### Gate 4 — Full Regression Pass

* Existing phase tests pass.
* New Phase 11 tests pass.

### Gate 5 — Drift Audit Pass

* No scope violations.
* No autonomy increase.

### Gate 6 — Optional Live Smoke Test

* Only runs when explicitly enabled.
* Non-blocking for normal development.

## Definition of Done

Phase 11 is complete only when:

1. `FoundryLocalClient` exists.
2. The client calls an OpenAI-compatible Foundry Local endpoint.
3. The client returns raw assistant content only.
4. The client fails closed on network and malformed-response errors.
5. Typed exceptions are implemented and tested.
6. Unit tests mock all HTTP behaviour.
7. The existing model adapter boundary is preserved.
8. Existing deterministic planner behaviour is unchanged.
9. Existing safety and executor behaviour is unchanged.
10. Full regression tests pass.
11. Optional live integration test is skipped by default.
12. No autonomy upgrade has been introduced.

## Suggested Git Commands

After tests pass:

```bash
git status
git add src/planning/foundry_client.py tests/test_foundry_client.py
git add tests/test_foundry_integration.py
git commit -m "Phase 11: add Foundry Local client adapter"
git tag phase-11-foundry-client
git push origin main --tags
```

Only add files that actually exist.
