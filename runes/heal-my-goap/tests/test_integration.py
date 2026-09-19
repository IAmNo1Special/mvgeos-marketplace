"""Live integration tests for OpenRouter synthesis and GoapEngine."""

import os
from typing import Any

import pytest
from dotenv import load_dotenv

from heal_my_goap import (
    Action,
    Gap,
    Goal,
    GoapEngine,
    LLMSynthesizer,
    WorldState,
)

load_dotenv()

HAS_API_KEY = bool(os.getenv("OPENROUTER_API_KEY"))


@pytest.mark.skipif(
    not HAS_API_KEY, reason="OPENROUTER_API_KEY not present in environment"
)
def test_live_openrouter_synthesizer() -> None:
    """Verifies live OpenRouter API action synthesis."""
    synthesizer = LLMSynthesizer()
    gap = Gap(
        missing_predicate={"has_key": True},
        dependent_action_name="open_door",
    )

    action = synthesizer.synthesize_bridge_action(gap, available_actions=[])

    assert action is not None
    assert action.effects.get("has_key") is True
    assert float(action.cost) >= 10.0  # type: ignore[arg-type]
    assert isinstance(action.name, str)


@pytest.mark.skipif(
    not HAS_API_KEY, reason="OPENROUTER_API_KEY not present in environment"
)
def test_live_openrouter_engine_self_healing(tmp_path: Any) -> None:
    """Verifies end-to-end live self-healing GOAP execution loop."""
    storage_file = str(tmp_path / "live_actions.json")

    open_door = Action(
        name="open_door",
        preconditions={"has_key": True},
        effects={"door_open": True},
        cost=1,
    )

    engine = GoapEngine(
        initial_actions=[open_door],
        storage_path=storage_file,
        max_heal_attempts=3,
    )

    ws_kwargs: dict[str, Any] = {"has_key": False, "door_open": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"door_open": True})

    result = engine.run(initial_state, goal)

    assert result.success is True
    assert result.final_state.get("door_open") is True
    assert len(result.healed_gaps) >= 1
