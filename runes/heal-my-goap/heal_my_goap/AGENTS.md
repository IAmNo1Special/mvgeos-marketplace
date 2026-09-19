______________________________________________________________________

## kind: agents

# AGENTS.md — `heal-my-goap` Project Guidelines

## Overview

`heal-my-goap` combines zero-token symbolic Goal-Oriented Action Planning (GOAP) via `goapauto` with LLM self-healing via OpenRouter.

## Architecture

- `src/heal_my_goap/models.py`: Domain schemas (`Gap`, `ExecutionResult`, `SynthesizedActionSchema`), UX helpers (`world_state_from_sensors`, `goal`, `action_from_tool`), & re-exports (`WorldState`, `Action`, `Goal`, `Planner`).
- `src/heal_my_goap/gap_analyzer.py`: Abstract interface (`BaseGapAnalyzer`) & diagnostic isolation (`GapAnalyzer`).
- `src/heal_my_goap/synthesizer.py`: Abstract interface (`BaseSynthesizer`) & OpenRouter LLM synthesizer (`LLMSynthesizer`).
- `src/heal_my_goap/storage.py`: Abstract interface (`BaseActionStorage`) & persistence (`ActionStorage`).
- `src/heal_my_goap/sandbox.py`: Abstract interface (`BaseSandboxExecutor`) & process sandbox (`SandboxExecutor`).
- `src/heal_my_goap/sensors.py`: OS metric sensors (`SystemSensors` with 28+ metrics).
- `src/heal_my_goap/observer.py`: Abstract interface (`BaseObserver`) & runtime state delta observer (`DeltaObserver`).
- `src/heal_my_goap/engine.py`: Orchestrator (`GoapEngine`) managing planning, state rollback, tool ingestion, state observation, and self-healing.

## Environment & Tooling

- **Package Manager**: Use `uv` exclusively (`uv sync`, `uv add --dev`).
- **Python**: `>=3.13,<3.14`. Command format: `uv run <command>` (omit `python`).
- **Formatting & Style**: 80-char line limit, Google Python Style Guide docstrings (`pydocstyle` convention `google`, Ruff rules `E,F,I,UP,D`). Use `uvx ruff check . --fix` and `uvx ruff format .`.

## Quality Assurance Invariants

Run and pass 100% before completing tasks:

1. `uv run --dev mypy src tests` (0 errors)
1. `uvx ruff check . --fix` & `uvx ruff format .` (0 violations)
1. `uv run --dev pytest -v -s --cov=heal_my_goap --cov-report=term-missing --cov-fail-under=100 -W error` (100% pass, 100% coverage, 0 warnings)

## Workflow & Safety Rules

- **Automated Changelogs**: Do not manually edit `CHANGELOG.md`. Generate via `uvx git-cliff --output CHANGELOG.md` driven by Conventional Commits (`feat:`, `fix:`, `docs:`, etc.).
- **Skill Promotion**: Confirm target skills explicitly with the user before promoting project skills to global `~/.agents/skills/`.
- **Google Docstrings**: Required for all modules, classes, and functions.
- **Module Imports**: Import packages/modules only (e.g. `import os.path`, `import heal_my_goap.models`).
- **Process Isolation**: Always use `multiprocessing.Process` with `process.terminate()` for dynamic code execution.
- **Atomic Commits**: Stage specific files manually using Conventional Commits (`<type>(<scope>): <message>`).
