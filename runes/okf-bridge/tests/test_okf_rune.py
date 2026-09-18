"""Unit and integration tests for okf-bridge rune lifecycle and spells."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mvgeos_runes.types import BeforeMvgeStartData, SigilHook, SpellDefinition
from mvgeos_runes_okf_bridge.rune import rune_factory


class MockRuneAPI:
    def __init__(self, cwd: Path) -> None:
        self._runner = MagicMock()
        self._runner.context = MagicMock()
        self._runner.context.cwd = str(cwd)
        self.hooks: dict[SigilHook, list] = {}
        self.spells: dict[str, SpellDefinition] = {}
        self.commands: dict[str, dict] = {}

    def on(self, hook: SigilHook, handler) -> None:
        self.hooks.setdefault(hook, []).append(handler)

    def register_spell(self, spell: SpellDefinition) -> None:
        self.spells[spell.name] = spell

    def register_command(self, name: str, description: str, handler) -> None:
        self.commands[name] = {"description": description, "handler": handler}


@pytest.mark.asyncio
async def test_okf_rune_lifecycle_and_spells(tmp_path: Path) -> None:
    okf_dir = tmp_path / ".okf"
    okf_dir.mkdir()

    (okf_dir / "index.md").write_text(
        '---\nokf_version: "0.2"\n---\n# Root\n', encoding="utf-8"
    )
    (okf_dir / "service-a.md").write_text(
        "---\n"
        "type: Service\n"
        "title: Service Alpha\n"
        "description: Primary service\n"
        "tags: [api]\n"
        "status: stable\n"
        "generated:\n"
        "  by: human:alice\n"
        "  at: '2026-09-01'\n"
        "---\n"
        "# Service Alpha\nBody content.\n",
        encoding="utf-8",
    )

    api = MockRuneAPI(cwd=tmp_path)
    rune_factory(api)

    # Verify registered hooks
    assert SigilHook.SESSION_START in api.hooks
    assert SigilHook.BEFORE_MVGE_START in api.hooks
    assert SigilHook.CONTEXT_TRANSFORM in api.hooks
    assert SigilHook.SESSION_SHUTDOWN in api.hooks

    # Verify registered spells
    assert "okf_search" in api.spells
    assert "okf_get" in api.spells
    assert "okf_validate" in api.spells

    # Verify registered commands
    assert "okf" in api.commands

    # 1. Test before_mvge_start
    before_hook = api.hooks[SigilHook.BEFORE_MVGE_START][0]
    data = BeforeMvgeStartData(
        base_prompt="System Prompt:",
        spell_names=[],
        config_dir=str(tmp_path),
        custom_prompt="",
        agent_name="test",
        cwd=str(tmp_path),
    )
    res_data = await before_hook(data)
    assert "<knowledge_catalog" in res_data.base_prompt
    assert "service-a" in res_data.base_prompt

    # 2. Test okf_search spell
    search_handler = api.spells["okf_search"]._handler
    search_json = await search_handler(arguments={"query": "Alpha"})
    search_results = json.loads(search_json)
    assert len(search_results) == 1
    assert search_results[0]["id"] == "service-a"

    # 3. Test okf_get spell
    get_handler = api.spells["okf_get"]._handler
    get_json = await get_handler(arguments={"concept_id": "service-a"})
    concept_data = json.loads(get_json)
    assert concept_data["id"] == "service-a"
    assert concept_data["type"] == "Service"
    assert concept_data["title"] == "Service Alpha"

    # Test okf_get missing
    missing_json = await get_handler(arguments={"concept_id": "nonexistent"})
    assert "not found" in missing_json

    # 4. Test okf_validate spell
    val_handler = api.spells["okf_validate"]._handler
    val_json = await val_handler(arguments={})
    val_data = json.loads(val_json)
    assert val_data["valid"] is True
    assert val_data["concepts_checked"] == 1

    # 5. Test /okf command
    cmd_handler = api.commands["okf"]["handler"]
    status_out = await cmd_handler("status")
    assert "OKF Knowledge Bundle Status" in status_out
    assert "Total Concepts:  1" in status_out

    search_out = await cmd_handler("search Alpha")
    assert "FOUND: 1 concepts" in search_out

    val_out = await cmd_handler("validate")
    assert "OK: Bundle is conformant" in val_out

    graph_out = await cmd_handler("graph")
    assert "OK: Interactive graph rendered" in graph_out
    assert (okf_dir / "viz.html").is_file()

    unknown_out = await cmd_handler("unknown_action")
    assert "Unknown okf command" in unknown_out

    # 6. Test context transform
    transform_hook = api.hooks[SigilHook.CONTEXT_TRANSFORM][0]
    inv_list = [{"role": "user", "content": "Hello"}]
    transformed = await transform_hook(inv_list)
    assert len(transformed) == 1
    assert "<knowledge_catalog" in transformed[0]["content"]

    # Non-list input
    assert await transform_hook("not-a-list") == "not-a-list"

    # 7. Test session shutdown
    shutdown_hook = api.hooks[SigilHook.SESSION_SHUTDOWN][0]
    await shutdown_hook()
