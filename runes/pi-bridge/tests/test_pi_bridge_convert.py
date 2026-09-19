"""Entry-mapping tests for pi-bridge (Pi entries -> Tome entries)."""

from __future__ import annotations

from pathlib import Path

from mvgeos_runes_pi_bridge.converter import convert_parsed, parse_pi_session
from mvgeos_tome.types import TomeEntryType

FIX = Path(__file__).parent / "fixtures"
V3 = FIX / "pi_v3_sample.jsonl"
V4 = FIX / "pi_v4_sample.jsonl"


def by_id(entries):
    return {e.id: e for e in entries}


def test_v3_mapping():
    parsed, _ = parse_pi_session(V3)
    out = convert_parsed(parsed)
    assert len(out) == 13  # every Pi entry retained; v3 has no mined extras
    m = by_id(out)

    # every entry keeps the full original Pi JSON
    for e in out:
        assert "pi_original" in e.payload
        assert e.payload["pi_original"]["id"] == e.id
        assert isinstance(e.timestamp, float)

    # user message
    m1 = m["m1"]
    assert m1.type == TomeEntryType.MESSAGE
    assert m1.payload["role"] == "user"
    assert m1.payload["content"] == "list the repo files"

    # assistant: text passes through, toolCall -> spell_cast, thinking dropped
    # from blocks (kept in pi_original)
    m2 = m["m2"]
    assert m2.type == TomeEntryType.MESSAGE
    assert m2.payload["role"] == "assistant"
    blocks = m2.payload["content"]
    assert blocks[0] == {"type": "text", "text": "I'll list them now."}
    assert blocks[1] == {
        "type": "spell_cast",
        "spell_cast": {"name": "bash", "arguments": {"command": "ls"}},
    }
    assert not any(b.get("type") == "thinking" for b in blocks)
    assert m2.payload["pi_original"]["message"]["content"][1]["type"] == "thinking"
    # Pi "toolUse" -> MvgeOS "spellUse"
    assert m2.payload["stop_reason"] == "spellUse"

    # toolResult -> spellResult with spell identity for reconstruct_invocations
    m3 = m["m3"]
    assert m3.payload["role"] == "spellResult"
    assert m3.payload["spell_name"] == "bash"
    assert m3.payload["spell_cast_id"] == "tc1"
    assert m3.payload["is_error"] is False

    # system role: resume drops it, so it goes to CUSTOM, preserved
    m4 = m["m4"]
    assert m4.type == TomeEntryType.CUSTOM
    assert m4.payload["type"] == "system"

    # compaction keeps the canonical resume shape
    c1 = m["c1"]
    assert c1.type == TomeEntryType.COMPACTION
    assert c1.payload["summary"] == "Listed repo files with bash."
    assert c1.payload["manaBefore"] == 5000
    assert c1.payload["firstKeptEntryId"] == "m1"
    tail = c1.payload["retainedTail"]
    assert [t["role"] for t in tail] == ["user", "assistant"]
    assert tail[1]["content"] == [{"type": "text", "text": "a.py and b.py"}]

    # the rest -> CUSTOM with their Pi kind
    assert m["b1"].payload["type"] == "branch_summary"
    assert m["l1"].payload["data"]["targetId"] == "m2"
    assert m["l1"].payload["data"]["label"] == "important"
    assert m["mc1"].payload["data"]["modelId"] == "claude-test-2"
    assert m["s1"].payload["data"]["name"] == "repo listing"
    assert m["cu1"].payload["data"]["customType"] == "my_plugin"
    assert m["cm1"].payload["data"]["customType"] == "notice"


def test_v3_parent_chain_intact():
    parsed, _ = parse_pi_session(V3)
    out = convert_parsed(parsed)
    m = by_id(out)
    assert m["m2"].parent_id == "m1"
    assert m["c1"].parent_id == "m4"
    assert m["cm1"].parent_id == "cu1"


def test_v4_mapping_and_extras():
    parsed, _ = parse_pi_session(V4)
    out = convert_parsed(parsed)
    m = by_id(out)

    # 6 Pi entries + label extra + session name extra + kv snapshot extra
    assert len(out) == 9

    # image block -> placeholder in resume content, full data in pi_original
    e1 = m["e1"]
    assert e1.payload["role"] == "user"
    assert "[image: image/png" in e1.payload["content"]
    assert "pi_original" in e1.payload
    img = e1.payload["pi_original"]["message"]["content"][1]
    assert img["data"] == "aGVsbG8="

    # mined label attaches to its target entry
    labels = [e for e in out if e.payload.get("type") == "label"]
    assert len(labels) == 1
    assert labels[0].parent_id == "e2"
    assert labels[0].payload["data"] == {"targetId": "e2", "label": "important"}

    # session name + kv snapshot preserved as custom entries
    infos = [e for e in out if e.payload.get("type") == "session_info"]
    assert infos and infos[0].payload["data"] == {"name": "v4 session"}
    kvs = [e for e in out if e.payload.get("type") == "pi_kv_snapshot"]
    assert kvs and "pi.lane.config" in kvs[0].payload["data"]

    # header and payloads carry no model/spells: resume must not warn
    # about mismatches (Pi model strings live in pi_original only)
    for e in out:
        assert "model" not in e.payload
