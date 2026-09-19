---
title: DeltaObserver
description: API reference for BaseObserver interface and DeltaObserver implementation.
---

# `heal_my_goap.observer`

!!! abstract "At a Glance"
    `BaseObserver` abstract interface and `DeltaObserver` concrete implementation for runtime state delta observation and automated effect learning.

## Import

```python
from heal_my_goap import DeltaObserver, BaseObserver
```

---

## Classes

### `BaseObserver`

Abstract base interface for state delta observers.

```python
class BaseObserver(ABC):
    @abstractmethod
    def compute_delta(
        self,
        before: dict[str, Any] | WorldState,
        after: dict[str, Any] | WorldState,
    ) -> dict[str, Any]:
        """Calculate predicate changes between before and after snapshots."""
        ...

    @abstractmethod
    def merge_effects(
        self,
        existing_effects: dict[str, Any],
        observed_delta: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge observed delta into existing action effects."""
        ...
```

---

### `DeltaObserver`

Runtime state delta observer for automated state formalization.

```python
DeltaObserver(
    ignored_keys: set[str] | None = None,
    numeric_tolerance: float = 0.001,
    merge_strategy: str = "update",
)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ignored_keys` | `set[str] \| None` | `DEFAULT_IGNORED_KEYS` | Volatile predicate keys to skip during comparison. Default: `{"uptime_minutes", "network_bytes_sent", "network_bytes_recv", "cpu_usage_pct", "load_avg_1m", "process_memory_rss"}` |
| `numeric_tolerance` | `float` | `0.001` | Minimum float difference to record a change. |
| `merge_strategy` | `str` | `"update"` | Effect merge policy: `"update"`, `"preserve_existing"`, `"overwrite"`. |

#### Methods

##### `compute_delta(before: dict | WorldState, after: dict | WorldState) -> dict[str, Any]`

Calculates predicate changes between `before` and `after` snapshots.

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `before` | `dict \| WorldState` | State snapshot before action execution. |
| `after` | `dict \| WorldState` | State snapshot after action execution. |

**Returns:** `dict[str, Any]` — Dictionary of changed predicates with new values.

---

##### `merge_effects(existing_effects: dict, observed_delta: dict) -> dict[str, Any]`

Merges observed delta into existing action effects based on `merge_strategy`.

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `existing_effects` | `dict` | Current action effects dictionary. |
| `observed_delta` | `dict` | Newly observed predicate changes. |

**Returns:** `dict[str, Any]` — Merged effects dictionary.

---

## Merge Strategy Behaviors

| Strategy | Behavior |
| :--- | :--- |
| `"update"` | Merges deltas, overwriting existing keys if changed, preserving un-observed keys. |
| `"preserve_existing"` | Keeps existing values for known keys, only adds new predicate keys. |
| `"overwrite"` | Replaces entire effects dict with observed delta. |

---

## Related Pages

- [User Guide: Delta Observer](../user-guide/delta-observer.md)
- [API Reference: GoapEngine](engine.md)
- [API Reference: SystemSensors](sensors.md)
- [Example: Coding Agent](../examples/coding-agent.md)