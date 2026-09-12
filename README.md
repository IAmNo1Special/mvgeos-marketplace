# MvgeOS Marketplace

Official marketplace catalog for MvgeOS Runes (extensions) and Mvges (agents).

## Overview

The MvgeOS Marketplace hosts official and community-contributed extensions (runes) and concrete agent packages (mvges) for MvgeOS.

## Available Mvges (Agents)

| Mvge | Version | Description | Path |
| --- | --- | --- | --- |
| `coding_mvge` | `0.2.6` | Official coding agent with built-in development spells | `mvges/coding_mvge` |

Install via MvgeOS CLI:
```powershell
mvgeos mvge install coding_mvge
```

## Available Runes (Extensions)

| Rune | Version | Description | Path |
| --- | --- | --- | --- |
| `openrouter-realm` | `0.1.0` | Official OpenRouter provider realm for MvgeOS | `runes/openrouter-realm` |
| `heal-my-goap` | `0.1.0` | Zero-token GOAP planning & LLM self-healing Rune | `runes/heal-my-goap` |
| `seeker` | `0.1.0` | Seeker Protocol - DCI-based discovery | `runes/seeker` |

Install via MvgeOS CLI:
```powershell
mvgeos rune install openrouter-realm
```

## Structure

```
mvgeos-marketplace/
|-- index.json
|-- README.md
|-- mvges/
|   `-- coding_mvge/
|       |-- manifest.json
|       |-- agent.md
|       |-- mvge.py
|       |-- spells/
|       |-- system_prompt/
|       `-- runes/
`-- runes/
    |-- openrouter-realm/
    |-- heal-my-goap/
    `-- seeker/
```
