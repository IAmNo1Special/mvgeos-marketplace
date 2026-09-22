"""End-to-end: real engine payload + real emit_chain with steering-bridge.

Spec §5.8: chain ordering — both sections append in load (registration)
order; dict round-trip — an earlier rune returning a dict passes through
``emit_chain``/``create_sigil_data`` with the new optional fields intact.
Uses the real ``BeforeMvgeStartData``, ``create_sigil_data``, and
``RuneRunner.emit_chain`` — no simulations.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import pytest
from mvgeos_runes import SigilHook
from mvgeos_runes.rune_runner import RuneRunner
from mvgeos_runes.types import create_sigil_data
from selfmod_bridge_conftest import FakeApi, make_rune

_STEERING_BRIDGE_ROOT = Path(__file__).resolve().parent.parent.parent / "steering-bridge"


def _load_steering_rune() -> Any:
    """Instantiate the real steering-bridge rune (sibling marketplace rune).

    The steering root is added to ``sys.path`` only for the import itself —
    leaving it there would let steering's top-level ``rune.py`` shadow this
    rune's own ``rune`` module in later tests.
    """

    sys.path.insert(0, str(_STEERING_BRIDGE_ROOT))
    try:
        mod = importlib.import_module("mvgeos_runes_steering_bridge.rune")
    finally:
        sys.path.remove(str(_STEERING_BRIDGE_ROOT))
    return mod.rune_factory(FakeApi())


def _payload_dict(tmp_path: Path) -> dict[str, Any]:
    return {
        "base_prompt": "engine base",
        "spell_names": [],
        "config_dir": str(tmp_path / "agent-config"),
        "custom_prompt": "",
        "agent_name": "test-agent",
        "cwd": str(tmp_path),
        "runes_paths": [str(tmp_path / "runes")],
        "system_path": str(tmp_path / "agent-config" / "SYSTEM.md"),
        "spells_dir": str(tmp_path / "agent-config" / "spells"),
    }


@pytest.mark.asyncio
async def test_real_payload_section_lands_in_base_prompt(
    tmp_path: Path,
) -> None:
    """The real engine payload type round-trips through create_sigil_data
    and the hook appends the section to base_prompt."""
    rune, _api = make_rune(tmp_path)
    payload = create_sigil_data(SigilHook.BEFORE_MVGE_START, _payload_dict(tmp_path))
    assert type(payload).__name__ == "BeforeMvgeStartData"
    await rune._on_before_mvge_start(payload)
    assert payload.base_prompt.startswith("engine base")
    assert "Self-Modification & Customization:" in payload.base_prompt


@pytest.mark.asyncio
async def test_chain_order_with_steering_bridge(tmp_path: Path) -> None:
    """Both runes' sections append in handler registration order through
    the real RuneRunner.emit_chain."""
    (tmp_path / "AGENTS.md").write_text("# Workspace rules\n\nBe kind.\n", encoding="utf-8")
    selfmod_rune, _api = make_rune(tmp_path)
    steering_rune = _load_steering_rune()

    runner = RuneRunner()
    runner.register_handler(SigilHook.BEFORE_MVGE_START, steering_rune.on_before_mvge_start)
    runner.register_handler(SigilHook.BEFORE_MVGE_START, selfmod_rune._on_before_mvge_start)

    result = await runner.emit_chain(SigilHook.BEFORE_MVGE_START, _payload_dict(tmp_path))
    prompt = result.base_prompt
    assert "engine base" in prompt
    steering_idx = prompt.find("Steering")
    selfmod_idx = prompt.find("Self-Modification & Customization:")
    assert steering_idx != -1, "steering section missing"
    assert selfmod_idx != -1, "selfmod section missing"
    assert steering_idx < selfmod_idx, "sections out of registration order"


@pytest.mark.asyncio
async def test_chain_order_reversed_registration(tmp_path: Path) -> None:
    """Registration order decides append order, not rune identity."""
    (tmp_path / "AGENTS.md").write_text("# Workspace rules\n\nBe kind.\n", encoding="utf-8")
    selfmod_rune, _api = make_rune(tmp_path)
    steering_rune = _load_steering_rune()

    runner = RuneRunner()
    runner.register_handler(SigilHook.BEFORE_MVGE_START, selfmod_rune._on_before_mvge_start)
    runner.register_handler(SigilHook.BEFORE_MVGE_START, steering_rune.on_before_mvge_start)

    result = await runner.emit_chain(SigilHook.BEFORE_MVGE_START, _payload_dict(tmp_path))
    prompt = result.base_prompt
    selfmod_idx = prompt.find("Self-Modification & Customization:")
    steering_idx = prompt.find("Steering")
    assert selfmod_idx != -1 and steering_idx != -1
    assert selfmod_idx < steering_idx, "sections out of registration order"


@pytest.mark.asyncio
async def test_dict_round_trip_through_emit_chain(tmp_path: Path) -> None:
    """An earlier rune returning a plain dict passes through emit_chain
    un-normalized; the selfmod hook still reads it via dict fallback and
    appends its section."""
    selfmod_rune, _api = make_rune(tmp_path)

    async def earlier_rune(payload: Any) -> dict[str, Any]:
        assert isinstance(payload, dict) or hasattr(payload, "base_prompt")
        return _payload_dict(tmp_path)

    runner = RuneRunner()
    runner.register_handler(SigilHook.BEFORE_MVGE_START, earlier_rune)
    runner.register_handler(SigilHook.BEFORE_MVGE_START, selfmod_rune._on_before_mvge_start)

    result = await runner.emit_chain(SigilHook.BEFORE_MVGE_START, _payload_dict(tmp_path))
    # The earlier rune returned a dict, so the chain stayed a dict.
    assert isinstance(result, dict)
    assert "Self-Modification & Customization:" in result["base_prompt"]
