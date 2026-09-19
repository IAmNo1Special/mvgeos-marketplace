---
title: LLM Self-Healing
description: Configure LLMSynthesizer, GapAnalyzer, and SandboxExecutor for autonomous gap resolution.
---

# OpenRouter LLM Self-Healing (`LLMSynthesizer`)

When an autonomous agent encounters an unexpected obstacle or broken pipeline link, `heal-my-goap` triggers automatic self-healing.

!!! abstract "At a Glance"
    Learn how the self-healing pipeline works: gap isolation → LLM micro-synthesis → validation → sandbox execution → persistence, and how to configure each component.

**Prerequisites**: [Installation](../getting-started/installation.md) complete.

**What you'll learn**:

- The gap isolation and LLM synthesis flow
- How to configure `LLMSynthesizer` with OpenRouter
- Sandbox safety guarantees for synthesized code
- How retry memory prevents repeated synthesis failures

---

## Gap Isolation & LLM Synthesis

1. **Gap Discovery**: When `goapauto`'s A* planner fails to find a valid plan, `GapAnalyzer` isolates the missing predicate (`Gap`).
2. **Micro-Prompt Synthesis**: `LLMSynthesizer` sends a focused prompt to OpenRouter requesting a single JSON `Action` schema that resolves `gap.missing_predicate`.
3. **Validation & Retry Memory**: If synthesis fails validation or code sandbox execution, the error is recorded in retry memory and sent back for self-correction.
4. **Action Storage**: Synthesized actions are stored locally in `.goap_actions.json`, preventing redundant LLM calls on future runs.

```mermaid
flowchart TD
    A[Plan Failed] --> B[GapAnalyzer.analyze_gap]
    B --> C[Gap(missing_predicate)]
    C --> D[LLMSynthesizer.synthesize_bridge_action]
    D --> E{Valid Action?}
    E -- No --> F[Record in Retry Memory]
    F --> D
    E -- Yes --> G[SandboxExecutor.run]
    G --> H{Executes Safely?}
    H -- No --> F
    H -- Yes --> I[ActionStorage.save]
    I --> J[Re-plan with New Action]
```

---

## Configuring `LLMSynthesizer`

```python
from heal_my_goap import LLMSynthesizer, GoapEngine

synthesizer = LLMSynthesizer(
    api_key="sk-or-v1-your-openrouter-key",
    model="anthropic/claude-3.5-sonnet",
    base_url="https://openrouter.ai/api/v1",
)

engine = GoapEngine(
    synthesizer=synthesizer,
    max_heal_attempts=3,
)
```

**Parameters**:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `api_key` | `str \| None` | `None` | OpenRouter API key (reads `OPENROUTER_API_KEY` env var if omitted) |
| `model` | `str \| None` | `None` | Model identifier (reads `OPENROUTER_MODEL` env var if omitted) |
| `base_url` | `str` | `"https://openrouter.ai/api/v1"` | OpenRouter API base URL |

If no API key is provided, `LLMSynthesizer` generates fallback wildcard actions (no LLM calls).

---

## Subprocess Sandbox Safety (`SandboxExecutor`)

Synthesized action code payloads execute inside `SandboxExecutor`:

- **Subprocess Isolation**: Runs in a separate Python process with explicit `process.terminate()` timeouts.
- **AST Imports Checking**: Blocks unsafe modules (`sys`, `os.system`, `subprocess`, `shutil`, `builtins.__import__`).
- **Hard Execution Timeout**: Kills runaway code loops automatically after 5.0 seconds.

```python
from heal_my_goap import SandboxExecutor

sandbox = SandboxExecutor(
    timeout=5.0,
    allowed_imports={"json", "pathlib", "datetime"},
)
```

---

## Retry Memory

`LLMSynthesizer` maintains a retry memory of failed synthesis attempts. Each failed attempt (validation error, sandbox execution error) is stored and included in the next synthesis prompt, enabling the LLM to self-correct.

```python
# Access retry memory (internal)
synthesizer._retry_memory  # List[dict] with gap, failed_action, error
```

Maximum retry attempts per gap are controlled by `GoapEngine(max_heal_attempts=3)`.

---

## Related Pages

- [Delta Observer Guide](delta-observer.md)
- [Core Concepts](../getting-started/concepts.md)
- [API Reference: Synthesizer & GapAnalyzer](../api-reference/synthesizer.md)
- [API Reference: GoapEngine](../api-reference/engine.md)
- [Example: Hospital Medic Robot](../examples/hospital-emergency.md)