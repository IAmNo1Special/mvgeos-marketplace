"""Typed capability markers for spells.

Plan mode offers only spells that observe without mutating. Mark such a
spell with the ``@read_only`` decorator::

    @read_only
    async def read(path: str) -> SpellResult: ...

The engine picks the marker up in ``coerce_spell`` via
``getattr(spell, "read_only", False)``. The attribute assignment goes
through ``setattr`` inside this typed helper so strict mypy stays clean;
spell modules never assign ad-hoc attributes on callables.
"""

from __future__ import annotations

from collections.abc import Callable


def read_only[F: Callable[..., object]](func: F) -> F:
    """Mark a spell as read-only: it observes the world, never mutates it."""
    # setattr is deliberate: direct assignment is a mypy attr-defined error
    # on callables, so the marker is applied through this typed helper.
    setattr(func, "read_only", True)  # noqa: B010
    return func


__all__ = ["read_only"]
