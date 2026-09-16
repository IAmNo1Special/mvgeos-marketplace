from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from mvgeos_runes.loader import load_factory_from_manifest
from mvgeos_runes.manifest import load_manifest
from mvgeos_runes.types import SigilHook


def _load_factory() -> Any:
    rune_dir = Path(__file__).resolve().parent.parent
    manifest = load_manifest(rune_dir)
    assert manifest is not None
    diags: list[Any] = []
    factory = load_factory_from_manifest(manifest, rune_dir, diagnostics=diags)
    assert factory is not None
    assert len(diags) == 0
    return factory


@pytest.mark.asyncio
async def test_heal_pins_own_spells_and_widens_allowlist() -> None:
    factory = _load_factory()
    api = MagicMock()
    api.get_global_spell_allowlist.return_value = ["tool_search"]
    factory(api)

    handlers = {
        call.args[0]: call.args[1] for call in api.on.call_args_list
    }
    assert SigilHook.SESSION_START in handlers
    assert SigilHook.BEFORE_INVOCATION in handlers

    session_handlers = [
        call.args[1]
        for call in api.on.call_args_list
        if call.args[0] == SigilHook.SESSION_START
    ]
    for handler in session_handlers:
        result = handler({"session_name": "s"})
        if inspect.isawaitable(result):
            await result

    # Own pin: exactly heal's 3, never a union copy.
    api.set_active_spells.assert_called_with(
        ["goap_plan_and_execute", "goap_sense_world", "goap_synthesize_action"]
    )
    # Global widen: called (SESSION_START + BEFORE_INVOCATION paths).
    widened: list[str] = []
    for call in api.widen_global_allowlist.call_args_list:
        widened.extend(call.args[0])
    assert set(widened) >= {
        "goap_plan_and_execute",
        "goap_sense_world",
        "goap_synthesize_action",
    }
