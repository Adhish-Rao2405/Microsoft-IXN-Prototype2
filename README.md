# Robot Arm Simulator with Foundry Local LLM Brain (Prototype 2.1)

A research-grade robotic simulation system that enables safe, structured, and deterministic control of a robot arm using a local LLM (Foundry Local).

This project extends an initial prototype into a fully evaluated, safety-constrained LLM control pipeline with testing, adversarial evaluation, and reproducible evidence generation.

---

## Key Features

- Local LLM control (Foundry Local) with no cloud APIs
- Strict JSON action schema to eliminate hallucinated commands
- Safety validation layer enforcing hard physical constraints
- Deterministic execution pipeline
- Evaluation harness for batch testing and metrics
- Adversarial testing for malformed or unsafe model outputs
- Evidence pack generation for reproducible outputs
- PyBullet simulation for real-time robotic control

---

## System Architecture (Prototype 2.1)

```text
User Input (Text / Voice)
   ↓
Planner (LLM / deterministic fallback)
   ↓
Structured Action Schema (JSON)
   ↓
Safety Validator (hard constraints)
   ↓
Executor (isolated control layer)
   ↓
Simulation (PyBullet)

+ Evaluation Harness
+ Adversarial Testing Layer
+ Evidence Pack Logging
```

---

## Evolution From Prototype 1

| Component | Prototype 1 | Prototype 2.1 |
|---|---|---|
| LLM Control | Direct | Structured and validated |
| Safety | Basic checks | Strict enforcement layer |
| Determinism | None | Deterministic core |
| Testing | Minimal | 700+ tests |
| Evaluation | None | Full experiment harness |
| Robustness | Low | Adversarial testing |
| Outputs | Manual | Evidence pack generation |

---

## Why Prototype 2.1 Matters

Prototype 1 proved feasibility, but it was not sufficient for reliability claims.
Prototype 2.1 addresses those limits with explicit safety constraints, deterministic behavior, and a reproducible evaluation workflow.

Research framing:

> Local LLMs can support robotic control only when combined with structured outputs, hard safety validation, and deterministic execution pipelines.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Foundry Local

```bash
foundry service start
```

### 3. Run the app

```powershell
$env:FOUNDRY_LOCAL_BASE_URL="http://127.0.0.1:61810"
$env:FOUNDRY_LOCAL_MODEL="Phi-3-mini-4k-instruct-generic-cpu:3"
python -m src.app
```

The selected model alias is config-driven and resolved in this order:

1. `FOUNDRY_LOCAL_MODEL`
2. `FOUNDRY_MODEL`
3. default in `Config.foundry_model_alias`

---

## Example Commands

```text
describe the scene
move to x 0.5 y 0.1 z 0.4
pick up the cube
place the cube at x 0.3 y 0.2 z 0.35
reset
```

---

## Evaluation and Experiments

The project includes:

- Deterministic and model planner evaluation runs
- Batch experiment execution with aggregate metrics
- Adversarial fail-closed evaluation
- Dissertation evidence pack generation

Outputs are saved as structured JSON/CSV/Markdown artifacts for reproducibility.

---

## Technologies

- Python
- PyBullet
- Foundry Local
- FastAPI
- JSON schema-style action validation
- pytest-based test-driven development

---

## Future Work

- Hardware robot integration
- Multi-agent planning strategies
- Vision-language grounding
- Formal real-time safety guarantees

---

## License

MIT License
