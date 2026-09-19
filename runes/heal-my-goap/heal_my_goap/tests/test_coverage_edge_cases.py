"""Edge cases and failure recovery tests for 100% coverage."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from heal_my_goap.engine import GoapEngine
from heal_my_goap.gap_analyzer import GapAnalyzer
from heal_my_goap.models import Action, Gap, Goal, WorldState
from heal_my_goap.sandbox import SandboxExecutor
from heal_my_goap.storage import ActionStorage
from heal_my_goap.synthesizer import LLMSynthesizer


def test_gap_analyzer_dict_initial_state() -> None:
    """Verifies gap analyzer support for iterable initial state objects."""

    class CustomState:
        def __init__(self, data: dict[str, Any]) -> None:
            self._data = data

        def __iter__(self) -> Any:
            return iter(self._data.items())

    state = CustomState({"in_room": True})
    goal = Goal(target_state={"file_downloaded": True})
    actions: list[Action] = []

    analyzer = GapAnalyzer()
    gap = analyzer.analyze(state, goal, actions)  # type: ignore[arg-type]
    assert gap.missing_predicate == {"file_downloaded": True}


def test_gap_analyzer_visited_nodes_loop() -> None:
    """Verifies gap analyzer loop prevention on cyclical preconditions."""
    act1 = Action(
        name="act1", preconditions={"p2": True}, effects={"p1": True}, cost=1
    )
    act2 = Action(
        name="act2", preconditions={"p1": True}, effects={"p2": True}, cost=1
    )

    initial_state = WorldState()
    goal = Goal(target_state={"p1": True})

    analyzer = GapAnalyzer()
    gap = analyzer.analyze(initial_state, goal, [act1, act2])
    assert gap is not None


def test_storage_corrupted_file_handling(tmp_path: Any) -> None:
    """Verifies ActionStorage error handling for corrupted JSON files."""
    corrupted_file = str(tmp_path / "corrupted.json")
    with open(corrupted_file, "w", encoding="utf-8") as f:
        f.write("{invalid json content")

    storage = ActionStorage(file_path=corrupted_file)
    assert storage.load_actions() == []

    non_existent = ActionStorage(
        file_path=str(tmp_path / "does_not_exist.json")
    )
    non_existent.clear()


def test_sandbox_import_from_forbidden() -> None:
    """Verifies AST safety visitor catches forbidden from-imports."""
    executor = SandboxExecutor()
    with pytest.raises(ValueError, match="Forbidden AST node"):
        executor.validate_ast("from os import path")


def test_synthesizer_api_http_error_handling() -> None:
    """Verifies synthesizer fallback when OpenRouter returns 500 error."""
    synthesizer = LLMSynthesizer(api_key="valid_key")
    gap = Gap(missing_predicate={"has_key": True})

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("httpx.Client.post", return_value=mock_resp):
        action = synthesizer.synthesize_bridge_action(gap, available_actions=[])
        assert "wildcard" in action.name


def test_synthesizer_rate_limit_retry_handling() -> None:
    """Verifies synthesizer exponential backoff retry on 429 status code."""
    synthesizer = LLMSynthesizer(api_key="valid_key")
    gap = Gap(missing_predicate={"has_key": True})

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    mock_resp_200 = MagicMock()
    mock_response_json = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"name": "fetch_key", "description": "Fetch key", '
                        '"preconditions": {}, "effects": {"has_key": true}, '
                        '"cost": 10.0}'
                    )
                }
            }
        ]
    }
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = mock_response_json

    with (
        patch("httpx.Client.post", side_effect=[mock_resp_429, mock_resp_200]),
        patch("time.sleep"),
    ):
        action = synthesizer.synthesize_bridge_action(gap, available_actions=[])
        assert action.name.startswith("synth_fetch_key")


def test_engine_idempotent_action_failure_recovery(tmp_path: Any) -> None:
    """Verifies engine state rollback and retry on flaky idempotent action."""
    storage_file = str(tmp_path / "engine_recovery.json")

    failing_idempotent_action = Action(
        name="retryable_fetch",
        preconditions={},
        effects={"fetched": True},
        cost=1,
    )

    call_count = 0

    def flaky_handler(state: WorldState) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Temporary network glitch")

    engine = GoapEngine(
        initial_actions=[failing_idempotent_action],
        storage_path=storage_file,
        max_heal_attempts=2,
    )
    engine.register_handler(
        "retryable_fetch", flaky_handler, is_idempotent=True
    )

    ws_kwargs: dict[str, Any] = {"fetched": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"fetched": True})

    result = engine.run(initial_state, goal)
    assert result.success is True
    assert result.final_state.get("fetched") is True
    assert len(engine.failed_attempts) == 1


def test_engine_max_heal_attempts_exceeded(tmp_path: Any) -> None:
    """Verifies engine error termination when max heal attempts exceeded."""
    storage_file = str(tmp_path / "max_attempts.json")

    mock_synthesizer = MagicMock(spec=LLMSynthesizer)
    mock_synthesizer.synthesize_bridge_action.side_effect = lambda g, a, f: (
        Action(
            name=f"impossible_{len(f)}",
            preconditions={"unfulfillable_predicate": True},
            effects=g.missing_predicate.copy(),
            cost=10,
        )
    )

    engine = GoapEngine(
        initial_actions=[],
        storage_path=storage_file,
        synthesizer=mock_synthesizer,
        max_heal_attempts=2,
    )

    initial_state = WorldState()
    goal = Goal(target_state={"impossible_goal": True})

    result = engine.run(initial_state, goal)
    assert result.success is False
    assert "Reached maximum heal attempts" in (result.error_message or "")
