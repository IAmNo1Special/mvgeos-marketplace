"""Advanced GOAP example: Coding Agent Build Pipeline.

This scenario simulates an AI coding agent tasked with implementing a
feature in a software project. The agent must navigate a complex
development workflow including writing code, running tests, building,
and shipping.

The scenario demonstrates:
- Dynamic action providers that change based on project state
- Sensors simulating file system changes and test results
- Multi-goal arbitration between competing objectives
- Self-healing when code doesn't compile or tests fail
- Complex precondition chains through the development pipeline
- Async concurrent planning for multiple development tasks
- Search tree visualization for debugging planning decisions
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
# Sensors - Simulate Development Environment Feedback
# ---------------------------------------------------------------------------


class TestResultSensor(Sensor):
    """Senses whether the test suite is currently passing."""

    def __init__(self, passing: bool = False):
        """Initialize the sensor with test status.

        Args:
            passing: Whether tests are currently passing.
        """
        self._passing = passing

    def sense(self) -> dict[str, Any]:
        """Return the current test status.

        Returns:
            A dictionary with the test pass/fail status.
        """
        return {"tests_passing": self._passing}


class LintStatusSensor(Sensor):
    """Senses whether the code passes linting."""

    def __init__(self, clean: bool = False):
        """Initialize the sensor with lint status.

        Args:
            clean: Whether code passes linting.
        """
        self._clean = clean

    def sense(self) -> dict[str, Any]:
        """Return the current lint status.

        Returns:
            A dictionary with the lint status.
        """
        return {"lint_clean": self._clean}


class BuildStatusSensor(Sensor):
    """Senses whether the project builds successfully."""

    def __init__(self, success: bool = False):
        """Initialize the sensor with build status.

        Args:
            success: Whether the build succeeds.
        """
        self._success = success

    def sense(self) -> dict[str, Any]:
        """Return the current build status.

        Returns:
            A dictionary with the build status.
        """
        return {"build_success": self._success}


class CodeQualitySensor(Sensor):
    """Senses code quality metrics (coverage, complexity)."""

    def __init__(
        self,
        coverage: int = 0,
        complexity: int = 0,
    ):
        """Initialize the sensor with quality metrics.

        Args:
            coverage: Current test coverage percentage.
            complexity: Current code complexity score.
        """
        self._coverage = coverage
        self._complexity = complexity

    def set_metrics(
        self,
        coverage: int,
        complexity: int,
    ):
        """Update quality metrics.

        Args:
            coverage: New coverage percentage.
            complexity: New complexity score.
        """
        self._coverage = coverage
        self._complexity = complexity

    def sense(self) -> dict[str, Any]:
        """Return current quality metrics.

        Returns:
            A dictionary with coverage and complexity.
        """
        return {
            "coverage_pct": self._coverage,
            "complexity_score": self._complexity,
        }


# ---------------------------------------------------------------------------
# Dynamic Action Provider - Development Workflow Actions
# ---------------------------------------------------------------------------


class DevActionProvider:
    """Provides development workflow actions dynamically.

    Actions change based on the current development state:
    - What files exist
    - What stage of the pipeline we're in
    - What errors are present
    - What tools are available
    """

    def provide_actions(self, state: WorldState) -> list[Action]:
        """Provide development actions for current state.

        Args:
            state: The current world state representing
                the development environment.

        Returns:
            A list of applicable Action objects.
        """
        actions: list[Action] = []

        # Fix syntax errors first (if any)
        if getattr(state, "has_syntax_errors", False):
            actions.append(
                Action(
                    name="fix_syntax_errors",
                    preconditions={"has_syntax_errors": True},
                    effects={
                        "has_syntax_errors": False,
                        "code_written": True,
                    },
                    cost=8.0,
                )
            )
        elif getattr(state, "code_written", False) is False:
            # Write code if no syntax errors and code not written
            if getattr(state, "requirements_read", False):
                actions.append(
                    Action(
                        name="write_implementation",
                        preconditions={
                            "requirements_read": True,
                            "code_written": False,
                        },
                        effects={
                            "code_written": True,
                        },
                        cost=10.0,
                    )
                )

        # Code review - requires written code
        if getattr(state, "code_written", False) and not getattr(
            state, "code_reviewed", False
        ):
            actions.append(
                Action(
                    name="run_code_review",
                    preconditions={
                        "code_written": True,
                        "code_reviewed": False,
                    },
                    effects={
                        "code_reviewed": True,
                        "lint_clean": True,
                    },
                    cost=3.0,
                )
            )

        # Build - requires code written and reviewed
        if (
            getattr(state, "code_written", False)
            and getattr(state, "code_reviewed", False)
            and not getattr(state, "build_success", True)
        ):
            actions.append(
                Action(
                    name="build_project",
                    preconditions={
                        "code_written": True,
                        "code_reviewed": True,
                        "build_success": False,
                    },
                    effects={"build_success": True},
                    cost=5.0,
                )
            )

        # Run tests - requires successful build
        if getattr(state, "build_success", False):
            actions.append(
                Action(
                    name="run_tests",
                    preconditions={
                        "build_success": True,
                    },
                    effects={
                        "tests_passing": True,
                        "coverage_pct": Increment(amount=30),
                    },
                    cost=4.0,
                )
            )

        # Fix failing tests
        if getattr(state, "build_success", True) and not getattr(
            state, "tests_passing", True
        ):
            actions.append(
                Action(
                    name="fix_failing_tests",
                    preconditions={
                        "build_success": True,
                        "tests_passing": False,
                    },
                    effects={"tests_passing": True},
                    cost=15.0,
                )
            )

        # Add more tests for coverage
        if (
            getattr(state, "tests_passing", False)
            and getattr(state, "coverage_pct", 0) < 30
        ):
            actions.append(
                Action(
                    name="add_more_tests",
                    preconditions={
                        "tests_passing": True,
                        "coverage_pct": lambda v: v < 30,
                    },
                    effects={
                        "coverage_pct": Increment(amount=20),
                    },
                    cost=7.0,
                )
            )

        # Optimize complexity if high
        if (
            getattr(state, "tests_passing", False)
            and getattr(state, "complexity_score", 0) > 5
        ):
            actions.append(
                Action(
                    name="optimize_performance",
                    preconditions={
                        "tests_passing": True,
                        "complexity_score": lambda v: v > 5,
                    },
                    effects={
                        "complexity_score": Decrement(amount=3),
                    },
                    cost=12.0,
                )
            )

        # Documentation - final step
        if (
            getattr(state, "tests_passing", False)
            and getattr(state, "coverage_pct", 0) >= 30
            and getattr(state, "complexity_score", 999) <= 5
            and not getattr(state, "documentation_written", False)
        ):
            actions.append(
                Action(
                    name="write_documentation",
                    preconditions={
                        "tests_passing": True,
                        "coverage_pct": lambda v: v >= 30,
                        "complexity_score": lambda v: v <= 5,
                        "documentation_written": False,
                    },
                    effects={
                        "documentation_written": True,
                    },
                    cost=6.0,
                )
            )

        return actions


# ---------------------------------------------------------------------------
# Custom Heuristic for Development Pipeline
# ---------------------------------------------------------------------------


def dev_heuristic(state: WorldState, goal: Goal) -> float:
    """Heuristic for development pipeline planning.

    Estimates progress needed for code quality, testing,
    and build status.

    Args:
        state: Current development state.
        goal: Target goal state.

    Returns:
        Estimated distance to goal.
    """
    target = goal.target_state
    distance = 0.0

    for key, desired in target.items():
        if callable(desired):
            continue
        current = getattr(state, key, None)

        if isinstance(desired, (int, float)):
            cur_num = current if isinstance(current, (int, float)) else 0
            if cur_num < desired:
                distance += (desired - cur_num) * 0.5
        elif current != desired:
            distance += 5.0

    return distance


# ---------------------------------------------------------------------------
# Main Scenario
# ---------------------------------------------------------------------------


DEV_STATE: dict[str, Any] = {
    "location": "workspace",
    "requirements_read": True,
    "code_written": False,
    "code_reviewed": False,
    "build_success": False,
    "tests_passing": False,
    "coverage_pct": 0,
    "complexity_score": 10,
    "has_syntax_errors": True,
    "lint_clean": False,
    "documentation_written": False,
}


def make_dev_state(**overrides: Any) -> WorldState:
    """Create a dev WorldState with all known attributes.

    Args:
        **overrides: Override specific state attributes.

    Returns:
        A WorldState representing the dev environment.
    """
    base = dict(DEV_STATE)
    base.update(overrides)
    return WorldState(**base)


async def run_coding_agent_scenario():
    """Run the coding agent development pipeline scenario.

    This function simulates a coding agent implementing a new
    feature through the full development lifecycle.
    """
    print("\n" + "=" * 70)
    print("CODING AGENT BUILD PIPELINE - GOAP SCENARIO")
    print("=" * 70)

    # Set up sensors
    test_sensor = TestResultSensor(passing=False)
    lint_sensor = LintStatusSensor(clean=False)
    build_sensor = BuildStatusSensor(success=False)
    quality_sensor = CodeQualitySensor(coverage=0, complexity=10)

    sensor_manager = SensorManager(
        sensors=[
            test_sensor,
            lint_sensor,
            build_sensor,
            quality_sensor,
        ]
    )

    # Initialize dev state
    state = make_dev_state()
    sensor_manager.update_state(state)

    print(f"\nInitial State: {state.to_dict()}")

    # Set up components
    action_provider = DevActionProvider()
    planner = Planner(
        providers=[action_provider],
        max_iterations=100,
        heuristic_fn=dev_heuristic,
    )

    plan_stats: list[dict[str, Any]] = []

    def on_plan_found(plan: list[str], stats: Any):
        """Collect plan statistics.

        Args:
            plan: The generated plan.
            stats: Planning statistics.
        """
        plan_stats.append(
            {
                "length": stats.plan_length,
                "expanded": stats.nodes_expanded,
                "visited": stats.nodes_visited,
            }
        )
        print(f"\n  [Hook] Plan: {plan}")

    planner.register_hook("on_plan_found", on_plan_found)
    visualizer = SearchTreeVisualizer()
    planner.register_hook("on_node_expanded", visualizer.on_node_expanded)

    # Goal arbitrator with development objectives
    dev_goals = [
        Goal(
            target_state={"documentation_written": True},
            priority=1,
            name="Ship Feature",
        ),
        Goal(
            target_state={"tests_passing": True},
            priority=2,
            name="Pass Tests",
        ),
        Goal(
            target_state={"build_success": True},
            priority=3,
            name="Build Success",
        ),
        Goal(
            target_state={"lint_clean": True},
            priority=4,
            name="Clean Lint",
        ),
    ]

    arbitrator = GoalArbitrator(goals=dev_goals)

    # Test 1: Full pipeline from broken to shipped
    print("\n" + "=" * 70)
    print("TEST 1: Full development pipeline")
    print("=" * 70)

    ship_goal = Goal(
        target_state={
            "code_written": True,
            "build_success": True,
            "tests_passing": True,
            "documentation_written": True,
        },
        priority=1,
        name="Ship Feature",
    )

    result = await planner.async_generate_plan(state, ship_goal)
    print(f"\nResult: {result.message}")
    if result.plan:
        for i, a in enumerate(result.plan, 1):
            print(f"  {i}. {a}")
        print(
            f"\nStats: expanded={planner.stats.nodes_expanded},"
            f" visited={planner.stats.nodes_visited}"
        )

    visualizer.export("coding_pipeline.mmd")
    print("[Viz] Exported to coding_pipeline.mmd")

    # Test 2: Goal arbitration
    print("\n" + "=" * 70)
    print("TEST 2: Development Goal Arbitration")
    print("=" * 70)

    selected = arbitrator.select_goal(state)
    if selected:
        print(f"Selected: {selected.name} (Priority: {selected.priority})")

    # Test 3: Bug fixing (self-healing)
    print("\n" + "=" * 70)
    print("TEST 3: Bug fixing with gap (self-healing)")
    print("=" * 70)

    # No existing action produces documentation_written
    # when has_syntax_errors=True and no fix path exists
    buggy_state = make_dev_state(
        has_syntax_errors=True,
        code_written=False,
        tests_passing=False,
        build_success=False,
        coverage_pct=0,
        complexity_score=10,
        documentation_written=False,
    )

    fix_goal = Goal(
        target_state={
            "has_syntax_errors": False,
            "tests_passing": True,
            "documentation_written": True,
        },
        priority=1,
        name="Fix and Ship",
    )

    visualizer.clear()
    result2 = await planner.async_generate_plan(buggy_state, fix_goal)
    print(f"\nResult: {result2.message}")
    if not result2.plan:
        print("\nGap for heal-my-goap to solve:")
        print("  - documentation_written=True")
        print("  - No action chain reaches this without specific fix patterns")
        print("  - LLMSynthesizer would synthesize a custom fix action")
    else:
        print("Plan found:")
        for i, a in enumerate(result2.plan, 1):
            print(f"  {i}. {a}")

    # Test 4: Concurrent planning
    print("\n" + "=" * 70)
    print("TEST 4: Concurrent development planning")
    print("=" * 70)

    base = make_dev_state()

    scenarios: list[tuple[str, Goal]] = [
        (
            "Build Focus",
            Goal(
                target_state={
                    "code_written": True,
                    "build_success": True,
                },
                name="Build",
            ),
        ),
        (
            "Test Focus",
            Goal(
                target_state={
                    "build_success": True,
                    "tests_passing": True,
                },
                name="Test",
            ),
        ),
        (
            "Quality Focus",
            Goal(
                target_state={
                    "tests_passing": True,
                    "coverage_pct": 30,
                },
                name="Quality",
            ),
        ),
    ]

    async def run_scenario(name: str, goal: Goal) -> tuple[str, Any]:
        """Execute a planning scenario.

        Args:
            name: Scenario name.
            goal: Goal to plan for.

        Returns:
            Tuple of name and result.
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
    print("TEST 5: WorldState diff - tracking dev changes")
    print("=" * 70)

    s1 = WorldState(
        code_written=False,
        build_success=False,
        tests_passing=False,
    )
    s2 = s1.copy(deep=True)
    s2.code_written = True
    s2.build_success = True

    diff = s1.diff(s2)
    print(f"State diff: {diff}")
    print("Tracks what changed between dev states!")

    print("\n" + "=" * 70)
    print("CODING AGENT SCENARIO COMPLETE")
    print("=" * 70)
    print(f"\nPlans found: {len(plan_stats)}")
    print("Demonstrates:")
    print("  - Dynamic action providers for dev workflows")
    print("  - Sensors for test/lint/build feedback")
    print("  - Goal arbitration between dev objectives")
    print("  - Self-healing for bug-fix scenarios")
    print("  - Async concurrent planning for tasks")
    print("  - WorldState diff for change tracking")
    print("  - Visualization for debugging planning")


def main() -> None:
    """Main entry point for the coding agent GOAP example."""
    asyncio.run(run_coding_agent_scenario())


if __name__ == "__main__":
    main()
