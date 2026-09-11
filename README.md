# MvgeOS Rune Marketplace

Official extension marketplace catalog for MvgeOS runes.

## Overview

The MvgeOS Rune Marketplace hosts official and community-contributed extensions (runes) for the MvgeOS agent framework. Runes extend agent capabilities by registering custom realm factories, providers, spells, commands, shortcuts, and sigil lifecycle hooks.

## Available Runes

| Rune | Version | Description | Path |
| --- | --- | --- | --- |
| `openrouter-realm` | `0.1.0` | Official OpenRouter provider realm for MvgeOS | `runes/openrouter-realm` |

## Installation

Install runes directly using the MvgeOS CLI:

```powershell
mvgeos rune install openrouter-realm
```

Or install from a local path:

```powershell
mvgeos rune install ./runes/openrouter-realm
```

## Structure

```
mvgeos-marketplace/
|-- index.json
|-- README.md
`-- runes/
    `-- openrouter-realm/
        |-- manifest.json
        |-- rune.py
        |-- pyproject.toml
        |-- README.md
        `-- tests/
            `-- test_rune.py
```

## Contributing

1. Place your rune in `runes/<rune-name>/`.
2. Include a valid `manifest.json`, entry point, `pyproject.toml`, and unit tests.
3. Register your rune in `index.json`.
4. Submit a pull request.
