"""Pin first-party packages to this repository, not to whatever is installed.

The engine puts ``~/.agents/agents`` at the front of ``sys.path`` the moment an
Mvge is constructed (``mvgeos_agent.mvge``), and ``coding_mvge`` builds one at
module scope. The consequence for this suite was severe and entirely silent:
``mvges/coding_mvge/tests`` imported ``coding_mvge``, which resolved to the
copy installed on the developer's machine rather than the tree beside it, so
those tests asserted against a stale snapshot and passed while the source was
broken. Adding ``mvges/coding_mvge`` to the ``pythonpath`` ini is not enough on
its own -- the insert lands at position 0 at runtime and wins.

So this pins resolution explicitly, before collection:

- Put this repository's own package roots at the front of ``sys.path``.
- Evict any already-imported first-party module that resolved outside the
  repository, so the next import re-resolves from the source tree.
- Assert the result, so any future regression fails loudly rather than
  quietly testing the wrong code.

The assertion is the point. A silent wrong-tree import is worse than no test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent

#: Import root for the coding_mvge package, which lives at
#: ``mvges/coding_mvge/`` -- so its root is ``mvges/``.
#:
#: Only this one directory is managed here. The rune roots are deliberately
#: left to the ``pythonpath`` ini option: every rune directory holds a
#: top-level ``rune.py`` and ``cli.py``, so reordering them here changes which
#: one a bare ``import rune`` resolves to.
_MVGE_ROOT = _REPO_ROOT / "mvges"
#: Top-level names that must resolve inside this repository.
_PINNED = ("coding_mvge",)


def _outside_repo(module: object) -> bool:
    """True when an imported module's file lives outside this repository."""
    file = getattr(module, "__file__", None)
    if file is None:
        return False
    try:
        Path(file).resolve().relative_to(_REPO_ROOT)
    except ValueError:
        return True
    return False


def pytest_configure(config: pytest.Config) -> None:
    import importlib

    for root in (_MVGE_ROOT,):
        text = str(root)
        while text in sys.path:
            sys.path.remove(text)
        sys.path.insert(0, text)

    # Drop anything already imported from outside the repository, including
    # its submodules, so the next import re-resolves against sys.path.
    for name in list(sys.modules):
        if name.split(".", 1)[0] == "coding_mvge" and _outside_repo(sys.modules[name]):
            del sys.modules[name]

    for name in _PINNED:
        module = importlib.import_module(name)
        assert not _outside_repo(module), (
            f"{name} resolved to {getattr(module, '__file__', '?')}, which is "
            f"outside {_REPO_ROOT}. Tests would run against an installed copy "
            f"instead of this checkout."
        )
