"""Self-healing GOAP demo featuring missing action synthesis."""

from heal_my_goap import Action, Goal, GoapEngine, WorldState


def main() -> None:
    """Executes self-healing GOAP planning demo."""
    initial_state = WorldState(has_key=False, door_open=False)

    open_door = Action(
        name="open_door",
        preconditions={"has_key": True},
        effects={"door_open": True},
        cost=1.0,
    )

    goal = Goal(target_state={"door_open": True})

    engine = GoapEngine(
        initial_actions=[open_door],
        storage_path="demo_actions.json",
        max_heal_attempts=3,
    )

    print("🚀 Running GoapEngine Self-Healing Loop...")
    result = engine.run(initial_state, goal)

    print(f"\nExecution Success: {result.success}")
    print(f"Final State: {result.final_state.to_dict()}")
    print("Executed Actions:")
    for act in result.executed_actions:
        print(f" - {act.name} (cost: {act.cost})")

    if result.healed_gaps:
        print("\nHealed Gaps Isolated:")
        for gap in result.healed_gaps:
            missing = gap.missing_predicate
            dep_action = gap.dependent_action_name
            print(
                f" - Missing predicate: {missing} for dependent action: "
                f"{dep_action}"
            )


if __name__ == "__main__":
    main()
