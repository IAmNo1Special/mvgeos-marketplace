"""System Monitor with heal-my-goap self-healing.

This scenario demonstrates the full heal-my-goap pipeline using
real OS-level sensors with ergonomic helpers:
- Zero-token symbolic GOAP planning via goapauto
- Gap isolation when plans are incomplete
- LLM-powered synthesis of novel maintenance actions
- Sandbox execution of synthesized bridge actions

The system monitor reads live metrics (RAM, CPU, disk, CWD,
temp files, processes, uptime, network, battery, CPU temp,
swap, network I/O, CPU count/freq, disk I/O, logged-in users,
load average, available memory) and plans maintenance actions
to restore system health. With no predefined baseline actions,
the engine must synthesize all bridge actions from scratch via
the self-healing pipeline.

Demonstrates goapauto 0.3.0+ features:
- Positional args for Set/Increment/Decrement effects
- JSON-serializable Predicate and Effect operators (GreaterThan, Set, etc.)
- WorldState.update_state properly applies effects
- world_state_from_sensors() for auto-deriving WorldState
- goal() for concise goal definition
"""

import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).parent.parent.parent))

from heal_my_goap import (
    Action,
    GoapEngine,
    WorldState,
    goal,
    world_state_from_sensors,
)
from heal_my_goap.sensors import SystemSensors


def main() -> None:
    """Run the system monitor self-healing demonstration.

    Reads live system metrics via ``SystemSensors``, constructs
    a ``WorldState`` using ``world_state_from_sensors()``, and
    runs the GOAP engine against health goals defined with
    ``goal()``. With no predefined baseline actions, every required
    action must be synthesized from scratch through the
    self-healing pipeline.
    """
    print("\n" + "=" * 70)
    print("SYSTEM MONITOR - HEALMYGOAP SCENARIO")
    print("=" * 70)

    sensors = SystemSensors()
    current_state = world_state_from_sensors(sensors)

    baseline_actions: list[Action] = []

    goals_and_states: list[tuple[str, WorldState, Any]] = [
        (
            "Healthy System (all metrics nominal)",
            current_state,
            goal(
                target_state={
                    "ram_usage_pct": 30.0,
                    "cpu_usage_pct": 20.0,
                    "disk_usage_pct": 40.0,
                    "temp_files_count": 0,
                    "network_connected": True,
                    "battery_pct": 80.0,
                },
                priority=1,
                name="Restore System Health",
            ),
        ),
        (
            "High RAM with no close action (self-heal trigger)",
            WorldState(
                **{
                    **current_state.to_dict(),
                    "ram_usage_pct": 95.0,
                    "temp_files_count": 10,
                }
            ),
            goal(
                target_state={
                    "ram_usage_pct": 30.0,
                    "temp_files_count": 0,
                },
                priority=1,
                name="Fix High RAM",
            ),
        ),
        (
            "No network with no refresh action (self-heal trigger)",
            WorldState(
                **{
                    **current_state.to_dict(),
                    "ram_usage_pct": 40.0,
                    "temp_files_count": 0,
                    "network_connected": False,
                }
            ),
            goal(
                target_state={"network_connected": True},
                priority=2,
                name="Restore Network",
            ),
        ),
        (
            "Low battery (self-heal trigger)",
            WorldState(
                **{
                    **current_state.to_dict(),
                    "ram_usage_pct": 40.0,
                    "temp_files_count": 0,
                    "battery_pct": 15.0,
                    "battery_plugged": False,
                }
            ),
            goal(
                target_state={"battery_pct": 80.0},
                priority=1,
                name="Charge Battery",
            ),
        ),
        (
            "High CPU temp with no cooling action (self-heal trigger)",
            WorldState(
                **{
                    **current_state.to_dict(),
                    "ram_usage_pct": 40.0,
                    "cpu_usage_pct": 60.0,
                    "temp_files_count": 0,
                    "cpu_temp_celsius": 95.0,
                }
            ),
            goal(
                target_state={"cpu_temp_celsius": 65.0},
                priority=1,
                name="Cool CPU",
            ),
        ),
        (
            "High swap usage (self-heal trigger)",
            WorldState(
                **{
                    **current_state.to_dict(),
                    "ram_usage_pct": 40.0,
                    "temp_files_count": 0,
                    "swap_usage_pct": 90.0,
                }
            ),
            goal(
                target_state={"swap_usage_pct": 30.0},
                priority=1,
                name="Reduce Swap",
            ),
        ),
        (
            "Deep cascade (multiple gaps)",
            WorldState(
                **{
                    **current_state.to_dict(),
                    "ram_usage_pct": 95.0,
                    "cpu_usage_pct": 95.0,
                    "disk_usage_pct": 95.0,
                    "temp_files_count": 500,
                    "running_processes": 500,
                    "network_connected": False,
                    "battery_pct": 5.0,
                    "battery_plugged": False,
                    "cpu_temp_celsius": 95.0,
                    "swap_usage_pct": 90.0,
                }
            ),
            goal(
                target_state={
                    "ram_usage_pct": 30.0,
                    "cpu_usage_pct": 20.0,
                    "disk_usage_pct": 40.0,
                    "temp_files_count": 0,
                    "running_processes": 50,
                    "network_connected": True,
                    "battery_pct": 80.0,
                    "cpu_temp_celsius": 65.0,
                    "swap_usage_pct": 30.0,
                },
                priority=1,
                name="Full System Recovery",
            ),
        ),
    ]

    engine = GoapEngine(
        initial_actions=baseline_actions,
        storage_path=".goap_system_actions.json",
        max_heal_attempts=3,
    )

    total = len(goals_and_states)
    for i, (label, state, g) in enumerate(goals_and_states, 1):
        print(f"\n--- [{i}/{total}] {label} ---")
        print(f"Initial: {state.to_dict()}")
        print(f"Goal:    {g.target_state}")

        result = engine.run(state, g)

        print(f"\nResult: {'SUCCESS' if result.success else 'FAILURE'}")
        if result.executed_actions:
            print("Executed Actions:")
            for act in result.executed_actions:
                print(f"  - {act.name} (cost: {act.cost})")

        if result.healed_gaps:
            print("Healed Gaps (synthesized bridge actions):")
            for gap in result.healed_gaps:
                print(
                    f"  - Missing: {gap.missing_predicate}"
                    f" (needed by: {gap.dependent_action_name})"
                )

        print(f"Final State: {result.final_state.to_dict()}")

    print("\n" + "=" * 70)
    print("SCENARIO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
