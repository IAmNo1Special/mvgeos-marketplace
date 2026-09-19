"""Diagnostic gap isolation engine for GOAP planning."""

from abc import ABC, abstractmethod
from typing import Any

from mvgeos_runes_heal_my_goap.models import Action, Gap, Goal, WorldState


class BaseGapAnalyzer(ABC):
    """Abstract interface for diagnostic gap isolation engines."""

    @abstractmethod
    def analyze(
        self,
        initial_state: WorldState,
        goal: Goal,
        actions: list[Action],
        expanded_nodes: list[Any] | None = None,
    ) -> Gap:
        """Isolates missing precondition gaps between current state and goal.

        Args:
            initial_state: Starting world state.
            goal: Target goal state.
            actions: Available baseline and synthesized actions.
            expanded_nodes: Optional list of expanded search nodes.

        Returns:
            A Gap object representing the missing state predicate.
        """


class GapAnalyzer(BaseGapAnalyzer):
    """Diagnostic engine for missing preconditions via goal graph traversal."""

    def analyze(
        self,
        initial_state: WorldState,
        goal: Goal,
        actions: list[Action],
        expanded_nodes: list[Any] | None = None,
    ) -> Gap:
        """Traverses goal graph to isolate missing state predicates.

        Args:
            initial_state: Starting world state.
            goal: Target goal state.
            actions: Available baseline and synthesized actions.
            expanded_nodes: Optional list of expanded search nodes.

        Returns:
            A Gap object containing missing predicate details.
        """
        state_dict = (
            initial_state.to_dict()
            if hasattr(initial_state, "to_dict")
            else dict(initial_state)
        )

        unsatisfied_goal_predicates: dict[str, Any] = {}
        for key, val in goal.target_state.items():
            if state_dict.get(key) != val:
                unsatisfied_goal_predicates[key] = val

        queue: list[tuple[str, Any, str | None]] = [
            (k, v, None) for k, v in unsatisfied_goal_predicates.items()
        ]
        visited: set[str] = set()

        missing_predicate: dict[str, Any] | None = None
        dependent_action_name: str | None = None

        while queue:
            pred_key, pred_val, dep_action = queue.pop(0)
            if pred_key in visited:
                continue
            visited.add(pred_key)

            producing_actions = [
                act for act in actions if act.effects.get(pred_key) == pred_val
            ]

            if not producing_actions:
                missing_predicate = {pred_key: pred_val}
                dependent_action_name = dep_action
                break

            for act in producing_actions:
                for pre_k, pre_v in act.preconditions.items():
                    if state_dict.get(pre_k) != pre_v:
                        queue.append((pre_k, pre_v, act.name))

        if missing_predicate is None:
            if unsatisfied_goal_predicates:
                first_key = next(iter(unsatisfied_goal_predicates))
                missing_predicate = {
                    first_key: unsatisfied_goal_predicates[first_key]
                }
            else:
                missing_predicate = {}

        return Gap(
            missing_predicate=missing_predicate,
            dependent_action_name=dependent_action_name,
            closest_state=state_dict,
        )
