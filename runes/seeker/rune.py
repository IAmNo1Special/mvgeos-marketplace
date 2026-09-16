from __future__ import annotations

from pathlib import Path
from typing import Any

from mvgeos_provider.registry import RealmRegistry
from mvgeos_runes.rune_api import RuneAPI
from mvgeos_runes.types import SigilHook
from mvgeos_runes_seeker.mcp_spell import MCPSearchSpell
from mvgeos_runes_seeker.skill_execute import SkillExecuteSpell
from mvgeos_runes_seeker.skill_spell import SkillSearchSpell
from mvgeos_runes_seeker.spell import ToolSearchSpell


def rune_factory(api: RuneAPI) -> None:
    provider_registry = RealmRegistry()
    runner = api._runner
    agent_name = getattr(runner.context, "agent_name", "coding-agent")

    # Get API key from agent context
    api_key = getattr(runner.context, "api_key", "")

    # Tool Search Spell
    tool_search = ToolSearchSpell(
        provider_registry=provider_registry,
        agent_name=agent_name,
        nlt_api_key=api_key,
        rune_api=api,
    )

    # Skill Search Spell
    skill_search = SkillSearchSpell(
        provider_registry=provider_registry,
        agent_name=agent_name,
        nlt_api_key=api_key,
    )

    # Skill Execute Spell
    skill_execute = SkillExecuteSpell(
        provider_registry=provider_registry,
        agent_name=agent_name,
        nlt_api_key=api_key,
    )

    # MCP Search Spell
    mcp_search = MCPSearchSpell(
        provider_registry=provider_registry,
        rune_runner=runner,
        rune_api=api,
        config={
            "search_roots": [Path(".agents/.mvgeos/extensions")],
            "max_connections": 5,
            "nlt_model": "openrouter/free",
            "nlt_api_key": api_key,
            "timeout": {
                "init": 15,
                "stdio": 30,
                "http": 30,
                "tool_list": 60,
            },
        },
    )

    api.register_spell(tool_search)
    api.register_spell(skill_search)
    api.register_spell(skill_execute)
    api.register_spell(mcp_search)

    # Register shutdown handler to clean up MCP connections

    async def close_mcp_connections(data: dict[str, Any]) -> None:
        if hasattr(mcp_search, "_connections"):
            for conn in mcp_search._connections.values():
                await conn.close()

    api.on(SigilHook.SESSION_SHUTDOWN, close_mcp_connections)

    # Seeker hides-all mode. The engine seeds the per-rune active set with
    # every registered rune spell by default; we narrow our own entry here
    # so only the meta-tools appear initially. The engine additionally
    # narrows the engine-owned global allowlist (checked by
    # Mvge._build_spells for builtins + all runes) to this rune's spells
    # because the manifest declares "spell_gateway": true -- so the model is
    # only aware of Seeker meta-tools and surfaces everything else through
    # discovery. Discovered tools widen the allowlist again via
    # RuneAPI.widen_global_allowlist (additive-only; runes can never replace
    # or drop the engine's filter).
    # Mirrors upstream Pi's setActiveTools called from a session_start hook.
    meta_spells = ["tool_search", "skill_search", "skill_execute", "mcp_search"]

    def activate_seeker_meta_tools(_data: dict[str, Any]) -> None:
        api.set_active_spells(meta_spells)

    api.on(SigilHook.SESSION_START, activate_seeker_meta_tools)
