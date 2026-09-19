# heal-my-goap 🩹🤖

[![Documentation](https://img.shields.io/badge/docs-live-brightgreen)](https://IAmNo1Special.github.io/heal_my_goap/)
[![PyPI](https://img.shields.io/pypi/v/heal-my-goap)](https://pypi.org/project/heal-my-goap/)
[![Python](https://img.shields.io/pypi/pyversions/heal-my-goap)](https://pypi.org/project/heal-my-goap/)

A production-ready Python library combining **zero-token symbolic Goal-Oriented Action Planning (GOAP)** via `goapauto` with **LLM-powered self-healing** via OpenRouter.

**Documentation**: https://IAmNo1Special.github.io/heal_my_goap/

`heal-my-goap` enables autonomous AI agents to plan and execute deterministic action sequences locally at zero API token cost. When unforeseen gaps or missing capabilities break an execution path, `heal-my-goap` isolates the unsatisfied state predicates, invokes an LLM to synthesize dynamic bridge actions, and persists learned actions locally for future zero-token reuse.

______________________________________________________________________

## Key Features

- ⚡ **Zero-Token A* Pathfinding*\*: Local, high-performance symbolic planning via `goapauto==0.3.0`.
- 🔍 **Frontier Gap Isolation**: `GapAnalyzer` traverses goal dependency graphs to pinpoint exact missing state predicates (`Gap`).
- 🤖 **Structured OpenRouter LLM Synthesis**: `LLMSynthesizer` auto-generates namespaced bridge actions with failure retry memory.
- 👁️ **Runtime State Delta Observer**: `DeltaObserver` observes real-world side effects (`after_state - before_state`) and formalizes GOAP action effects without token costs.
- 🛠️ **Ergonomic Tool Registration**: Convert Python callables and schema dicts into GOAP actions via `action_from_tool` and `GoapEngine(tools=[...])`.
- 💾 **Deduplicated Action Persistence**: `ActionStorage` maintains bounded `.goap_actions.json` storage with in-place action updates.
- 🛡️ **Subprocess Code Sandbox**: `SandboxExecutor` executes dynamic python code with AST safety checks, import blocks, and hard timeout isolation.
- 📊 **OS System Sensor Suite**: `SystemSensors` provides 28+ live system metrics (RAM, CPU, disk, process RSS, load averages, battery, network).

______________________________________________________________________

## Architecture & Workflow

```
                        ┌─────────────────────────────────┐
                        │      GoapEngine.run(state, goal)│
                        └────────────────┬────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │   GoapEngine Planning Loop      │
                        │  (Local A* Search via goapauto) │
                        └────────────────┬────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │                                           │
                   ▼ (Plan Found)                              ▼ (Plan Broken)
    ┌───────────────────────────────┐           ┌───────────────────────────────┐
    │ Take Snapshot 1: `before_state`│           │  GapAnalyzer Diagnostic       │
    └──────────────┬────────────────┘           │  Isolation (`Gap`)            │
                   │                            └──────────────┬────────────────┘
                   ▼                                           │
    ┌───────────────────────────────┐                          ▼
    │    Execute Action Step        │           ┌───────────────────────────────┐
    └──────────────┬────────────────┘           │  LLMSynthesizer (OpenRouter)  │
                   │                            │  Synthesizes Bridge Action    │
                   ▼                            └──────────────┬────────────────┘
    ┌───────────────────────────────┐                          │
    │ Take Snapshot 2: `after_state`│◄─────────────────────────┘
    └──────────────┬────────────────┘
                   │
                   ▼
    ┌───────────────────────────────┐
    │  DeltaObserver.compute_delta()│
    │  - Noise key filtering        │
    │  - Update action effects      │
    │  - Save to ActionStorage      │
    └───────────────────────────────┘
```

______________________________________________________________________

## Installation

Add `heal-my-goap` to your project using `uv`:

```bash
uv add heal-my-goap
```

______________________________________________________________________

## Quickstart

```python
from heal_my_goap import (
    Action,
    DeltaObserver,
    Goal,
    GoapEngine,
    WorldState,
    action_from_tool,
)


# 1. Define Python callable tools
def clean_temp_files() -> None:
    """Deletes temporary files from disk."""
    print("🧹 Cleaning temporary files...")


# Convert tool callable into a GOAP Action
clean_action = action_from_tool(
    name="clean_temp_files",
    description="Deletes temporary files from disk",
    parameters=clean_temp_files,
    effects={"temp_files_count": 0},
    cost=5.0,
)

# 2. Define baseline actions
open_door = Action(
    name="open_door",
    preconditions={"has_key": True},
    effects={"door_open": True},
    cost=1.0,
)

# 3. Initialize GoapEngine with tool ingestion and DeltaObserver
engine = GoapEngine(
    initial_actions=[open_door],
    tools=[clean_action],
    observer=DeltaObserver(),
    storage_path=".goap_actions.json",
    max_heal_attempts=3,
)

# 4. Execute planning and self-healing loop
initial_state = WorldState(has_key=False, door_open=False, temp_files_count=10)
target_goal = Goal(target_state={"door_open": True})

result = engine.run(initial_state, target_goal)

print(f"Success: {result.success}")
print(f"Executed Actions: {[a.name for a in result.executed_actions]}")
```

______________________________________________________________________

## Ingesting Tools (`action_from_tool`)

`heal-my-goap` allows registering agent tools directly from Python function signatures or parameter dictionaries:

```python
from heal_my_goap import action_from_tool, GoapEngine


def run_type_checker_mypy(code_written: bool, types_installed: bool) -> None:
    """Run mypy type checker across source files."""
    pass


# Auto-derives preconditions and effects from function annotations
mypy_tool = action_from_tool(
    name="run_type_checker_mypy",
    description="Run mypy type checker across source files",
    parameters=run_type_checker_mypy,
    effects={"type_check_clean": True},
    cost=4.0,
)

engine = GoapEngine(tools=[mypy_tool])
```

______________________________________________________________________

## Runtime State Delta Observer (`DeltaObserver`)

`DeltaObserver` automatically learns action side effects at runtime by comparing live environment snapshots (`after_state - before_state`) before and after action execution:

```python
from heal_my_goap import DeltaObserver, GoapEngine

# Custom noise filtering and merge policies
observer = DeltaObserver(
    ignored_keys={"uptime_minutes", "network_bytes_sent", "cpu_usage_pct"},
    numeric_tolerance=0.1,
    merge_strategy="update",  # Options: "update", "preserve_existing", "overwrite"
)

engine = GoapEngine(
    observer=observer,
    state_refresh_callback=lambda: get_live_environment_state(),
)
```

______________________________________________________________________

## Included Examples

Explore full-stack runnable scenarios in the `examples/` directory:

| Example Script | Description | Run Command |
| :--- | :--- | :--- |
| `examples/heal_my_goap/system_monitor.py` | Full system monitor using 28+ live OS metrics (`SystemSensors`) to diagnose and heal high RAM, broken network, low battery, and high swap scenarios. | `uv run examples/heal_my_goap/system_monitor.py` |
| `examples/heal_my_goap/coding_agent.py` | Modern autonomous AI coding agent lifecycle (Git branching, symbol search, ruff linting, mypy type checks, pytest suite, and self-healing missing type stubs or DB migrations). | `uv run examples/heal_my_goap/coding_agent.py` |
| `examples/heal_my_goap/hospital_emergency.py` | Hospital emergency robot medic triage with dynamic equipment failure self-healing. | `uv run examples/heal_my_goap/hospital_emergency.py` |

______________________________________________________________________

## Quality Assurance Invariants

All contributions must maintain 100% quality standards:

1. **Strict Type Checking**: `uv run --dev mypy src tests` (0 errors)
1. **Formatting & Linting**: `uvx ruff check .` & `uvx ruff format .` (0 violations)
1. **100% Test Coverage**: `uv run --dev pytest -v -s --cov=heal_my_goap --cov-report=term-missing --cov-fail-under=100 -W error` (100% pass, 100% coverage, 0 warnings)

______________________________________________________________________

## License

This project is licensed under the [MIT License](LICENSE).
