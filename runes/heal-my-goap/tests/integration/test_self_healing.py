from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("mvgeos_agent")
pytest.importorskip("heal_my_goap")

from mvgeos_runes.types import SigilHook
from mvgeos_agent.mvge import Mvge


@pytest.mark.asyncio
async def test_missing_read_tool_self_healing_execution(tmp_path: Path) -> None:
    """Verifies heal_my_goap synthesizes and executes code when tool missing."""
    readme_file = tmp_path / "README.md"
    readme_file.write_text(
        "Hello from heal_my_goap self-healing read!", encoding="utf-8"
    )

    # Pass marketplace runes directory so the agent can discover openrouter-realm rune
    marketplace_runes_dir = Path(__file__).resolve().parent.parent.parent.parent

    agent = Mvge(
        name="coding_mvge",
        api_key="test_mock_key",
        runes_paths=[str(marketplace_runes_dir)],
    )
    await agent.initialize()

    # Mock synthesizer to return a synthesized Action with code for reading file
    mock_action = MagicMock()
    mock_action.name = "synth_read_file"
    mock_action.code = (
        "read_content = 'README file contents read via heal_my_goap self-healing!'\n"
)
    mock_action.preconditions = {}
    mock_action.effects = {"file_read": True}

    assert agent._runner is not None
    target_spell = cast(Any, agent._runner._spells["goap_plan_and_execute"])
    with patch.object(
        target_spell._engine.synthesizer,
        "synthesize_bridge_action",
        return_value=mock_action,
    ):
        failed_payload = {
            "spell_name": "read",
            "spell_cast_id": "cast_read_001",
            "arguments": {"path": str(readme_file)},
            "result": {"error": "Spell 'read' not found or failed"},
        }
        healed_res = await agent._runner.emit_chain(
            SigilHook.AFTER_SPELL_RESULT,
            failed_payload,
        )

        assert healed_res is not None
        result_data = healed_res.get("result", {})
        assert result_data.get("status") == "spell_registered"
        assert result_data.get("registered_spell_name") == "synth_read_file"

        # Verify synthesized action registered on RuneRunner
        assert "synth_read_file" in agent._runner.get_active_spells()

        # Execute the registered synthesized spell to verify single execution
        synth_spell = next(
            s
            for s in agent._runner.get_all_registered_spells()
            if s.name == "synth_read_file"
        )
        synth_res = await synth_spell.execute(
            "cast_synth_001", {"path": str(readme_file)}
        )
        assert "read_content" in synth_res
        assert (
            synth_res["read_content"]
            == "README file contents read via heal_my_goap self-healing!"
        )

    await agent.close()
