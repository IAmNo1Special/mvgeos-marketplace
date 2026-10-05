"""The Rune must resolve OpenRouter auth the way the engine does.

``rune_factory`` once read ``~/.agents/.mvgeos/auth/openrouter.json``. That
path is dead: ADR-0002 chose ``.agents/.mvgeos/`` and ADR-0014 superseded it
with standard protocol names, so no first-party code has ever written there.
The Rune's LLM-backed spells therefore could not authenticate on a correctly
installed system.

The fix routes the Rune through ``mvgeos_core.auth_file``, the engine's single
resolver for ``<global>/auth/<provider>.json`` -- the store the CLI writes a
prompted key into and the engine reads one back from.

Every fixture here relocates the global layer into ``tmp_path``. Nothing in
this file may read the Summoner's real credential store: a test that resolves
against ``~/.agents`` proves nothing and would handle a live secret.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mvgeos_core import GLOBAL_DIR_ENV, auth_file, global_agents_dir

from mvgeos_runes_heal_my_goap.paths import (
    load_openrouter_credentials,
    openrouter_auth_path,
)


@pytest.fixture
def relocated_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the global ``.agents`` layer at a temp root for one test."""
    # Deliberately local rather than shared from the repository root:
    # each rune is an independently installable, independently testable
    # package (its own pyproject.toml declares its own testpaths), and a
    # suite run from inside the rune directory never loads the root
    # conftest.py.
    root = tmp_path / "global"
    monkeypatch.setenv(GLOBAL_DIR_ENV, str(root))
    return root


def seed_credential(layer: Path, api_key: str, **extra: str) -> Path:
    """Write a credential into ``layer``'s engine auth store."""
    path = auth_file("openrouter")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"api_key": api_key, **extra}), encoding="utf-8")
    return path


def test_auth_path_is_the_engines_credential_store(
    relocated_global: Path,
) -> None:
    """The path is the engine's own, not one this Rune assembled."""
    assert (
        openrouter_auth_path() == relocated_global / "auth" / "openrouter.json"
    )


def test_auth_path_agrees_with_the_engine_resolver(
    relocated_global: Path,
) -> None:
    """Route through the engine rather than re-deriving the same path.

    Asserting the engine's answer directly is what makes this a contract on
    the engine's resolver. Asserting a hardcoded literal would let the two
    drift apart again, which is the defect this file exists to catch.
    """
    assert openrouter_auth_path() == auth_file("openrouter")


def test_no_mvgeos_segment_remains(relocated_global: Path) -> None:
    """The dead ``.mvgeos`` layout is gone from the credential path.

    The failure this pins is silent: the path is well-formed and absolute,
    so a regression here shows up only as a Rune that cannot authenticate.
    """
    assert ".mvgeos" not in openrouter_auth_path().parts


def test_auth_path_is_not_taken_from_the_real_home_layer(
    relocated_global: Path,
) -> None:
    """The literal home layer is never consulted.

    Asserted unconditionally: the fixture relocates to a temp directory, so
    a conditional here would only ever be a silent skip.
    """
    assert (
        openrouter_auth_path()
        != Path("~/.agents/auth/openrouter.json").expanduser()
    )
    assert not openrouter_auth_path().is_relative_to(Path.home())


def test_default_location_without_the_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no override the path is the engine's documented default."""
    monkeypatch.delenv(GLOBAL_DIR_ENV, raising=False)
    assert global_agents_dir() == Path("~/.agents").expanduser()
    assert openrouter_auth_path() == (
        Path("~/.agents").expanduser() / "auth" / "openrouter.json"
    )


def test_auth_path_is_resolved_at_call_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Read the override per call, not once at import.

    ``rune_factory`` runs at load time, which can be well after the process
    started. Freezing the layer at import is what made the original
    expression wrong for any late-set override -- and it is why this Rune
    does not call ``mvgeos_agent.auth.load_api_key_from_auth``, whose
    ``AUTH_FILE_PATH`` is bound once at module import.
    """
    monkeypatch.delenv(GLOBAL_DIR_ENV, raising=False)

    relocated = tmp_path / "relocated"
    monkeypatch.setenv(GLOBAL_DIR_ENV, str(relocated))
    assert openrouter_auth_path() == relocated / "auth" / "openrouter.json"


def test_credentials_load_from_the_relocated_layer(
    relocated_global: Path,
) -> None:
    """A relocated run authenticates against the relocated store.

    This is the behaviour the dead path broke: the credential the engine
    placed in its own store, in the layer the engine is actually running
    against, is the credential this Rune reads. No network call is involved
    or permitted -- the read is entirely local.
    """
    seed_credential(relocated_global, "sk-or-relocated")

    assert load_openrouter_credentials()["api_key"] == "sk-or-relocated"


def test_credentials_ignore_the_dead_layer_even_when_present(
    relocated_global: Path,
) -> None:
    """A credential left at the dead path is not used.

    A stale ``.mvgeos`` file can survive from before ADR-0014. Reading it
    would mean silently authenticating with a key the Summoner retired,
    which is the specific confusion this fix removes.
    """
    seed_credential(relocated_global, "sk-or-current")
    stale = relocated_global / ".mvgeos" / "auth" / "openrouter.json"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text(json.dumps({"api_key": "sk-or-stale"}), encoding="utf-8")

    assert load_openrouter_credentials()["api_key"] == "sk-or-current"


def test_missing_credential_is_not_an_error(relocated_global: Path) -> None:
    """No credential is a normal state, not a failure."""
    assert load_openrouter_credentials() == {}


def test_unparseable_credential_degrades_to_empty(
    relocated_global: Path,
) -> None:
    """Malformed JSON yields no credential rather than raising.

    A corrupt store must not stop the Rune from loading; the engine reports
    a missing key far better than a loader traceback.
    """
    path = auth_file("openrouter")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    assert load_openrouter_credentials() == {}


def test_non_mapping_credential_degrades_to_empty(
    relocated_global: Path,
) -> None:
    """A JSON document that is not a mapping is not a credential."""
    path = auth_file("openrouter")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(["sk-or-list"]), encoding="utf-8")

    assert load_openrouter_credentials() == {}
