"""Tests for heal_my_goap domain models and custom exceptions."""

from typing import Any, cast

import pytest
from pydantic import ValidationError

from heal_my_goap.models import (
    Action,
    ExecutionResult,
    Gap,
    Goal,
    GreaterThan,
    NonIdempotentExecutionError,
    Planner,
    SandboxTimeoutError,
    SynthesisError,
    SynthesizedActionSchema,
    WorldState,
    action_from_tool,
    goal,
    world_state_from_sensors,
)


def test_reexported_models() -> None:
    """Verifies re-exported goapauto models."""
    ws_kwargs: dict[str, Any] = {"has_key": True}
    ws = WorldState(**ws_kwargs)
    assert ws.get("has_key") is True

    action = Action(
        name="open_door",
        preconditions={"has_key": True},
        effects={"door_open": True},
        cost=1,
    )
    assert action.name == "open_door"

    goal = Goal(target_state={"door_open": True})
    assert goal.target_state == {"door_open": True}

    planner = Planner(actions_list=cast(Any, [action]))
    assert planner is not None


def test_gap_model() -> None:
    """Verifies Gap model initialization and attributes."""
    gap = Gap(
        missing_predicate={"has_key": True},
        dependent_action_name="open_door",
        closest_state={"has_key": False},
    )
    assert gap.missing_predicate == {"has_key": True}
    assert gap.dependent_action_name == "open_door"
    assert isinstance(gap.id, str) and len(gap.id) > 0


def test_synthesized_action_schema_cost_constraint() -> None:
    """Verifies cost >= 10 validation constraint on SynthesizedActionSchema."""
    valid_schema = SynthesizedActionSchema(
        name="synth_find_key",
        description="Find key in drawer",
        preconditions={"in_room": True},
        effects={"has_key": True},
        cost=10.0,
        is_idempotent=True,
    )
    assert valid_schema.cost == 10.0

    with pytest.raises(ValidationError):
        SynthesizedActionSchema(
            name="synth_free_magic",
            description="Magic action",
            preconditions={},
            effects={"has_key": True},
            cost=1.0,
        )


def test_execution_result_and_exceptions() -> None:
    """Verifies ExecutionResult container and exception inheritance."""
    ws_kwargs: dict[str, Any] = {"door_open": True}
    ws = WorldState(**ws_kwargs)
    res = ExecutionResult(
        success=True,
        final_state=ws,
        executed_actions=[],
        healed_gaps=[],
    )
    assert res.success is True
    assert res.error_message is None
    assert res.is_successful() is True

    res_fail = ExecutionResult(
        success=False,
        final_state=ws,
    )
    assert res_fail.is_successful() is False


assert issubclass(NonIdempotentExecutionError, Exception)
assert issubclass(SandboxTimeoutError, Exception)
assert issubclass(SynthesisError, Exception)


def test_world_state_from_sensors() -> None:
    """Verifies world_state_from_sensors creates a WorldState."""

    class FakeSensors:
        def read_state(self) -> dict[str, Any]:
            return {"has_key": True, "door_open": False}

    ws = world_state_from_sensors(FakeSensors())
    assert ws.get("has_key") is True
    assert ws.get("door_open") is False


def test_goal_builder() -> None:
    """Verifies the goal() convenience builder creates a Goal."""
    g = goal(target_state={"door_open": True}, priority=1, name="Open Door")
    assert g.target_state == {"door_open": True}
    assert g.priority == 1
    assert g.name == "Open Door"


def test_goal_builder_defaults() -> None:
    """Verifies goal() uses sensible defaults."""
    g = goal(target_state={"done": True})
    assert g.priority == 1
    assert g.name == "Unnamed Goal"


def test_action_from_tool_with_dict() -> None:
    """Verifies action_from_tool creates an Action from a parameter dict."""
    action = action_from_tool(
        name="check_ram",
        description="Check RAM usage",
        parameters={"ram_usage_pct": "float"},
    )
    assert action.name == "check_ram"
    assert getattr(action, "description") == "Check RAM usage"
    assert "ram_usage_pct" in action.preconditions
    assert isinstance(action.preconditions["ram_usage_pct"], GreaterThan)
    assert action.preconditions["ram_usage_pct"](60.0) is True
    assert "ram_usage_pct" in action.effects


def test_action_from_tool_with_callable() -> None:
    """Verifies action_from_tool inspects a callable's signature."""

    def my_tool(ram_usage_pct: float, temp_files_count: int) -> None:
        """Check system health."""

    action = action_from_tool(
        name="check_health",
        description="Check system health",
        parameters=my_tool,
    )
    assert action.name == "check_health"
    assert isinstance(action.preconditions["ram_usage_pct"], GreaterThan)
    assert isinstance(action.preconditions["temp_files_count"], GreaterThan)


def test_action_from_tool_with_effects() -> None:
    """Verifies action_from_tool uses provided effects when given."""
    action = action_from_tool(
        name="clear_temp",
        description="Clear temp files",
        parameters={"temp_files_count": "int"},
        effects={"temp_files_count": 0},
        cost=5.0,
    )
    assert action.cost == 5.0
    assert action.effects == {"temp_files_count": 0}


def test_action_from_tool_callable_unannotated() -> None:
    """Verifies action_from_tool defaults unannotated params to str."""

    def my_tool(ram_usage_pct: float, temp_files_count: int) -> None:
        """Check system health."""

    action = action_from_tool(
        name="check_health",
        description="Check system health",
        parameters=my_tool,
    )
    assert "ram_usage_pct" in action.preconditions
    assert "temp_files_count" in action.preconditions


def test_action_from_tool_callable_mixed_annotations() -> None:
    """Verifies action_from_tool defaults unannotated params to str."""

    def my_tool(ram_usage_pct, temp_files_count: int) -> None:  # type: ignore[no-untyped-def]
        """Check system health."""

    action = action_from_tool(
        name="check_health",
        description="Check system health",
        parameters=my_tool,
    )
    assert "ram_usage_pct" in action.preconditions
    assert action.preconditions["ram_usage_pct"] == ""
    assert action.effects["ram_usage_pct"] == "done"


def test_action_from_tool_bool_type() -> None:
    """Verifies action_from_tool handles bool parameter type."""
    action = action_from_tool(
        name="toggle_network",
        description="Toggle network",
        parameters={"network_connected": "bool"},
    )
    assert action.preconditions["network_connected"] is False
    assert action.effects["network_connected"] is True


def test_action_from_tool_str_type() -> None:
    """Verifies action_from_tool handles str parameter type."""
    action = action_from_tool(
        name="set_cwd",
        description="Set working directory",
        parameters={"cwd": "str"},
    )
    assert action.preconditions["cwd"] == ""
    assert action.effects["cwd"] == "done"
