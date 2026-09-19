"""Roundtrip tests: import a Pi file, then prove the Tome actually resumes.

Uses the real TomeHandleFactory write path and MvgeTome.reconstruct_invocations
— the same code the resume path runs. If this passes, the imported Tome is
resume-compatible by construction, not by assertion.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mvgeos_agent.agent_session import MvgeTome
from mvgeos_core.channel import MvgeResponse
from mvgeos_core.invocations import SummonerRequest
from mvgeos_core.spells import SpellResultMessage
from mvgeos_runes_pi_bridge.converter import PiFormatError, import_pi_session
from mvgeos_tome.handle import TomeHandleFactory
from mvgeos_tome.types import TomeEntryType

FIX = Path(__file__).parent / "fixtures"
V3 = FIX / "pi_v3_sample.jsonl"
V4 = FIX / "pi_v4_sample.jsonl"


def open_tome(factory: TomeHandleFactory, tome_id: str) -> MvgeTome:
    return MvgeTome(
        factory, factory.open_write(tome_id), factory.open_read(tome_id), None
    )


def test_v3_import_resumes(tmp_path):
    tome_dir = tmp_path / "sessions"
    report = import_pi_session(V3, tome_dir=tome_dir)
    assert report.pi_format == "v3"
    assert report.tome_id == "v3sess-001"  # Pi session id reused
    assert report.entries == 13
    assert Path(report.tome_path).is_file()

    factory = TomeHandleFactory(tome_dir=tome_dir)

    # header is a valid MvgeOS v1 tome
    meta = factory.open_read("v3sess-001").get_metadata()
    assert meta.version == 1
    assert meta.id == "v3sess-001"
    assert meta.model is None  # no false MODEL_MISMATCH diagnostics

    # leaf points at the last imported entry (the LEAF marker itself is entries[-1])
    entries = factory.open_read("v3sess-001").get_entries()
    content_ids = [e.id for e in entries if e.type != TomeEntryType.LEAF]
    assert factory.get_leaf_id("v3sess-001") == content_ids[-1] == "cm1"

    # the actual resume path reconstructs the conversation
    invocations = open_tome(factory, "v3sess-001").reconstruct_invocations()
    kinds = [type(i).__name__ for i in invocations]
    assert kinds == [
        "SummonerRequest",  # m1
        "MvgeResponse",  # m2
        "SpellResultMessage",  # m3
        "SummonerRequest",  # c1 summary
        "SummonerRequest",  # retainedTail user
        "MvgeResponse",  # retainedTail assistant
    ]
    assert invocations[0].content == "list the repo files"
    blocks = invocations[1].content
    assert blocks[0] == {"type": "text", "text": "I'll list them now."}
    assert blocks[1]["type"] == "spell_cast"
    assert blocks[1]["spell_cast"]["name"] == "bash"
    assert isinstance(invocations[2], SpellResultMessage)
    assert invocations[2].spell_name == "bash"
    assert invocations[2].spell_cast_id == "tc1"
    assert invocations[3].content.startswith(
        "Summary of earlier conversation:\n\nListed repo files"
    )
    assert invocations[5].content == [{"type": "text", "text": "a.py and b.py"}]

    # every stored line is valid JSON with the original Pi data attached
    for line in Path(report.tome_path).read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        if obj.get("type") == "leaf":
            continue
        if obj.get("type") == "session":
            assert obj["version"] == 1
            continue
        assert "pi_original" in obj["payload"]


def test_v4_import_resumes(tmp_path):
    tome_dir = tmp_path / "sessions"
    report = import_pi_session(V4, tome_dir=tome_dir)
    assert report.pi_format == "v4"
    assert report.tome_id == "v4sess-001"
    assert report.entries == 9  # 6 entries + label + session name + kv snapshot

    factory = TomeHandleFactory(tome_dir=tome_dir)
    entries = factory.open_read("v4sess-001").get_entries()
    content_ids = [e.id for e in entries if e.type != TomeEntryType.LEAF]
    # leaf targets the last real Pi entry (e6), not the mined metadata extras
    assert factory.get_leaf_id("v4sess-001") == "e6"
    assert content_ids[-4] == "e6"

    invocations = open_tome(factory, "v4sess-001").reconstruct_invocations()
    assert isinstance(invocations[0], SummonerRequest)
    assert "hello" in invocations[0].content
    assert isinstance(invocations[1], MvgeResponse)
    assert isinstance(invocations[2], SpellResultMessage)
    assert invocations[2].spell_name == "read"
    assert invocations[3].content.startswith("Summary of earlier conversation")


def test_tome_id_override_and_force(tmp_path):
    tome_dir = tmp_path / "sessions"
    r1 = import_pi_session(V3, tome_id="custom-id", tome_dir=tome_dir)
    assert r1.tome_id == "custom-id"

    # second import without --force refuses to overwrite
    with pytest.raises(PiFormatError, match="already exists"):
        import_pi_session(V3, tome_id="custom-id", tome_dir=tome_dir)

    r2 = import_pi_session(V3, tome_id="custom-id", tome_dir=tome_dir, force=True)
    assert r2.tome_id == "custom-id"


def test_invalid_tome_id_rejected(tmp_path):
    with pytest.raises(PiFormatError, match="invalid tome id"):
        import_pi_session(V3, tome_id="not a valid id!", tome_dir=tmp_path)


def test_dry_run_writes_nothing(tmp_path):
    tome_dir = tmp_path / "sessions"
    report = import_pi_session(V3, tome_dir=tome_dir, dry_run=True)
    assert report.dry_run is True
    assert report.entries == 13
    assert not tome_dir.exists()


def test_empty_session_rejected(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text(
        json.dumps(
            {
                "type": "session",
                "version": 3,
                "id": "x",
                "timestamp": "2026-09-10T12:00:00.000Z",
                "cwd": "/tmp",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(PiFormatError, match="no entries to import"):
        import_pi_session(p, tome_dir=tmp_path)
