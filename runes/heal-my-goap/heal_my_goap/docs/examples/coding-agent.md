---
title: Autonomous Coding Agent
description: Full 9-tool AI software engineering pipeline with DeltaObserver and LLM self-healing.
---

# Autonomous AI Coding Agent Example

Demonstrates a modern software engineering agent pipeline (Git branching, symbol search, code edits, ruff linter, mypy type checker, pytest suite, git commits, PR creation) with `DeltaObserver` state tracking and LLM self-healing.

!!! abstract "At a Glance"
    **Scenario**: End-to-end autonomous feature development — branch, code, lint, type-check, test, commit, PR.
    **Key Features Used**: `DeltaObserver`, `action_from_tool`, `LLMSynthesizer`, `GapAnalyzer`, `SandboxExecutor`, retry memory, persistence.

---

## Scenario Setup

You want an AI agent that can take a feature request and autonomously execute the full development lifecycle: create a branch, explore the codebase, apply edits, run linters, type check, test, commit, and open a PR. When obstacles arise (missing type stubs, missing DB migrations), the agent self-heals by synthesizing bridge actions.

This example shows a 9-tool pipeline where `DeltaObserver` learns action effects from actual execution, and `LLMSynthesizer` generates recovery actions when gaps are encountered.

---

## Full Code

```python
from heal_my_goap import (
    DeltaObserver,
    GoapEngine,
    WorldState,
    action_from_tool,
    goal,
)


# 1. Define typed callable tools
def git_checkout_branch(branch_name: str) -> None:
    pass


def search_codebase_symbols(query: str) -> list[str]:
    pass


def apply_code_edits(files: list[str], changes: str) -> None:
    pass


def run_linter_ruff() -> None:
    pass


def run_type_checker_mypy() -> None:
    pass


def run_pytest_suite() -> None:
    pass


def git_commit_changes(message: str) -> None:
    pass


def create_pull_request(title: str, body: str) -> None:
    pass


def install_type_stubs(package: str) -> None:
    pass


tools = [
    action_from_tool(
        "git_checkout_branch", "Branch checkout", git_checkout_branch
    ),
    action_from_tool(
        "search_codebase_symbols", "Symbol search", search_codebase_symbols
    ),
    action_from_tool("apply_code_edits", "Apply edits", apply_code_edits),
    action_from_tool("run_linter_ruff", "Run ruff linter", run_linter_ruff),
    action_from_tool(
        "run_type_checker_mypy", "Run mypy type checker", run_type_checker_mypy
    ),
    action_from_tool("run_pytest_suite", "Run pytest suite", run_pytest_suite),
    action_from_tool("git_commit_changes", "Git commit", git_commit_changes),
    action_from_tool("create_pull_request", "Create PR", create_pull_request),
    action_from_tool(
        "install_type_stubs", "Install type stubs", install_type_stubs
    ),
]

# 2. Initialize GoapEngine with DeltaObserver
engine = GoapEngine(
    tools=tools,
    observer=DeltaObserver(),
    storage_path=".goap_coding_actions.json",
)

# 3. Execute scenario
result = engine.run(
    initial_state=WorldState(repo_initialized=True, pr_created=False),
    goal=goal(target_state={"pr_created": True}),
)

print(f"PR Created: {result.final_state.get('pr_created')}")
```

---

## Scenarios Demonstrated

1. **Happy Path Feature Lifecycle**: 8-step pipeline execution (`git_checkout_branch` → `search_codebase_symbols` → `apply_code_edits` → `run_linter_ruff` → `run_type_checker_mypy` → `run_pytest_suite` → `git_commit_changes` → `create_pull_request`).
2. **Missing Type Stubs Obstacle**: `types_installed=False` blocks `mypy`, prompting `GoapEngine` to synthesize `synth_install_type_stubs`.
3. **Missing DB Migration Obstacle**: `db_schema_migrated=False` blocks `pytest`, prompting `GoapEngine` self-healing to bridge the gap.

---

## Expected Output

```
PR Created: True
```

*When obstacles occur, you'll see self-healing in action:*
```
Gap detected: missing_predicate={'types_installed': True}
Synthesizing bridge action: synth_install_type_stubs
Executing synthesized action...
Type stubs installed. Re-planning...
PR Created: True
```

---

## Run Command

```bash
uv run examples/heal_my_goap/coding_agent.py
```

---

## Related Pages

- [Tool Registration Guide](../user-guide/tool-ingestion.md)
- [Delta Observer Guide](../user-guide/delta-observer.md)
- [Self-Healing Guide](../user-guide/self-healing.md)
- [API Reference: GoapEngine](../api-reference/engine.md)
- [API Reference: Models & Helpers](../api-reference/models.md)