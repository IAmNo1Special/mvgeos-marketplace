# heal-my-goap

Zero-token Goal-Oriented Action Planning (GOAP) and LLM-powered self-healing for MvgeOS.

When a tool is missing or a spell fails, this rune doesn't just report the error — it detects the gap at runtime, synthesizes a working Python action via OpenRouter, registers it as a new spell, and replans. Plans that already exist execute deterministically with zero tokens.

## Spells

| Spell | Description |
|-------|-------------|
| `goap_plan_and_execute` | Executes a multi-step deterministic action plan to reach a goal state. |
| `goap_sense_world` | Reads live system metrics into a WorldState dictionary. |
| `goap_synthesize_action` | Synthesizes a missing Python action script via OpenRouter. |

Failed or missing actions can also surface as dynamically registered spells, so the model sees the healed capability as a first-class tool on the next turn.

## How self-healing works

1. **Gap detection** — `after_spell_result` notices a failed or missing capability.
2. **Synthesis** — the gap analyzer asks OpenRouter for a Python action script that fills it.
3. **Registration** — the new action is registered as a spell (the rune widens the shared spell allowlist additively).
4. **Replan & execute** — the GOAP engine replans from the current world state and runs the plan with no further LLM calls.

## Configuration

Synthesis needs an OpenRouter API key, read from `~/.agents/.mvgeos/auth/openrouter.json` (`api_key` or `token`). Without a key, planning and sensing still work — only synthesis is unavailable.

## Hooks

`session_start`, `before_invocation`, `after_spell_result`.

## Dependencies

`heal_my_goap` (vendored in-tree at `runes/heal-my-goap/heal_my_goap/`).
