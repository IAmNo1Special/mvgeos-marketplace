"""Generate pi-bridge test fixtures (realistic Pi v3/v4 session files)."""

import json
from pathlib import Path


def gen_fixtures() -> None:
    FIX = Path(__file__).parent / "fixtures"
    FIX.mkdir(exist_ok=True)

    V3 = [
        {
            "type": "session",
            "version": 3,
            "id": "v3sess-001",
            "timestamp": "2026-09-10T12:00:00.000Z",
            "cwd": "/tmp/pi-proj",
        },
        {
            "type": "message",
            "id": "m1",
            "parentId": None,
            "timestamp": "2026-09-10T12:00:01.000Z",
            "message": {
                "role": "user",
                "content": "list the repo files",
                "timestamp": 1725883201000,
            },
        },
        {
            "type": "message",
            "id": "m2",
            "parentId": "m1",
            "timestamp": "2026-09-10T12:00:05.000Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll list them now."},
                    {"type": "thinking", "thinking": "which tool? ls is fine"},
                    {
                        "type": "toolCall",
                        "id": "tc1",
                        "name": "bash",
                        "arguments": {"command": "ls"},
                    },
                ],
                "api": "anthropic-messages",
                "provider": "anthropic",
                "model": "claude-test",
                "usage": {"input": 10, "output": 20, "totalTokens": 30},
                "stopReason": "toolUse",
                "timestamp": 1725883205000,
            },
        },
        {
            "type": "message",
            "id": "m3",
            "parentId": "m2",
            "timestamp": "2026-09-10T12:00:06.000Z",
            "message": {
                "role": "toolResult",
                "toolCallId": "tc1",
                "toolName": "bash",
                "content": [{"type": "text", "text": "a.py\nb.py"}],
                "isError": False,
                "timestamp": 1725883206000,
            },
        },
        {
            "type": "message",
            "id": "m4",
            "parentId": "m3",
            "timestamp": "2026-09-10T12:00:07.000Z",
            "message": {
                "role": "system",
                "content": "system prompt here",
                "timestamp": 1725883207000,
            },
        },
        {
            "type": "compaction",
            "id": "c1",
            "parentId": "m4",
            "timestamp": "2026-09-10T12:01:00.000Z",
            "summary": "Listed repo files with bash.",
            "firstKeptEntryId": "m1",
            "tokensBefore": 5000,
            "fromHook": False,
            "retainedTail": [
                {
                    "role": "user",
                    "content": "list the repo files",
                    "timestamp": 1725883201000,
                },
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "a.py and b.py"}],
                    "stopReason": "stop",
                    "timestamp": 1725883260000,
                },
            ],
        },
        {
            "type": "branch_summary",
            "id": "b1",
            "parentId": "c1",
            "timestamp": "2026-09-10T12:01:01.000Z",
            "fromId": "root",
            "summary": "branched to try something",
            "fromHook": False,
        },
        {
            "type": "label",
            "id": "l1",
            "parentId": "b1",
            "timestamp": "2026-09-10T12:01:02.000Z",
            "targetId": "m2",
            "label": "important",
        },
        {
            "type": "model_change",
            "id": "mc1",
            "parentId": "l1",
            "timestamp": "2026-09-10T12:01:03.000Z",
            "provider": "anthropic",
            "modelId": "claude-test-2",
        },
        {
            "type": "thinking_level_change",
            "id": "tl1",
            "parentId": "mc1",
            "timestamp": "2026-09-10T12:01:04.000Z",
            "thinkingLevel": "high",
        },
        {
            "type": "active_tools_change",
            "id": "at1",
            "parentId": "tl1",
            "timestamp": "2026-09-10T12:01:05.000Z",
            "activeToolNames": ["bash"],
        },
        {
            "type": "session_info",
            "id": "s1",
            "parentId": "at1",
            "timestamp": "2026-09-10T12:01:06.000Z",
            "name": "repo listing",
        },
        {
            "type": "custom",
            "id": "cu1",
            "parentId": "s1",
            "timestamp": "2026-09-10T12:01:07.000Z",
            "customType": "my_plugin",
            "data": {"foo": 1},
        },
        {
            "type": "custom_message",
            "id": "cm1",
            "parentId": "cu1",
            "timestamp": "2026-09-10T12:01:08.000Z",
            "customType": "notice",
            "content": "a notice",
            "display": True,
        },
    ]

    V4 = [
        {
            "v": 4,
            "kind": "header",
            "id": "v4sess-001",
            "storageVersion": 1,
            "createdAt": 1725883200000,
            "cwd": "/tmp/pi-proj",
        },
        {
            "kind": "entry",
            "id": "e1",
            "parentId": None,
            "seq": 1,
            "timestamp": 1725883201000,
            "type": "message",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "hello"},
                    {"type": "image", "data": "aGVsbG8=", "mimeType": "image/png"},
                ],
                "timestamp": 1725883201000,
            },
        },
        [  # multi-write transaction: entry + usage ledger row
            {
                "kind": "entry",
                "id": "e2",
                "parentId": "e1",
                "seq": 2,
                "timestamp": 1725883205000,
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "hi"},
                        {
                            "type": "toolCall",
                            "id": "tc9",
                            "name": "read",
                            "arguments": {"path": "a.py"},
                        },
                    ],
                    "api": "openai-completions",
                    "provider": "openai",
                    "model": "gpt-test",
                    "usage": {"input": 5, "output": 7, "totalTokens": 12},
                    "stopReason": "toolUse",
                    "timestamp": 1725883205000,
                },
            },
            {
                "kind": "usage",
                "id": "u1",
                "seq": 3,
                "usage": {"input": 5, "output": 7},
                "entryId": "e2",
            },
        ],
        {
            "kind": "entry",
            "id": "e3",
            "parentId": "e2",
            "seq": 4,
            "timestamp": 1725883206000,
            "type": "message",
            "message": {
                "role": "toolResult",
                "toolCallId": "tc9",
                "toolName": "read",
                "content": [{"type": "text", "text": "contents"}],
                "isError": False,
                "timestamp": 1725883206000,
            },
        },
        {
            "kind": "value",
            "op": "set",
            "seq": 5,
            "namespace": "pi.entry.label",
            "key": "e2",
            "value": "important",
        },
        {
            "kind": "value",
            "op": "set",
            "seq": 6,
            "namespace": "pi.entry.label",
            "key": "e9-missing",
            "value": "dangling-target",
        },
        {
            "kind": "value",
            "op": "delete",
            "seq": 7,
            "namespace": "pi.entry.label",
            "key": "e9-missing",
        },
        {
            "kind": "value",
            "op": "set",
            "seq": 8,
            "namespace": "pi.session.name",
            "key": "name",
            "value": "v4 session",
        },
        {
            "kind": "value",
            "op": "set",
            "seq": 9,
            "namespace": "pi.lane.config",
            "key": "config",
            "value": {"model": "gpt-test"},
        },
        {
            "kind": "entry",
            "id": "e4",
            "parentId": "e3",
            "seq": 10,
            "timestamp": 1725883260000,
            "type": "compaction",
            "summary": "Said hi.",
            "retainedTail": [
                {"role": "user", "content": "hello", "timestamp": 1725883201000},
            ],
            "tokensBefore": 120,
            "fromHook": False,
        },
        {
            "kind": "entry",
            "id": "e5",
            "parentId": "e4",
            "seq": 11,
            "timestamp": 1725883261000,
            "type": "branch_summary",
            "fromId": None,
            "summary": "tried a branch",
            "fromHook": False,
        },
        {
            "kind": "entry",
            "id": "e6",
            "parentId": "e5",
            "seq": 12,
            "timestamp": 1725883262000,
            "type": "custom",
            "customType": "plugin_x",
            "data": {"a": [1, 2]},
        },
        {
            "kind": "list",
            "op": "append",
            "seq": 13,
            "namespace": "pi.pending.assistant_frame",
            "key": "f1",
            "value": {},
        },
        {"kind": "mystery", "seq": 14, "note": "unknown write kind"},
    ]

    (FIX / "pi_v3_sample.jsonl").write_text(
        "\n".join(json.dumps(o) for o in V3) + "\n", encoding="utf-8"
    )
    (FIX / "pi_v4_sample.jsonl").write_text(
        "\n".join(json.dumps(o) for o in V4) + "\n", encoding="utf-8"
    )
    # torn tail: last line has no terminating newline -> must be skipped
    torn = V3[:4]
    (FIX / "pi_v3_torn.jsonl").write_text(
        "\n".join(json.dumps(o) for o in torn), encoding="utf-8"
    )
    print("fixtures written:", sorted(p.name for p in FIX.iterdir()))


if __name__ == "__main__":
    gen_fixtures()
