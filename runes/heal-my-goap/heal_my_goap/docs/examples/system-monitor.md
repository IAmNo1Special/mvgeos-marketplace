---
title: OS System Monitor
description: Monitor 28+ live OS metrics and automatically heal system health goals.
---

# OS System Monitor Example

Demonstrates `heal-my-goap` using 28+ real-time OS metrics via `SystemSensors` to diagnose and heal system health goals.

!!! abstract "At a Glance"
    **Scenario**: Automatically restore system health (RAM usage, temp files, network connectivity) using live OS metrics.
    **Key Features Used**: `SystemSensors`, `world_state_from_sensors`, `goal`, `GoapEngine`, basic self-healing.

---

## Scenario Setup

Your system is running hot — RAM usage is above 80%, temporary files are accumulating, and network connectivity is flaky. Instead of writing custom monitoring scripts for each metric, you define a health goal and let `heal-my-goap` figure out the rest.

The engine reads live metrics via `SystemSensors`, plans a sequence of actions to reach the target state, and executes them. If any action fails or a precondition isn't met, the self-healing loop kicks in.

---

## Full Code

```python
from heal_my_goap import GoapEngine, goal, world_state_from_sensors
from heal_my_goap.sensors import SystemSensors

# 1. Read live OS metrics snapshot
sensors = SystemSensors()
current_state = world_state_from_sensors(sensors)

# 2. Define health restoration goal
health_goal = goal(
    target_state={
        "ram_usage_pct": 30.0,
        "temp_files_count": 0,
        "network_connected": True,
    },
    priority=1,
    name="Restore System Health",
)

# 3. Run self-healing engine
engine = GoapEngine(
    storage_path=".goap_sysmon.json",
    max_heal_attempts=3,
)

result = engine.run(current_state, health_goal)

print(f"Result: {'SUCCESS' if result.success else 'FAILURE'}")
print(f"Final RAM %: {result.final_state.get('ram_usage_pct')}")
```

---

## Expected Output

```
Result: SUCCESS
Final RAM %: 28.5
```

*Note: Actual output varies based on your system state. The engine may synthesize actions like `clear_temp_files`, `flush_memory_cache`, or `restart_network_interface` to achieve the goal.*

---

## Run Command

```bash
uv run examples/heal_my_goap/system_monitor.py
```

---

## Related Pages

- [API Reference: SystemSensors](../api-reference/sensors.md)
- [API Reference: GoapEngine](../api-reference/engine.md)
- [API Reference: Models & Helpers](../api-reference/models.md)
- [Core Concepts](../getting-started/concepts.md)