"""Domain models and exceptions for heal-my-goap."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from goapauto import (
    Actions,
    Decrement,
    Equal,
    GreaterThan,
    Increment,
    LessThan,
    NotEqual,
    PlanExecutionError,
    Range,
    Set,
    Unset,
)
from goapauto.models.actions import Action
from goapauto.models.goal import Goal
from goapauto.models.goap_planner import Planner
from goapauto.models.worldstate import WorldState
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "Action",
    "Actions",
    "Decrement",
    "Equal",
    "ExecutionResult",
    "Gap",
    "Goal",
    "GreaterThan",
    "HealMyGoapError",
    "Increment",
    "LessThan",
    "NonIdempotentExecutionError",
    "NotEqual",
    "PlanExecutionError",
    "Planner",
    "Range",
    "SandboxTimeoutError",
    "Set",
    "SynthesisError",
    "SynthesizedAction",
    "SynthesizedActionSchema",
    "Unset",
    "WorldState",
    "action_from_tool",
    "goal",
    "world_state_from_sensors",
]


def world_state_from_sensors(
    sensors: Any,
) -> WorldState:
    """Creates a ``WorldState`` populated from a ``SystemSensors`` snapshot.

    Args:
        sensors: A ``SystemSensors`` instance (or any object with a
            ``read_state()`` method returning a flat dict).

    Returns:
        A ``WorldState`` with all sensor predicates set to their
        current live values.
    """
    state_dict = sensors.read_state()
    return WorldState(**state_dict)


def goal(
    target_state: dict[str, Any],
    priority: int = 1,
    name: str = "Unnamed Goal",
) -> Goal:
    """Convenience builder for ``Goal`` instances.

    Args:
        target_state: Dict of predicate names to target values.
        priority: Goal priority (lower = higher priority).
        name: Human-readable goal label.

    Returns:
        A ``Goal`` instance.
    """
    return Goal(
        target_state=target_state,
        priority=priority,
        name=name,
    )


def action_from_tool(
    name: str,
    description: str,
    parameters: dict[str, Any] | Callable[..., Any],
    effects: dict[str, Any] | None = None,
    cost: float = 10.0,
) -> Action:
    """Creates a GOAP ``Action`` from a tool-style parameter schema or callable.

    Converts a tool definition (name, description, parameters dict or
    callable) into a deterministic GOAP action. When a callable is
    passed as ``parameters``, it is inspected to derive preconditions
    and effects from its signature and docstring.

    Args:
        name: The action name (also used as the tool name).
        description: Human-readable description of what the action does.
        parameters: Either a dict mapping parameter names to their type
            info (e.g., ``{"ram_usage_pct": "float"}``) or a callable
            whose signature is inspected for parameter names and types.
        effects: Optional dict of predicate effects. If omitted,
            effects are inferred from parameter names where possible.
        cost: Action cost for planning (default 10.0).

    Returns:
        An ``Action`` instance ready for use in a ``GoapEngine``.
    """
    if callable(parameters) and not isinstance(parameters, dict):
        import inspect

        sig = inspect.signature(parameters)
        param_types: dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                param_types[param_name] = param.annotation.__name__
            else:
                param_types[param_name] = "str"
        parameters = param_types

    preconditions: dict[str, Any] = {}
    if effects is None:
        effects = {}
    for param_name, param_type in parameters.items():
        if param_type == "bool":
            preconditions[param_name] = False
            effects[param_name] = True
        elif param_type == "float":
            preconditions[param_name] = GreaterThan(50.0)
            effects[param_name] = 30.0
        elif param_type == "int":
            preconditions[param_name] = GreaterThan(0)
            effects[param_name] = 0
        elif param_type == "str":
            preconditions[param_name] = ""
            effects[param_name] = "done"

    return Action(
        name=name,
        preconditions=preconditions,
        effects=effects,
        cost=cost,
        description=description,
    )


class Gap(BaseModel):
    """Encapsulates an unsatisfied precondition gap in GOAP planning."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    missing_predicate: dict[str, Any]
    dependent_action_name: str | None = None
    closest_state: dict[str, Any] = Field(default_factory=dict)

    def is_satisfied_by_effects(self, effects: dict[str, Any]) -> bool:
        """Checks if missing predicates are satisfied by an effects dict.

        Args:
            effects: A dictionary mapping predicate names to target values.

        Returns:
            True if all missing predicates match values in effects, False
            otherwise.
        """
        for key, val in self.missing_predicate.items():
            if effects.get(key) != val:
                return False
        return True


@dataclass
class SynthesizedAction(Action):
    """Action dataclass subclass supporting synthesized Python code payload."""

    code: str | None = None


class SynthesizedActionSchema(BaseModel):
    """Pydantic domain schema for structured LLM action synthesis validation."""

    name: str
    description: str
    preconditions: dict[str, Any]
    effects: dict[str, Any]
    cost: float = Field(default=10.0, ge=10.0)
    is_idempotent: bool = True
    code_payload: str | None = None


class ExecutionResult(BaseModel):
    """Domain container for GoapEngine execution results."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool
    final_state: WorldState
    executed_actions: list[Action] = Field(default_factory=list)
    healed_gaps: list[Gap] = Field(default_factory=list)
    error_message: str | None = None

    def is_successful(self) -> bool:
        """Determines if the GOAP execution achieved its goal.

        Returns:
            True if execution was successful, False otherwise.
        """
        return self.success


class HealMyGoapError(Exception):
    """Base exception for heal-my-goap object hierarchy."""


class NonIdempotentExecutionError(HealMyGoapError):
    """Raised when execution of a non-idempotent action fails."""


class SandboxTimeoutError(HealMyGoapError):
    """Raised when dynamic action sandbox execution times out."""


class SynthesisError(HealMyGoapError):
    """Raised when LLM action synthesis fails."""
