"""The one place Seeker derives a search root from the ``.agents`` layer.

Four of these roots used to be relative literals spelled out inside the
Rune: ``.agents/.mvgeos/spells``, ``.agents/.mvgeos/skills``,
``.agents/.mvgeos/extensions`` and ``.agents/.mvgeos/runes``. That layer
is dead. ADR-0002 chose it, ADR-0014 superseded it, and no first-party code
in either repository has ever written there -- so every one of those
searches matched nothing on a correctly installed system.

Each resolver here is a thin wrapper over the matching ``mvgeos_core``
resolver, and each is a *call* rather than a module constant. That second
part matters as much as the first: the layer is read when the path is asked
for, so a Rune loaded once at startup still follows a layer relocated by
``$MVGEOS_GLOBAL_DIR`` afterwards. ``mvgeos_core.layers`` states the reason
in one line -- the install path and the discovery path resolving
differently is what allows a Rune to install successfully and then load
nowhere.

``~/.claude/skills`` and ``.agents/skills`` are listed by
:func:`skill_roots` and are not this layer. The first is a third-party
convention; the second is the project-relative spelling of our own layer,
consulted only when the project actually has one. Neither moves with
``$MVGEOS_GLOBAL_DIR``, and neither is routed through a global resolver.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from mvgeos_core import agent_dir, extensions_dir, skills_dir

#: Spells live at ``<global>/agents/<name>/spells``.
#:
#: Named rather than inlined because ``mvgeos_core.layers`` has no resolver
#: for it: ``agent_extensions_dir`` and ``agent_skills_dir`` are both
#: exported, the spells directory is not. Composing it from the exported
#: ``agent_dir`` keeps the search path equal to the install path the engine
#: discovers from (``resolve_config_dir(name) / "spells"``) instead of
#: introducing a second derivation of a directory the engine owns.
SPELLS_SUBDIR = "spells"

#: The project-relative spelling of our own skills layer.
PROJECT_SKILLS_DIR = Path(".agents") / "skills"


def spells_root(agent_name: str) -> Path:
    """The agent-scope Spells directory: ``<global>/agents/<name>/spells``."""
    return agent_dir(agent_name) / SPELLS_SUBDIR


def extensions_root() -> Path:
    """The user-scope Rune directory ``mcp_search`` scans: ``<global>/extensions``."""
    return extensions_dir()


def skill_roots() -> list[Path]:
    """Every skills directory Seeker searches, resolved now and unfiltered.

    Order is precedence. The user-scope layer leads because it is ours;
    the two conventions follow so a project-local Skill can still be found
    in a checkout that has one.
    """
    return [
        skills_dir(),
        Path.home() / ".claude" / "skills",
        PROJECT_SKILLS_DIR,
    ]


def missing(roots: Iterable[Path]) -> list[Path]:
    """Which of ``roots`` do not exist, so a silent empty search can name them.

    A search that returns nothing because its root does not exist is
    indistinguishable from one that found nothing. That indistinguishability
    is how a dead layer stays invisible for a release, so each Spell reports
    the roots it could not search rather than returning a bare zero.
    """
    return [root for root in roots if not root.is_dir()]
