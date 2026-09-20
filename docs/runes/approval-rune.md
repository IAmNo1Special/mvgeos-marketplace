# Approval Rune

Fail-closed execution gate: every uncovered mutating spell cast pauses until you approve it — once, for the spell, for the session, or for the project. Deny rules always win, and every decision lands in a durable, redacted audit log before anything executes.

The gate is simple; the boundaries are not. This is an approval layer, not a sandbox: it controls whether a cast executes, never what the model can see.

## The popup

One modal, one cast. Every uncovered mutating cast gets its own prompt showing the operation, the normalized arguments, and the engine-derived spell identity. The operation is frozen while you decide — closing the window means deny.

- **Allow once** — authorizes exactly this cast (cast id, spell identity, argument digest, project, tome). Consumed once, never reconfirmed.
- **Always allow this spell** — persistent grant, pinned to the engine-derived identity *and* the spell's code digest. If the spell's code changes, the grant stops matching until you re-approve. Needs an extra confirmation; an unconstrained grant for a shell or write-capable spell says plainly that it authorizes every future argument.
- **Approve all this session** — memory-only. Clears on tome switch, fork, new tome, project change, or exit. A persistent badge shows while it is active.
- **Approve all in this project** — persistent, keyed to the canonical project root. A rename, move, or different symlink target does not inherit trust.
- **Always deny this spell** — persistent never-allow rule. Overrides every grant, including read-only auto-allow.

Identical denials stay quiet: after a deny, the same exact call is denied without re-prompting for the rest of the session, so a looping agent cannot popup-DDoS you.

## Permissions screen

Marketplace → Approval Rune card → settings cog. It lists session state, trusted projects, always-allowed spells, never-allowed spells, constraints, source identity, last-used time, and recent activity — each with a one-click revoke. Revocation takes effect before the next cast.

## Policy file

User-owned, at `~/.agents/approval/policy.toml` — never inside a repository, so project files cannot grant themselves trust. Writes are atomic with user-only permissions. Malformed TOML fails closed: a bad rule is dropped with a warning; an unparseable file ignores all allows, suspends the session switch, and prompts on every mutating cast.

## Audit log

`~/.agents/approval/audit.jsonl` — one record per gated cast, including automatic decisions, with secret-like fields redacted recursively and full file contents replaced by digests. Survives uninstall; rotates at 30 days / 25 MB.

## Headless

With no presenter bound (headless/CI), mutating casts deny by default. Environment variables never grant approval.

## Data contract for the settings dialog

`get_permissions_view()` returns plain data (`session`, `trusted_projects`, `always_allowed`, `never_allowed`, `source_identity`, `recent_activity`, `warnings`); `revoke_grant(kind, id)` revokes one grant with `kind` in `allow_rule`, `deny_rule`, `project`, `session`.

## Hooks

`after_spell_result` (records execution outcomes for allowed casts; the gate itself registers via the engine's critical gate contract).

## Dependencies

`tomli-w` for policy writes; everything else is stdlib.
