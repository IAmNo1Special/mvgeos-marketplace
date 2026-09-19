---
title: Installation
description: Install heal-my-goap with uv or pip, configure OpenRouter API key, and verify your setup.
---

# Installation

Getting started with `heal-my-goap` in your Python environment.

!!! abstract "At a Glance"
    Install `heal-my-goap` via `uv` or `pip`, optionally configure an OpenRouter API key for LLM self-healing, and verify the installation works in under 30 seconds.

**Prerequisites**: Python `>=3.13,<3.14` and `uv` (recommended) or `pip`.

**What you'll learn**:

- How to install `heal-my-goap` with `uv` or `pip`
- How to configure the OpenRouter API key for self-healing
- How to verify your installation

---

## Installing with `uv`

The recommended package manager for `heal-my-goap` is [`uv`](https://github.com/astral-sh/uv) — fast, reliable, and consistent with the project's tooling.

```bash
uv add heal-my-goap
```

---

## Installing with `pip`

You can also install directly via standard PyPI:

```bash
pip install heal-my-goap
```

---

## Environment Setup (OpenRouter API)

For LLM self-healing capability, set your OpenRouter API key in an `.env` file or export it directly:

```env
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

`LLMSynthesizer` will automatically read `OPENROUTER_API_KEY` from your environment. If no key is provided, the engine falls back to wildcard action generation (no LLM calls).

---

## Verification

Verify your installation by running a quick Python check:

```python
import heal_my_goap

print(f"heal-my-goap version: {heal_my_goap.__version__}")
```

Expected output:
```
heal-my-goap version: 0.1.0
```

---

## Related Pages

- [Core Concepts](concepts.md)
- [Tool Registration Guide](../user-guide/tool-ingestion.md)
- [API Reference: GoapEngine](../api-reference/engine.md)