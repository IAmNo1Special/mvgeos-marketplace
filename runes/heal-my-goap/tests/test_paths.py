"""The OpenRouter credential file must live in the relocated global layer.

``rune_factory`` hardcoded ``~/.agents/.mvgeos/auth/openrouter.json``. Under
``$MVGEOS_GLOBAL_DIR`` the engine relocates its credential store, so a
relocated run either failed to find its key or read one the user had not
placed there.

Only the *global layer* is in scope here. The ``.mvgeos`` path segment is
the engine's own legacy credential location and is tracked separately; this
rune must not silently change which filename it reads.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mvgeos_core import GLOBAL_DIR_ENV, global_agents_dir

from mvgeos_runes_heal_my_goap.paths import openrouter_auth_path


@pytest.fixture
def relocated_global(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Point the global ``.agents`` layer at a temp root for one test."""
    # Deliberately local rather than shared from the repository root:
    # each rune is an independently installable, independently testable
    # package (its own pyproject.toml declares its own testpaths), and a
    # suite run from inside the rune directory never loads the root
    # conftest.py.
    root = tmp_path / "global"
    monkeypatch.setenv(GLOBAL_DIR_ENV, str(root))
    return root




def test_auth_path_follows_the_relocated_layer(relocated_global: Path) -> None:
    """The credential path moves with the global layer."""
    assert openrouter_auth_path() == (
        relocated_global / ".mvgeos" / "auth" / "openrouter.json"
    )


def test_auth_path_is_not_taken_from_the_real_home_layer(
    relocated_global: Path,
) -> None:
    """The literal home layer is no longer consulted.

    Asserted unconditionally: the fixture relocates to a temp directory, so
    a conditional here would only ever be a silent skip.
    """
    home_layer = (
        Path("~/.agents").expanduser()
        / ".mvgeos"
        / "auth"
        / "openrouter.json"
    )
    assert openrouter_auth_path() != home_layer
    assert not openrouter_auth_path().is_relative_to(Path.home())


def test_default_location_without_the_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no override the path is unchanged from what it always was."""
    monkeypatch.delenv(GLOBAL_DIR_ENV, raising=False)
    assert global_agents_dir() == Path("~/.agents").expanduser()
    assert openrouter_auth_path() == (
        Path("~/.agents").expanduser()
        / ".mvgeos"
        / "auth"
        / "openrouter.json"
    )


def test_auth_path_is_resolved_at_call_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Read the override per call, not once at import.

    ``rune_factory`` runs at load time, which can be well after the process
    started; freezing the layer at import is what made the original
    expression wrong for any late-set override.
    """
    monkeypatch.delenv(GLOBAL_DIR_ENV, raising=False)
    assert openrouter_auth_path().is_absolute()

    relocated = tmp_path / "relocated"
    monkeypatch.setenv(GLOBAL_DIR_ENV, str(relocated))
    assert openrouter_auth_path() == (
        relocated / ".mvgeos" / "auth" / "openrouter.json"
    )


def test_auth_path_is_an_absolute_path_under_the_layer(
    relocated_global: Path,
) -> None:
    """Never a relative path, whatever the override looks like."""
    path = openrouter_auth_path()
    assert path.is_absolute()
    assert path.is_relative_to(relocated_global)
