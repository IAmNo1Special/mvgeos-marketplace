# Troubleshooting

Every error on this page was reproduced and pasted verbatim from a real run.
If your error is not here, it belongs here — open an issue with the output.

## Install

### `mvgeos was not found in the package registry`

```text
$ uvx mvgeos --help
  × No solution found when resolving tool dependencies:
  ╰─▶ Because mvgeos was not found in the package registry and you require
      mvgeos, we can conclude that your requirements are unsatisfiable.
```

The `mvgeos` console script exists on the root distribution, but no release has
been published to PyPI yet — so the short form has nothing to resolve against
until one ships. Use the git form:

```bash
uvx --from "git+https://github.com/IAmNo1Special/mvgeos#subdirectory=mvgeos-cli" mvgeos --help
```

The `mvgeos` **command** comes from the `mvgeos-cli` subdirectory of the
monorepo, which is why the path ends in `#subdirectory=mvgeos-cli`. If you
drop that part you get this error, or a confusing failure deep in a build.

To install it properly instead:

```bash
uv tool install "git+https://github.com/IAmNo1Special/mvgeos#subdirectory=mvgeos-cli"
```

Confirm what landed:

```bash
uv tool list
```

```text
mvgeos-cli v0.6.5
- mvgeos
```

### `No executables are provided by package mkdocs-material`

Only relevant if you are building these docs. `mkdocs-material` is a theme
library with no entry point. Install `mkdocs`, which has it:

```bash
uv tool install mkdocs --with mkdocs-material --with pymdown-extensions
```

## Getting a model to answer

### `Authentication failed (401)`

```text
Authentication failed (401). Check your OPENROUTER_API_KEY or --api-key.
```

The key is wrong, expired, or revoked. The engine reached the provider and was
rejected, which means the install and the Realm are both fine — only the
credential is not.

Where the CLI looked, in order:

1. the `--api-key` flag
2. `OPENROUTER_API_KEY` in the environment
3. `~/.agents/auth/openrouter.json`

A stale file in step 3 will shadow a correct environment variable only if the
variable is unset, so check what you actually exported:

```bash
printf 'set: %s\n' "${OPENROUTER_API_KEY:+yes}"
cat ~/.agents/auth/openrouter.json 2>/dev/null | head -c 12; echo
```

The format check in `validate_api_key` is a prefix check, not a validity check:
keys must start with `sk-or-` (OpenRouter) or `AIza` (Google). A key with the
right prefix but no credit still produces this 401.

### `Error: API key is required.` on a local model

```text
$ mvgeos --agent-name coding_mvge -m "ollama/llama3" "say hi"
Error: API key is required.
```

Known bug, not your mistake. The CLI clears the key for `ollama/` models before
validation, but then validates without passing the model ID, so the exemption
never applies and the empty key is rejected. There is no Ollama Realm in the
marketplace either. Until both are fixed, use a keyed Realm.

### `No Realm extension installed`

```text
Error: No Realm extension installed.
```

The engine has no way to reach a model yet. Install one:

```bash
mvgeos rune install openrouter-realm --confirm-python-deps
```

Interactively, `mvgeos` offers to install it for you and then retries. That
prompt is skipped when stdout is not a terminal — in a script or a CI job you
must run the install yourself first.

## The wrong Mvge loaded

### `Agent: default-mvge`, and every Spell is `(none)`

```bash
mvgeos --agent-name coding_mvge info     # WRONG - flag silently ignored
```

```text
Agent: default-mvge
Model: nvidia/nemotron-3-ultra-550b-a55b:free

                    Spells
┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name   ┃ Source ┃ Source Rune ┃ Description ┃
┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ (none) │        │             │             │
└────────┴────────┴─────────────┴─────────────┴──────────────────────────────┘
```

`--agent-name` before a subcommand is parsed by the root callback, and each
subcommand resolves its own agent, so the flag never reaches it. Nothing warns
you. Put it after the subcommand:

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
└────────────┴─────────┴─────────────┴───────────────────────────────────────────┘
```

For a one-shot run there is no subcommand, so the flag goes before the prompt:
`mvgeos --agent-name coding_mvge "your task"`.

## Runes and Spells

### `Skipping unreviewed python dependencies`

```text
Non-interactive session: skipping install of unreviewed python dependencies
['mvgeos-agent', 'mvgeos-core', 'mvgeos-provider', 'mvgeos-runes'].
Re-run with confirm=True to install.
Successfully installed mvge 'coding_mvge' to ~/.agents/agents/coding_mvge
```

Not an error, and for `mvgeos mvge install` the correct outcome: those are the
engine packages you already installed in step 1. If you are installing from
source and actually need them pulled in, re-run with confirmation.

The same message on `mvgeos rune install` means the Rune has a dependency you
have not approved. Pass `--confirm-python-deps` when you trust it.

### A Rune installed but its Spells are missing

Runes are discovered from standard extension directories. Check that the load
path and the enabled set agree:

```bash
mvgeos info --agent-name coding_mvge
ls ~/.agents/extensions/
```

Runes scoped to a specific Mvge live under that Mvge's directory
(`~/.agents/agents/coding_mvge/runes/`) and only load for that Mvge. A Rune
installed for one agent is invisible to another — that is not a bug.

### `MVGEOS_WORKSPACE_ROOT` and files you expected to be reachable

`write`, `edit`, and `bash` Spells are confined to an authorized root. By
default that is the working directory you launched from. Launch MvgeOS from the
project you want it to touch, or set `MVGEOS_WORKSPACE_ROOT` explicitly.
`mvgeos info` prints the resolved values and the file each came from, which is
the fastest way to see what is actually configured. See
[Concepts](concepts.md) for the rest of the environment.

### `Input should be a valid integer` on `offset` or `limit`

```text
Invalid arguments for spell read: 2 validation errors for read_Schema
offset
  Input should be a valid integer [type=int_type, input_value=None, input_type=NoneType]
limit
  Input should be a valid integer [type=int_type, input_value=None, input_type=NoneType]
```

Known engine bug, tracked as SOM-23. You will see it whenever a Mvge calls
`read` (or `grep`, `find`, or `list_files`) with only its required arguments and
leaves the optional paging arguments out.

The Mvge recovers on its own — it retries with explicit `offset` and `limit` and
the task completes correctly. You will notice it as one extra model round-trip,
so a task takes slightly longer and costs slightly more Mana than you would
expect. If you are watching a run, this is what the message means; it is not a
sign your key, your Realm, or your prompt is wrong.

Nothing to fix on your side. It goes away when SOM-23 lands.

### `mvgeos` is not found after installing

If you used the `uvx --from "git+..."` form, nothing is installed — `uvx` runs
from a throwaway environment and leaves nothing on your `PATH`. That is the
point of that form. Use `uv tool install` if you want a persistent command.

If you *did* use `uv tool install`, check that the tool bin directory is on your
`PATH`:

```bash
uv tool dir --bin
echo $PATH
```

## Sessions

### `mvgeos tome list` is empty after a run that worked

Tomes are written to `~/.agents/sessions/`, keyed by the Mvge and project. If
you ran with `--tome-dir`, the Tomes went there instead. `mvgeos config path`
prints the config file backing the active agent if you need to see which layers
are in play.

## Still stuck

Include the output of these — together they pin down almost everything:

```bash
mvgeos info --agent-name coding_mvge
mvgeos setup check
uv --version && python3 --version
```

Then open an issue at
[github.com/IAmNo1Special/mvgeos](https://github.com/IAmNo1Special/mvgeos/issues).
See also the [FAQ](faq.md) for the questions that come up before anything
breaks.