"""Tests for the heal-my-goap spell allowlist pinning."""

from __future__ import annotations

import inspect
import sys
import types
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from mvgeos_runes.loader import load_factory_from_manifest
from mvgeos_runes.manifest import load_manifest
from mvgeos_runes.types import SigilHook

# Stub the in-tree engine package so this test exercises hook registration
# and spell pinning/widening without importing goapauto or the real engine.
_HEAL_STUBS: dict[str, list[str]] = {
    "mvgeos_runes_heal_my_goap": [],
    "mvgeos_runes_heal_my_goap.engine": ["GoapEngine"],
    "mvgeos_runes_heal_my_goap.models": [
        "Action",
        "Gap",
        "Goal",
        "WorldState",
        "goal",
        "world_state_from_sensors",
    ],
    "mvgeos_runes_heal_my_goap.sensors": ["SystemSensors"],
}


@pytest.fixture(autouse=True)
def _stub_engine_package(monkeypatch: pytest.MonkeyPatch) -> None:
    pkg = types.ModuleType("mvgeos_runes_heal_my_goap")
    pkg.__path__ = []  # type: ignore[attr-defined]
    pkg.__spec__ = ModuleSpec(
        "mvgeos_runes_heal_my_goap", loader=None, is_package=True
    )
    monkeypatch.setitem(sys.modules, "mvgeos_runes_heal_my_goap", pkg)
    for mod_name, attrs in _HEAL_STUBS.items():
        if mod_name == "mvgeos_runes_heal_my_goap":
            continue
        mod = types.ModuleType(mod_name)
        mod.__spec__ = ModuleSpec(mod_name, loader=None)
        for attr in attrs:
            setattr(mod, attr, MagicMock(name=attr))
        monkeypatch.setitem(sys.modules, mod_name, mod)
        setattr(pkg, mod_name.split(".")[-1], mod)


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
    """The rune pins its own spells and widens the allowlist additively."""
    factory = _load_factory()
    api = MagicMock()
    api.get_global_spell_allowlist.return_value = ["tool_search"]
    factory(api)

    handlers = {call.args[0]: call.args[1] for call in api.on.call_args_list}
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
