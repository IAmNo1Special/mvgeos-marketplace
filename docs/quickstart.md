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

## Which version this page describes

`v0.6.8`, installed as `mvgeos-cli v0.6.8`. There is no `mvgeos --version` yet —
the flag does not exist, so this is how you check:

```console
$ uv tool list | grep mvgeos-cli
mvgeos-cli v0.6.8
- mvgeos
```

The install command below points at the **default branch**, not a tag, so it
gives you the newest code rather than the newest release. That is deliberate
while the project is pre-1.0 and the command surface is still moving, and it has
a consequence worth stating plainly: **you cannot end up reading these
instructions against code they do not match.** Whatever you install and these
instructions are the same tree at the moment you run them.

If a command on this page is missing when you run it, you have something older
than `v0.6.8`. The newest command here, `mvge install --confirm-python-deps` in
step 3, landed in `v0.6.7` — it is not in `v0.6.6`.

This page is not version-pinned yet, and there is a reason: the install is not
pinned either, so there are no versions to choose between. Once the install
becomes a released package, this page is what gets versioned per release, and
the version selector appears here.

!!! warning "Steps 1-4 always work. Step 5 depends on someone else's free tier."
    The install is yours and takes seconds. The model call in step 5 goes
    through OpenRouter's free tier, which allows **50 requests a day per
    account** and resets at 00:00 UTC. If that allowance is spent — yours, or
    shared with anything else on the account — step 5 fails and it is not your
    setup. That is the most common reason this page appears broken on day one,
    and [Troubleshooting](troubleshooting.md#daily-free-model-quota-exhausted)
    has the message your version prints for it. Everything below step 5 still
    works.

## Before you start

You need three things:

| Requirement | Why |
| --- | --- |
| [`uv`](https://docs.astral.sh/uv/) | MvgeOS installs and runs entirely through `uv` / `uvx`. There is no `pip` path. |
| Python 3.13+ | Pulled in automatically by `uv`. You do not need to install it yourself. |
| An API key for a model | MvgeOS does not ship models. You bring a key for the [Realm](concepts.md#mvge-spell-realm) you want to use. The default Realm is OpenRouter. |

You do not need a Python environment, a virtualenv, or a clone of this
repository.

## The whole thing, recorded

The steps below as one continuous take on a machine with an empty `$HOME` — no
cuts, no re-run, 23 seconds:

![Terminal recording: installing mvgeos from git, installing the openrouter-realm Rune and the coding_mvge Mvge, writing the credential, then running one task that creates hello.txt and verifying it with od -c](images/mvgeos-demo.gif)

The recording pipes `yes` into the prompt that step 3 asks, so it can run
unattended. Interactively you will be asked, and the answer that works is `y`.

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
ships nine built-in Spells: `bash`, `edit`, `find`, `grep`, `list_files`,
`read`, `read_url`, `search_web`, `write`.

```bash
mvgeos mvge install coding_mvge
```

That is the whole step, and it works as written — no flag, no prompt to answer.

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
    mvgeos mvge install --confirm-python-deps coding_mvge
    ```

    This matters for a Mvge whose dependencies are **not** already covered by
    the engine. `coding_mvge`'s are, so the flag is optional here.

```text
Non-interactive session: skipping install of unreviewed python dependencies
['mvgeos-agent', 'mvgeos-core', 'mvgeos-provider', 'mvgeos-runes'].
Re-run with confirm=True to install.
Successfully installed mvge 'coding_mvge' to ~/.agents/agents/coding_mvge
```

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

It took about 30 seconds against a free model. That figure is from a run that
succeeded; when the free allowance is spent, this step fails rather than being
slow. See the warning at the top.

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
  bash        builtin
  edit        builtin
  find        builtin
  grep        builtin
  list_files  builtin
  read        builtin
  read_url    builtin
  search_web  builtin
  write       builtin
```

The real table has a Description column several paragraphs long per Spell, and
is followed by the Rune, Config, Prompt, Skills, and Diagnostics tables. All
elided here for width. For the full parameter schemas as JSON:

```bash
mvgeos build --agent-name coding_mvge
```

!!! warning "`mvge install` has no non-interactive flag"
    Answering `y` at the prompt in step 2 is what makes the Spells available.
    There is no `--confirm-python-deps` to script it with, so in a script or CI
    job — where stdin is not a TTY and nothing is prompted — the fetch is skipped
    with a warning. Read the output rather than assuming.

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

- **The five-minute budget holds for steps 1-4, not reliably for step 5.** The
  transcript above is real output from a run that succeeded, but the default free
  model has failed this task on every clean-machine re-verification since. Two
  separate causes, each measured 3 of 3, and they need different fixes:
  endpoint saturation (`Upstream error from Nvidia: Service temporarily
  overloaded`) and an exhausted account-wide free allowance (`Daily free-model
  quota exhausted`, see
  [Troubleshooting](troubleshooting.md#daily-free-model-quota-exhausted)).
  Treat "install and configure in five minutes" as the promise, and expect step 5
  to need a retry or a different model. A run can also exit non-zero after the
  file it created is already correct.

- Model choice is narrower than OpenRouter's catalog. `-m` resolves against a
  static list shipped in the repository, that list is a drifting snapshot, and no
  `mvgeos` subcommand refreshes it. Two real failures are documented under
  [`Error: Unknown model`](troubleshooting.md#error-unknown-model). Only the two
  `nvidia/nemotron-3-*:free` ids have been run end to end. Other Realms and models
  are unverified here.

- A spent free allowance is reported as `Daily free-model quota exhausted` on
  builds that read the quota headers, naming the reset time instead of suggesting
  a retry — which is what a limit lasting until 00:00 UTC needs. The message is
  shorter when your model is `openrouter/free`, because that response carries no
  reset time to report. Earlier builds report the same condition as `Upstream
  provider overloaded: Provider returned error`, and in interactive mode count 60
  seconds down against a window measured in hours. Which wording you get depends
  on your version; the fix is the same either way, and
  [Troubleshooting](troubleshooting.md#upstream-provider-overloaded-provider-returned-error)
  covers the older wording. Endpoint saturation is a separate condition with its
  own message.

- The `read` Spell bug described in step 5 is open (SOM-23). Until it is fixed,
  expect one extra model round-trip whenever a Mvge checks its own work.

- MvgeOS is pre-1.0. The command surface moves, and the version moves faster
  than this page does — see
  [Which version this page describes](#which-version-this-page-describes).

- Rune code runs **in-process** via `importlib`. A Rune is Python that executes
  inside the engine with your permissions. Read manifests before installing
  them. See [Runes](runes/approval-rune.md) for the gate that puts a human
  back in front of mutating casts.

Next: [Concepts](concepts.md) for what the vocabulary means,
[Troubleshooting](troubleshooting.md) if something broke,
or the [Rune catalog](index.md#rune-catalog) to see what else exists.