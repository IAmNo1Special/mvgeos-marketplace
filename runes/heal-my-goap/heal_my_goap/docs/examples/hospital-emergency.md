---
title: Hospital Medic Robot
description: Autonomous robot medic with dynamic self-healing when medicine is missing.
---

# Hospital Emergency Response Example

Simulates an autonomous robot medic navigating hospital wards, treating patients, and handling equipment failures with dynamic self-healing when medicine is missing.

!!! abstract "At a Glance"
    **Scenario**: Robot medic must stabilize a patient but lacks required medicine — self-healing synthesizes a retrieval action.
    **Key Features Used**: Baseline `Action` definitions, `GapAnalyzer`, `LLMSynthesizer`, `SandboxExecutor`, `ActionStorage` persistence.

---

## Scenario Setup

A patient in the emergency ward needs immediate medication. The robot medic starts in the lobby with `has_medicine=False`. The baseline actions can navigate to the ward and administer medicine — but only if the robot already has medicine.

When `GoapEngine` tries to plan, `GapAnalyzer` isolates the missing `has_medicine: True` predicate. `LLMSynthesizer` generates a bridge action to retrieve medicine from the pharmacy, `SandboxExecutor` validates it safely, and the engine re-plans with the new action.

---

## Full Code

```python
from heal_my_goap import Action, Goal, GoapEngine, WorldState

baseline_actions = [
    Action(
        name="navigate_to_ward",
        preconditions={"location": "lobby"},
        effects={"location": "emergency_ward"},
        cost=2.0,
    ),
    Action(
        name="administer_medicine",
        preconditions={"location": "emergency_ward", "has_medicine": True},
        effects={"patient_stabilized": True},
        cost=1.0,
    ),
]

engine = GoapEngine(
    initial_actions=baseline_actions,
    storage_path=".goap_hospital_actions.json",
    max_heal_attempts=3,
)

# Patient needs medicine, but has_medicine=False
result = engine.run(
    initial_state=WorldState(
        location="lobby", has_medicine=False, patient_stabilized=False
    ),
    goal=Goal(target_state={"patient_stabilized": True}),
)

print(f"Patient Stabilized: {result.final_state.get('patient_stabilized')}")
```

---

## Expected Output

```
Patient Stabilized: True
```

*Self-healing trace:*
```
Gap detected: missing_predicate={'has_medicine': True}
Synthesizing bridge action: synth_retrieve_medicine_from_pharmacy
Sandbox validation passed.
Executing synthesized action...
Medicine retrieved. Re-planning...
Patient Stabilized: True
```

On subsequent runs, the synthesized action is loaded from `.goap_hospital_actions.json` and executes at zero token cost.

---

## Run Command

```bash
uv run examples/heal_my_goap/hospital_emergency.py
```

---

## Related Pages

- [Core Concepts](../getting-started/concepts.md)
- [Self-Healing Guide](../user-guide/self-healing.md)
- [API Reference: GoapEngine](../api-reference/engine.md)
- [API Reference: Synthesizer & GapAnalyzer](../api-reference/synthesizer.md)