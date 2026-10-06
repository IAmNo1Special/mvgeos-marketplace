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

from mvgeos_core import agent_spells_dir, extensions_dir, skills_dir

#: The project-relative spelling of our own skills layer.
PROJECT_SKILLS_DIR = Path(".agents") / "skills"


def spells_root(agent_name: str) -> Path:
    """The agent-scope Spells directory: ``<global>/agents/<name>/spells``.

    Routed through ``mvgeos_core.agent_spells_dir``, which the engine added
    for exactly this Rune's reason: the host spells this path out in its
    installer and in its own Spell discovery, and a Rune that searches it
    must not spell out a third copy. This function used to compose the path
    from ``agent_dir(name) / "spells"`` because the engine exported no
    resolver for it. It does now, so the local derivation is a second copy
    of a directory the engine owns, and the comment that justified it had
    become false.
    """
    return agent_spells_dir(agent_name)


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
