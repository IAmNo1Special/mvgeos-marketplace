# Quickstart

From nothing to a Mvge running a real task. Budget five minutes; on a warm
network cache it takes about forty seconds — plus however long you spend
retrying the model call, which is the step that is not reliable yet.

Every command below was run end to end on a clean machine — an empty `$HOME`,
empty `XDG` directories, a private `uv` cache, and nothing preinstalled on
`PATH` — before being written here, including the model call in step 5. Each
command is re-run on a clean machine on a schedule, because a documented command
that stops working is worse than no documentation at all. Where something is not
yet true, or is true only intermittently, it says so; see
[What is not verified yet](#what-is-not-verified-yet).

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

This is real output, pasted unedited from a run on a clean machine. The only
change is that the terminal's own line wrapping is preserved rather than
reflowed:

```text
Created hello.txt with the content "hello from mvgeos". Verified the file contents match
exactly.
Stop reason: stop
```

The file is really there, and the content is byte-for-byte what was asked for:

```console
$ ls -l hello.txt
-rw-r--r-- 1 you you 17 hello.txt
$ od -c hello.txt
0000000   h   e   l   l   o       f   r   o   m       m   v   g   e   o
0000020   s
0000021
$ wc -c hello.txt
17 hello.txt
```

17 bytes for 17 characters: there is no trailing newline, because the Mvge was
asked for *exactly* that text and did precisely that.

It took about 30 seconds against the default free model.

!!! warning "The default free model is the fragile part of this page"
    Everything above this warning was verified on a clean machine. The model
    call was verified on a different day than the install, and on a later
    re-verification **three consecutive runs of this exact task failed** against
    the default free model:

    ```text
    Error: Upstream error from Nvidia: Service temporarily overloaded
    ```

    Twice the correct 17-byte `hello.txt` was already on disk when the run
    exited non-zero; once nothing was. Retrying immediately did not clear it.

    So expect step 5 to fail the first time or two, and check the file before
    you assume you lost the work:

    ```bash
    ls -l hello.txt && cat hello.txt
    ```

    Naming a different model made the same task succeed, exit 0:

    ```bash
    mvgeos -m nvidia/nemotron-3-super-120b-a12b:free --agent-name coding_mvge \
      "Create a file named hello.txt containing exactly the text: hello from mvgeos"
    ```

    `-m` only accepts ids from the model list shipped in the repository, so read
    it before reaching for an arbitrary OpenRouter model. See
    [Troubleshooting](troubleshooting.md#error-unknown-model).

### What actually happened underneath

The Mvge verified its own work rather than assuming it, which is the behaviour
you want. Here is the run as recorded in the Tome, unedited:

```text
think  The user wants me to create a file named hello.txt with the exact text "hello from mvgeos". I'll use the write tool to do this.
cast   write({"path": ".../hello.txt", "content": "hello from mvgeos"})
result Wrote to .../hello.txt
think  The file has been created successfully. Let me confirm it contains the exact text requested
cast   read({"path": ".../hello.txt"})
result Invalid arguments for spell read: 2 validation errors for read_Schema
       offset
         Input should be a valid integer
       limit
         Input should be a valid integer
think  The read function requires offset and limit parameters. Let me try again with proper parameters
cast   read({"limit": 10, "path": ".../hello.txt", "offset": 1})
result hello from mvgeos
say    Created `hello.txt` with the content "hello from mvgeos". Verified the file contents match exactly.
```

The `read` Spell failed on its first call even though the Mvge passed only the
required argument, exactly as the Spell's own signature allows. This is a real
engine bug, not a mistake in the prompt: a Spell argument declared
`int | None = None` loses its nullability when the JSON Schema is turned into a
validator, and because a Spell is validated twice per cast, the first pass fills
the omitted arguments with `null` and the second pass then rejects them. Four of
the five built-in Spells in `coding_mvge` are affected (`read`, `grep`, `find`,
`list_files`).

It is tracked as SOM-23. It is harmless to correctness — the task completed and
the file was right — but it costs one extra model round-trip per self-check, so
expect a slightly higher Mana bill than the transcript implies.

### Replay it yourself

Every run is recorded. To see what the Mvge cast and concluded:

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

Stated plainly, because this page is meant to be trustworthy. Every command
above has been run end to end on a clean machine, including the model call in
step 5. What remains true:

- The install line is a `git+` URL, not a package name. `uvx mvgeos` does **not**
  resolve yet, because the distribution has not reached PyPI:

    ```console
    $ uvx mvgeos --help
    × No solution found when resolving tool dependencies:
    ╰─▶ Because mvgeos was not found in the package registry and you require
        mvgeos, we can conclude that your requirements are unsatisfiable.
    ```

    Use the `git+` form on this page until that changes. If a page ever tells you
    to run bare `uvx mvgeos`, it is ahead of the release.

- Timings are from a warm `uv` cache on a warm git clone: about 5s for `uvx
  --help`, 2s for `uv tool install`, 4s for the Rune, 2s for the Mvge, and 31s
  for the task itself. A genuinely cold machine is slower. The budget is
  dominated by the model call, not the install.

- **Step 5 is not reliable on the default free model.** It failed on three of
  three consecutive clean-machine re-verifications with `Upstream error from
  Nvidia: Service temporarily overloaded`, and a run can exit non-zero after the
  file it created is already correct. The transcript above is real output from a
  run that succeeded; treat the model call as the unreliable step, not the
  install. Budget for a retry, and see
  [Troubleshooting](troubleshooting.md#upstream-error-from-provider-service-temporarily-overloaded).

- Model choice is narrower than OpenRouter's catalog. `-m` resolves against a
  static list shipped in the repository, that list is a drifting snapshot, and no
  `mvgeos` subcommand refreshes it. Two real failures are documented under
  [`Error: Unknown model`](troubleshooting.md#error-unknown-model). Only
  `nvidia/nemotron-3-ultra-550b-a55b:free` and
  `nvidia/nemotron-3-super-120b-a12b:free` have been run end to end. Other Realms
  and models are unverified here.

- The `read` Spell bug described in step 5 is open (SOM-23). Until it is fixed,
  expect one extra model round-trip whenever a Mvge checks its own work.

- MvgeOS is pre-1.0 (`v0.6.5`). The command surface moves.

- Rune code runs **in-process** via `importlib`. A Rune is Python that executes
  inside the engine with your permissions. Read manifests before installing
  them. See [Runes](runes/approval-rune.md) for the gate that puts a human
  back in front of mutating casts.

Next: [Concepts](concepts.md) for what the vocabulary means,
[Troubleshooting](troubleshooting.md) if something broke,
or the [Rune catalog](index.md#rune-catalog) to see what else exists.