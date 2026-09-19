"""Rune factory for pi-bridge.

pi-bridge is a CLI-only rune: the importer is invoked by the user as
`mvgeos pi-import <file>`, never by the agent mid-session, so there is no
session wiring here. The loader requires a `rune_factory`; it is a no-op.
"""

from __future__ import annotations

from mvgeos_runes.rune_api import RuneAPI


def rune_factory(api: RuneAPI) -> None:
    """Bind pi-bridge. Nothing to wire: the CLI command carries the feature."""
    _ = api
