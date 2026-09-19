# Session Title

Auto-generates session titles from conversation content — with an instant fallback and an optional LLM upgrade.

Nobody names their sessions by hand. This rune watches the conversation and produces a short, readable title automatically.

## How it works

1. **Instant fallback** — after the first user message, it derives a title from the message text (up to 8 words / 96 bytes), normalized and stripped of control characters. Zero latency, zero tokens.
2. **LLM upgrade** — a later turn can ask the model for a better title (max 120 bytes), replacing the fallback.
3. **User pins win** — a manually set title is never overwritten; revisions are tracked per session.

## Hooks

`session_start`, `input`, `turn_end`, `agent_end`, `session_shutdown`.

## Dependencies

None — stdlib only.
