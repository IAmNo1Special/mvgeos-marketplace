"""Coding Agent Build Pipeline with heal-my-goap self-healing.

This scenario demonstrates an autonomous AI coding agent lifecycle (similar to
Claude Code, Antigravity, or Devin) using heal-my-goap:
- Tool ingestion (`action_from_tool`) mapping Python callables to GOAP actions
- Zero-token symbolic GOAP planning via goapauto A* search
- Runtime state delta tracking via `DeltaObserver`
- LLM self-healing via `LLMSynthesizer` when encountering unexpected obstacles
"""

from typing import Any

from heal_my_goap import (
    DeltaObserver,
    Goal,
    GoapEngine,
    WorldState,
    action_from_tool,
    goal,
)


def main() -> None:
    """Runs the autonomous coding AI agent self-healing demonstration."""
    print("\n" + "=" * 70)
    print("AUTONOMOUS AI CODING AGENT - REAL-WORLD GOAP SCENARIO")
    print("=" * 70)

    # State repository for simulated live environment
    live_state: dict[str, Any] = {
        "repo_initialized": True,
        "feature_branch_active": False,
        "context_gathered": False,
        "code_written": False,
        "lint_clean": False,
        "types_installed": True,
        "type_check_clean": False,
        "db_schema_migrated": True,
        "tests_passing": False,
        "changes_committed": False,
        "pr_created": False,
    }

    # Tool definitions with typed callables
    def git_checkout_branch(branch_name: str) -> None:
        """Check out a new feature branch for development."""
        live_state["feature_branch_active"] = True

    def search_codebase_symbols(query: str) -> None:
        """Search codebase AST and symbols to gather context."""
        live_state["context_gathered"] = True

    def apply_code_edits(file_path: str) -> None:
        """Apply targeted code edits to implement requested feature."""
        live_state["code_written"] = True

    def run_linter_ruff() -> None:
        """Run ruff linter to verify code formatting and style."""
        live_state["lint_clean"] = True

    def run_type_checker_mypy() -> None:
        """Run mypy type checker across source files."""
        if live_state.get("types_installed"):
            live_state["type_check_clean"] = True

    def run_pytest_suite() -> None:
        """Run pytest unit and integration test suite."""
        if live_state.get("db_schema_migrated"):
            live_state["tests_passing"] = True

    def fix_failing_tests() -> None:
        """Diagnose test failures and apply fix to pass pytest suite."""
        live_state["tests_passing"] = True

    def git_commit_changes(message: str) -> None:
        """Stage files and create atomic git commit."""
        live_state["changes_committed"] = True

    def create_pull_request(title: str) -> None:
        """Open a pull request for team review."""
        live_state["pr_created"] = True

    tools = [
        action_from_tool(
            name="git_checkout_branch",
            description="Check out a new feature branch for development",
            parameters=git_checkout_branch,
            effects={"feature_branch_active": True},
            cost=2.0,
        ),
        action_from_tool(
            name="search_codebase_symbols",
            description="Search codebase AST and symbols to gather context",
            parameters=search_codebase_symbols,
            effects={"context_gathered": True},
            cost=3.0,
        ),
        action_from_tool(
            name="apply_code_edits",
            description="Apply code edits to implement requested feature",
            parameters=apply_code_edits,
            effects={"code_written": True},
            cost=10.0,
        ),
        action_from_tool(
            name="run_linter_ruff",
            description="Run ruff linter to verify code formatting",
            parameters=run_linter_ruff,
            effects={"lint_clean": True},
            cost=2.0,
        ),
        action_from_tool(
            name="run_type_checker_mypy",
            description="Run mypy type checker across source files",
            parameters=run_type_checker_mypy,
            effects={"type_check_clean": True},
            cost=4.0,
        ),
        action_from_tool(
            name="run_pytest_suite",
            description="Run pytest unit and integration test suite",
            parameters=run_pytest_suite,
            effects={"tests_passing": True},
            cost=5.0,
        ),
        action_from_tool(
            name="fix_failing_tests",
            description="Diagnose test failures and apply fix for pytest",
            parameters=fix_failing_tests,
            effects={"tests_passing": True},
            cost=8.0,
        ),
        action_from_tool(
            name="git_commit_changes",
            description="Stage files and create atomic git commit",
            parameters=git_commit_changes,
            effects={"changes_committed": True},
            cost=3.0,
        ),
        action_from_tool(
            name="create_pull_request",
            description="Open a pull request for team review",
            parameters=create_pull_request,
            effects={"pr_created": True},
            cost=5.0,
        ),
    ]

    # Explicit preconditions for tools requiring prior pipeline stages
    tools[0].preconditions = {"repo_initialized": True}
    tools[1].preconditions = {"feature_branch_active": True}
    tools[2].preconditions = {"context_gathered": True}
    tools[3].preconditions = {"code_written": True}
    tools[4].preconditions = {"code_written": True, "types_installed": True}
    tools[5].preconditions = {
        "code_written": True,
        "type_check_clean": True,
        "db_schema_migrated": True,
    }
    tools[6].preconditions = {
        "code_written": True,
        "type_check_clean": True,
        "db_schema_migrated": True,
    }
    tools[7].preconditions = {
        "lint_clean": True,
        "type_check_clean": True,
        "tests_passing": True,
    }
    tools[8].preconditions = {"changes_committed": True}

    scenarios: list[tuple[str, dict[str, Any], Goal]] = [
        (
            "Happy Path Feature Lifecycle",
            {
                "repo_initialized": True,
                "feature_branch_active": False,
                "context_gathered": False,
                "code_written": False,
                "lint_clean": False,
                "types_installed": True,
                "type_check_clean": False,
                "db_schema_migrated": True,
                "tests_passing": False,
                "changes_committed": False,
                "pr_created": False,
            },
            goal(
                target_state={"pr_created": True},
                priority=1,
                name="Ship Feature PR",
            ),
        ),
        (
            "Missing Type Stubs Obstacle (Self-Healing Trigger)",
            {
                "repo_initialized": True,
                "feature_branch_active": False,
                "context_gathered": False,
                "code_written": False,
                "lint_clean": False,
                "types_installed": False,  # missing stub package
                "type_check_clean": False,
                "db_schema_migrated": True,
                "tests_passing": False,
                "changes_committed": False,
                "pr_created": False,
            },
            goal(
                target_state={"pr_created": True},
                priority=1,
                name="Fix Type Stubs & Ship PR",
            ),
        ),
        (
            "Missing Database Migration Obstacle (Self-Healing Trigger)",
            {
                "repo_initialized": True,
                "feature_branch_active": False,
                "context_gathered": False,
                "code_written": False,
                "lint_clean": False,
                "types_installed": True,
                "type_check_clean": False,
                "db_schema_migrated": False,  # schema out of sync
                "tests_passing": False,
                "changes_committed": False,
                "pr_created": False,
            },
            goal(
                target_state={"pr_created": True},
                priority=1,
                name="Migrate DB & Ship PR",
            ),
        ),
    ]

    observer = DeltaObserver()

    for i, (label, state_dict, target_goal) in enumerate(scenarios, 1):
        print(f"\n--- [{i}/{len(scenarios)}] {label} ---")
        live_state.clear()
        live_state.update(state_dict)

        def refresh_live_state() -> dict[str, Any]:
            return dict(live_state)

        engine = GoapEngine(
            tools=tools,
            observer=observer,
            state_refresh_callback=refresh_live_state,
            storage_path=".goap_coding_actions.json",
            max_heal_attempts=3,
        )

        init_ws = WorldState(**refresh_live_state())
        result = engine.run(init_ws, target_goal)

        print(f"Result: {'SUCCESS' if result.success else 'FAILURE'}")
        if result.executed_actions:
            print("Executed Action Sequence:")
            for step_idx, act in enumerate(result.executed_actions, 1):
                desc = getattr(act, "description", act.name)
                print(f"  {step_idx}. {act.name} (cost: {act.cost}) - {desc}")

        if result.healed_gaps:
            print("Healed Gaps (synthesized bridge actions):")
            for gap in result.healed_gaps:
                print(
                    f"  - Missing predicate: {gap.missing_predicate}"
                    f" (dependent: {gap.dependent_action_name})"
                )

        print(f"Final State PR Created: {result.final_state.get('pr_created')}")

    print("\n" + "=" * 70)
    print("SCENARIO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
