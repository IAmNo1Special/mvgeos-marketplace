# mcp-bridge

Official Model Context Protocol (MCP) bridge rune for MvgeOS.

Provides full MCP client capabilities using `mcp>=2.2.0`,
auto-discovers `~/.agents/mcp.json` and `<project>/.agents/mcp.json`,
and exposes MCP tools as `mcp_{server}_{tool}` spells.

## Installation

```bash
mvgeos rune install mcp-bridge
```

## Commands

- `/mcp list` - List connected servers and tools
- `/mcp test <server>` - Test server connection
- `mvgeos mcp list-servers` - CLI: list configured servers
- `mvgeos mcp test <server>` - CLI: test server connection
