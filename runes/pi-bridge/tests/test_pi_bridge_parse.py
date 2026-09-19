"""Parsing and validation tests for pi-bridge (no engine dependency)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mvgeos_runes_pi_bridge.converter import (
    PiFormatError,
    _parse_v4_entry,
    _validate_tree,
    detect_format,
    parse_pi_session,
)

FIX = Path(__file__).parent / "fixtures"
V3 = FIX / "pi_v3_sample.jsonl"
V4 = FIX / "pi_v4_sample.jsonl"
TORN = FIX / "pi_v3_torn.jsonl"


def write_tmp(tmp_path: Path, name: str, lines: list) -> Path:
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(o) for o in lines) + "\n", encoding="utf-8")
    return p


# --- format detection -------------------------------------------------------


def test_detect_v3():
    assert detect_format({"type": "session", "version": 3}) == "v3"


def test_detect_v4():
    assert detect_format({"v": 4, "kind": "header"}) == "v4"


def test_detect_v4_wins_over_v3_shaped():
    # detection order mirrors Pi's codec.ts: v4 first
    assert detect_format({"v": 4, "kind": "header", "type": "session"}) == "v4"


@pytest.mark.parametrize(
    "header",
    [
        {},
        {"type": "session", "version": 2},
        {"v": 5, "kind": "header"},
        {"v": 4, "kind": "entry"},
        {"type": "tome", "version": 1},
        "not-a-dict",
    ],
)
def test_detect_rejects(header):
    with pytest.raises(PiFormatError):
        detect_format(header)


# --- v3 parsing --------------------------------------------------------------


def test_parse_v3_fixture():
    parsed, warnings = parse_pi_session(V3)
    assert parsed.format == "v3"
    assert parsed.header["id"] == "v3sess-001"
    assert warnings == []
    kinds = [e.kind for e in parsed.entries]
    assert kinds == [
        "message",
        "message",
        "message",
        "message",
        "compaction",
        "branch_summary",
        "label",
        "model_change",
        "thinking_level_change",
        "active_tools_change",
        "session_info",
        "custom",
        "custom_message",
    ]
    # ISO timestamps -> epoch seconds
    m1 = parsed.entries[0]
    assert m1.id == "m1" and m1.parent_id is None
    assert m1.timestamp == pytest.approx(1789041601.0)  # 2026-09-10T12:00:01Z
    # parent chain preserved verbatim
    assert [e.parent_id for e in parsed.entries[1:4]] == ["m1", "m2", "m3"]
    # branch_summary "root" sentinel -> None (legacy-v3.ts:208-211)
    b1 = parsed.entries[5]
    assert b1.fields["fromId"] is None
    assert b1.original["fromId"] == "root"  # original untouched


def test_parse_v3_unknown_type_rejected(tmp_path):
    p = write_tmp(
        tmp_path,
        "bad.jsonl",
        [
            {
                "type": "session",
                "version": 3,
                "id": "x",
                "timestamp": "2026-09-10T12:00:00.000Z",
                "cwd": "/tmp",
            },
            {
                "type": "message",
                "id": "m1",
                "parentId": None,
                "timestamp": "2026-09-10T12:00:01.000Z",
                "message": {"role": "user", "content": "hi", "timestamp": 1},
            },
            {
                "type": "frobnicate",
                "id": "f1",
                "parentId": "m1",
                "timestamp": "2026-09-10T12:00:02.000Z",
            },
        ],
    )
    with pytest.raises(PiFormatError, match="unknown v3 entry type"):
        parse_pi_session(p)


def test_parse_v3_bad_iso_rejected(tmp_path):
    # header timestamp isn't parsed; the entry timestamp is
    p2 = write_tmp(
        tmp_path,
        "bad2.jsonl",
        [
            {
                "type": "session",
                "version": 3,
                "id": "x",
                "timestamp": "2026-09-10T12:00:00.000Z",
                "cwd": "/tmp",
            },
            {
                "type": "message",
                "id": "m1",
                "parentId": None,
                "timestamp": "yesterday-ish",
                "message": {"role": "user", "content": "hi", "timestamp": 1},
            },
        ],
    )
    with pytest.raises(PiFormatError, match="bad ISO timestamp"):
        parse_pi_session(p2)


# --- v4 parsing --------------------------------------------------------------


def test_parse_v4_fixture():
    parsed, warnings = parse_pi_session(V4)
    assert parsed.format == "v4"
    assert parsed.header["id"] == "v4sess-001"
    assert [e.kind for e in parsed.entries] == [
        "message",
        "message",
        "message",
        "compaction",
        "branch_summary",
        "custom",
    ]
    # ms timestamps -> epoch seconds
    e1 = parsed.entries[0]
    assert e1.timestamp == pytest.approx(1725883201.0)
    # multi-write transaction line unwrapped; usage row skipped
    assert parsed.entries[1].id == "e2"
    # labels mined from kind:"value" writes: set wins, delete removes
    assert parsed.labels == {"e2": "important"}
    # session name mined
    assert parsed.session_name == "v4 session"
    # other KV namespaces kept for the record, ledger/list rows skipped
    assert parsed.kv_snapshot["pi.lane.config"]["config"] == {"model": "gpt-test"}
    # unknown write kind -> warning, not failure
    assert any("mystery" in w for w in warnings)


def test_parse_v4_message_timestamp_preferred():
    warnings: list[str] = []
    e = _parse_v4_entry(
        {
            "id": "e",
            "parentId": None,
            "seq": 1,
            "timestamp": 2000,
            "type": "message",
            "message": {"role": "user", "content": "hi", "timestamp": 1000},
        },
        "test:2",
        warnings,
    )
    assert e.timestamp == pytest.approx(1.0)  # message ts, not commit ts
    assert warnings == []


def test_parse_v4_bad_message_timestamp_falls_back():
    warnings: list[str] = []
    e = _parse_v4_entry(
        {
            "id": "e",
            "parentId": None,
            "seq": 1,
            "timestamp": 2000,
            "type": "message",
            "message": {"role": "user", "content": "hi", "timestamp": "bogus"},
        },
        "test:2",
        warnings,
    )
    assert e.timestamp == pytest.approx(2.0)
    assert len(warnings) == 1


def test_parse_v4_unknown_entry_type_rejected(tmp_path):
    p = write_tmp(
        tmp_path,
        "bad.jsonl",
        [
            {
                "v": 4,
                "kind": "header",
                "id": "x",
                "storageVersion": 1,
                "createdAt": 1,
                "cwd": "/tmp",
            },
            {
                "kind": "entry",
                "id": "e1",
                "parentId": None,
                "seq": 1,
                "timestamp": 1000,
                "type": "frobnicate",
            },
        ],
    )
    with pytest.raises(PiFormatError, match="unknown v4 entry type"):
        parse_pi_session(p)


# --- torn tails, duplicates, dangling parents --------------------------------


def test_torn_tail_skipped():
    # torn fixture = header + m1..m3 with the m3 line unterminated -> dropped
    parsed, warnings = parse_pi_session(TORN)
    assert [e.id for e in parsed.entries] == ["m1", "m2"]
    assert any("mid-write" in w for w in warnings)


def test_empty_file_rejected(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    with pytest.raises(PiFormatError, match="empty file"):
        parse_pi_session(p)


def test_missing_file_rejected(tmp_path):
    with pytest.raises(PiFormatError, match="not a file"):
        parse_pi_session(tmp_path / "nope.jsonl")


def test_unsupported_header_rejected(tmp_path):
    p = write_tmp(tmp_path, "bad.jsonl", [{"type": "tome", "version": 1}])
    with pytest.raises(PiFormatError, match="unsupported Pi session header"):
        parse_pi_session(p)


def test_duplicate_ids_rejected(tmp_path):
    p = write_tmp(
        tmp_path,
        "dup.jsonl",
        [
            {
                "type": "session",
                "version": 3,
                "id": "x",
                "timestamp": "2026-09-10T12:00:00.000Z",
                "cwd": "/tmp",
            },
            {
                "type": "message",
                "id": "m1",
                "parentId": None,
                "timestamp": "2026-09-10T12:00:01.000Z",
                "message": {"role": "user", "content": "hi", "timestamp": 1},
            },
            {
                "type": "message",
                "id": "m1",
                "parentId": None,
                "timestamp": "2026-09-10T12:00:02.000Z",
                "message": {"role": "user", "content": "again", "timestamp": 2},
            },
        ],
    )
    parsed, _ = parse_pi_session(p)
    with pytest.raises(PiFormatError, match="duplicate entry id"):
        _validate_tree(parsed.entries)


def test_dangling_parent_rejected(tmp_path):
    # Malcom's call: dangling parents are a hard error, not a silent remap.
    p = write_tmp(
        tmp_path,
        "dangle.jsonl",
        [
            {
                "type": "session",
                "version": 3,
                "id": "x",
                "timestamp": "2026-09-10T12:00:00.000Z",
                "cwd": "/tmp",
            },
            {
                "type": "message",
                "id": "m1",
                "parentId": "ghost",
                "timestamp": "2026-09-10T12:00:01.000Z",
                "message": {"role": "user", "content": "hi", "timestamp": 1},
            },
        ],
    )
    parsed, _ = parse_pi_session(p)
    with pytest.raises(PiFormatError, match="dangling parent"):
        _validate_tree(parsed.entries)
