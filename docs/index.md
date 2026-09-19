# MvgeOS Marketplace

The official extension marketplace for MvgeOS — runes, realms, and bridges that plug new capabilities into your agents.

## What is a rune?

A rune is a Python extension package for the MvgeOS engine. Each rune ships a `manifest.json` that declares its name, version, entry point, the lifecycle hooks it handles, the spells (tools) it provides, and the CLI commands it adds. The engine discovers runes through `index.json` at the repo root and loads them via the manifest's `entry_point` (`rune.py`), which exposes a `rune_factory` the engine calls with its rune API.

Standard rune layout:

```
runes/<name>/
  rune.py            # entry point (or a 5-line shim over the package below)
  manifest.json      # name, hooks, spells, commands, deps
  pyproject.toml     # Python packaging + third-party deps
  README.md
  tests/             # rune test suite (runs in marketplace CI)
  mvgeos_runes_<name>/  # the importable package (bridge-style runes)
```

## Catalog

| Rune | What it does |
|------|--------------|
| [ADR Bridge](runes/adr-bridge.md) | MADR 3.0 architectural decision records: scaffold, validate, and inject decisions into the prompt |
| [heal-my-goap](runes/heal-my-goap.md) | Zero-token GOAP planning with LLM-powered self-healing when tools fail or go missing |
| [MCP Bridge](runes/mcp-bridge.md) | Model Context Protocol client — mounts MCP servers as spells |
| [OKF Bridge](runes/okf-bridge.md) | Open Knowledge Format (v0.2) knowledge bundles + ADR parsing, injected into context |
| [OpenRouter Realm](runes/openrouter-realm.md) | Provider realm for the OpenRouter API gateway |
| [OpenTelemetry Bridge](runes/opentelemetry-bridge.md) | GenAI tracing across sessions, turns, provider calls, and spell casts |
| [Seeker](runes/seeker.md) | On-demand discovery of spells, skills, and MCP servers (the tool gateway) |
| [Session Title](runes/session-title.md) | Auto-generates session titles from conversation content |
| [Skills Bridge](runes/skills-bridge.md) | Agent Skills / Agent Plugins discovery with progressive disclosure |
| [Steering Bridge](runes/steering-bridge.md) | Repository steering via `AGENTS.md` layered into the system prompt |

## Installing runes

```bash
mvgeos rune install <name>
```

Python dependencies declared in each rune's `manifest.json` (`python_deps`) are installed with the rune. Runes that need the MvgeOS engine packages (`mvgeos-core`, `mvgeos-agent`, `mvgeos-runes`, …) get them from the engine itself.

## Concepts

**Spells** are the tools a rune gives the model. Some runes register a fixed set; others (MCP Bridge, heal-my-goap) register spells dynamically at runtime. Runes pin their own spell set with `set_active_spells` and can widen the shared allowlist as they discover new capabilities.

**Sigils** are lifecycle hooks — `session_start`, `before_mvge_start`, `context_transform`, `before_invocation`, `after_spell_result`, `turn_end`, and more. A rune subscribes to the hooks it needs in its manifest and the engine calls it at the right moment (injecting knowledge into the prompt, reacting to tool results, …).

**Commands** are CLI/chat commands a rune adds, e.g. `mvgeos adr new` or `/mcp list`.

## Building the docs

```bash
pip install -r docs/requirements.txt
mkdocs serve   # live preview at http://127.0.0.1:8000
mkdocs build   # static site in site/
```
