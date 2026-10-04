"""Read ``index.json`` as the single source of truth for what we publish.

The marketplace publishes two kinds of artifact:

``runes``
    Extensions. Installed into ``~/.agents/extensions/<name>`` and loaded by
    the engine through ``RuneRunner`` -- a ``rune_factory(api)`` entry point
    plus sigil ``hooks``.

``mvges``
    Agents. Installed into ``~/.agents/agents/<name>`` and resolved *by name*
    (``agent_dir("coding_mvge")``); its spells are discovered by directory
    convention. No sigil hooks, no registry mutation, and the engine never
    reads its ``entry_point``.

Those are genuinely different things, so the split is real. What is *not*
real is a second, hand-maintained copy of that fact. The index already
declares the kind of every artifact; this module is the only place the rest
of the tooling reads it from, and ``tests/test_index_consistency.py`` fails
the build if the index, the filesystem, and the static pytest config ever
disagree.

TOML cannot call into Python, so ``pyproject.toml`` still has to spell out
``testpaths``/``pythonpath`` literally. Rather than pretend otherwise, the
consistency test asserts those literal lists cover every indexed artifact, so
the duplication is checked rather than trusted.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
INDEX_PATH = REPO_ROOT / "index.json"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

#: Index section name -> the manifest keys that kind of artifact must declare.
#:
#: This is the one place the "kind" of an artifact is encoded. A rune is an
#: extension that hooks into a running agent; an mvge is an agent package with
#: its own spells. Both must declare ``entry_point`` and ``name``.
#:
#: ``hooks`` is deliberately *not* required of a rune: ``pi-codec`` is a
#: legitimate rune that contributes a session codec and no sigils. What makes
#: the two kinds distinguishable is that each declares its own marker key and
#: is forbidden the other's -- see ``FORBIDDEN_MANIFEST_KEYS``.
REQUIRED_MANIFEST_KEYS: dict[str, tuple[str, ...]] = {
    "runes": ("types",),
    "mvges": ("spells",),
}

#: Keys that would contradict the section an artifact is listed under.
FORBIDDEN_MANIFEST_KEYS: dict[str, tuple[str, ...]] = {
    "runes": ("spells",),
    "mvges": ("hooks",),
}


@dataclass(frozen=True)
class Artifact:
    """One entry in ``index.json``, resolved against the filesystem."""

    kind: str
    """``"runes"`` or ``"mvges"`` -- which index section declared it."""

    name: str
    """The index key, which must match the manifest ``name``."""

    path: Path
    """Absolute path to the artifact directory."""

    manifest: dict[str, object]
    """Parsed ``<path>/manifest.json``."""

    @property
    def relative_path(self) -> str:
        return self.path.relative_to(REPO_ROOT).as_posix()

    @property
    def is_itself_a_package(self) -> bool:
        """True when the artifact directory *is* the importable package.

        Two layouts exist in this marketplace and both are legitimate:

        ``runes/skills-bridge``
            ``manifest.json`` sits beside the ``mvgeos_runes_skills_bridge``
            package, so the artifact directory is the import root. This is the
            convention every rune follows.

        ``mvges/coding_mvge``
            The directory is itself the ``coding_mvge`` package, with the
            manifest inside it, so the import root is its *parent*.

        Getting this wrong puts the wrong directory on ``sys.path``, which
        makes the artifact importable as a namespace package of its own name --
        a quiet shadowing hazard rather than an error.
        """
        return (self.path / "__init__.py").is_file()

    @property
    def import_root(self) -> Path:
        """Directory to put on ``sys.path`` to import this artifact."""
        return self.path.parent if self.is_itself_a_package else self.path

    @property
    def top_level_names(self) -> set[str]:
        """Top-level module names this artifact contributes.

        Empty for a single-file rune with no package (``session-title`` keeps
        its whole implementation in ``rune.py``); such an artifact needs no
        ``sys.path`` entry, and adding one would only make a bare ``import
        rune`` ambiguous between artifacts.
        """
        if self.is_itself_a_package:
            return {self.path.name}
        return {
            child.name
            for child in self.path.iterdir()
            if child.is_dir() and (child / "__init__.py").is_file()
        }

    @property
    def test_dir(self) -> Path:
        return self.path / "tests"

    def has_tests(self) -> bool:
        return self.test_dir.is_dir()

    def entry_point_path(self) -> Path:
        """Where ``manifest.entry_point`` must exist for the engine to load it."""
        return self.path / str(self.manifest.get("entry_point", ""))


def load_index() -> dict[str, object]:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def iter_artifacts() -> Iterator[Artifact]:
    """Yield every artifact the marketplace publishes, in index order."""
    index = load_index()
    for kind in REQUIRED_MANIFEST_KEYS:
        section = index.get(kind, {})
        assert isinstance(section, dict), (
            f"index.json section {kind!r} must be an object"
        )
        for name, entry in sorted(section.items()):
            path = (REPO_ROOT / entry["path"]).resolve()
            manifest_path = path / "manifest.json"
            manifest: dict[str, object] = {}
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            yield Artifact(
                kind=kind,
                name=name,
                path=path,
                manifest=manifest,
            )


def artifacts() -> list[Artifact]:
    return list(iter_artifacts())


def artifact_dirs_on_disk() -> list[Path]:
    """Artifact directories present in the tree, whether or not they are indexed.

    This is how an artifact that exists but was never added to ``index.json``
    gets noticed. Only immediate subdirectories that carry a ``manifest.json``
    count, so packaging output such as ``__pycache__`` is ignored.
    """
    found: list[Path] = []
    for kind_dir in sorted(REPO_ROOT.iterdir()):
        if not kind_dir.is_dir() or kind_dir.name not in REQUIRED_MANIFEST_KEYS:
            continue
        for candidate in sorted(kind_dir.iterdir()):
            if candidate.is_dir() and (candidate / "manifest.json").is_file():
                found.append(candidate.resolve())
    return found


def pytest_config() -> dict[str, object]:
    """The ``[tool.pytest.ini_options]`` table from the root ``pyproject.toml``."""
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    pytest_table = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    return pytest_table


def as_repo_paths(paths: list[Path]) -> set[str]:
    """Normalise absolute paths to ``/``-separated paths relative to the repo."""
    return {p.resolve().relative_to(REPO_ROOT).as_posix() for p in paths}
