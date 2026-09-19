"""GOAP execution engine with state rollback and LLM self-healing."""

import asyncio
import copy
from collections.abc import Callable
from typing import Any, cast

from mvgeos_runes_heal_my_goap.gap_analyzer import BaseGapAnalyzer, GapAnalyzer
from mvgeos_runes_heal_my_goap.models import (
    Action,
    ExecutionResult,
    Gap,
    Goal,
    Planner,
    WorldState,
    action_from_tool,
)
from mvgeos_runes_heal_my_goap.observer import BaseObserver, DeltaObserver
from mvgeos_runes_heal_my_goap.sandbox import BaseSandboxExecutor, SandboxExecutor
from mvgeos_runes_heal_my_goap.storage import ActionStorage, BaseActionStorage
from mvgeos_runes_heal_my_goap.synthesizer import BaseSynthesizer, LLMSynthesizer


class GoapEngine:
    """Orchestration harness for GOAP execution, rollback, and self-healing.

    Attributes:
        actions_dict: Dictionary mapping action names to Action instances.
        storage: Persistence handler for synthesized actions.
        synthesizer: LLM synthesis engine for bridging unsatisfied gaps.
        gap_analyzer: Diagnostic engine for identifying missing state gaps.
        sandbox: Isolated subprocess code executor.
        observer: Runtime state delta observer.
        state_refresh_callback: Live state refresh callback function.
        max_heal_attempts: Maximum self-healing retry iterations allowed.
        handlers: Runtime action execution handlers.
        idempotency_map: Idempotency flags per action name.
        failed_attempts: List of failed actions encountered during execution.
    """

    def __init__(
        self,
        initial_actions: list[Action] | None = None,
        storage: BaseActionStorage | str | None = None,
        synthesizer: BaseSynthesizer | None = None,
        gap_analyzer: BaseGapAnalyzer | None = None,
        sandbox: BaseSandboxExecutor | None = None,
        observer: BaseObserver | None = None,
        state_refresh_callback: (
            Callable[[], WorldState | dict[str, Any]] | None
        ) = None,
        max_heal_attempts: int = 3,
        storage_path: str | None = None,
        tools: list[Any] | None = None,
    ) -> None:
        """Initializes GoapEngine.

        Args:
            initial_actions: Baseline deterministic GOAP actions.
            storage: Storage instance or path for synthesized actions.
            synthesizer: Optional custom synthesizer instance.
            gap_analyzer: Optional custom gap analyzer instance.
            sandbox: Optional custom sandbox executor instance.
            observer: Optional runtime state delta observer instance.
            state_refresh_callback: Optional live state refresh callback.
            max_heal_attempts: Maximum allowed self-healing retries.
            storage_path: Optional storage path override string.
            tools: Optional list of tools/functions or tool spec dicts to
                automatically convert to actions via ``action_from_tool``.
        """
        actions = initial_actions or []
        self.actions_dict: dict[str, Action] = {a.name: a for a in actions}

        storage_val = storage_path or storage or ".goap_actions.json"
        self.storage: BaseActionStorage = (
            ActionStorage(file_path=storage_val)
            if isinstance(storage_val, str)
            else storage_val
        )
        self.synthesizer: BaseSynthesizer = synthesizer or LLMSynthesizer()
        self.gap_analyzer: BaseGapAnalyzer = gap_analyzer or GapAnalyzer()
        self.sandbox: BaseSandboxExecutor = sandbox or SandboxExecutor()
        self.observer: BaseObserver = observer or DeltaObserver()
        self.state_refresh_callback = state_refresh_callback
        self.max_heal_attempts = max_heal_attempts

        self.handlers: dict[str, Callable[[WorldState], None]] = {}
        self.idempotency_map: dict[str, bool] = {}
        self.failed_attempts: list[Action] = []

        for action in self.storage.load_actions():
            self.actions_dict[action.name] = action

        if tools:
            self.register_tools(tools)

    def _get_live_state(self, current_simulated: WorldState) -> dict[str, Any]:
        """Captures live state via refresh callback if available."""
        if self.state_refresh_callback is not None:
            res = self.state_refresh_callback()
            return res.to_dict() if isinstance(res, WorldState) else res
        return current_simulated.to_dict()

    def register_tool(
        self,
        tool: Any,
        name: str | None = None,
        description: str = "",
        effects: dict[str, Any] | None = None,
        cost: float = 10.0,
    ) -> Action:
        """Registers a tool or function as a GOAP Action on the engine.

        Args:
            tool: A function/callable, dict parameter schema, or dict tool spec.
            name: Optional action name override (defaults to function
                name or dict key).
            description: Optional action description.
            effects: Optional dictionary of predicate effects.
            cost: Action planning cost (default 10.0).

        Returns:
            The created and registered ``Action``.
        """
        if isinstance(tool, dict):
            tool_name = name or str(tool.get("name", "unnamed_tool"))
            tool_desc = description or str(tool.get("description", ""))
            tool_params = tool.get("parameters", tool)
            tool_effects = effects or tool.get("effects")
            tool_cost = cost if cost != 10.0 else float(tool.get("cost", 10.0))
        elif callable(tool):
            raw_name = name or getattr(tool, "__name__", "unnamed_tool")
            tool_name = str(raw_name)
            tool_desc = (
                description or getattr(tool, "__doc__", "") or "Callable tool"
            ).strip()
            tool_params = tool
            tool_effects = effects
            tool_cost = cost
        elif isinstance(tool, Action):
            self.actions_dict[tool.name] = tool
            return tool
        else:
            tool_name = name or "unnamed_tool"
            tool_desc = description
            tool_params = {}
            tool_effects = effects
            tool_cost = cost

        act = action_from_tool(
            name=tool_name,
            description=tool_desc,
            parameters=tool_params,
            effects=tool_effects,
            cost=tool_cost,
        )
        self.actions_dict[act.name] = act

        if callable(tool):
            import inspect

            sig = inspect.signature(tool)

            def _handler(ws: WorldState) -> None:
                if not sig.parameters:
                    tool()
                else:
                    kwargs = {
                        k: ws.get(k)
                        for k in sig.parameters
                        if ws.get(k) is not None
                    }
                    tool(**kwargs)

            self.register_handler(act.name, _handler)

        return act

    def register_tools(self, tools: list[Any]) -> list[Action]:
        """Registers multiple tools or functions as GOAP Actions on the engine.

        Args:
            tools: List of tools/functions or tool spec dictionaries.

        Returns:
            List of created and registered ``Action`` instances.
        """
        registered: list[Action] = []
        for t in tools:
            registered.append(self.register_tool(t))
        return registered

    def register_handler(
        self,
        action_name: str,
        handler_func: Callable[[WorldState], None],
        is_idempotent: bool = True,
    ) -> None:
        """Registers a runtime handler function for an action.

        Args:
            action_name: Name of target action.
            handler_func: Execution callback function taking WorldState.
            is_idempotent: Whether the action can be retried safely.
        """
        self.handlers[action_name] = handler_func
        self.idempotency_map[action_name] = is_idempotent

    async def arun(
        self, initial_state: WorldState, goal: Goal
    ) -> ExecutionResult:
        """Asynchronously executes GOAP planning loop in an executor thread.

        Args:
            initial_state: Starting world state.
            goal: Target GOAP goal state.

        Returns:
            An ExecutionResult indicating success status and final state.
        """
        return await asyncio.to_thread(self.run, initial_state, goal)

    def run(self, initial_state: WorldState, goal: Goal) -> ExecutionResult:
        """Executes GOAP planning loop with self-healing retry logic.

        Args:
            initial_state: Starting world state.
            goal: Target GOAP goal state.

        Returns:
            An ExecutionResult indicating success status and final state.
        """
        current_state = copy.deepcopy(initial_state)
        executed_actions: list[Action] = []
        healed_gaps: list[Gap] = []

        heal_attempts = 0

        while heal_attempts <= self.max_heal_attempts:
            available_actions = list(self.actions_dict.values())
            planner = Planner(actions_list=cast(Any, available_actions))
            plan_result = planner.generate_plan(current_state, goal)

            plan_actions: list[Any] = []
            if plan_result and hasattr(plan_result, "plan"):
                raw_plan = getattr(plan_result, "plan", None)
                if raw_plan is not None:
                    plan_actions = list(raw_plan)
            elif isinstance(plan_result, list):
                plan_actions = list(plan_result)

            if plan_actions:
                execution_successful = True
                for item in plan_actions:
                    action_obj = (
                        self.actions_dict.get(item)
                        if isinstance(item, str)
                        else item
                    )
                    if not action_obj:
                        continue

                    is_idempotent = self.idempotency_map.get(
                        action_obj.name, True
                    )
                    state_checkpoint = copy.deepcopy(current_state)

                    try:
                        before_state = self._get_live_state(current_state)

                        if action_obj.name in self.handlers:
                            self.handlers[action_obj.name](current_state)

                        after_state = self._get_live_state(current_state)
                        delta = self.observer.compute_delta(
                            before_state, after_state
                        )
                        if delta:
                            action_obj.effects = self.observer.merge_effects(
                                action_obj.effects, delta
                            )
                            self.actions_dict[action_obj.name] = action_obj
                            self.storage.save_action(action_obj)

                        if hasattr(current_state, "update_state"):
                            current_state.update_state(action_obj.effects)
                        for k, v in action_obj.effects.items():
                            setattr(current_state, k, v)

                        executed_actions.append(action_obj)
                    except Exception as exc:
                        execution_successful = False
                        if not is_idempotent:
                            err_msg = (
                                f"Non-idempotent action '{action_obj.name}' "
                                f"failed: {exc!s}"
                            )
                            return ExecutionResult(
                                success=False,
                                final_state=state_checkpoint,
                                executed_actions=executed_actions,
                                healed_gaps=healed_gaps,
                                error_message=err_msg,
                            )
                        current_state = state_checkpoint
                        self.failed_attempts.append(action_obj)
                        break

                if execution_successful:
                    curr_dict = (
                        current_state.to_dict()
                        if hasattr(current_state, "to_dict")
                        else dict(current_state)
                    )
                    goal_satisfied = True
                    for gk, gv in goal.target_state.items():
                        if curr_dict.get(gk) != gv:
                            goal_satisfied = False
                            break

                    if goal_satisfied:
                        return ExecutionResult(
                            success=True,
                            final_state=current_state,
                            executed_actions=executed_actions,
                            healed_gaps=healed_gaps,
                        )

            gap = self.gap_analyzer.analyze(
                current_state, goal, available_actions
            )
            healed_gaps.append(gap)

            bridge_action = self.synthesizer.synthesize_bridge_action(
                gap, available_actions, self.failed_attempts
            )

            self.storage.save_action(bridge_action)
            self.actions_dict[bridge_action.name] = bridge_action

            heal_attempts += 1

        err_msg = (
            f"Reached maximum heal attempts ({self.max_heal_attempts}) "
            "without reaching goal."
        )
        return ExecutionResult(
            success=False,
            final_state=current_state,
            executed_actions=executed_actions,
            healed_gaps=healed_gaps,
            error_message=err_msg,
        )
