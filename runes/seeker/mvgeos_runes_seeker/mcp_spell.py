from __future__ import annotations
from pathlib import Path
from typing import Any

from mvgeos_core.spells import MvgeSpell, SpellExecutionMode
from mvgeos_provider.registry import RealmRegistry

from .discovery import MCPConfigDiscovery, MCPServerInfo
from .mcp_selector import MCPNLTSelector
from .connector import MCPConnector, MCPToolSpell, MCPTransportError


class MCPSearchSpell(MvgeSpell):
    """
    Discover MCP servers and register their tools as MCPToolSpell instances.
    """

    def __init__(
        self,
        provider_registry: RealmRegistry,
        rune_runner: Any | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._cfg = config or {}
        super().__init__(
            name="mcp_search",
            description="Find and connect to MCP servers providing external tools",
            parameters={
                "type": "object",
                "properties": {
                    "capability": {
                        "type": "string",
                        "description": "What capability you need",
                    },
                    "domain": {"type": "string", "description": "Domain hint"},
                    "auto_connect": {"type": "boolean", "default": True},
                    "max_results": {"type": "integer", "default": 3},
                },
                "required": ["capability"],
            },
            execution_mode=SpellExecutionMode.SEQUENTIAL,
        )
        self._provider_registry = provider_registry
        self._rune_runner = rune_runner
        self._connections: dict[str, MCPConnector] = {}
        search_roots = self._cfg.get("search_roots", None)
        if search_roots is not None:
            search_roots = [Path(r) for r in search_roots]
        self._discovery = MCPConfigDiscovery(search_roots=search_roots)
        # Read timeout overrides from config (keys match config schema section 8)
        timeout_cfg = self._cfg.get("timeout", {})
        self._timeout_overrides: dict[str, int] = {}
        if isinstance(timeout_cfg, dict):
            self._timeout_overrides = {k: int(v) for k, v in timeout_cfg.items()}

    async def execute(
        self,
        spell_cast_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        capability = params["capability"]
        max_results = params.get("max_results", 3)
        auto_connect = params.get("auto_connect", True)
        max_connections = self._cfg.get("max_connections", 5)

        # Check global connection limit
        if len(self._connections) >= max_connections:
            return {
                "serversFound": 0,
                "servers": [],
                "error": f"maximum {max_connections} MCP connections reached",
            }

        try:
            configs = await self._discovery.search(capability)
        except MCPTransportError as e:
            return {"serversFound": 0, "servers": [], "error": str(e)}

        selector = MCPNLTSelector(
            self._provider_registry,
            model_id=self._cfg.get("nlt_model", "openrouter/free"),
        )
        try:
            selected = await selector.select(capability, configs, max_results)
        except Exception as e:
            return {"serversFound": 0, "servers": [], "error": str(e)}

        results = []
        for server_info in selected:
            if auto_connect:
                try:
                    tools = await self._connect_server(server_info)
                    results.append(
                        {
                            "server": server_info.name,
                            "toolsRegistered": [t.name for t in tools],
                            "status": "connected",
                        }
                    )
                except (MCPTransportError, TimeoutError) as e:
                    results.append(
                        {
                            "server": server_info.name,
                            "status": "failed",
                            "error": str(e),
                        }
                    )
            else:
                results.append(
                    {
                        "server": server_info.name,
                        "description": server_info.description,
                        "status": "discovered",
                    }
                )

        return {"serversFound": len(results), "servers": results, "error": None}

    async def _connect_server(self, info: MCPServerInfo) -> list[SpellDefinition]:
        if info.name in self._connections:
            connector = self._connections[info.name]
            return connector.tool_spells

        # Build connector but do NOT store until fully initialized
        connector = MCPConnector(
            info, self._rune_runner, timeout_overrides=self._timeout_overrides
        )
        try:
            await connector.connect()
            tool_spells = await connector.register_all_capabilities()
        except Exception:
            await connector.close()
            raise

        # Only store after full initialization succeeds
        self._connections[info.name] = connector
        return tool_spells
