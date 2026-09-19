---
title: Models & Helpers
description: API reference for domain schemas and UX helper functions.
---

# `heal_my_goap.models`

!!! abstract "At a Glance"
    Domain schemas (`Gap`, `ExecutionResult`, `SynthesizedActionSchema`), UX helpers (`world_state_from_sensors`, `goal`, `action_from_tool`), and operator re-exports (`WorldState`, `Action`, `Goal`, `Planner`).

## Import

```python
from heal_my_goap import (
    Action,
    Goal,
    WorldState,
    Gap,
    ExecutionResult,
    action_from_tool,
    goal,
    world_state_from_sensors,
)
```

---

## Domain Schemas

### `Action`

Re-exported from `goapauto.models.actions.Action`.

```python
Action(
    name: str,
    preconditions: dict[str, Any],
    effects: dict[str, Any],
    cost: float = 1.0,
    description: str = "",
)
```

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | — | Unique action identifier. |
| `preconditions` | `dict[str, Any]` | — | Required state predicates for execution. |
| `effects` | `dict[str, Any]` | — | State changes after execution. |
| `cost` | `float` | `1.0` | Planning cost for A* pathfinding. |
| `description` | `str` | `""` | Human-readable description. |

---

### `WorldState`

Re-exported from `goapauto.models.worldstate.WorldState`. Dictionary-like state container with predicate key-value pairs.

```python
WorldState(
    predicate1: value1,
    predicate2: value2,
    ...
)
```

---

### `Goal`

Re-exported from `goapauto.models.goal.Goal`.

```python
Goal(
    target_state: dict[str, Any],
    priority: int = 1,
    name: str = "Unnamed Goal",
)
```

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `target_state` | `dict[str, Any]` | — | Desired end state predicates. |
| `priority` | `int` | `1` | Goal priority (higher = more important). |
| `name` | `str` | `"Unnamed Goal"` | Human-readable goal name. |

---

### `Gap`

Pydantic model representing an unsatisfied precondition gap.

```python
Gap(
    id: str,                          # UUID4
    missing_predicate: dict[str, Any],
    dependent_action_name: str | None,
    closest_state: dict[str, Any],
)
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Unique identifier (UUID4). |
| `missing_predicate` | `dict[str, Any]` | The exact predicate key-value pairs blocking progress. |
| `dependent_action_name` | `str \| None` | Name of action requiring the missing predicate. |
| `closest_state` | `dict[str, Any]` | State at the frontier node where planning stopped. |

---

### `ExecutionResult`

Result of `GoapEngine.run()`.

```python
ExecutionResult(
    success: bool,
    final_state: WorldState,
    plan: list[Action],
    heal_attempts: int,
    actions_executed: int,
    error: str | None = None,
)
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `success` | `bool` | Whether the goal was achieved. |
| `final_state` | `WorldState` | State after execution (or at failure). |
| `plan` | `list[Action]` | The action sequence that was executed. |
| `heal_attempts` | `int` | Number of self-healing iterations performed. |
| `actions_executed` | `int` | Count of actions successfully executed. |
| `error` | `str \| None` | Error message if `success=False`. |

---

## UX Helpers

### `world_state_from_sensors(sensors: SystemSensors) -> WorldState`

Auto-derives a `WorldState` snapshot from `sensors.read_state()`.

```python
from heal_my_goap import world_state_from_sensors
from heal_my_goap.sensors import SystemSensors

sensors = SystemSensors()
state = world_state_from_sensors(sensors)
```

---

### `goal(target_state: dict[str, Any], priority: int = 1, name: str = "Unnamed Goal") -> Goal`

Concise `Goal` builder with default priority and name.

```python
from heal_my_goap import goal

g = goal(
    target_state={"ram_usage_pct": 30.0, "temp_files_count": 0},
    priority=1,
    name="System Health",
)
```

---

### `action_from_tool(name: str, description: str, parameters: dict[str, Any] | Callable[..., Any], effects: dict[str, Any] | None = None, cost: float = 10.0) -> Action`

Converts a tool callable or dictionary schema into a GOAP `Action`.

```python
from heal_my_goap import action_from_tool


def my_tool(param: str) -> None:
    pass


action = action_from_tool(
    name="my_tool",
    description="Does something",
    parameters=my_tool,
    effects={"done": True},
    cost=5.0,
)
```

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | — | Action name. |
| `description` | `str` | — | Human-readable description. |
| `parameters` | `dict \| Callable` | — | Function or schema dict. |
| `effects` | `dict \| None` | `None` | Explicit effects (overrides inference). |
| `cost` | `float` | `10.0` | Action cost. |

---

## Operator Re-exports

The following are re-exported from `goapauto` for convenience:

- `WorldState` — State container
- `Action` — Action definition
- `Goal` — Goal definition
- `Planner` — A* planner class

---

## Related Pages

- [API Reference: GoapEngine](engine.md)
- [User Guide: Tool Registration](../user-guide/tool-ingestion.md)
- [Getting Started: Core Concepts](../getting-started/concepts.md)
- [Example: Coding Agent](../examples/coding-agent.md)