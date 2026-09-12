from __future__ import annotations

from pathlib import Path
from typing import Any
import pytest

from mvgeos_runes.manifest import load_manifest
from mvgeos_runes.loader import load_factory_from_manifest
from mvgeos_runes.rune_runner import RuneRunner
from mvgeos_runes.types import RuneLoad


@pytest.mark.asyncio
async def test_seeker_rune_load() -> None:
    rune_dir = Path(__file__).resolve().parent.parent
    manifest = load_manifest(rune_dir)
    assert manifest is not None
    assert manifest.name == "seeker"

    diags: list[Any] = []
    factory = load_factory_from_manifest(manifest, rune_dir, diagnostics=diags)
    assert factory is not None
    assert len(diags) == 0

    runner = RuneRunner()
    load = RuneLoad(manifest=manifest, factory=factory)
    await runner.load_rune_loads([load])

    spells = [s.name for s in runner.get_all_registered_spells()]
    assert "tool_search" in spells
    assert "skill_search" in spells
    assert "skill_execute" in spells
    assert "mcp_search" in spells
    assert runner.get_active_spells() == ["mcp_search", "skill_execute", "skill_search", "tool_search"]
