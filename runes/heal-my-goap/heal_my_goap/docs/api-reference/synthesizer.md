---
title: Synthesizer & GapAnalyzer
description: API reference for LLMSynthesizer, GapAnalyzer, and SandboxExecutor.
---

# `heal_my_goap.synthesizer`

!!! abstract "At a Glance"
    LLM self-healing synthesis (`LLMSynthesizer`), diagnostic gap isolation (`GapAnalyzer`), and subprocess code sandbox (`SandboxExecutor`) for safe dynamic action execution.

## Import

```python
from heal_my_goap import LLMSynthesizer, GapAnalyzer, SandboxExecutor
```

---

## `LLMSynthesizer`

OpenRouter-backed LLM synthesizer for bridge action generation.

### Constructor

```python
LLMSynthesizer(
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = "https://openrouter.ai/api/v1",
) -> None
```

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `api_key` | `str \| None` | `None` | OpenRouter API key (reads `OPENROUTER_API_KEY` env var if omitted). |
| `model` | `str \| None` | `None` | Model identifier (reads `OPENROUTER_MODEL` env var if omitted). |
| `base_url` | `str` | `"https://openrouter.ai/api/v1"` | OpenRouter API base URL. |

### Methods

#### `synthesize_bridge_action(gap: Gap, available_actions: list[Action], failed_attempts: list[Action] | None = None) -> Action`

Synthesizes a structured GOAP `Action` to satisfy `gap.missing_predicate`.

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `gap` | `Gap` | The isolated gap with missing predicate. |
| `available_actions` | `list[Action]` | Current action registry for context. |
| `failed_attempts` | `list[Action] \| None` | Previously failed synthesis attempts (retry memory). |

**Returns:** `Action` — Synthesized bridge action. Falls back to wildcard action if no API key or retries exhausted.

---

## `GapAnalyzer`

Diagnostic gap isolation for missing predicates.

### Constructor

```python
GapAnalyzer() -> None
```

### Methods

#### `analyze_gap(initial_state: WorldState, goal: Goal, actions: list[Action]) -> Gap`

Traverses goal graph backwards to find the nearest unsatisfied precondition predicate blocking plan generation.

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `initial_state` | `WorldState` | Starting state for planning. |
| `goal` | `Goal` | Target goal state. |
| `actions` | `list[Action]` | Available action registry. |

**Returns:** `Gap` — Isolated gap with `missing_predicate`, `dependent_action_name`, and `closest_state`.

---

## `SandboxExecutor`

Subprocess code sandbox with AST safety checks.

### Constructor

```python
SandboxExecutor(
    timeout: float = 5.0,
    allowed_imports: set[str] | None = None,
) -> None
```

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `timeout` | `float` | `5.0` | Hard execution timeout in seconds. |
| `allowed_imports` | `set[str] \| None` | `None` | Whitelisted import modules (None = use defaults). |

### Methods

#### `execute(code: str, context: dict[str, Any] | None = None) -> Any`

Executes Python code in an isolated subprocess with safety checks.

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `code` | `str` | Python code string to execute. |
| `context` | `dict \| None` | Variable context available to the code. |

**Returns:** `Any` — Return value of the executed code.

**Safety Guarantees:**
- **Subprocess Isolation**: Runs in separate process with `process.terminate()` on timeout.
- **AST Import Checking**: Blocks unsafe modules (`sys`, `os.system`, `subprocess`, `shutil`, `builtins.__import__`).
- **Hard Timeout**: Kills runaway loops after `timeout` seconds.

---

## Related Pages

- [User Guide: Self-Healing](../user-guide/self-healing.md)
- [API Reference: GoapEngine](engine.md)
- [API Reference: Models & Helpers](models.md)
- [Example: Hospital Medic Robot](../examples/hospital-emergency.md)