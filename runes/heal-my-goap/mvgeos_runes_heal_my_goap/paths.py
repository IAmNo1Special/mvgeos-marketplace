"""Credential resolution for the Rune.

Kept out of ``rune.py`` because the entry-point module is loaded by the
engine as a parentless top-level module whose name (``rune``) is ambiguous
across the marketplace, so nothing in ``tests/`` can import it. The package
itself has a unique name and is importable. That constraint is why the
credential read lives here too: a test cannot drive ``rune_factory`` to
prove which file the Rune authenticated against.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mvgeos_core import auth_file

logger = logging.getLogger(__name__)


def openrouter_auth_path() -> Path:
    """The OpenRouter credential file this Rune reads at load time.

    Resolved by the engine's own ``auth_file`` rather than spelled out, so
    this Rune consults the engine's credential store instead of a path it
    derived itself. ``auth_file`` is the single resolver for
    ``<global>/auth/<provider>.json``, which is where the CLI writes a
    prompted key (``save_api_key_to_auth``) and where the engine reads one
    back. A path built here could only ever agree with that store by
    coincidence.

    Imported from the ``mvgeos_core`` package root rather than
    ``mvgeos_core.layers``: the root is the public surface, and it
    re-exports the resolvers whether they live in ``constants`` or in the
    newer ``layers`` module.

    Resolved per call rather than at import because ``rune_factory`` runs
    when the engine loads the Rune, which is not necessarily when the
    process started, and ``$MVGEOS_GLOBAL_DIR`` is read on every call by
    design.

    Deliberately *not* ``mvgeos_agent.auth.load_api_key_from_auth``. That
    helper binds ``AUTH_FILE_PATH`` once at module import, so once a
    process has imported it, relocating the global layer stops working:
    the helper keeps returning the credential from the real home store
    while the engine is running against a relocated one. Resolving per call
    here is what makes a relocated run read the relocated store.
    """
    return auth_file("openrouter")


def load_openrouter_credentials() -> dict[str, str]:
    """Read the OpenRouter credential from the engine's store.

    Returns the parsed mapping, or an empty mapping when the file is absent
    or unreadable. A missing credential is a normal state -- the Summoner
    may authenticate by other means -- so it is not an error.

    Keys:
        api_key: The OpenRouter credential.
        model: Optional default model identifier.
    """
    auth_path = openrouter_auth_path()
    if not auth_path.exists():
        return {}

    try:
        with auth_path.open("r", encoding="utf-8") as f:
            creds = json.load(f)
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "Failed to load OpenRouter credential from %s", auth_path
        )
        return {}

    if not isinstance(creds, dict):
        logger.warning("Unexpected credential file shape at %s", auth_path)
        return {}
    return creds


__all__ = ["load_openrouter_credentials", "openrouter_auth_path"]
