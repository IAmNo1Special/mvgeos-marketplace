---
title: Examples
description: Working code examples demonstrating heal-my-goap capabilities.
---

# Examples

Complete, runnable examples showing `heal-my-goap` in action across different domains.

## Example Gallery

| Example | Scenario | Difficulty | Key Features |
| :--- | :--- | :--- | :--- |
| [OS System Monitor](system-monitor.md) | System health restoration via live OS metrics | Beginner | `SystemSensors`, `world_state_from_sensors`, `goal`, basic self-healing |
| [Autonomous Coding Agent](coding-agent.md) | 9-tool AI software engineering pipeline | Advanced | `DeltaObserver`, `action_from_tool`, LLM synthesis, retry memory, git/PR automation |
| [Hospital Medic Robot](hospital-emergency.md) | Robot medic with dynamic medicine shortage healing | Intermediate | Baseline actions, `GapAnalyzer`, `LLMSynthesizer`, `SandboxExecutor`, persistence |
| [Google ADK Integration](google-adk-integration.md) | heal-my-goap as symbolic planner inside ADK agents | Intermediate | `GoapEngine` as ADK tool, `DeltaObserver`, `LLMSynthesizer`, streaming, workflows |

<div class="grid cards">
  <div>
    <h3>🖥️ OS System Monitor</h3>
    <p>Monitor 28+ live OS metrics and automatically heal system health goals (RAM, temp files, network).</p>
    <p><a href="system-monitor/">Read more →</a></p>
  </div>
  <div>
    <h3>🤖 Autonomous Coding Agent</h3>
    <p>Full 8-step software engineering pipeline with git, linting, type checking, testing, and PR creation.</p>
    <p><a href="coding-agent/">Read more →</a></p>
  </div>
  <div>
    <h3>🏥 Hospital Medic Robot</h3>
    <p>Autonomous robot medic navigating wards, treating patients, and self-healing when medicine is missing.</p>
    <p><a href="hospital-emergency/">Read more →</a></p>
  </div>
  <div>
    <h3>🔗 Google ADK Integration</h3>
    <p>Use heal-my-goap as a zero-token symbolic planner inside Google ADK agents with streaming and workflows.</p>
    <p><a href="google-adk-integration/">Read more →</a></p>
  </div>
</div>