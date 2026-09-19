# Antigravity Agent — Heal-My-GOAP Benchmark Report

*Generated at 2026-08-02T13:03:03*

---

## Results Summary

| # | Scenario | Result | Time (ms) | Actions | Healed Gaps |
|---|----------|--------|-----------|---------|-------------|
| 1 | Happy Path QA | ✅ SUCCESS | 18935 ms | 4 | 0 |
| 2 | Changelog Gap (Self-Healing) | ✅ SUCCESS | 16036 ms | 5 | 1 |
| 3 | Full Commit Pipeline | ✅ SUCCESS | 14732 ms | 5 | 0 |

---

## Scenario Details

### 1. Happy Path QA — ✅ SUCCESS

- **Elapsed**: 18935 ms
- **Actions Executed** (4):
  1. `run_ruff_check`
  2. `run_mypy`
  3. `run_pytest`
  4. `run_pytest_coverage`
- **Healed Gaps**: none (happy path)

### 2. Changelog Gap (Self-Healing) — ✅ SUCCESS

- **Elapsed**: 16036 ms
- **Actions Executed** (5):
  1. `run_ruff_check`
  2. `run_mypy`
  3. `run_pytest`
  4. `run_pytest_coverage`
  5. `synth_wildcard_changelog_generated_136a6c97`
- **Healed Gaps** (1) — LLM synthesizer invoked:
  - Missing predicate(s): `['changelog_generated']`

### 3. Full Commit Pipeline — ✅ SUCCESS

- **Elapsed**: 14732 ms
- **Actions Executed** (5):
  1. `run_ruff_check`
  2. `run_mypy`
  3. `run_pytest`
  4. `run_pytest_coverage`
  5. `git_dry_run_commit`
- **Healed Gaps**: none (happy path)
