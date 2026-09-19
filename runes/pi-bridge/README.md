# pi-bridge

Import [Pi](https://github.com/badlogic/pi) agent session logs (JSONL v3/v4) into MvgeOS Tomes so any Pi session can resume in MvgeOS.

This is a CLI-only rune: the importer is user-operated migration tooling invoked as `mvgeos pi-import <file>`, never a spell the agent calls mid-session. `rune_factory` is a no-op to satisfy the loader.

## Usage

```bash
mvgeos pi-import /path/to/pi-session.jsonl --dry-run
mvgeos pi-import /path/to/pi-session.jsonl
mvgeos --resume ~/.agents/sessions/<tome-id>.jsonl
```

## Layout

- `mvgeos_runes_pi_bridge/converter.py` — v3/v4 parsing, validation, Pi→Tome mapping, import orchestration.
- `mvgeos_runes_pi_bridge/cli.py` — Typer CLI (mounted as `pi-import`).
- `tests/` — fixtures (realistic v3/v4 sessions) + 35 tests, including a full roundtrip through the real `TomeHandle` and `MvgeTome.reconstruct_invocations`.

## Design rules

- Source of truth is Pi's source (`packages/agent/src/harness/session/jsonl/`), not its docs.
- Entry ids and parent chains preserved verbatim; dangling parents are a hard error.
- Every entry keeps the full original Pi JSON under `payload.pi_original`.
- The Tome header is written through the engine's own `TomeHandleFactory`, so the emitted format is always the engine's current version by construction.
- Import the original v3 file when both v3 and Pi's converted v4 copy exist (Pi's migration remints ids).
