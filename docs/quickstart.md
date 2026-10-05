# Quickstart

From nothing to a Mvge running a real task. Budget five minutes; on a warm
network cache it takes about thirty seconds.

Every command below was run end to end on a clean machine (an empty `$HOME`,
no `.agents` directory) before being written here. Where something is not yet
true, it says so.

## Before you start

You need three things:

| Requirement | Why |
| --- | --- |
| [`uv`](https://docs.astral.sh/uv/) | MvgeOS installs and runs entirely through `uv` / `uvx`. There is no `pip` path. |
| Python 3.13+ | Pulled in automatically by `uv`. You do not need to install it yourself. |
| An API key for a model | MvgeOS does not ship models. You bring a key for the [Realm](concepts.md#mvge-spell-realm) you want to use. The default Realm is OpenRouter. |

You do not need a Python environment, a virtualenv, or a clone of this
repository.

## 1. Install the CLI

Pick one. The first is for trying it; the second gives you a persistent
`mvgeos` command.

```bash
# Try it without installing anything -- runs from a throwaway environment
uvx --from "git+https://github.com/IAmNo1Special/mvgeos#subdirectory=mvgeos-cli" mvgeos --help
```

```bash
# Or install it once and get a real `mvgeos` command on your PATH
uv tool install "git+https://github.com/IAmNo1Special/mvgeos#subdirectory=mvgeos-cli"
mvgeos --help
```

If the second command installs without complaint, the CLI is working. It
prints its command table:

```text
 Usage: mvgeos [OPTIONS] COMMAND [ARGS]...

 MvgeOS - a Python-based AI coding agent

╭─ Commands ────────────────────────────────────────────────────────────────────╮
│ build   Serialise the resolved runtime manifest (read-only).                 │
│ config  Configuration management                                             │
│ info    Display the runtime snapshot as rich tables (read-only).             │
│ mvge    Mvge (agent) management                                              │
│ rune    Extension rune management                                            │
│ setup   Install system dependencies for runes                                │
│ tome    Session tome management                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

!!! note "Running from source instead"
    Cloning the monorepo and running `uv sync && uv run mvgeos` also works, and
    is what contributors want. It pulls in the desktop GUI's dependencies too,
    so it is noticeably heavier than the two commands above.

## 2. Give it access to a model

MvgeOS reaches models through a **Realm** — an extension that speaks one
provider's API. No Realm is installed yet, and the CLI will not talk to a model
without one.

```bash
mvgeos rune install openrouter-realm --confirm-python-deps
```

```text
Successfully installed rune 'openrouter-realm' to
~/.agents/extensions/openrouter-realm
```

`--confirm-python-deps` acknowledges that the Rune's manifest is an instruction
to fetch packages from PyPI. Read the manifest before you pass it if you would
rather not.

If you would rather use a different provider, install that provider's Realm
instead — this one exists because OpenRouter is the default, not because it is
required. See [Runes](runes/openrouter-realm.md) for what it registers.

## 3. Install a Mvge

An engine with no Mvge has no Spells. `coding_mvge` is the coding Mvge — it
ships the development Spells (`bash`, `read`, `write`, `edit`, `find`, `list`,
`grep`).

```bash
mvgeos mvge install coding_mvge
```

```text
Non-interactive session: skipping install of unreviewed python dependencies
['mvgeos-agent', 'mvgeos-core', 'mvgeos-provider', 'mvgeos-runes'].
Re-run with confirm=True to install.
Successfully installed mvge 'coding_mvge' to ~/.agents/agents/coding_mvge
```

The skipped dependencies are the engine packages you already have from step 1,
so leaving them out is correct here.

## 4. Authenticate

MvgeOS looks for a key in this order: the `--api-key` flag, then
`OPENROUTER_API_KEY` in the environment, then `~/.agents/auth/openrouter.json`.

For a one-off run, the environment variable is simplest:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

To avoid re-exporting it in every shell, write it where the CLI looks:

```bash
mkdir -p ~/.agents/auth
printf '{"api_key": "sk-or-..."}' > ~/.agents/auth/openrouter.json
```

If you run `mvgeos` interactively with no key at all, it prompts for one and
saves it to that file for you.

## 5. Run one task

```bash
mvgeos --agent-name coding_mvge "Create a file named hello.txt containing exactly the text: hello from mvgeos"
```

The Mvge reads the directory, casts the `write` Spell, and creates the file. To
see what it cast and what it concluded, replay the Tome it recorded:

```bash
mvgeos tome list
mvgeos tome show <id>
```

## 6. Check what you actually have

Worth running once. It resolves the whole runtime the same way a real run does
and prints it: which Spells are loaded, which Runes are enabled and which
Sigils they hooked, and where every config value came from.

```bash
mvgeos info --agent-name coding_mvge
```

```text
Agent: coding_mvge
Model: nvidia/nemotron-3-ultra-550b-a55b:free

                    Spells
┏━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name       ┃ Source  ┃ Source Rune ┃ Description                               ┃
┡━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ bash       │ builtin │ -           │ Execute a shell command with working dir…  │
│ read       │ builtin │ -           │ Read a file from the workspace…           │
│ write      │ builtin │ -           │ Create or overwrite a file…               │
└────────────┴─────────┴─────────────┴───────────────────────────────────────────┘
```

!!! warning "Put `--agent-name` after the subcommand"
    `mvgeos --agent-name coding_mvge info` silently ignores the flag and reports
    `Agent: default-mvge` with no Spells loaded — no error, just the wrong Mvge.
    `mvgeos info --agent-name coding_mvge` is correct. For the one-shot run in
    step 5 there is no subcommand, so the flag goes before the prompt.

## Where things landed

Everything installed into the standard `.agents` directories:

```text
~/.agents/
├── extensions/openrouter-realm/   # the Realm Rune
├── agents/coding_mvge/            # the Mvge, and its Spells
├── auth/openrouter.json           # your key, if you saved one
└── sessions/                      # Tomes, as JSONL
```

## Interactive use

The one-shot form above is for scripting. For a conversation, run `mvgeos` with
no prompt:

```bash
mvgeos --agent-name coding_mvge
```

Add `--tui` for the full-screen terminal interface. Spell casts that mutate
anything can require your approval; the REPL will prompt, and
`--approval-mode allow-all` skips the gate for a single run if you trust the
Tome.

## What is not verified yet

Stated plainly, because this page is meant to be trustworthy:

- The steps above were run on a clean machine through step 4. The final
  model call depends on a working API key; if yours is wrong or expired you
  will see `Authentication failed (401)` and nothing else will help.
- MvgeOS is pre-1.0 (`v0.6.5`). The command surface moves.
- Rune code runs **in-process** via `importlib`. A Rune is Python that executes
  inside the engine with your permissions. Read manifests before installing
  them. See [Runes](runes/approval-rune.md) for the gate that puts a human
  back in front of mutating casts.

Next: [Concepts](concepts.md) for what the vocabulary means,
[Troubleshooting](troubleshooting.md) if something broke,
or the [Rune catalog](index.md#rune-catalog) to see what else exists.