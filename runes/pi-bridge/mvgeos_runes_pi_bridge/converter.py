"""Import Pi agent session logs (JSONL v3/v4) into MvgeOS Tomes.

Pi format truth (read from Pi source, not docs):
  packages/agent/src/harness/session/jsonl/types.ts      v4 header + entry shapes
  packages/agent/src/harness/session/jsonl/codec.ts      header detection (v4, then v3)
  packages/agent/src/harness/session/jsonl/legacy-v3.ts  v3 header + 10 entry types
  packages/agent/src/harness/session/jsonl/io.ts         transaction-line read/write
  packages/agent/src/harness/session/commit.ts           v4 entry write wrapping
  packages/ai/src/types.ts                               AgentMessage union

MvgeOS truth:
  mvgeos-tome/src/mvgeos_tome/handle.py   header validation, entry parsing, leaf
  mvgeos-tome/src/mvgeos_tome/types.py    TomeEntryType enum (6 values)
  mvgeos-agent/src/mvgeos_agent/agent_session.py  reconstruct_invocations,
    record_message/record_compaction/record_custom payload shapes

Design rules (all decided, see runes/pi-bridge README):
  - v3: bare entry lines, ISO-8601 timestamps. v4: transaction-write lines
    (single write object or array), millisecond timestamps, entries unwrapped
    by stripping the ``kind`` field.
  - Timestamps are normalized to epoch-seconds floats (the Tome read path
    raises on ISO strings and misreads ms ints as year-50000 dates).
  - Every imported entry keeps the full original Pi JSON under
    ``payload["pi_original"]`` — resume ignores unknown payload keys.
  - Entry ids and parent chains are preserved verbatim. Dangling parent
    references are REJECTED (hard error), matching Pi's own strictness.
  - The imported header omits model/spells/contemplation so resume does not
    emit false MODEL_MISMATCH / MISSING_SPELL diagnostics. Pi model strings
    survive inside ``pi_original``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


class PiFormatError(ValueError):
    """Raised when a Pi session file is not a readable v3/v4 JSONL session."""


# MvgeOS tome id rule: ^[A-Za-z0-9][A-Za-z0-9_-]*$
# (mvgeos-tome/src/mvgeos_tome/handle.py::_validate_tome_id). Pi session ids
# are uuid/uuidv7 hex with dashes, so they pass as-is.
_TOME_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

# MvgeOS stop reasons (mvgeos-core/src/mvgeos_core/channel.py::StopReason).
_VALID_STOP_REASONS = frozenset(
    {"pending", "stop", "length", "spellUse", "error", "aborted"}
)
# Pi stopReason -> MvgeOS StopReason. Anything unmapped falls back to "stop",
# which is also what reconstruct_invocations does with invalid values.
_PI_STOP_REASON_MAP = {"toolUse": "spellUse", "deferred": "stop"}

# Closed entry-type sets, from Pi's own parsers (legacy-v3.ts:176-192,
# harness/session/types.ts:17). Unknown types are rejected, not guessed.
_V3_ENTRY_TYPES = frozenset(
    {
        "message",
        "custom",
        "custom_message",
        "branch_summary",
        "compaction",
        "model_change",
        "thinking_level_change",
        "active_tools_change",
        "session_info",
        "label",
    }
)
_V4_ENTRY_TYPES = frozenset({"message", "compaction", "branch_summary", "custom"})

# v4 KV namespaces with user-meaningful data (values.ts, legacy-v3.ts).
_V4_LABEL_NAMESPACE = "pi.entry.label"
_V4_SESSION_NAME_NAMESPACE = "pi.session.name"


@dataclass
class PiEntry:
    """One normalized Pi session entry, format-independent."""

    id: str
    parent_id: str | None
    timestamp: float  # epoch seconds
    kind: str  # Pi entry type, e.g. "message", "compaction", "label"
    message: dict[str, Any] | None  # AgentMessage for kind == "message"
    fields: dict[str, Any]  # type-specific fields (summary, customType, ...)
    original: dict[str, Any]  # full original Pi JSON (goes to pi_original)


@dataclass
class ParsedSession:
    format: str  # "v3" or "v4"
    header: dict[str, Any]
    entries: list[PiEntry]
    # v4 session-level extras mined from kind:"value" writes
    labels: dict[str, Any]  # entry id -> label value (set ops win in file order)
    session_name: Any | None
    kv_snapshot: dict[str, dict[str, Any]]  # other namespaces, for the record
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImportReport:
    source: str
    pi_format: str
    tome_id: str
    tome_path: str | None
    entries: int
    by_pi_type: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    skipped_lines: int = 0
    dry_run: bool = False


# ---------------------------------------------------------------------------
# low-level parsing
# ---------------------------------------------------------------------------


def _read_complete_lines(path: Path) -> tuple[list[str], int]:
    """Read a JSONL file, dropping Pi's torn tail like Pi's own reader does.

    Pi ignores a final line without a terminating newline
    (legacy-v3.ts:335, storage.ts:32-37): the file was mid-write.
    Returns (complete lines, number of skipped tail lines).
    """
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise PiFormatError(f"{path}: empty file, no header line")
    if text.endswith("\n"):
        lines = text.split("\n")[:-1]  # trailing "" is not a line
        skipped = 0
    else:
        *lines, _torn = text.split("\n")
        skipped = 1
    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        raise PiFormatError(f"{path}: no complete lines (torn tail only)")
    return lines, skipped


def _load_json(raw: str, where: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise PiFormatError(f"{where}: invalid JSON: {e}") from e


def _iso_to_seconds(value: Any, where: str) -> float:
    """Pi v3 ISO-8601 string -> epoch seconds."""
    if not isinstance(value, str):
        raise PiFormatError(
            f"{where}: v3 timestamp must be an ISO string, got {value!r}"
        )
    text = value.strip()
    try:
        # Python 3.11+ fromisoformat handles Pi's toISOString() output
        # ("2026-09-10T12:00:01.000Z") natively.
        dt = datetime.fromisoformat(text)
    except ValueError as e:
        raise PiFormatError(f"{where}: bad ISO timestamp {value!r}") from e
    if dt.tzinfo is None:
        # naive ISO (no offset): Pi always means UTC here
        dt = datetime(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.microsecond,
            tzinfo=datetime.UTC,
        )
    return dt.timestamp()


def _ms_to_seconds(value: Any, where: str) -> float:
    """Pi v4 integer millisecond timestamp -> epoch seconds."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PiFormatError(f"{where}: v4 timestamp must be ms int, got {value!r}")
    return float(value) / 1000.0


def detect_format(header: dict[str, Any]) -> str:
    """Identify the Pi JSONL format from the header line.

    Detection order mirrors Pi's own codec.ts: v4 first, then v3-legacy.
    """
    if not isinstance(header, dict):
        raise PiFormatError("header line is not a JSON object")
    if header.get("v") == 4 and header.get("kind") == "header":
        return "v4"
    if header.get("type") == "session" and header.get("version") == 3:
        return "v3"
    raise PiFormatError(
        "unsupported Pi session header (expected v3 "
        '{"type":"session","version":3} or v4 {"v":4,"kind":"header"}); '
        "this importer only reads Pi JSONL v3/v4"
    )


# ---------------------------------------------------------------------------
# v3 front-end: bare entry lines, ISO timestamps
# ---------------------------------------------------------------------------


def _parse_v3(lines: list[str], source: str) -> ParsedSession:
    header = _load_json(lines[0], f"{source}:1")
    if not isinstance(header, dict) or "id" not in header:
        raise PiFormatError(f"{source}:1: v3 header missing 'id'")
    entries: list[PiEntry] = []
    for lineno, raw in enumerate(lines[1:], start=2):
        where = f"{source}:{lineno}"
        obj = _load_json(raw, where)
        if not isinstance(obj, dict):
            raise PiFormatError(f"{where}: entry line is not a JSON object")
        kind = obj.get("type")
        if kind not in _V3_ENTRY_TYPES:
            raise PiFormatError(f"{where}: unknown v3 entry type {kind!r}")
        if "id" not in obj:
            raise PiFormatError(f"{where}: entry missing 'id'")
        if "timestamp" not in obj:
            raise PiFormatError(f"{where}: entry missing 'timestamp'")
        message = obj.get("message")
        if kind == "message" and not isinstance(message, dict):
            raise PiFormatError(f"{where}: message entry missing 'message' object")
        fields = {
            k: v
            for k, v in obj.items()
            if k not in ("id", "parentId", "timestamp", "type", "message")
        }
        # branch_summary "root" sentinel means null (legacy-v3.ts:208-211)
        if kind == "branch_summary" and fields.get("fromId") == "root":
            fields["fromId"] = None
        entries.append(
            PiEntry(
                id=str(obj["id"]),
                parent_id=obj.get("parentId"),
                timestamp=_iso_to_seconds(obj["timestamp"], where),
                kind=kind,
                message=message if isinstance(message, dict) else None,
                fields=fields,
                original=obj,
            )
        )
    return ParsedSession(
        format="v3",
        header=header,
        entries=entries,
        labels={},
        session_name=None,
        kv_snapshot={},
    )


# ---------------------------------------------------------------------------
# v4 front-end: transaction-write lines, ms timestamps
# ---------------------------------------------------------------------------


def _parse_v4(lines: list[str], source: str) -> ParsedSession:
    header = _load_json(lines[0], f"{source}:1")
    if not isinstance(header, dict) or "id" not in header:
        raise PiFormatError(f"{source}:1: v4 header missing 'id'")
    entries: list[PiEntry] = []
    labels: dict[str, Any] = {}
    session_name: Any | None = None
    kv_snapshot: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for lineno, raw in enumerate(lines[1:], start=2):
        where = f"{source}:{lineno}"
        val = _load_json(raw, where)
        writes = val if isinstance(val, list) else [val]
        for w in writes:
            if not isinstance(w, dict):
                raise PiFormatError(f"{where}: write is not a JSON object")
            kind = w.get("kind")
            if kind == "entry":
                entries.append(_parse_v4_entry(w, where, warnings))
            elif kind == "value":
                ns = w.get("namespace")
                op = w.get("op")
                key = w.get("key")
                if ns == _V4_LABEL_NAMESPACE and isinstance(key, str):
                    if op == "set":
                        labels[key] = w.get("value")
                    elif op == "delete":
                        labels.pop(key, None)
                elif ns == _V4_SESSION_NAME_NAMESPACE:
                    if op == "set":
                        session_name = w.get("value")
                    elif op == "delete":
                        session_name = None
                elif isinstance(ns, str):
                    bucket = kv_snapshot.setdefault(ns, {})
                    bucket[key] = (
                        w.get("value") if op == "set" else {"__deleted__": True}
                    )
            elif kind in ("usage", "list"):
                continue  # ledger / list-store rows: not session history
            else:
                warnings.append(f"{where}: unknown write kind {kind!r} — skipped")
    return ParsedSession(
        format="v4",
        header=header,
        entries=entries,
        labels=labels,
        session_name=session_name,
        kv_snapshot=kv_snapshot,
        warnings=warnings,
    )


def _parse_v4_entry(write: dict[str, Any], where: str, warnings: list[str]) -> PiEntry:
    """Unwrap one v4 entry write (commit.ts: entry fields + kind/seq/timestamp)."""
    entry = {k: v for k, v in write.items() if k != "kind"}
    kind = entry.get("type")
    if kind not in _V4_ENTRY_TYPES:
        raise PiFormatError(f"{where}: unknown v4 entry type {kind!r}")
    if "id" not in entry:
        raise PiFormatError(f"{where}: entry missing 'id'")
    base_ts = _ms_to_seconds(entry.get("timestamp"), where)
    message = entry.get("message")
    if kind == "message" and not isinstance(message, dict):
        raise PiFormatError(f"{where}: message entry missing 'message' object")
    # The message's own timestamp is the semantically meaningful per-message
    # time; the entry timestamp is the commit time shared by the transaction.
    ts = base_ts
    if isinstance(message, dict) and "timestamp" in message:
        try:
            ts = _ms_to_seconds(message["timestamp"], f"{where} message.timestamp")
        except PiFormatError:
            warnings.append(f"{where}: bad message.timestamp, using entry time")
    fields = {
        k: v
        for k, v in entry.items()
        if k not in ("id", "parentId", "seq", "timestamp", "type", "message")
    }
    return PiEntry(
        id=str(entry["id"]),
        parent_id=entry.get("parentId"),
        timestamp=ts,
        kind=kind,
        message=message if isinstance(message, dict) else None,
        fields=fields,
        original=entry,
    )


# ---------------------------------------------------------------------------
# mapping Pi entries -> Tome entries
# ---------------------------------------------------------------------------


def _image_placeholder(block: dict[str, Any]) -> str:
    data = block.get("data") or ""
    return (
        f"[image: {block.get('mimeType', 'unknown')}, "
        f"{len(data)} bytes of base64 — full data preserved in pi_original]"
    )


def _user_text(content: Any) -> str:
    """Pi user content (str | (Text|Image)[]) -> plain text for resume."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                parts.append(str(block.get("text", "")))
            elif btype == "image":
                parts.append(_image_placeholder(block))
        return "\n".join(p for p in parts if p)
    if content is None:
        return ""
    return str(content)


def _assistant_blocks(content: Any) -> list[dict[str, Any]]:
    """Pi assistant content -> MvgeOS content blocks.

    text passes through; Pi toolCall becomes the MvgeOS spell_cast block
    (the exact shape compatibility.py and compaction.py read:
    {"type":"spell_cast","spell_cast":{"name","arguments"}}); thinking blocks
    are omitted here but survive verbatim in pi_original (MvgeOS has no
    thinking block type).
    """
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return [{"type": "text", "text": str(content) if content is not None else ""}]
    blocks: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            blocks.append({"type": "text", "text": str(block.get("text", ""))})
        elif btype == "toolCall":
            blocks.append(
                {
                    "type": "spell_cast",
                    "spell_cast": {
                        "name": str(block.get("name", "")),
                        "arguments": block.get("arguments", {}),
                    },
                }
            )
        elif btype == "image":
            blocks.append({"type": "text", "text": _image_placeholder(block)})
        # "thinking" (+ signatures): pi_original only, by design
    return blocks


def _map_stop_reason(value: Any) -> str:
    mapped = _PI_STOP_REASON_MAP.get(value, value)
    return mapped if mapped in _VALID_STOP_REASONS else "stop"


def _spell_result_payload(message: dict[str, Any]) -> dict[str, Any]:
    content = message.get("content")
    if isinstance(content, list):
        blocks: list[dict[str, Any]] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                blocks.append({"type": "text", "text": str(block.get("text", ""))})
            elif block.get("type") == "image":
                blocks.append({"type": "text", "text": _image_placeholder(block)})
    elif isinstance(content, str):
        blocks = [{"type": "text", "text": content}]
    else:
        blocks = []
    return {
        "role": "spellResult",
        "content": blocks,
        "spell_name": str(message.get("toolName") or ""),
        "spell_cast_id": str(message.get("toolCallId") or ""),
        "is_error": bool(message.get("isError")),
    }


def _map_message(entry: PiEntry, message_t: Any, custom_t: Any) -> Any:
    """Pi message entry -> Tome MESSAGE (user/assistant/toolResult) or CUSTOM."""
    from mvgeos_tome.types import TomeEntry  # local import: engine-provided

    message = entry.message or {}
    role = message.get("role")
    payload: dict[str, Any] = {"pi_original": entry.original}
    if role == "user":
        payload.update({"role": "user", "content": _user_text(message.get("content"))})
        entry_type = message_t
    elif role == "assistant":
        payload.update(
            {
                "role": "assistant",
                "content": _assistant_blocks(message.get("content")),
                "stop_reason": _map_stop_reason(message.get("stopReason")),
            }
        )
        entry_type = message_t
    elif role == "toolResult":
        payload.update(_spell_result_payload(message))
        entry_type = message_t
    else:
        # system messages and Pi custom roles (custom, bashExecution,
        # branchSummary, compactionSummary...): resume drops unknown roles, so
        # they go to CUSTOM where they are preserved but invisible.
        custom_type = (
            message.get("customType")
            if role == "custom"
            else (role if isinstance(role, str) else "unknown")
        )
        payload.update({"type": custom_type, "data": {"message": message}})
        entry_type = custom_t
    return TomeEntry(
        id=entry.id,
        parent_id=entry.parent_id,
        type=entry_type,
        timestamp=entry.timestamp,
        payload=payload,
    )


def _map_retained_tail(
    tail: Any,
) -> list[dict[str, Any]]:
    """Map compaction retainedTail messages with the same role logic as live entries.

    Unmappable roles are dropped from the tail (the full messages survive in
    the compaction entry's pi_original); the tail is a resume aid, not storage.
    """
    out: list[dict[str, Any]] = []
    if not isinstance(tail, list):
        return out
    for item in tail:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role == "user":
            out.append({"role": "user", "content": _user_text(item.get("content"))})
        elif role == "assistant":
            out.append(
                {
                    "role": "assistant",
                    "content": _assistant_blocks(item.get("content")),
                    "stop_reason": _map_stop_reason(item.get("stopReason")),
                }
            )
        elif role == "toolResult":
            out.append(_spell_result_payload(item))
    return out


def _map_compaction(entry: PiEntry, compaction_t: Any) -> Any:
    from mvgeos_tome.types import TomeEntry  # local import: engine-provided

    fields = entry.fields
    payload: dict[str, Any] = {
        # canonical record_compaction shape: summary / manaBefore / retainedTail
        "summary": fields.get("summary", ""),
        "manaBefore": fields.get("tokensBefore", 0),
        "retainedTail": _map_retained_tail(fields.get("retainedTail")),
        "pi_original": entry.original,
    }
    if "firstKeptEntryId" in fields:  # v3 only
        payload["firstKeptEntryId"] = fields["firstKeptEntryId"]
    return TomeEntry(
        id=entry.id,
        parent_id=entry.parent_id,
        type=compaction_t,
        timestamp=entry.timestamp,
        payload=payload,
    )


def _map_custom(entry: PiEntry, custom_t: Any) -> Any:
    """Everything else -> CUSTOM, mirroring record_custom's {type, data} shape."""
    from mvgeos_tome.types import TomeEntry  # local import: engine-provided

    data = dict(entry.fields)
    if entry.message is not None:
        data["message"] = entry.message
    # v3 label entries: keep the target + label value explicit at top level too
    payload: dict[str, Any] = {
        "type": entry.kind,
        "data": data,
        "pi_original": entry.original,
    }
    return TomeEntry(
        id=entry.id,
        parent_id=entry.parent_id,
        type=custom_t,
        timestamp=entry.timestamp,
        payload=payload,
    )


def _extra_entry(
    entry_id: str,
    parent_id: str | None,
    timestamp: float,
    custom_type: str,
    data: dict[str, Any],
    original: dict[str, Any],
    custom_t: Any,
) -> Any:
    from mvgeos_tome.types import TomeEntry  # local import: engine-provided

    return TomeEntry(
        id=entry_id,
        parent_id=parent_id,
        type=custom_t,
        timestamp=timestamp,
        payload={"type": custom_type, "data": data, "pi_original": original},
    )


def _unique_id(base: str, taken: set[str]) -> str:
    candidate, n = base, 1
    while candidate in taken:
        n += 1
        candidate = f"{base}-{n}"
    taken.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def parse_pi_session(path: str | Path) -> tuple[ParsedSession, list[str]]:
    """Parse a Pi JSONL session file into format-independent entries."""
    source = Path(path)
    if not source.is_file():
        raise PiFormatError(f"not a file: {source}")
    lines, skipped = _read_complete_lines(source)
    header = _load_json(lines[0], f"{source}:1")
    fmt = detect_format(header)
    parsed = (
        _parse_v3(lines, str(source)) if fmt == "v3" else _parse_v4(lines, str(source))
    )
    warnings: list[str] = list(parsed.warnings)
    if skipped:
        warnings.append(
            f"skipped {skipped} unterminated tail line(s) (file was mid-write)"
        )
    return parsed, warnings


def _validate_tree(entries: list[PiEntry]) -> None:
    """Reject duplicate ids and dangling parent references. Hard fail, by design."""
    seen: dict[str, PiEntry] = {}
    for e in entries:
        if e.id in seen:
            raise PiFormatError(f"duplicate entry id {e.id!r} — import rejected")
        seen[e.id] = e
    for e in entries:
        if e.parent_id is not None and e.parent_id not in seen:
            raise PiFormatError(
                f"entry {e.id!r} references missing parent {e.parent_id!r} "
                "— import rejected (dangling parent)"
            )


def convert_parsed(parsed: ParsedSession) -> list[Any]:
    """Map parsed Pi entries to TomeEntry objects (engine types)."""
    from mvgeos_tome.types import TomeEntryType  # local import: engine-provided

    out: list[Any] = []
    for e in parsed.entries:
        if e.kind == "message":
            out.append(_map_message(e, TomeEntryType.MESSAGE, TomeEntryType.CUSTOM))
        elif e.kind == "compaction":
            out.append(_map_compaction(e, TomeEntryType.COMPACTION))
        else:
            out.append(_map_custom(e, TomeEntryType.CUSTOM))

    # v4 session-level extras mined from kind:"value" writes.
    # They attach to the tree (never dangle) but are NOT resume content:
    # the leaf below targets the last real Pi entry so the branch walk
    # from the leaf covers the conversation, not the metadata.
    taken = {e.id for e in parsed.entries}
    last_ts = max((e.timestamp for e in parsed.entries), default=0.0)
    known_ids = {e.id for e in parsed.entries}
    last_pi_id = parsed.entries[-1].id if parsed.entries else None
    for target_id, value in parsed.labels.items():
        eid = _unique_id(f"pi-label-{target_id}", taken)
        out.append(
            _extra_entry(
                eid,
                target_id if target_id in known_ids else None,
                last_ts,
                "label",
                {"targetId": target_id, "label": value},
                {"namespace": _V4_LABEL_NAMESPACE, "key": target_id, "value": value},
                TomeEntryType.CUSTOM,
            )
        )
    if parsed.session_name is not None:
        out.append(
            _extra_entry(
                _unique_id("pi-session-name", taken),
                last_pi_id,
                last_ts,
                "session_info",
                {"name": parsed.session_name},
                {
                    "namespace": _V4_SESSION_NAME_NAMESPACE,
                    "value": parsed.session_name,
                },
                TomeEntryType.CUSTOM,
            )
        )
    if parsed.kv_snapshot:
        out.append(
            _extra_entry(
                _unique_id("pi-kv-snapshot", taken),
                last_pi_id,
                last_ts,
                "pi_kv_snapshot",
                parsed.kv_snapshot,
                {"kv": parsed.kv_snapshot},
                TomeEntryType.CUSTOM,
            )
        )
    return out


def leaf_target_id(parsed: ParsedSession, tome_entries: list[Any]) -> str:
    """Id of the last real Pi entry — the resume leaf target.

    Mined extras (labels, session name, KV snapshot) are appended after the
    Pi entries in the converted list; the leaf must point at the conversation,
    not at the metadata.
    """
    return tome_entries[len(parsed.entries) - 1].id


def import_pi_session(
    source: str | Path,
    tome_id: str | None = None,
    tome_dir: str | Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> ImportReport:
    """Import a Pi session JSONL file into a MvgeOS Tome.

    Writes through the engine's own TomeHandleFactory so the emitted header
    is always the engine's current format version. Sets the leaf to the last
    imported entry; the result resumes through the normal path.
    """
    from mvgeos_core.constants import DEFAULT_TOME_DIR  # engine-provided
    from mvgeos_tome.handle import TomeHandleFactory  # engine-provided

    parsed, warnings = parse_pi_session(source)
    _validate_tree(parsed.entries)
    if not parsed.entries:
        raise PiFormatError(f"{source}: no entries to import")
    tome_entries = convert_parsed(parsed)

    tid = tome_id or str(parsed.header.get("id"))
    if not tid or not _TOME_ID_RE.match(tid):
        raise PiFormatError(
            f"invalid tome id {tid!r} (must match ^[A-Za-z0-9][A-Za-z0-9_-]*$); "
            "pass --tome-id to choose one"
        )

    by_pi_type: dict[str, int] = {}
    for e in parsed.entries:
        by_pi_type[e.kind] = by_pi_type.get(e.kind, 0) + 1

    target_dir = Path(tome_dir) if tome_dir else DEFAULT_TOME_DIR
    tome_path = target_dir / f"{tid}.jsonl"
    report = ImportReport(
        source=str(source),
        pi_format=parsed.format,
        tome_id=tid,
        tome_path=str(tome_path),
        entries=len(tome_entries),
        by_pi_type=by_pi_type,
        warnings=warnings,
        dry_run=dry_run,
    )
    if dry_run:
        return report

    if tome_path.exists():
        if not force:
            raise PiFormatError(
                f"tome {tid} already exists at {tome_path} — pass --force to overwrite"
            )
        tome_path.unlink()
        lock = tome_path.with_name(tome_path.name + ".lock")
        if lock.exists():
            lock.unlink()

    cwd = str(parsed.header.get("cwd") or "")
    factory = TomeHandleFactory(tome_dir=str(target_dir))
    handle = factory.create_tome(cwd=cwd, tome_id=tid)
    for entry in tome_entries:
        handle.append(entry)
    handle.append_leaf(leaf_target_id(parsed, tome_entries))
    return report
