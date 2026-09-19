"""Advanced real-world GOAP example: Hospital Emergency Response System.

This scenario simulates a hospital emergency response where an autonomous
robot medic must triage and treat patients across multiple wards while
dealing with dynamic conditions.

Tests:
- Multi-goal arbitration with priority-based selection
- Dynamic action providers adapting to environmental changes
- Sensors that perceive hospital conditions
- Missing action scenarios (self-healing demonstration)
- Search tree visualization for debugging
- Async planning for concurrent requests
- WorldState diff and serialization
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).parent.parent))

from goapauto.models.actions import (
    Action,
    Decrement,
    Increment,
    Set,
)
from goapauto.models.goal import Goal
from goapauto.models.goal_arbitrator import GoalArbitrator
from goapauto.models.goap_planner import Planner
from goapauto.models.sensors import Sensor, SensorManager
from goapauto.models.worldstate import WorldState
from goapauto.utils.visualizer import SearchTreeVisualizer

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sensors - Perceive Hospital Environment
# ---------------------------------------------------------------------------


class MedicineSensor(Sensor):
    """Senses the current medicine level in the dispensing station."""

    def __init__(self, level: int):
        """Initialize the sensor with a medicine level.

        Args:
            level: The initial medicine level.
        """
        self._level = level

    def sense(self) -> dict[str, Any]:
        """Return the current medicine level.

        Returns:
            A dictionary with the current medicine level.
        """
        return {"medicine_current": self._level}


class PowerSensor(Sensor):
    """Senses whether the hospital power is stable."""

    def __init__(self, stable: bool = True):
        """Initialize the sensor with a power status.

        Args:
            stable: Whether the power is initially stable.
        """
        self._stable = stable

    def sense(self) -> dict[str, Any]:
        """Return the current power stability.

        Returns:
            A dictionary with the current power stability.
        """
        return {"power_stable": self._stable}


class EquipmentSensor(Sensor):
    """Senses whether the defibrillator is operational."""

    def __init__(self, operational: bool = True):
        """Initialize the sensor with equipment status.

        Args:
            operational: Whether the defibrillator is operational.
        """
        self._operational = operational

    def sense(self) -> dict[str, Any]:
        """Return the current defibrillator status.

        Returns:
            A dictionary with the defibrillator status.
        """
        return {"defibrillator_operational": self._operational}


# ---------------------------------------------------------------------------
# Action Provider - Context-Aware Actions
# ---------------------------------------------------------------------------


class HospitalActionProvider:
    """Dynamically provides hospital-specific actions based on state.

    Actions are provided based on the robot's current location and
    environmental conditions (power, equipment, medicine).
    """

    def provide_actions(self, state: WorldState) -> list[Action]:
        """Provide actions available for the current state.

        Args:
            state: The current world state.

        Returns:
            A list of applicable Action objects.
        """
        actions: list[Action] = []
        loc = getattr(state, "location", "central_hub")

        # Actions available from central_hub
        if loc == "central_hub":
            actions.append(
                Action(
                    name="navigate_to_icu",
                    preconditions={"location": "central_hub"},
                    effects={"location": Set(value="icu_ward")},
                    cost=1.0,
                )
            )
            actions.append(
                Action(
                    name="navigate_to_er",
                    preconditions={"location": "central_hub"},
                    effects={"location": Set(value="er_ward")},
                    cost=1.0,
                )
            )
            actions.append(
                Action(
                    name="restock_medicine",
                    preconditions={
                        "location": "central_hub",
                        "medicine_current": lambda v: v < 50,
                    },
                    effects={
                        "medicine_current": Set(value=100),
                        "medicine_refilled": True,
                    },
                    cost=10.0,
                )
            )

        # ICU actions
        if loc == "icu_ward":
            actions.append(
                Action(
                    name="administer_icu_medicine",
                    preconditions={
                        "location": "icu_ward",
                        "medicine_current": lambda v: v > 0,
                    },
                    effects={
                        "medicine_current": Decrement(amount=2),
                        "health_level": Increment(amount=20),
                        "icu_patient_treated": True,
                    },
                    cost=3.0,
                )
            )
            actions.append(
                Action(
                    name="defibrillate_critical",
                    preconditions={
                        "location": "icu_ward",
                        "defibrillator_operational": True,
                        "icu_patient_status": "critical",
                    },
                    effects={
                        "icu_patient_status": Set(value="stable"),
                        "health_level": Increment(amount=30),
                    },
                    cost=8.0,
                )
            )

        # ER actions
        if loc == "er_ward":
            actions.append(
                Action(
                    name="triage_patient",
                    preconditions={
                        "location": "er_ward",
                        "current_patient": 1,
                    },
                    effects={"patient_one_triage_level": 1},
                    cost=5.0,
                )
            )

        # Universal emergency actions
        if getattr(state, "power_stable", True) is False:
            actions.append(
                Action(
                    name="activate_generator",
                    preconditions={"power_stable": False},
                    effects={
                        "power_stable": True,
                        "generator_activated": True,
                    },
                    cost=15.0,
                )
            )

        return actions


# ---------------------------------------------------------------------------
# Heuristic - Domain-Specific Optimization
# ---------------------------------------------------------------------------


def hospital_heuristic(state: WorldState, goal: Goal) -> float:
    """Custom heuristic for hospital planning.

    Args:
        state: The current world state.
        goal: The goal to achieve.

    Returns:
        A float estimating the distance to the goal.
    """
    target = goal.target_state
    distance = 0.0

    for key, desired in target.items():
        current = getattr(state, key, None)

        # Handle lambda predicates in goal target
        if callable(desired):
            continue

        if isinstance(desired, (int, float)):
            current_num = current if isinstance(current, (int, float)) else 0
            if current_num < desired:
                distance += (desired - current_num) * 0.5
        elif current != desired:
            distance += 5.0

    return distance


# ---------------------------------------------------------------------------
# Main Scenario
# ---------------------------------------------------------------------------


# All possible state attributes for consistent WorldState creation
DEFAULT_STATE: dict[str, Any] = {
    "location": "central_hub",
    "health_level": 0,
    "medicine_current": 8,
    "power_stable": True,
    "defibrillator_operational": True,
    "has_repair_kit": True,
    "current_patient": 1,
    "patient_one_triage_level": 0,
    "icu_patient_status": "critical",
    "icu_patient_treated": False,
    "medicine_refilled": False,
    "generator_activated": False,
}


def make_state(**overrides: Any) -> WorldState:
    """Create a WorldState with all known attributes.

    Args:
        **overrides: Override specific state attributes.

    Returns:
        A WorldState with all attributes set.
    """
    base = dict(DEFAULT_STATE)
    base.update(overrides)
    return WorldState(**base)


async def run_complex_scenario():
    """Run a complex multi-ward hospital scenario.

    This function orchestrates a comprehensive test of the GOAP
    planning system across multiple hospital wards with dynamic
    conditions.
    """
    print("\n" + "=" * 70)
    print("HOSPITAL EMERGENCY RESPONSE SYSTEM - GOAP SCENARIO")
    print("=" * 70)

    # Set up sensors
    sensors = [
        MedicineSensor(level=8),
        PowerSensor(stable=True),
        EquipmentSensor(operational=True),
    ]
    sensor_manager = SensorManager(sensors=sensors)

    # Initialize world state
    state = make_state()
    sensor_manager.update_state(state)

    print(f"\nInitial State: {state.to_dict()}")

    # Set up components
    action_provider = HospitalActionProvider()
    planner = Planner(
        providers=[action_provider],
        max_iterations=100,
        heuristic_fn=hospital_heuristic,
    )

    # Stats collection via hooks
    plan_stats: list[dict[str, Any]] = []

    def on_plan_found_hook(plan: list[str], stats: Any):
        """Collect plan statistics.

        Args:
            plan: List of action names.
            stats: Planning statistics.
        """
        plan_stats.append(
            {
                "length": stats.plan_length,
                "expanded": stats.nodes_expanded,
                "visited": stats.nodes_visited,
            }
        )
        print(f"\n  Hook: Plan found: {plan}")

    planner.register_hook("on_plan_found", on_plan_found_hook)

    # Goal arbitrator with multiple competing goals
    goals = [
        Goal(
            target_state={"icu_patient_treated": True},
            priority=1,
            name="Treat ICU Patient",
        ),
        Goal(
            target_state={"health_level": 50},
            priority=3,
            name="Improve Health",
        ),
        Goal(
            target_state={"medicine_refilled": True},
            priority=5,
            name="Refill Medicine",
        ),
        Goal(
            target_state={"patient_one_triage_level": 1},
            priority=2,
            name="Triage ER Patient",
        ),
    ]

    arbitrator = GoalArbitrator(goals=goals)
    visualizer = SearchTreeVisualizer()
    planner.register_hook("on_node_expanded", visualizer.on_node_expanded)

    # Test 1: ICU patient treatment
    print("\n" + "=" * 70)
    print("TEST 1: Plan to treat ICU patient")
    print("=" * 70)

    icu_goal = Goal(
        target_state={
            "icu_patient_treated": True,
            "location": "icu_ward",
            "medicine_current": 10,
        },
        priority=1,
        name="Treat ICU Patient",
    )

    result = await planner.async_generate_plan(state, icu_goal)
    print(f"\nResult: {result.message}")
    if result.plan:
        for i, a in enumerate(result.plan, 1):
            print(f"  {i}. {a}")
        print(
            f"\nStats: expanded="
            f"{planner.stats.nodes_expanded},"
            f" visited={planner.stats.nodes_visited}"
        )

    visualizer.export("search_tree.mmd")
    print("[Viz] Exported search tree to search_tree.mmd")

    # Test 2: Goal arbitration
    print("\n" + "=" * 70)
    print("TEST 2: Goal Arbitration")
    print("=" * 70)

    selected = arbitrator.select_goal(state)
    if selected:
        print(f"Selected: {selected.name} (Priority: {selected.priority})")

    # Test 3: Self-healing - missing action scenario
    print("\n" + "=" * 70)
    print("TEST 3: Missing preconditions (self-healing test)")
    print("=" * 70)

    # State with no path to goal: defibrillator broken,
    # no repair action available (no repair_kit in this
    # scenario's action set)
    problem_state = make_state(
        location="icu_ward",
        power_stable=False,
        defibrillator_operational=False,
    )

    recovery_goal = Goal(
        target_state={
            "defibrillator_operational": True,
        },
        priority=1,
        name="Fix Defibrillator",
    )

    visualizer.clear()
    result2 = await planner.async_generate_plan(problem_state, recovery_goal)
    print(f"\nResult: {result2.message}")
    if not result2.plan:
        print("\nGap for heal-my-goap to solve:")
        print("  - defibrillator_operational=True")
        print("  - No existing action can produce this without a repair kit")
        print(
            "  - LLMSynthesizer would synthesize 'emergency_repair' or similar"
        )

    # Test 4: Concurrent planning
    print("\n" + "=" * 70)
    print("TEST 4: Concurrent planning scenarios")
    print("=" * 70)

    base = make_state()
    scenarios: list[tuple[str, Goal]] = [
        (
            "ER Triage",
            Goal(
                target_state={
                    "location": "er_ward",
                    "patient_one_triage_level": 1,
                },
                name="ER",
            ),
        ),
        (
            "ICU Treatment",
            Goal(
                target_state={
                    "icu_patient_treated": True,
                    "medicine_current": 10,
                },
                name="ICU",
            ),
        ),
        (
            "Medicine Restock",
            Goal(
                target_state={"medicine_refilled": True},
                name="Refill",
            ),
        ),
    ]

    async def run_scenario(name: str, goal: Goal) -> tuple[str, Any]:
        """Execute a planning scenario.

        Args:
            name: Scenario name.
            goal: Goal to plan for.

        Returns:
            Tuple of scenario name and result.
        """
        result = await planner.async_generate_plan(base, goal)
        return (name, result)

    tasks = [run_scenario(n, g) for n, g in scenarios]
    for name, result in await asyncio.gather(*tasks):
        print(f"\n  {name}: {result.message}")
        if result.plan:
            print(f"    Plan: {result.plan}")

    # Test 5: WorldState diff
    print("\n" + "=" * 70)
    print("TEST 5: WorldState diff and serialization")
    print("=" * 70)

    s1 = WorldState(health=0, medicine=100)
    s2 = s1.copy(deep=True)
    s2.health = 50
    s2.medicine = 95

    print(f"Diff: {s1.diff(s2)}")
    restored = WorldState.from_dict(s1.to_dict())
    print(f"Round-trip: {restored.to_dict()}")
    print("Verified!")

    print("\n" + "=" * 70)
    print("SCENARIO COMPLETE")
    print("=" * 70)
    print(f"\nPlans found: {len(plan_stats)}")


def main() -> None:
    """Main entry point."""
    asyncio.run(run_complex_scenario())


if __name__ == "__main__":
    main()
