"""Filesystem locations the Rune reads from.

Kept out of ``rune.py`` because the entry-point module is loaded by the
engine as a parentless top-level module whose name (``rune``) is ambiguous
across the marketplace, so nothing in ``tests/`` can import it. The package
itself has a unique name and is importable.
"""

from __future__ import annotations

from pathlib import Path

from mvgeos_core import global_agents_dir


def openrouter_auth_path() -> Path:
    """The OpenRouter credential file this Rune reads at load time.

    The global layer is resolved through ``global_agents_dir`` rather than
    spelled out from ``Path.home()``, so a relocated global layer
    (``$MVGEOS_GLOBAL_DIR``) is honoured. Resolved per call rather than at
    import for the same reason: ``rune_factory`` runs when the engine loads
    the rune, which is not necessarily when the process started.

    Imported from the ``mvgeos_core`` package root rather than
    ``mvgeos_core.constants``: the root is the public surface, and it
    re-exports the resolvers whether they live in ``constants`` or in the
    newer ``layers`` module.

    The ``.mvgeos`` segment is the engine's legacy credential location and
    is deliberately preserved. Correcting it is a separate change; this
    function fixes only which *layer* is consulted.
    """
    return global_agents_dir() / ".mvgeos" / "auth" / "openrouter.json"


__all__ = ["openrouter_auth_path"]
