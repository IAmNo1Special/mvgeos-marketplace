# openrouter-realm

Official OpenRouter provider realm for MvgeOS.

## Overview

The `openrouter-realm` rune connects MvgeOS agents to the OpenRouter API gateway, enabling access to diverse foundation models with SSE streaming, tool calls, and reasoning parameter handling.

## Manifest Configuration

- Runtime: Python (>= 3.13)
- Entry point: `rune.py`
- Python dependencies: `httpx>=0.27`
- Registered Hooks: `before_provider_request`, `after_provider_response`

## Usage

When installed into `~/.agents/extensions/openrouter-realm`, MvgeOS automatically discovers and activates the rune. The rune registers:
- Realm factory for `openrouter`
- Provider configuration with base URL `https://openrouter.ai/api/v1`
