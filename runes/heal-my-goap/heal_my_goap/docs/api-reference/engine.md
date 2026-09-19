---
title: GoapEngine
description: API reference for GoapEngine — orchestrator for planning, execution, observation, and self-healing.
---

# `heal_my_goap.engine`

!!! abstract "At a Glance"
    `GoapEngine` is the main orchestrator class that combines zero-token A* planning, runtime state delta observation, state rollback, tool ingestion, and LLM self-healing into a single `run()` call.

## Import

```python
from heal_my_goap import GoapEngine
```

---

## `GoapEngine`

The `GoapEngine` orchestrates zero-token A* planning, runtime state delta observation, state rollback, tool ingestion, and LLM self-healing.

### Constructor

```python
GoapEngine(
    initial_actions: list[Action] | None = None,
    storage: BaseActionStorage | str | None = None,
    synthesizer: BaseSynthesizer | None = None,
    gap_analyzer: BaseGapAnalyzer | None = None,
    sandbox: BaseSandboxExecutor | None = None,
    observer: BaseObserver | None = None,
    state_refresh_callback: Callable[[], WorldState | dict[str, Any]] | None = None,
    max_heal_attempts: int = 3,
    storage_path: str | None = None,
    tools: list[Any] | None = None,
) -> None
```

| Parameter | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `initial_actions` | `list[Action] \| None` | `None` | No | List of baseline GOAP `Action` objects. |
| `storage` | `BaseActionStorage \| str \| None` | `None` | No | Action persistence handler or storage file path (defaults to `.goap_actions.json`). |
| `synthesizer` | `BaseSynthesizer \| None` | `None` | No | LLM synthesis engine instance (defaults to `LLMSynthesizer`). |
| `gap_analyzer` | `BaseGapAnalyzer \| None` | `None` | No | Diagnostic gap isolator instance (defaults to `GapAnalyzer`). |
| `sandbox` | `BaseSandboxExecutor \| None` | `None` | No | Code execution sandbox (defaults to `SandboxExecutor`). |
| `observer` | `BaseObserver \| None` | `None` | No | Runtime state delta observer (defaults to `DeltaObserver`). |
| `state_refresh_callback` | `Callable[[], WorldState \| dict] \| None` | `None` | No | Optional callable returning current live environment state. |
| `max_heal_attempts` | `int` | `3` | No | Maximum allowed self-healing retry iterations. |
| `storage_path` | `str \| None` | `None` | No | Shortcut for file-based storage path. |
| `tools` | `list[Any] \| None` | `None` | No | Optional list of callables or tool spec dicts auto-converted via `action_from_tool`. |

### Methods

#### `run(initial_state: WorldState, goal: Goal) -> ExecutionResult`

Executes planning, action execution, delta observation, and self-healing loops to reach the target `Goal`.

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `initial_state` | `WorldState` | Starting world state for planning. |
| `goal` | `Goal` | Target goal with desired end state. |

**Returns:** `ExecutionResult` — Contains `success` (bool), `final_state` (WorldState), `plan` (list[Action]), `heal_attempts` (int), `actions_executed` (int).

---

#### `register_tool(tool: Any, description: str | None = None, effects: dict[str, Any] | None = None, cost: float = 10.0) -> Action`

Converts a Python callable or tool schema dict into an `Action` and registers it with the engine.

**Parameters:**

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `tool` | `Any` | — | Callable function or tool schema dict. |
| `description` | `str \| None` | `None` | Tool description (extracted from docstring if omitted). |
| `effects` | `dict[str, Any] \| None` | `None` | Explicit effects dict (overrides inference). |
| `cost` | `float` | `10.0` | Action cost for A* planning. |

**Returns:** `Action` — The registered action.

---

#### `register_tools(tools: list[Any]) -> list[Action]`

Batch registers a list of tool callables or schemas.

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `tools` | `list[Any]` | List of callables or tool schema dicts. |

**Returns:** `list[Action]` — List of registered actions.

---

## Related Pages

- [User Guide: Tool Registration](../user-guide/tool-ingestion.md)
- [User Guide: Self-Healing](../user-guide/self-healing.md)
- [API Reference: Models & Helpers](models.md)
- [API Reference: Synthesizer & GapAnalyzer](synthesizer.md)
- [Example: Coding Agent](../examples/coding-agent.md)