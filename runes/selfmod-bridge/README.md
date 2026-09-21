# selfmod-bridge Rune

Official **self-modification & customization** bridge for MvgeOS. Gives the
agent the ability to extend itself — scaffold spells, runes, and skills from
normative templates, revise its own instructions, and snapshot / roll back
the files that define it.

## Install

```bash
mvgeos rune install selfmod-bridge
```

On `before_mvge_start` the rune appends a `Self-Modification &
Customization:` section to the system prompt (one `- Runes:
<path>/AGENTS.md` line per configured runes path — no existence check —
plus a `- System Instructions: <path>` line when the file exists;
byte-identical to the text the old engine prompt carried, minus a dead
Spells pointer). Injection runs exactly once per prompt build, guarded on
the section marker itself. When nothing resolves, the prompt is left
unchanged and the rune emits a `selfmod_bridge_warning` event plus a
warning log (zero prompt overhead, not zero signal). Prompt injection needs
the hook payload fields (`config_dir`, `runes_paths`,
`system_path`, `spells_dir`, …) from the parallel engine build —
without them the section is skipped with a warning.

## Usage

Talk to the agent naturally, or use the commands:

- `/selfmod status` — show extension inventory and snapshot count.
- `/selfmod show` — show the effective injected prompt section.

## Spells

Read-only (safe to call any time):

- `extension_status()` — inventory of installed runes/spells/skills, the
  resolved system instructions file, and the snapshot list.
- `self_snapshot(label=None)` — snapshot the self: the system instructions
  file, the active spells dir, `config.json`, and the rune manifest, into
  `<config_dir>/.selfmod-snapshots/<id>/`. Immediately durable; capped at
  20, oldest pruned.

Mutating (narrowed from the model's view and routed through the
approval-rune when it is installed; this rune implements **no private
execution gate**):

- `scaffold_spell(name, description)` — generate `<spells_dir>/<name>.py`
  from the normative template via exclusive-create (never overwrites).
  Seeds a minimal `AGENTS.md` in the spells dir when absent.
- `scaffold_rune(name, description, target_dir=None)` — generate a full
  rune tree (manifest, pyproject, package, root entry, CLI, tests),
  atomically: the tree is built in a sibling staging dir
  (`.selfmod-staging-<uuid>`) and moved into place with one `os.replace`.
  `target_dir` must be absolute and inside a configured runes path;
  default is the first writable configured runes path (agent > user >
  project scope precedence).
- `scaffold_skill(name, description, scope="agent")` — generate
  `<root>/<name>/SKILL.md` at `agent` (`<config_dir>/skills`), `user`
  (`$MVGEOS_GLOBAL_DIR/skills`), or `project` scope. `description` is
  required — the skills-bridge loader skips skills with a missing or empty
  description.
- `revise_persona(old_text, new_text, path=None)` — replace one exact span
  in the instructions file (defaults to the active system instructions
  file). 0 matches → `no_match`, 2+ → `ambiguous_match`; no write.
- `teach(section, mode, old_text="", new_text="", text="", path=None)` —
  `mode="append"` adds a paragraph under the named `## <section>` header
  (header created at EOF when missing; duplicate paragraphs suppressed);
  `mode="replace"` patches one exact match like `revise_persona`.
  Snapshot-first, atomic write.
- `self_rollback(snapshot_id)` — restore a snapshot. Takes a pre-rollback
  snapshot first, so rollback is itself recoverable. The id is resolved
  under the snapshots dir *before* the existence check — traversal gets
  `unknown_snapshot`, never a distinct not-found vs rejected signal.

All mutating spells return `effective_after: "reload"` with a human-readable
`note` — the change is on disk immediately but is not live in the running
process until the next reload. Every mutating result carries these fields,
including failures.

Failure results carry `error` codes: the pinned §6.3 vocabulary (`exists`,
`invalid_name`, `invalid_label`, `invalid_scope`, `no_spells_dir`,
`no_skills_dir`, `no_runes_paths`, `outside_runes_paths`,
`state_not_initialized`, `no_match`, `ambiguous_match`,
`unknown_snapshot`) plus per-operation codes for situations the spec leaves
unnamed (`missing_section`, `invalid_mode`, `missing_old_text`,
`missing_new_text`, `missing_description`, `no_system_path`,
`no_config_dir`, `scaffold_failed`).

## Snapshots

Snapshots live under `<config_dir>/.selfmod-snapshots/<id>/`. Each holds
`SYSTEM.md` (the system instructions file), `spells/` (the active spells
dir), `config.json` (when present), and `manifest.json`. This location is
namespaced but **non-standard** — no established protocol covers snapshots,
so it is documented here rather than invented silently. Rollback restores
the system file and the spells dir, is contained to the snapshot (no path
escapes), and never deletes the snapshots directory itself. A failed
snapshot aborts the mutation before anything is written (snapshot-first).

## Hooks

- `before_mvge_start` — injects the `Self-Modification & Customization:`
  section into the system prompt, exactly once. Emits
  `selfmod_bridge_warning` with a `stage` of `bypass` (nothing resolved),
  `prompt_build` (section build failed), or `payload_shape` (unknown
  payload); the warning log is the live signal until a subscriber consumes
  the event.

## Safety notes

- Extension names are validated (lowercase identifiers, no leading
  underscore; Windows reserved device names like `con`/`nul` rejected) to
  stop path traversal at the API boundary.
- Never-overwrite is enforced by an explicit verify-non-existence check
  under the instance `asyncio.Lock`, immediately before the rename — POSIX
  `os.replace` would replace an existing *empty* dir, so the rename alone
  is not the guard. Cross-process races remain a documented residual.
- Two concurrent same-name scaffolds: one wins, the other gets `exists`;
  no interleaved tree (single-rename atomicity). Crash orphans are
  identifiable by the `.selfmod-staging-<uuid>` name pattern.
- `revise_persona` and `teach` share the instructions file by design (one
  mind, one file) — `revise_persona` patches exact spans, `teach` owns
  append + named-section lifecycle. Both are snapshot-first with atomic
  writes, and both take both sides of the diff explicitly in params so the
  approval presenter shows the user what will change.
