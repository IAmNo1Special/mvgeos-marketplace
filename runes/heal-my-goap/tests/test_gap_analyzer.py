"""Tests for diagnostic gap analyzer engine."""

from typing import Any

from heal_my_goap.gap_analyzer import GapAnalyzer
from heal_my_goap.models import Action, Goal, WorldState


def test_gap_analyzer_direct_missing_precondition() -> None:
    """Verifies gap isolation for missing action precondition."""
    ws_kwargs: dict[str, Any] = {"in_room": True, "file_downloaded": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"file_processed": True})
    actions = [
        Action(
            name="process_file",
            preconditions={"file_downloaded": True},
            effects={"file_processed": True},
            cost=1,
        )
    ]

    analyzer = GapAnalyzer()
    gap = analyzer.analyze(initial_state, goal, actions)

    assert gap is not None
    assert gap.missing_predicate == {"file_downloaded": True}
    assert gap.dependent_action_name == "process_file"


def test_gap_analyzer_direct_goal_gap() -> None:
    """Verifies gap isolation for direct goal predicate requirement."""
    ws_kwargs: dict[str, Any] = {"file_downloaded": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"file_downloaded": True})
    actions: list[Action] = []

    analyzer = GapAnalyzer()
    gap = analyzer.analyze(initial_state, goal, actions)

    assert gap is not None
    assert gap.missing_predicate == {"file_downloaded": True}
    assert gap.dependent_action_name is None


def test_gap_analyzer_complex_types() -> None:
    """Verifies gap isolation with non-boolean predicate values."""
    ws_kwargs: dict[str, Any] = {"power_level": 0}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"laser_fired": True})
    actions = [
        Action(
            name="fire_laser",
            preconditions={"power_level": 100},
            effects={"laser_fired": True},
            cost=1,
        )
    ]

    analyzer = GapAnalyzer()
    gap = analyzer.analyze(initial_state, goal, actions)

    assert gap.missing_predicate == {"power_level": 100}
    assert gap.dependent_action_name == "fire_laser"


def test_gap_analyzer_when_all_goals_satisfied() -> None:
    """Verifies gap analyzer output when goals are satisfied."""
    ws_kwargs: dict[str, Any] = {"power_level": 100}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"power_level": 100})
    actions: list[Action] = []

    analyzer = GapAnalyzer()
    gap = analyzer.analyze(initial_state, goal, actions)

    assert gap.missing_predicate == {}
    assert gap.dependent_action_name is None
