# Prototype 2.1 Action Schema

## Allowed Actions

```text
inspect_workcell()
start_conveyor(speed: float)
stop_conveyor()
wait(seconds: float)
pick_target(object_id: str)
place_in_bin(bin_id: str)
reset_workcell()
```

## JSON Format

Planner output must be a single JSON object:

```json
{
  "actions": [
    {
      "action": "pick_target",
      "parameters": {
        "object_id": "obj_1"
      }
    }
  ]
}
```

## Strict Output Rules

- Top-level object must contain only `actions`.
- `actions` must be a non-empty array when a task is active.
- Each action object must contain only `action` and `parameters`.
- `action` must be one of the allowed action names.
- `parameters` must be an object.
- No extra keys.
- No natural language.
- No markdown.
- No Python code.
- No comments.

## Parameter Rules

### inspect_workcell

```json
{}
```

### start_conveyor

```json
{
  "speed": 0.08
}
```

Rules:

- `speed` is required.
- `speed` must be a number.
- `speed` must be greater than `0`.
- `speed` must be less than or equal to the configured maximum conveyor speed.

### stop_conveyor

```json
{}
```

### wait

```json
{
  "seconds": 1.5
}
```

Rules:

- `seconds` is required.
- `seconds` must be a number.
- `seconds` must be greater than `0`.
- `seconds` must be less than or equal to the configured maximum wait.

### pick_target

```json
{
  "object_id": "obj_1"
}
```

Rules:

- `object_id` is required.
- `object_id` must be a string.
- Referenced object must exist.
- Referenced object must be in the pick zone.
- Conveyor must be stopped.
- Robot must not already be holding an object.

### place_in_bin

```json
{
  "bin_id": "A"
}
```

Rules:

- `bin_id` is required.
- `bin_id` must be a string.
- Referenced bin must exist.
- Robot must be holding an object.

### reset_workcell

```json
{}
```
