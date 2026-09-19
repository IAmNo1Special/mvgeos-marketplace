"""Antigravity Agent Benchmark with heal-my-goap self-healing.

This script benchmarks the Antigravity AI agent by modelling its real
coding-pipeline capabilities as GOAP actions backed by live subprocess
handlers. The ``GoapEngine`` plans and executes quality-gate checks against
the ``heal_my_goap`` codebase itself, measuring success, timing, and any
self-healing events triggered by predicate gaps the planner cannot bridge.

Scenarios
---------
1. **Happy Path QA** — verify ruff, mypy, pytest, and coverage pass in
   sequence. No healing expected.
2. **Changelog Gap (Self-Healing)** — same QA chain, plus a
   ``changelog_generated`` goal predicate for which *no action exists*.
   The gap analyzer fires, the LLM synthesizer creates a bridge action,
   and the engine resolves the goal symbolically.
3. **Full Commit Pipeline** — full QA chain plus a symbolic git dry-run
   commit as the delivery gate.

Design notes
------------
- All quality predicates start as ``False`` ("unverified") so the planner
  must execute real subprocess actions to reach ``True``.
- Each benchmark run uses an isolated ``tempfile`` storage path to prevent
  cross-scenario action contamination.
- Subprocess handlers use ``shell=True`` for Windows compatibility with
  ``uv`` / ``uvx`` on ``PATH``.
- ``state_refresh_callback`` returns only the seven domain predicates so
  ``DeltaObserver`` never sees noisy OS metric churn.
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PROJECT_DIR = str(Path(__file__).resolve().parent.parent.parent)

sys.path.insert(0, str(Path(PROJECT_DIR) / "src"))

from mvgeos_runes_heal_my_goap import (  # noqa: E402
    Action,
    DeltaObserver,
    ExecutionResult,
    GoapEngine,
    WorldState,
    goal,  # noqa: I001
)

# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def _run(cmd: str) -> tuple[int, str]:
    """Runs a shell command in the project directory.

    Args:
        cmd: Shell command string to execute.

    Returns:
        Tuple of (returncode, combined stdout+stderr).
    """
    proc = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
    )
    output = proc.stdout + proc.stderr
    return proc.returncode, output


# ---------------------------------------------------------------------------
# Action definitions — constructed directly (no action_from_tool inference)
# ---------------------------------------------------------------------------


def _make_actions() -> list[Action]:
    """Builds the baseline GOAP action list for the benchmark.

    Returns:
        List of ``Action`` instances with explicit preconditions and effects.
    """
    run_ruff_check = Action(
        name="run_ruff_check",
        preconditions={},
        effects={"ruff_clean": True},
        cost=2,
        description="Run ruff linter; sets ruff_clean=True when exit 0.",
    )
    apply_ruff_autofix = Action(
        name="apply_ruff_autofix",
        preconditions={"ruff_clean": False},
        effects={"ruff_clean": True},
        cost=5,
        description="Run ruff --fix + format; repairs lint violations.",
    )
    run_mypy = Action(
        name="run_mypy",
        preconditions={"ruff_clean": True},
        effects={"mypy_clean": True},
        cost=4,
        description="Run mypy strict type checking across src + tests.",
    )
    run_pytest = Action(
        name="run_pytest",
        preconditions={"mypy_clean": True},
        effects={"tests_passing": True},
        cost=5,
        description="Run pytest suite; sets tests_passing=True on exit 0.",
    )
    run_pytest_coverage = Action(
        name="run_pytest_coverage",
        preconditions={"tests_passing": True},
        effects={"coverage_100": True},
        cost=6,
        description="Run pytest --cov-fail-under=100; sets coverage_100=True.",
    )
    git_dry_run_commit = Action(
        name="git_dry_run_commit",
        preconditions={
            "ruff_clean": True,
            "mypy_clean": True,
            "tests_passing": True,
            "coverage_100": True,
        },
        effects={"changes_committed": True},
        cost=3,
        description="Symbolic git dry-run commit (no real git mutation).",
    )
    # Intentionally no action for changelog_generated — triggers healing.
    return [
        run_ruff_check,
        apply_ruff_autofix,
        run_mypy,
        run_pytest,
        run_pytest_coverage,
        git_dry_run_commit,
    ]


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


def _register_handlers(
    engine: GoapEngine,
    live_state: dict[str, Any],
    verbose: bool = True,
) -> None:
    """Registers live subprocess handlers onto a GoapEngine.

    Args:
        engine: The ``GoapEngine`` instance to register handlers on.
        live_state: Shared mutable dict updated by each handler.
        verbose: Whether to print handler output to stdout.
    """

    def _log(name: str, rc: int, out: str) -> None:
        if verbose:
            lines = out.strip().splitlines()
            preview = lines[-1] if lines else "(no output)"
            status = "✓" if rc == 0 else "✗"
            print(f"      [{status}] {name}: rc={rc}  {preview}")

    def handle_run_ruff_check(ws: WorldState) -> None:  # noqa: ARG001
        """Handler: runs ruff linter."""
        rc, out = _run("uvx ruff check .")
        live_state["ruff_clean"] = rc == 0
        _log("run_ruff_check", rc, out)
        if rc != 0:
            raise RuntimeError(f"ruff check failed (rc={rc})")

    def handle_apply_ruff_autofix(ws: WorldState) -> None:  # noqa: ARG001
        """Handler: runs ruff --fix then format."""
        rc, out = _run("uvx ruff check . --fix && uvx ruff format .")
        live_state["ruff_clean"] = rc == 0
        _log("apply_ruff_autofix", rc, out)
        if rc != 0:
            raise RuntimeError(f"ruff autofix failed (rc={rc})")

    def handle_run_mypy(ws: WorldState) -> None:  # noqa: ARG001
        """Handler: runs mypy strict."""
        rc, out = _run("uv run --dev mypy src tests")
        live_state["mypy_clean"] = rc == 0
        _log("run_mypy", rc, out)
        if rc != 0:
            raise RuntimeError(f"mypy failed (rc={rc})")

    def handle_run_pytest(ws: WorldState) -> None:  # noqa: ARG001
        """Handler: runs pytest (no coverage threshold)."""
        rc, out = _run("uv run --dev pytest -q -W error")
        live_state["tests_passing"] = rc == 0
        _log("run_pytest", rc, out)
        if rc != 0:
            raise RuntimeError(f"pytest failed (rc={rc})")

    def handle_run_pytest_coverage(ws: WorldState) -> None:  # noqa: ARG001
        """Handler: runs pytest with 100% coverage gate."""
        rc, out = _run(
            "uv run --dev pytest -q -W error"
            " --cov=heal_my_goap"
            " --cov-fail-under=100"
        )
        live_state["coverage_100"] = rc == 0
        _log("run_pytest_coverage", rc, out)
        if rc != 0:
            raise RuntimeError(f"coverage check failed (rc={rc})")

    def handle_git_dry_run_commit(ws: WorldState) -> None:  # noqa: ARG001
        """Handler: symbolic dry-run (no real git mutation)."""
        rc, out = _run("git status --short")
        live_state["changes_committed"] = True
        _log("git_dry_run_commit (symbolic)", rc, out)

    engine.register_handler("run_ruff_check", handle_run_ruff_check)
    engine.register_handler("apply_ruff_autofix", handle_apply_ruff_autofix)
    engine.register_handler("run_mypy", handle_run_mypy)
    engine.register_handler("run_pytest", handle_run_pytest)
    engine.register_handler("run_pytest_coverage", handle_run_pytest_coverage)
    engine.register_handler(
        "git_dry_run_commit", handle_git_dry_run_commit, is_idempotent=True
    )


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def _run_scenario(
    label: str,
    initial_state_dict: dict[str, Any],
    target_goal: Any,
    actions: list[Action],
    verbose: bool = True,
) -> dict[str, Any]:
    """Runs a single benchmark scenario and returns metrics.

    Args:
        label: Human-readable scenario label.
        initial_state_dict: Starting predicate dict (all predicates False).
        target_goal: GOAP ``Goal`` instance.
        actions: Baseline ``Action`` list.
        verbose: Whether to print step-by-step output.

    Returns:
        Dict of benchmark metrics for this scenario.
    """
    live_state: dict[str, Any] = dict(initial_state_dict)

    def refresh() -> dict[str, Any]:
        return dict(live_state)

    # Isolated per-run storage to prevent cross-scenario contamination
    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=True, dir=PROJECT_DIR
    ) as tmp:
        storage_path = tmp.name

    engine = GoapEngine(
        initial_actions=actions,
        storage_path=storage_path,
        observer=DeltaObserver(),
        state_refresh_callback=refresh,
        max_heal_attempts=3,
    )
    _register_handlers(engine, live_state, verbose=verbose)

    init_ws = WorldState(**initial_state_dict)

    t0 = time.perf_counter()
    result: ExecutionResult = engine.run(init_ws, target_goal)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    return {
        "label": label,
        "success": result.success,
        "elapsed_ms": elapsed_ms,
        "executed_count": len(result.executed_actions),
        "executed_names": [a.name for a in result.executed_actions],
        "healed_count": len(result.healed_gaps),
        "healed_predicates": [
            list(g.missing_predicate.keys()) for g in result.healed_gaps
        ],
        "error_message": result.error_message,
        "final_state": result.final_state.to_dict(),
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _write_report(metrics: list[dict[str, Any]], report_path: str) -> None:
    """Writes a structured markdown benchmark report.

    Args:
        metrics: List of per-scenario metric dicts.
        report_path: Absolute path to write the markdown file.
    """
    lines: list[str] = [
        "# Antigravity Agent — Heal-My-GOAP Benchmark Report\n",
        f"*Generated at {time.strftime('%Y-%m-%dT%H:%M:%S')}*\n",
        "---\n",
        "## Results Summary\n",
        "| # | Scenario | Result | Time (ms) | Actions | Healed Gaps |",
        "|---|----------|--------|-----------|---------|-------------|",
    ]

    for i, m in enumerate(metrics, 1):
        icon = "✅" if m["success"] else "❌"
        lines.append(
            f"| {i} | {m['label']} | {icon} "
            f"{'SUCCESS' if m['success'] else 'FAILURE'} "
            f"| {m['elapsed_ms']} ms "
            f"| {m['executed_count']} "
            f"| {m['healed_count']} |"
        )

    lines += ["\n---\n", "## Scenario Details\n"]

    for i, m in enumerate(metrics, 1):
        icon = "✅" if m["success"] else "❌"
        lines += [
            f"### {i}. {m['label']} — {icon}"
            f" {'SUCCESS' if m['success'] else 'FAILURE'}\n",
            f"- **Elapsed**: {m['elapsed_ms']} ms",
            f"- **Actions Executed** ({m['executed_count']}):",
        ]
        for j, name in enumerate(m["executed_names"], 1):
            lines.append(f"  {j}. `{name}`")

        if m["healed_count"]:
            lines.append(
                f"- **Healed Gaps** ({m['healed_count']}) — "
                "LLM synthesizer invoked:"
            )
            for preds in m["healed_predicates"]:
                lines.append(f"  - Missing predicate(s): `{preds}`")
        else:
            lines.append("- **Healed Gaps**: none (happy path)")

        if m["error_message"]:
            lines.append(f"- **Error**: {m['error_message']}")

        lines.append("")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n  📄  Report written to: {report_path}")


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

INITIAL_STATE: dict[str, Any] = {
    "ruff_clean": False,
    "mypy_clean": False,
    "tests_passing": False,
    "coverage_100": False,
    "changelog_generated": False,
    "changes_committed": False,
}

SCENARIOS: list[tuple[str, dict[str, Any], Any]] = [
    (
        "Happy Path QA",
        {
            k: v
            for k, v in INITIAL_STATE.items()
            if k
            in {"ruff_clean", "mypy_clean", "tests_passing", "coverage_100"}
        },
        goal(
            target_state={
                "ruff_clean": True,
                "mypy_clean": True,
                "tests_passing": True,
                "coverage_100": True,
            },
            priority=1,
            name="All Quality Gates Pass",
        ),
    ),
    (
        "Changelog Gap (Self-Healing)",
        {
            k: v
            for k, v in INITIAL_STATE.items()
            if k
            in {
                "ruff_clean",
                "mypy_clean",
                "tests_passing",
                "coverage_100",
                "changelog_generated",
            }
        },
        goal(
            target_state={
                "ruff_clean": True,
                "mypy_clean": True,
                "tests_passing": True,
                "coverage_100": True,
                "changelog_generated": True,
            },
            priority=1,
            name="QA + Changelog Generated",
        ),
    ),
    (
        "Full Commit Pipeline",
        dict(INITIAL_STATE),
        goal(
            target_state={
                "ruff_clean": True,
                "mypy_clean": True,
                "tests_passing": True,
                "coverage_100": True,
                "changes_committed": True,
            },
            priority=1,
            name="Ship-Ready Commit",
        ),
    ),
]


def main() -> None:
    """Runs all benchmark scenarios and writes the markdown report."""
    print("\n" + "=" * 70)
    print("ANTIGRAVITY AGENT — HEAL-MY-GOAP BENCHMARK")
    print(f"Project: {PROJECT_DIR}")
    print("=" * 70)

    actions = _make_actions()
    all_metrics: list[dict[str, Any]] = []

    for i, (label, state_dict, target_goal) in enumerate(SCENARIOS, 1):
        print(f"\n{'─' * 70}")
        print(f"  [{i}/{len(SCENARIOS)}]  {label}")
        print(f"{'─' * 70}")
        print(f"  Initial predicates : {list(state_dict.keys())}")
        print(f"  Goal predicates    : {list(target_goal.target_state.keys())}")
        print()

        metrics = _run_scenario(
            label=label,
            initial_state_dict=state_dict,
            target_goal=target_goal,
            actions=actions,
            verbose=True,
        )
        all_metrics.append(metrics)

        icon = "✅ SUCCESS" if metrics["success"] else "❌ FAILURE"
        print(f"\n  → {icon}  ({metrics['elapsed_ms']} ms)")
        print(f"  → Actions executed : {metrics['executed_names']}")
        if metrics["healed_count"]:
            print(
                f"  → Self-healing     : {metrics['healed_count']} gap(s) "
                f"healed — {metrics['healed_predicates']}"
            )

    # Write report
    report_path = str(
        Path(PROJECT_DIR) / "examples" / "mvgeos_runes_heal_my_goap" / "benchmark_results.md"
    )
    _write_report(all_metrics, report_path)

    print("\n" + "=" * 70)
    passed = sum(1 for m in all_metrics if m["success"])
    print(f"BENCHMARK COMPLETE — {passed}/{len(all_metrics)} scenarios passed")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
