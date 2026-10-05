"""The version the docs claim must be the version the engine declares.

The docs name a version in exactly one place -- the Quickstart's "Which
version this page describes" section -- because the install line points at
the engine's default branch and that section is where a reader goes to find
out what they are running. Every other page points there instead of
restating the number.

That is a convention, and conventions rot silently. Three releases in two
days each shipped with a stale version somewhere in these docs: twice
because a page restated a number the Quickstart already owned, and once
because a *historical* claim about which release added a flag was wrong, so
a reader missing that flag was told they were current.

These tests exist so that drift fails the build instead of being found by a
reader. Both are offline. The engine's declared version is read from the
clone CI already makes, not from tags: the tag series is not semver
monotonic (``v3.0.0`` is a September tag from a different numbering era, so
"highest tag" is ``v3.0.0`` and means nothing), and the declared version is
what the package actually calls itself.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
# CI clones the engine as ./mvgeos next to this repository and syncs it
# before pytest runs; conftest.py puts the same tree on sys.path.
ENGINE_PYPROJECT = REPO_ROOT.parent / "mvgeos" / "pyproject.toml"

ANY_VERSION = re.compile(r"v\d+\.\d+\.\d+")
VERSION_SECTION = re.compile(
    r"`(v?\d+\.\d+\.\d+)`,\s*installed as `mvgeos-cli (v?\d+\.\d+\.\d+)`"
)
# The only page allowed to name the current version. Everything else points
# at this section via its anchor.
OWNS_THE_VERSION = "quickstart.md"
VERSION_SECTION_ANCHOR = "which-version-this-page-describes"


def _declared_version() -> str | None:
    if not ENGINE_PYPROJECT.is_file():
        return None
    with ENGINE_PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


DECLARED = _declared_version()

needs_engine = pytest.mark.skipif(
    DECLARED is None,
    reason=f"no engine clone at {ENGINE_PYPROJECT}; cannot check the version claim",
)


@pytest.mark.parametrize("page", sorted(p.name for p in DOCS.glob("*.md")))
def test_only_one_page_names_the_current_version(page: str) -> None:
    """No page but the Quickstart may state the version the reader installed.

    A page may name an older release when it says which release introduced
    something -- that is history and does not rot. What must not survive is
    a *current* version claim anywhere but the section that owns it.
    """
    if page == OWNS_THE_VERSION or DECLARED is None:
        pytest.skip("this page owns the version, or there is nothing to compare")
    versions = {v for v in ANY_VERSION.findall((DOCS / page).read_text())}
    current = f"v{DECLARED}"
    assert current not in versions, (
        f"{page} states {current}, the current version, outside "
        f"{OWNS_THE_VERSION}.md; link its version section instead so there is "
        "one place to update"
    )


@needs_engine
def test_version_section_matches_the_declared_version() -> None:
    """The number a reader is told they installed is the number that ships."""
    text = (DOCS / OWNS_THE_VERSION).read_text()
    found = VERSION_SECTION.search(text)
    assert found, f"{OWNS_THE_VERSION}.md lost its version claim; readers need it"
    claimed, printed = found.group(1).lstrip("v"), found.group(2).lstrip("v")
    assert claimed == printed, (
        f"the section claims {claimed} but shows `uv tool list` printing "
        f"{printed}; a reader comparing the two is told they are wrong"
    )
    assert claimed == DECLARED, (
        f"docs claim {claimed}; the engine declares {DECLARED}"
    )
