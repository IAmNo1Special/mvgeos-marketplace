# OKF Bridge

Official Open Knowledge Format (OKF v0.2) and MADR 3.0 knowledge bridge for MvgeOS.

Discovers `.okf/` knowledge bundles in your workspace (plus the global `~/.agents/.okf/`), parses and lints them against the OKF v0.2 normative spec, and injects a compact `<knowledge_catalog>` into `<project_context>` at startup. MADR decision records in `docs/adr/` are parsed and linted too.

## Spells

| Spell | Description |
|-------|-------------|
| `okf_search` | Search the project Open Knowledge Format (`.okf/`) knowledge base by query, type, or tags. |
| `okf_get` | Retrieve detailed specifications, trust metadata, sources, and links for a specific OKF concept. |
| `okf_validate` | Validate an Open Knowledge Format bundle against the v0.2 specification (§11). |
| `adr_list` | List Architectural Decision Records (MADR 3.0) in the project. |
| `adr_get` | Retrieve detailed decision outcome, options, and consequences for an ADR by number. |

## Commands

- `mvgeos okf …` — search, inspect, and validate knowledge bundles (cp1252-safe ASCII output).
- `mvgeos adr …` — ADR subcommands.

## Hooks

`session_start`, `before_mvge_start`, `context_transform`, `session_shutdown`.

## Conformance

Strict OKF v0.2: §3 (bundle structure), §11 (conformance), §5 (trust / provenance / lifecycle), §10 (attestation), §13 (changes from v0.1).

## Dependencies

`pyyaml>=6.0`, `typer>=0.12`.
