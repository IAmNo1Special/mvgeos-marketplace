---
title: API Reference
description: Complete API reference for heal-my-goap modules, classes, and functions.
---

# API Reference

Complete module map with import paths, signatures, parameter tables, and return types.

## Module Map

| Module | Import Path | Description |
| :--- | :--- | :--- |
| `engine` | `from heal_my_goap import GoapEngine` | Orchestrator for planning, execution, observation, and self-healing |
| `models` | `from heal_my_goap import Action, Goal, WorldState, Gap, ExecutionResult, action_from_tool, goal, world_state_from_sensors` | Domain schemas and UX helpers |
| `observer` | `from heal_my_goap import DeltaObserver, BaseObserver` | Runtime state delta observer |
| `sensors` | `from heal_my_goap import SystemSensors` | Live OS metrics collector (28+ metrics) |
| `synthesizer` | `from heal_my_goap import LLMSynthesizer, GapAnalyzer, SandboxExecutor` | LLM synthesis, gap analysis, and code sandbox |

<div class="grid cards">
  <div>
    <h3>⚙️ GoapEngine</h3>
    <p>Constructor parameters, <code>run()</code>, <code>register_tool()</code>, <code>register_tools()</code>.</p>
    <p><a href="engine/">Read more →</a></p>
  </div>
  <div>
    <h3>📦 Models & Helpers</h3>
    <p>Domain schemas (<code>Gap</code>, <code>ExecutionResult</code>), UX helpers, operator re-exports.</p>
    <p><a href="models/">Read more →</a></p>
  </div>
  <div>
    <h3>👁️ DeltaObserver</h3>
    <p><code>BaseObserver</code> interface, constructor, <code>compute_delta()</code>, <code>merge_effects()</code>.</p>
    <p><a href="observer/">Read more →</a></p>
  </div>
  <div>
    <h3>📊 SystemSensors</h3>
    <p>Full 28+ metrics method table with return types and descriptions.</p>
    <p><a href="sensors/">Read more →</a></p>
  </div>
  <div>
    <h3>🤖 Synthesizer & GapAnalyzer</h3>
    <p><code>LLMSynthesizer</code> config, <code>GapAnalyzer</code> methods, <code>SandboxExecutor</code> safety.</p>
    <p><a href="synthesizer/">Read more →</a></p>
  </div>
</div>