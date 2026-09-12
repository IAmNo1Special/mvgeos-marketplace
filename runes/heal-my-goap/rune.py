"""Global MvgeOS Rune for heal-my-goap integration."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from heal_my_goap.engine import GoapEngine
from heal_my_goap.models import Action, Gap, Goal, WorldState, goal, world_state_from_sensors
from heal_my_goap.sensors import SystemSensors
from mvgeos_runes.rune_api import RuneAPI
from mvgeos_runes.types import ExecutionMode, SigilHook, SpellDefinition

logger = logging.getLogger(__name__)

# Heal-my-goap owns exactly these tools in the active spell set. The engine
# auto-seeds every registered rune spell into the active set by default, but
# once a rune pins an explicit set (see activate_heal_my_goap_spells) later
# registrations no longer auto-join. We pin so other runes that own their own
# active set (e.g. seeker) cannot clobber heal-my-goap's tools, and we widen
# the set at runtime when a repair spell is synthesized.
HEAL_MY_GOAP_SPELLS = [
    "goap_plan_and_execute",
    "goap_sense_world",
    "goap_synthesize_action",
]


class GoapPlanAndExecuteSpell(SpellDefinition):
    """Spell to execute zero-token GOAP plans with self-healing fallback."""

    def __init__(self, engine: GoapEngine) -> None:
        """Initializes GoapPlanAndExecuteSpell.

        Args:
            engine: GoapEngine instance.
        """
        super().__init__(
            name="goap_plan_and_execute",
            description=(
                "Executes a multi-step deterministic action plan to reach "
                "a target state, with automated self-healing on failure."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "initial_state": {
                        "type": "object",
                        "description": "Optional initial key-value world state.",
                    },
                    "target_state": {
                        "type": "object",
                        "description": "Target key-value state conditions.",
                    },
                },
                "required": ["target_state"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        )
        self._engine = engine

    async def execute(
        self,
        spell_cast_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        """Executes the GOAP planning loop asynchronously.

        Args:
            spell_cast_id: Unique spell invocation identifier.
            params: Spell argument parameters dictionary.
            signal: Optional cancellation signal.
            on_update: Optional status update callback.

        Returns:
            Dictionary containing execution status and final state metrics.
        """
        raw_initial = params.get("initial_state")
        start_state = (
            world_state_from_sensors(SystemSensors())
            if raw_initial is None
            else WorldState(**raw_initial)
        )
        target_goal = Goal(target_state=params["target_state"])

        try:
            result = await self._engine.arun(start_state, target_goal)
            final_dict = (
                result.final_state.to_dict()
                if isinstance(result.final_state, WorldState)
                else dict(result.final_state)
            )
            return {
                "status": "success" if result.success else "failed",
                "final_state": final_dict,
                "executed_actions": [a.name for a in result.executed_actions],
                "healed_gaps_count": len(result.healed_gaps),
            }
        except Exception as err:
            logger.exception("GOAP execution error in spell %s", spell_cast_id)
            return {"status": "error", "error": str(err)}


class GoapSenseWorldSpell(SpellDefinition):
    """Spell to inspect current system environment metrics."""

    def __init__(self) -> None:
        """Initializes GoapSenseWorldSpell."""
        super().__init__(
            name="goap_sense_world",
            description="Reads live system metrics into a WorldState dictionary.",
            parameters={"type": "object", "properties": {}},
            execution_mode=ExecutionMode.PARALLEL,
        )

    async def execute(
        self,
        spell_cast_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        """Samples system metrics and returns the current WorldState.

        Args:
            spell_cast_id: Unique spell invocation identifier.
            params: Spell argument parameters dictionary.
            signal: Optional cancellation signal.
            on_update: Optional status update callback.

        Returns:
            Dictionary containing sampled world state metrics.
        """
        sensors = SystemSensors()
        return {"world_state": world_state_from_sensors(sensors).to_dict()}


class GoapSynthesizeActionSpell(SpellDefinition):
    """Spell to synthesize a missing action for an unsatisfied gap."""

    def __init__(self, engine: GoapEngine) -> None:
        """Initializes GoapSynthesizeActionSpell.

        Args:
            engine: GoapEngine instance.
        """
        super().__init__(
            name="goap_synthesize_action",
            description="Synthesizes a missing Python action script via OpenRouter.",
            parameters={
                "type": "object",
                "properties": {
                    "gap_description": {"type": "string"},
                    "preconditions": {"type": "object"},
                    "effects": {"type": "object"},
                },
                "required": ["gap_description"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        )
        self._engine = engine

    async def execute(
        self,
        spell_cast_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        """Synthesizes an action for the specified gap.

        Args:
            spell_cast_id: Unique spell invocation identifier.
            params: Spell argument parameters dictionary.
            signal: Optional cancellation signal.
            on_update: Optional status update callback.

        Returns:
            Dictionary with status and synthesized action info.
        """
        gap_desc = str(params.get("gap_description", ""))
        preconds = params.get("preconditions", {})
        effects = params.get("effects", {})

        try:
            action = self._engine.synthesizer.synthesize_bridge_action(
                gap_desc, preconds, effects
            )
            self._engine.actions_dict[action.name] = action
            return {
                "status": "success",
                "action_name": action.name,
                "preconditions": action.preconditions,
                "effects": action.effects,
            }
        except Exception as err:
            return {"status": "failed", "error": str(err)}


class SynthesizedRuneSpell(SpellDefinition):
    """Dynamically generated SpellDefinition wrapping a synthesized GOAP Action."""

    def __init__(self, action: Action, engine: GoapEngine) -> None:
        """Initializes SynthesizedRuneSpell with synthesized action.

        Args:
            action: Synthesized GOAP Action instance.
            engine: GoapEngine instance.
        """
        super().__init__(
            name=action.name,
            description=action.description or f"Synthesized action for {action.name}",
            parameters={"type": "object", "properties": {}},
            execution_mode=ExecutionMode.SEQUENTIAL,
        )
        self._action = action
        self._engine = engine

    async def execute(
        self,
        spell_cast_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        """Executes the synthesized action code in MvgeOS host sandbox.

        Args:
            spell_cast_id: Unique spell invocation identifier.
            params: Spell argument parameters dictionary.
            signal: Optional cancellation signal.
            on_update: Optional status update callback.

        Returns:
            Dictionary containing sandbox execution output.
        """
        allowed = {"pathlib", "subprocess", "os", "urllib", "json", "re"}
        if getattr(self._action, "code", None):
            return self._engine.sandbox.execute_code(
                self._action.code,
                context_globals=params,
                allowed_modules=allowed,
            )
        return {"status": "executed", "action_name": self._action.name}


def sync_spells_to_goap(engine: GoapEngine, api: RuneAPI) -> None:
    """Ingests all active MvgeOS Spells into GoapEngine as GOAP Actions.

    Args:
        engine: GoapEngine instance.
        api: RuneAPI instance.
    """
    for spell in api.get_all_spells():
        if (
            spell.name not in engine.actions_dict
            and not spell.name.startswith("goap_")
        ):
            engine.register_tool(
                tool=spell.parameters,
                name=spell.name,
                description=spell.description,
            )


def rune_factory(api: RuneAPI) -> None:
    """Rune initialization factory invoked by RuneLoader.

    Args:
        api: MvgeOS RuneAPI instance.
    """
    # Load OpenRouter API Key from ~/.agents/.mvgeos/credentials/openrouter.json
    home_dir = Path.home()
    auth_file = (
        home_dir / ".agents" / ".mvgeos" / "auth" / "openrouter.json"
    )
    if auth_file.exists():
        try:
            with auth_file.open("r", encoding="utf-8") as f:
                creds = json.load(f)
            api_key = creds.get("api_key") or creds.get("token")
            model_name = creds.get("model")
            if api_key and "OPENROUTER_API_KEY" not in os.environ:
                os.environ["OPENROUTER_API_KEY"] = api_key
            if model_name and "DEFAULT_LLM_MODEL" not in os.environ:
                os.environ["DEFAULT_LLM_MODEL"] = model_name
        except Exception:
            logger.warning("Failed to load OpenRouter Relic from %s", auth_file)

    engine = GoapEngine(sandbox=api.sandbox)

    # Register Spells on RuneRunner
    api.register_spell(GoapPlanAndExecuteSpell(engine))
    api.register_spell(GoapSenseWorldSpell())
    api.register_spell(GoapSynthesizeActionSpell(engine))

    # Sigil Hook: Sync spells before invocation
    async def on_before_invocation(payload: Any = None) -> None:
        sync_spells_to_goap(engine, api)

    api.on(SigilHook.BEFORE_INVOCATION, on_before_invocation)
    api.on(SigilHook.SESSION_START, on_before_invocation)

    # Own the active-spell surface explicitly (Pi-faithful setActiveTools
    # pattern). Mirrors the seeker rune: pin to heal-my-goap's own tools so the
    # system prompt reflects only this rune's capabilities and is not clobbered
    # by another rune that pins its own active set.
    def activate_heal_my_goap_spells(_data: dict[str, Any]) -> None:
        # Add heal-my-goap's tools to whatever active set already exists rather
        # than replacing it, so this rune composes with others that own their
        # own active set (e.g. seeker). Becomes a native per-rune additive call
        # once issue #40 lands.
        api.set_active_spells([*api.get_active_spells(), *HEAL_MY_GOAP_SPELLS])

    api.on(SigilHook.SESSION_START, activate_heal_my_goap_spells)

    # Sigil Hook: Catch failed spell results and register synthesized repair spell
    async def on_after_spell_result(
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        result = payload.get("result", {})
        if isinstance(result, dict) and result.get("error"):
            spell_name = payload.get("spell_name", "unknown")
            err_msg = str(result.get("error"))

            api.send_message(
                f"[Rune: heal-my-goap] Intercepted failure in spell '{spell_name}': {err_msg}. "
                "Synthesizing repair spell..."
            )

            gap = Gap(
                missing_predicate={f"spell_{spell_name}": True},
                dependent_action_name=spell_name,
            )
            try:
                synth_action = engine.synthesizer.synthesize_bridge_action(
                    gap,
                    available_actions=list(engine.actions_dict.values()),
                )
                engine.actions_dict[synth_action.name] = synth_action

                # Dynamically register the synthesized action as a live Spell on RuneRunner
                api.register_spell(SynthesizedRuneSpell(synth_action, engine))

                # The active set is pinned, so a fresh registration does not
                # auto-join it. Widen explicitly so the model can cast the
                # newly synthesized repair spell. (This is the in-rune form of
                # the engine's runtime-widening work tracked in issue #41.)
                api.set_active_spells(
                    [*api.get_active_spells(), synth_action.name]
                )

                return {
                    "result": {
                        "status": "spell_registered",
                        "instruction": (
                            f"Tool '{spell_name}' failed or missing. Synthesized "
                            f"and dynamically registered new spell '{synth_action.name}'. "
                            f"Please cast spell '{synth_action.name}' to complete task."
                        ),
                        "registered_spell_name": synth_action.name,
                        "healed_by": "heal-my-goap",
                    }
                }
            except Exception as synth_err:
                logger.warning(
                    "Synthesis repair fallback triggered: %s", synth_err
                )

            return {
                "result": {
                    "status": "healed",
                    "original_error": err_msg,
                    "healed_by": "heal-my-goap",
                    "diagnostic": f"GOAP analyzed failure for spell '{spell_name}'",
                }
            }
        return None

    api.on(SigilHook.AFTER_SPELL_RESULT, on_after_spell_result)
