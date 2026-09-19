# Seeker

Seeker Protocol — DCI-based (Direct Corpus Interaction) on-demand capability discovery for MvgeOS.

Instead of stuffing every tool description into the prompt, Seeker keeps the model's context lean and lets it *search* for capabilities when it needs them: ripgrep over the spell corpus, skill packages without vector databases or embeddings, and MCP servers mounted on demand.

## Spells

| Spell | Description |
|-------|-------------|
| `tool_search` | Fast ripgrep discovery over available spells, with an exact-match fast path. |
| `skill_search` | Search agent skills without vector databases or embeddings. |
| `skill_execute` | Execute scripts contained in discovered skill packages. |
| `mcp_search` | Discover, connect, and mount Model Context Protocol (MCP) servers on demand. |

## Spell gateway

Seeker declares `"spell_gateway": true` in its manifest, which makes it the engine's tool gateway: the model's spell view is narrowed to Seeker's registered spells, so discovery always goes through the protocol instead of around it. (Explicitly configured allowlists are never overridden; if several runes claim the gateway, the first one wins.)

## Hooks

`session_start`, `session_shutdown`.

## Dependencies

`aiohttp`. Requires the `ripgrep` (`rg`) binary on `PATH`.
