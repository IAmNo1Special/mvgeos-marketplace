"""Tests for the OKF concept write lifecycle: write, verify, deprecate, context.

Writes are atomic (temp file + rename), keep timestamped backups under
<config>/.backups/knowledge/<concept-id>/ (max 10, oldest rotated out),
and append entries to the bundle log.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mvgeos_runes_okf_bridge.graph import KnowledgeGraph
from mvgeos_runes_okf_bridge.validator import validate_okf_bundle
from mvgeos_runes_okf_bridge.writer import (
    deprecate_concept,
    ensure_bundle,
    set_concept_context,
    verify_concept,
    write_concept,
)


@pytest.fixture()
def bundle(tmp_path: Path) -> Path:
    root = tmp_path / ".agents" / "knowledge"
    ensure_bundle(root)
    return root


def test_ensure_bundle_scaffolds_index_and_log(bundle: Path) -> None:
    assert (bundle / "index.md").is_file()
    assert 'okf_version: "0.2"' in (bundle / "index.md").read_text(encoding="utf-8")
    assert (bundle / "log.md").is_file()


def test_write_concept_creates_conformant_file(bundle: Path) -> None:
    concept = write_concept(
        bundle,
        "notes/my-note",
        type="Note",
        title="My Note",
        description="A short description.",
        body="# My Note\n\nSome body text.",
        tags=["a", "b"],
        context="auto",
        generated_by="mvgeos/okf-bridge",
    )
    target = bundle / "notes" / "my-note.md"
    assert target.is_file()
    assert concept.id == "notes/my-note"
    assert concept.context == "auto"
    assert concept.generated["by"] == "mvgeos/okf-bridge"
    assert concept.generated["at"]  # timestamp stamped

    report = validate_okf_bundle(bundle)
    assert report.valid, [e.message for e in report.errors]


def test_write_concept_requires_type(bundle: Path) -> None:
    with pytest.raises(ValueError, match="type"):
        write_concept(bundle, "no-type", type="")


def test_write_concept_rejects_path_traversal(bundle: Path) -> None:
    with pytest.raises(ValueError, match="[Ee]scape"):
        write_concept(bundle, "../evil", type="Note")
    with pytest.raises(ValueError, match="[Ee]scape"):
        write_concept(bundle, "sub/../../evil", type="Note")
    assert not (bundle.parent / "evil.md").exists()


def test_write_concept_rejects_absolute_id(bundle: Path) -> None:
    with pytest.raises(ValueError, match="[Aa]bsolute"):
        write_concept(bundle, "/abs/path", type="Note")


def test_write_concept_rejects_bad_context(bundle: Path) -> None:
    with pytest.raises(ValueError, match="context"):
        write_concept(bundle, "x", type="Note", context="sometimes")


def test_rewrite_backs_up_previous_version(bundle: Path) -> None:
    write_concept(bundle, "note", type="Note", body="v1")
    write_concept(bundle, "note", type="Note", body="v2")

    backups = sorted((bundle.parent / ".backups" / "knowledge" / "note").glob("*.md"))
    assert len(backups) == 1
    assert "v1" in backups[0].read_text(encoding="utf-8")
    assert "v2" in (bundle / "note.md").read_text(encoding="utf-8")


def test_backup_rotation_keeps_ten(bundle: Path) -> None:
    for i in range(12):
        write_concept(bundle, "note", type="Note", body=f"v{i}")
    backups = list((bundle.parent / ".backups" / "knowledge" / "note").glob("*.md"))
    assert len(backups) == 10


def test_write_appends_log_entry(bundle: Path) -> None:
    write_concept(bundle, "note", type="Note", generated_by="mvgeos/okf-bridge")
    log = (bundle / "log.md").read_text(encoding="utf-8")
    assert "note" in log
    assert "mvgeos/okf-bridge" in log


def test_verify_concept_appends_verified_entry(bundle: Path) -> None:
    write_concept(bundle, "note", type="Note", generated_by="mvgeos/okf-bridge")
    concept = verify_concept(bundle, "note", by="human:malcom")

    assert concept.trust_tier.value == "human-reviewed"
    assert concept.verified[-1]["by"] == "human:malcom"

    # Reloaded from disk keeps the entry
    reloaded = KnowledgeGraph.load(bundle_path=bundle).get("note")
    assert reloaded is not None
    assert reloaded.trust_tier.value == "human-reviewed"

    log = (bundle / "log.md").read_text(encoding="utf-8")
    assert "human:malcom" in log


def test_verify_requires_actor(bundle: Path) -> None:
    write_concept(bundle, "note", type="Note")
    with pytest.raises(ValueError, match="[Bb]y"):
        verify_concept(bundle, "note", by="")


def test_verify_missing_concept_raises(bundle: Path) -> None:
    with pytest.raises(FileNotFoundError):
        verify_concept(bundle, "ghost", by="human:malcom")


def test_deprecate_concept_flips_status(bundle: Path) -> None:
    write_concept(bundle, "note", type="Note", body="still here")
    concept = deprecate_concept(bundle, "note")
    assert concept.status == "deprecated"
    # File preserved, not deleted
    assert (bundle / "note.md").is_file()

    reloaded = KnowledgeGraph.load(bundle_path=bundle).get("note")
    assert reloaded is not None
    assert reloaded.status == "deprecated"


def test_set_concept_context_flips_injection(bundle: Path) -> None:
    write_concept(bundle, "note", type="Note", context="search-only")
    concept = set_concept_context(bundle, "note", "auto")
    assert concept.context == "auto"
    concept = set_concept_context(bundle, "note", "search-only")
    assert concept.context == "search-only"
    with pytest.raises(ValueError, match="context"):
        set_concept_context(bundle, "note", "always")


def test_lifecycle_preserves_body_text(bundle: Path) -> None:
    body = "# Title\n\nBody with [a link](/other.md) and *formatting*.\n"
    write_concept(bundle, "note", type="Note", body=body)
    verify_concept(bundle, "note", by="human:malcom")
    set_concept_context(bundle, "note", "auto")
    concept = KnowledgeGraph.load(bundle_path=bundle).get("note")
    assert concept is not None
    assert concept.body == body
