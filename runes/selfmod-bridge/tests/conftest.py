"""Shared test doubles for the selfmod-bridge rune."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from mvgeos_runes_selfmod_bridge.rune import SelfmodBridgeRune
from mvgeos_runes_selfmod_bridge.state import SelfmodState

# Unique alias: the bare ``tests.conftest`` / ``rune`` module names collide
# across marketplace runes in full-suite runs (every rune ships
# ``tests/conftest.py`` and a top-level ``rune.py``, and ``tests`` becomes a
# namespace package spanning them all). pytest always imports this conftest
# before the test modules in this directory, so the alias is in place when
# they do ``from selfmod_bridge_conftest import ...``.
sys.modules.setdefault("selfmod_bridge_conftest", sys.modules[__name__])


class FakeApi:
    """Minimal RuneAPI double: records hook/command/spell registration,
    allowlist widening, emitted events, and audit calls."""

    def __init__(self) -> None:
        self.hooks: dict[Any, Any] = {}
        self.commands: dict[str, Any] = {}
        self.spells: dict[str, Any] = {}
        self.widened: list[str] = []
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.audit_records: list[dict[str, Any]] = []
        self.audit_error: BaseException | None = None

    def on(self, hook: Any, handler: Any) -> None:
        self.hooks[hook] = handler

    def register_command(self, name: str, *args: Any) -> None:
        # Tolerant: sibling runes register (name, description, handler).
        self.commands[name] = args[-1]

    def register_spell(self, spell: Any) -> None:
        self.spells[spell.name] = spell

    def widen_global_allowlist(self, names: list[str]) -> None:
        self.widened.extend(names)

    def emit_event(self, name: str, payload: dict[str, Any]) -> None:
        self.events.append((name, payload))

    def audit(
        self,
        op: str,
        *,
        outcome: str,
        code: str,
        message: str,
        target: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if self.audit_error is not None:
            raise self.audit_error
        self.audit_records.append(
            {
                "op": op,
                "outcome": outcome,
                "code": code,
                "message": message,
                "target": target,
                "extra": extra,
            }
        )


def make_state(tmp_path: Path) -> SelfmodState:
    config = tmp_path / "agent-config"
    config.mkdir(exist_ok=True)
    spells = config / "spells"
    spells.mkdir(exist_ok=True)
    system = config / "SYSTEM.md"
    system.write_text("# Test System\n\nYou are a test agent.\n", encoding="utf-8")
    runes_root = tmp_path / "runes"
    runes_root.mkdir(exist_ok=True)
    return SelfmodState(
        config_dir=config,
        runes_paths=[runes_root],
        system_path=system,
        spells_dir=spells,
        agent_name="test-agent",
        cwd=tmp_path,
    )


def make_rune(tmp_path: Path, *, with_state: bool = True) -> tuple[Any, FakeApi]:
    api = FakeApi()
    rune = SelfmodBridgeRune(api, {"version": "0.1.0"})
    if with_state:
        rune.state = make_state(tmp_path)
    return rune, api


def load_root_module(name: str) -> Any:
    """Load ``runes/selfmod-bridge/<name>.py`` under a unique module name.

    A bare ``import rune`` collides with every other marketplace rune's
    top-level ``rune.py`` in full-suite runs; the unique name keeps this
    rune's entry point unambiguous.
    """
    path = Path(__file__).resolve().parent.parent / f"{name}.py"
    module_name = f"selfmod_bridge_root_{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod
