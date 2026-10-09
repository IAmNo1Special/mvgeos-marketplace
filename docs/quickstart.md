# Quickstart

From nothing to a Mvge running a real task. Budget five minutes; on a warm
network cache the install steps take about forty seconds.

Every install command below was run end to end on a clean machine — an empty
`$HOME`, empty `XDG` directories, a private `uv` cache, no credentials, and
nothing preinstalled on `PATH` — before being written here. Each is re-run on a
clean machine on a schedule, because a documented command that stops working is
worse than no documentation at all. The model call in step 4 is a different
matter and is not covered by that claim; see
[What is not verified yet](#what-is-not-verified-yet).

## What this page promises, exactly

**Your first run needs no account and no API key.** Install a Realm, install a
Mvge, run a task. There is no credential step, because the default Realm's free
tier is served without one.

**It does not promise the model call always answers, and no version of MvgeOS
can.** The default Realm's free tier is not MvgeOS's to give you, and it is
shared with everyone else on it. Steps 1-3 are your side of the line and they
work; step 4 is somebody else's, and when it says no, that is not your setup.

## Which version this page describes

The published distribution on PyPI. There is no `mvgeos --version` yet — the
flag does not exist, so this is how you check:

```console
$ uv tool list
mvgeos v0.6.16
- mvgeos
```

If a command on this page is missing when you run it, you have something older
than `v0.6.8`. The newest command here, `mvge install --confirm-python-deps` in
step 3, landed in `v0.6.7` — it is not in `v0.6.6`.

This page is not version-pinned yet, and there is a reason: the install is not
pinned either, so there are no versions to choose between. Once the install
becomes a released package, this page is what gets versioned per release, and
the version selector appears here.

!!! warning "Steps 1-3 always work. Step 4 depends on someone else's free tier."
    The install is yours and takes seconds. The model call in step 4 goes through
    OpenCode Zen's free tier, which is shared and can be at capacity. When it is,
    step 4 fails with a rate-limit message and it is not your setup. That is the
    most common reason this page appears broken on day one, and
    [Troubleshooting](troubleshooting.md#rate-limited-by-the-provider)
    has the message your version prints for it. Everything below step 4 still
    works.

## Before you start

You need two things:

| Requirement | Why |
| --- | --- |
| [`uv`](https://docs.astral.sh/uv/) | MvgeOS installs and runs entirely through `uv` / `uvx`. There is no `pip` path. |
| Python 3.13+ | Pulled in automatically by `uv`. You do not need to install it yourself. |

You do not need an account, an API key, a Python environment, a virtualenv, or a
clone of this repository.

## 1. Install the CLI

Pick one. The first is for trying it; the second gives you a persistent
`mvgeos` command.

```bash
# Try it without installing anything -- runs from a throwaway environment
uvx mvgeos --help
```

```bash
# Or install it once and get a real `mvgeos` command on your PATH
uv tool install mvgeos
mvgeos --help
```

Both spellings print the command table and exit 0:

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

Every command on the rest of this page works with either spelling: write `uvx
mvgeos …` if you did not install, `mvgeos …` if you did. `uvx` adds a few
seconds per call because it re-resolves the environment; `uv tool install` does
not.

!!! note "Running from source instead"
    Cloning the monorepo and running `uv sync && uv run mvgeos` also works, and
    is what contributors want. It pulls in the desktop GUI's dependencies too,
    so it is noticeably heavier than the two commands above.

## 2. Give it access to a model

MvgeOS reaches models through a **Realm** — an extension that speaks one
provider's API. No Realm is installed yet, and the CLI will not talk to a model
without one.

```bash
uvx mvgeos rune install opencode-realm --confirm-python-deps
```

```text
Successfully installed rune 'opencode-realm' to
~/.agents/extensions/opencode-realm
```

**`opencode-realm` is the Realm you want, and the name matters.** The engine's
default model is `opencode/space-bunny-free`; the slug's prefix is the Realm, so
a run resolves the `opencode` Realm and nothing else answers it. Installing
`openrouter-realm` instead gets you a working engine that cannot reach its own
default model. Reproduced on a clean `$HOME` with the two installs both exiting
0 and the task then failing:

```text
$ uvx mvgeos --agent-name coding_mvge "Create a file named hello.txt containing exactly the text: hello from mvgeos"
Error: No Realm factory registered for model 'opencode/space-bunny-free'. Run
'mvgeos rune install opencode-realm' to install it from the central marketplace.
```

Current builds name the Rune to install in that message. Older builds named only
`openrouter-realm`, which is worse than no remedy — so if you followed an older
page and installed that one, install this one too.

OpenRouter is a fine Realm and is in the catalog — see
[Use another Realm](#use-another-realm) — it is just not the one the default
model needs.

`--confirm-python-deps` acknowledges that the Rune's manifest is an instruction
to fetch packages from PyPI. Read the manifest before you pass it if you would
rather not. See [OpenCode Realm](runes/opencode-realm.md) for what it registers.

## 3. Install a Mvge

An engine with no Mvge has no Spells. `coding_mvge` is the coding Mvge — it
ships nine built-in Spells: `bash`, `edit`, `find`, `grep`, `list_files`,
`read`, `read_url`, `search_web`, `write`.

```bash
uvx mvgeos mvge install coding_mvge
```

That is the whole step. It takes no flag, and on a terminal it may ask one
question you do not have to care about.

!!! note "You may see a prompt, and it is safe to skip"
    `coding_mvge` declares four `python_deps`, and installing a Mvge gates them
    the same way `rune install` does. On a TTY you get a `[y/N]` prompt.

    **The four packages it names — `mvgeos-agent`, `mvgeos-core`,
    `mvgeos-provider`, `mvgeos-runes` — are already installed as dependencies of
    the engine you installed in step 1.** So answering `n`, or skipping
    automatically in a script, costs you nothing here. Measured on a clean
    machine, the resolved Spell set is the same nine either way:

    ```text
    with    --confirm-python-deps -> 9  bash edit find grep list_files read read_url search_web write
    without --confirm-python-deps -> 9  bash edit find grep list_files read read_url search_web write
    ```

    Do not read the skip warning as a broken install. It reads like an error and
    is not one.

    To fetch them anyway, `mvge install` takes the same flag `rune install` does,
    added in `v0.6.7`:

    ```bash
    uvx mvgeos mvge install --confirm-python-deps coding_mvge
    ```

    This matters for a Mvge whose dependencies are **not** already covered by
    the engine. `coding_mvge`'s are, so the flag is optional here.

```text
Non-interactive session: skipping install of unreviewed python dependencies
['mvgeos-agent', 'mvgeos-core', 'mvgeos-provider', 'mvgeos-runes'].
Re-run with confirm=True to install.
Successfully installed mvge 'coding_mvge' to ~/.agents/agents/coding_mvge
```

## 4. Run one task

There is no authentication step, and skipping one is not an oversight. The
default model is a free model on a Realm whose free tier answers with no
credential at all, so the first task runs as the first command you type. If you
want a Realm that needs a key instead, that is
[Use another Realm](#use-another-realm).

```bash
uvx mvgeos --agent-name coding_mvge "Create a file named hello.txt containing exactly the text: hello from mvgeos"
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

!!! warning "The default free model is the fragile part of this page"
    Every install and inspect command above was verified on a clean machine and
    works. This model call is not, because the free tier is not MvgeOS's to give
    you. When it is at capacity the message is:

    ```text
    Rate limited by the provider: Realm requested 2209s retry delay (max: 60s). Rate
    limit exceeded. Please try again later..
    No spells ran before the failure, so nothing was written.
    ```

    Measured today, not guessed: seven consecutive clean-machine attempts at
    exactly this command all returned that message. The window it asks for is
    about 35 minutes, so a fast retry loop will not clear it — read the delay
    before you try again. A refused attempt costs a few seconds and writes
    nothing.

    Check the file before you re-run, so you do not overwrite work you already
    have:

    ```bash
    ls -l hello.txt && cat hello.txt || uvx mvgeos --agent-name coding_mvge \
      "Create a file named hello.txt containing exactly the text: hello from mvgeos"
    ```

    The check comes first on purpose. A run that dies *after* a `write` can leave
    a correct file behind and still exit non-zero.

    The full message set, including what a spent OpenRouter daily allowance looks
    like when you have switched Realms, is in
    [Troubleshooting](troubleshooting.md).

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
uvx mvgeos tome list
uvx mvgeos tome show <id>
```

## 5. Check what you actually have

Worth running once. It resolves the whole runtime the same way a real run does
and prints it: which Spells are loaded, which Runes are enabled and which
Sigils they hooked, and where every config value came from.

```bash
uvx mvgeos info --agent-name coding_mvge
```

```text
Agent: coding_mvge
Model: opencode/space-bunny-free
```

The `Model:` line is the Realm-prefixed slug this Mvge resolves to, and its
prefix is the Realm the run will use — which is why step 2 asked for
`opencode-realm`. Below it the real table lists the nine Spells by name with a
Description column several paragraphs long each, and is followed by the Rune,
Config, Prompt, Skills, and Diagnostics tables. All elided here for width. For
the full parameter schemas as JSON:

```bash
uvx mvgeos build --agent-name coding_mvge
```

## Use another Realm

The default Realm is the one that needs no key. If you already pay for
something else, that is the supported path and it is the reason the Realm is an
abstraction. Install the Realm you want, give it its key, and name a model its
slug space:

```bash
uvx mvgeos rune install openrouter-realm --confirm-python-deps
export OPENROUTER_API_KEY="sk-or-..."
uvx mvgeos --agent-name coding_mvge -m nvidia/nemotron-3-super-120b-a12b:free \
  "Create a file named hello.txt containing exactly the text: hello from mvgeos"
```

Each Realm reads its own variable — `OPENROUTER_API_KEY` for OpenRouter,
`OPENCODE_API_KEY` for Zen — and the CLI does not fall back to another Realm's
variable, because a key presented to the wrong host authenticates nowhere and
then fails with a message about the model rather than about the credential. A
key reaches the Realm you named and nothing else.

Two Realms ship today:

| Realm | Credential | What it is |
| --- | --- | --- |
| [opencode-realm](runes/opencode-realm.md) | none needed for free models | OpenCode Zen. The default. Free models carry a `-free` suffix. |
| [openrouter-realm](runes/openrouter-realm.md) | `OPENROUTER_API_KEY` | OpenRouter. One key, a wide catalog. Free models carry a `:free` suffix. |

`-m` accepts only ids from the model list shipped in the repository, and that
list is a drifting snapshot — see
[Troubleshooting](troubleshooting.md#error-unknown-model). Run
`mvgeos info --agent-name coding_mvge` to see the slug you would otherwise get,
and read the shipped list before you name a different one.

!!! warning "Put `--agent-name` after the subcommand"
    `mvgeos --agent-name coding_mvge info` silently ignores the flag and reports
    `Agent: default-mvge` with no Spells loaded — no error, just the wrong Mvge.
    `mvgeos info --agent-name coding_mvge` is correct. For the one-shot run in
    step 4 there is no subcommand, so the flag goes before the prompt.

## Where things landed

Everything installed into the standard `.agents` directories:

```text
~/.agents/
├── extensions/opencode-realm/   # the Realm Rune
├── agents/coding_mvge/          # the Mvge, and its Spells
└── sessions/                    # Tomes, as JSONL
```

There is no `auth/` entry, because no key was written. Add one only if you
switch to a Realm that needs a credential.

## Interactive use

The one-shot form above is for scripting. For a conversation, run `mvgeos` with
no prompt:

```bash
uvx mvgeos --agent-name coding_mvge
```

Add `--tui` for the full-screen terminal interface. Spell casts that mutate
anything can require your approval; the REPL will prompt, and
`--approval-mode allow-all` skips the gate for a single run if you trust the
Tome.

## What is not verified yet

Stated plainly, because this page is meant to be trustworthy.

**Verified on a clean machine, unedited, and pasted above:** `uvx mvgeos --help`,
`uv tool install mvgeos`, the `opencode-realm` install, the `coding_mvge`
install, and `mvgeos info --agent-name coding_mvge`. Empty `$HOME`, empty `XDG`
directories, private `uv` cache, no credentials anywhere, stdin not a TTY.

**Not verified here, and said so rather than implied:** the model call in step
4. It is somebody else's free tier. What remains true:

- **Step 4 can be refused, and the message names the cause.** Measured today, in
  a loop against a clean `$HOME`, the default model returned this on seven
  consecutive attempts:

    ```text
    Rate limited by the provider: Realm requested 2209s retry delay (max: 60s). Rate
    limit exceeded. Please try again later..
    No spells ran before the failure, so nothing was written.
    ```

    The delay it asks for is around 35 minutes, so a tight retry loop will not
    clear it — nothing is wrong, you are early. Wait for the window it names and
    run the command again.

- **A refusal writes nothing.** The message above ends with
    `No spells ran before the failure, so nothing was written.`, and the check
    confirmed an empty working directory. But a run that dies *after* a `write`
    can leave a correct file behind and still exit non-zero, so check before you
    re-run rather than assuming:

    ```bash
    ls -l hello.txt && cat hello.txt || uvx mvgeos --agent-name coding_mvge \
      "Create a file named hello.txt containing exactly the text: hello from mvgeos"
    ```

    The check comes first on purpose, so a re-run cannot overwrite work you
    already have.

- **Install timings are from a warm cache.** About 1s to resolve and install with
  `uv tool install`, and a few seconds each for the two `rune`/`mvge` installs.
  A genuinely cold machine is slower; `uvx` re-resolves on every call, so the
  `uvx` spelling costs a few seconds more per command than the installed one.

- **Model choice is narrower than either Realm's live catalog.** `-m` resolves
  against a static list shipped in the repository, that list is a drifting
  snapshot, and no `mvgeos` subcommand refreshes it. Real failures are documented
  under [`Error: Unknown model`](troubleshooting.md#error-unknown-model).

- The `read` Spell bug described in step 4 is open (SOM-23). Until it is fixed,
  expect one extra model round-trip whenever a Mvge checks its own work.

- MvgeOS is pre-1.0. The command surface moves, and the version moves faster
  than this page does — see
  [Which version this page describes](#which-version-this-page-describes).

- Rune code runs **in-process** via `importlib`. A Rune is Python that executes
  inside the engine with your permissions. Read manifests before installing
  them. See [approval-rune](runes/approval-rune.md) for the gate that puts a
  human back in front of mutating casts.

Next: [Concepts](concepts.md) for what the vocabulary means,
[Troubleshooting](troubleshooting.md) if something broke,
or the [Rune catalog](index.md#rune-catalog) to see what else exists.