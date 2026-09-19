---
title: Tool Registration
description: Convert Python callables and JSON schemas into GOAP actions with action_from_tool and GoapEngine.
---

# Ergonomic Tool Registration

`heal-my-goap` makes converting Python callable tools and JSON schema dictionaries into GOAP actions seamless using `action_from_tool` and `GoapEngine(tools=[...])`.

!!! abstract "At a Glance"
    Learn how to register tools as GOAP actions using `action_from_tool` — from Python callables with type inference to dictionary schemas — and how to integrate them with `GoapEngine`.

**Prerequisites**: [Installation](../getting-started/installation.md) complete.

**What you'll learn**:

- How to convert Python callables into GOAP actions with automatic type inference
- Type inference rules for `bool`, `float`, `int`, `str` parameters
- How to pass dictionary schemas (OpenAPI/MCP compatible)
- How to register tools in `GoapEngine` via constructor or dynamic methods

---

## Registered Tool Conversion (`action_from_tool`)

### 1. From Python Callable Functions

Passing a typed Python function automatically inspects parameter annotations to derive preconditions and effects:

```python
from heal_my_goap import action_from_tool


def git_checkout_branch(branch_name: str) -> None:
    """Check out a new feature branch for development."""
    pass


action = action_from_tool(
    name="git_checkout_branch",
    description="Check out a new feature branch for development",
    parameters=git_checkout_branch,
    effects={"feature_branch_active": True},
    cost=2.0,
)

assert action.name == "git_checkout_branch"
assert action.description == "Check out a new feature branch for development"
```

### 2. Type Inference Rules

When preconditions/effects are omitted, `action_from_tool` infers them based on parameter type annotations:

| Parameter Type | Inferred Precondition | Inferred Effect |
| :--- | :--- | :--- |
| `bool` | `False` | `True` |
| `float` | `GreaterThan(50.0)` | `30.0` |
| `int` | `GreaterThan(0)` | `0` |
| `str` | `""` | `"done"` |

### 3. From Parameter Schema Dictionaries

You can also pass dictionary specifications matching OpenAPI or MCP tool definitions:

```python
action = action_from_tool(
    name="system_cleanup",
    description="Cleans temporary files and caches",
    parameters={"ram_usage_pct": "float", "temp_files_count": "int"},
    effects={"temp_files_count": 0},
    cost=5.0,
)
```

---

## Registering Tools in `GoapEngine`

Pass a list of tools directly to `GoapEngine.__init__` or use `register_tool()` / `register_tools()`:

```python
from heal_my_goap import GoapEngine

# Batch ingestion via constructor
engine = GoapEngine(tools=[git_checkout, mypy_tool, pytest_tool])

# Dynamic registration post-instantiation
engine.register_tool(linter_tool)
engine.register_tools([formatter_tool, test_tool])
```

---

## Related Pages

- [Core Concepts](../getting-started/concepts.md)
- [Delta Observer Guide](delta-observer.md)
- [API Reference: GoapEngine](../api-reference/engine.md)
- [API Reference: Models & Helpers](../api-reference/models.md)
- [Example: Coding Agent](../examples/coding-agent.md)