# Pi Bridge

Import [Pi](https://github.com/badlogic/pi) agent session logs (JSONL v3/v4) into MvgeOS Tomes, so any Pi session can resume in MvgeOS.

Pi and MvgeOS both store sessions as JSONL, but their schemas are unrelated: Pi's format versions (v3/v4) are Pi's own invention, and MvgeOS Tomes are v1 with a different entry model. This rune is the compatibility layer — it is deliberately **not** a spell. The importer is user-operated migration tooling; the agent never calls it mid-session.

## Commands

- `mvgeos pi-import <session-file>` — import a Pi `.jsonl` session into `~/.agents/sessions/`.
- `mvgeos pi-import <session-file> --tome-id <id>` — choose the Tome id (default: the Pi session id).
- `mvgeos pi-import <session-file> --tome-dir <dir>` — choose the Tome directory.
- `mvgeos pi-import <session-file> --dry-run` — parse and report without writing anything.
- `mvgeos pi-import <session-file> --force` — overwrite an existing Tome with the same id.

After import, resume normally:

```bash
mvgeos --resume ~/.agents/sessions/<tome-id>.jsonl
```

## How it converts

Both Pi JSONL formats are read (auto-detected from the header line):

| Pi source | Tome entry | Resume behavior |
|---|---|---|
| User message | `message` (role `user`) | Reconstructed as `SummonerRequest` |
| Assistant message | `message` (role `assistant`) | Reconstructed as `MvgeResponse`; Pi `toolCall` blocks become MvgeOS `spell_cast` blocks |
| Tool result | `message` (role `spellResult`, `spell_name`/`spell_cast_id` set) | Linked to its spell call |
| Compaction | `compaction` (`summary`, `manaBefore`, `retainedTail`) | Summary injected + tail replayed |
| System / custom roles / config changes / labels / session info | `custom` | Preserved, invisible to resume |

Details that matter:

- **Timestamps** are normalized to epoch-seconds floats. Pi v3 uses ISO-8601 strings, Pi v4 uses millisecond ints — both are unreadable to the Tome parser as-is.
- **Every entry keeps its full original Pi JSON** under `payload.pi_original`. Pi thinking blocks, image data, usage stats, provider signatures, and unknown extension fields all survive there even when they have no MvgeOS equivalent.
- **Ids and parent chains are preserved verbatim**, so conversation branches stay intact.
- **Pi v4 labels and session names** (stored as KV value writes, not entries) are mined into `custom` entries attached to the tree.
- The imported header carries **no model/spell metadata**, so resume doesn't emit false `MODEL_MISMATCH` / `MISSING_SPELL` diagnostics. Pi model strings remain in `pi_original`.
- The leaf is set to the last real Pi entry, so the imported Tome resumes through the normal path.
- **Strict rejection**: duplicate entry ids, dangling parent references, unknown entry types, and unsupported versions are hard errors naming the offending entry — matching Pi's own strictness.

## Which file to import

If you have both an original Pi v3 file and Pi's own converted v4 copy of the same session, **import the original v3 file**. Pi's v3→v4 migration remints every entry id and converts some entry types into KV writes, so the two files describe the same conversation with different ids.

## Dependencies

`typer>=0.12`.
