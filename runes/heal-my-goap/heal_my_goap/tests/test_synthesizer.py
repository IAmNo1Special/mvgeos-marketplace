"""Tests for LLM bridge action synthesizer."""

from unittest.mock import MagicMock, patch

import httpx

from heal_my_goap.models import Action, Gap
from heal_my_goap.synthesizer import LLMSynthesizer


def test_synthesizer_fallback_wildcard_action_when_no_api_key() -> None:
    """Verifies wildcard fallback action generated when API key missing."""
    synthesizer = LLMSynthesizer(api_key="")
    gap = Gap(
        missing_predicate={"file_downloaded": True},
        dependent_action_name="process_file",
    )

    with patch("heal_my_goap.synthesizer.os.getenv", return_value=""):
        synthesizer = LLMSynthesizer(api_key="")
        action = synthesizer.synthesize_bridge_action(gap, available_actions=[])
    assert action is not None
    assert action.effects.get("file_downloaded") is True
    assert float(action.cost) >= 10  # type: ignore[arg-type]
    assert "wildcard" in action.name or "synth" in action.name


def test_synthesizer_retry_exception_falls_back_to_wildcard() -> None:
    """Verifies synthesizer falls back to wildcard after repeated errors."""
    synthesizer = LLMSynthesizer(api_key="valid_key")
    gap = Gap(missing_predicate={"has_key": True})

    with (
        patch(
            "httpx.Client.post",
            side_effect=httpx.HTTPError("connection failed"),
        ),
        patch("time.sleep"),
    ):
        action = synthesizer.synthesize_bridge_action(gap, available_actions=[])
    assert "wildcard" in action.name


def test_synthesizer_mock_openrouter_response() -> None:
    """Verifies synthesis parsing with mocked OpenRouter API response."""
    gap = Gap(
        missing_predicate={"has_key": True},
        dependent_action_name="open_door",
    )
    synthesizer = LLMSynthesizer(api_key="mock_key")

    mock_llm_json = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"name": "find_key", "description": "Search room for '
                        'door key", "preconditions": {"in_room": true}, '
                        '"effects": {"has_key": true}, "cost": 10.0, '
                        '"is_idempotent": true, "code_payload": null}'
                    )
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_llm_json

    with patch("httpx.Client.post", return_value=mock_response):
        action = synthesizer.synthesize_bridge_action(gap, available_actions=[])
        assert action is not None
        assert action.effects == {"has_key": True}
        assert float(action.cost) >= 10  # type: ignore[arg-type]
        assert action.name.startswith("synth_find_key")


def test_synthesizer_synthesis_memory() -> None:
    """Verifies synthesis memory excludes failed actions from prompt."""
    synthesizer = LLMSynthesizer(api_key="mock_key")
    gap = Gap(missing_predicate={"has_key": True})
    failed_action = Action(
        name="synth_failed_action",
        preconditions={},
        effects={"has_key": True},
        cost=10,
    )

    mock_llm_json = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"name": "fetch_key_from_safe", "description": "Fetch'
                        ' key from safe", "preconditions": {"knows_code": '
                        'true}, "effects": {"has_key": true}, "cost": 10.0, '
                        '"is_idempotent": true, "code_payload": null}'
                    )
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_llm_json

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        action = synthesizer.synthesize_bridge_action(
            gap, available_actions=[], failed_attempts=[failed_action]
        )
        assert action is not None
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        prompt_content = call_kwargs["json"]["messages"][0]["content"]
        assert "synth_failed_action" in prompt_content
