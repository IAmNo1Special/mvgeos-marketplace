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
mvgeos-cli v0.6.7
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

### `Daily free-model quota exhausted`

```text
$ mvgeos --agent-name coding_mvge "say hi"
Daily free-model quota exhausted (50/50 requests). Resets at 00:00 UTC.
Hint: Add credits to your OpenRouter account, switch to a paid model, or wait for the daily reset.
```

**This one is a spent allowance, not a fault.** Nothing is wrong with your
install, your key, or the tool. Retry will not help until the reset time.

The message may be shorter than the one above. If your model is
`openrouter/free`, OpenRouter's Free Models Router, it reports the exhaustion
without the count and without a reset time, because the 402 it returns carries no
rate-limit headers to read:

```text
Daily free-model quota exhausted.
Hint: Add credits to your OpenRouter account, switch to a paid model, or wait for the daily reset.
```

Same condition, same fix. The tool does not invent a reset time it was not given.

OpenRouter gives every account a **daily allowance of 50 free-model requests**,
counted across the whole account — not per model, not per app. When it is spent,
every free model returns HTTP 429 with the code `free-models-per-day` and these
headers:

```text
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1791244800000     # milliseconds since epoch
```

MvgeOS reads those headers on builds that do so, which is why the message can name
the exhaustion and the reset time instead of guessing. `X-RateLimit-Reset` is a
Unix timestamp in **milliseconds**. `1791244800000` is `2026-10-06T00:00:00Z` —
the allowance resets at **00:00 UTC**, so the wait can be anywhere from a minute
to most of a day. To read it yourself:

```bash
python3 -c 'import datetime,sys; print(datetime.datetime.fromtimestamp(int(sys.argv[1])/1000, datetime.UTC))' 1791244800000
```

Your options are: wait for the reset, add credit to raise the cap, or pass a paid
model with `-m`. In interactive mode MvgeOS prints this message once and stops —
it does not count down, because a countdown is only honest when the window is
measured in seconds.

!!! warning "Which message you get depends on your version"
    Builds before this one name the same condition differently — see
    [`Upstream provider overloaded`](#upstream-provider-overloaded-provider-returned-error),
    which is what a released `v0.6.7` prints. Both mean the same thing; only the
    wording differs. If you installed from the git line and you see the
    overloaded message, read that entry — the advice there is correct for the
    message you actually received.

### `Upstream provider overloaded: Provider returned error`

```text
$ mvgeos --agent-name coding_mvge "say hi"
Upstream provider overloaded: Provider returned error
```

**Read the cause before you retry.** This message is the catch-all for "the
provider would not serve this request", and it covers two problems that need
opposite responses. Retrying helps one and cannot help the other.

1. **The provider is genuinely saturated.** Some free endpoints return
   "Service temporarily overloaded" under load. This clears on its own — run the
   command again.
2. **Your daily free allowance is spent.** OpenRouter allows 50 free-model
   requests per account per day, resetting at **00:00 UTC**. Nothing about your
   setup changes this, and no number of retries will get past it.

To tell them apart, read `X-RateLimit-Remaining` on the 429 response. `0` means
the allowance is gone and retrying is pointless until the reset; anything above
`0` means you are being throttled per-minute or the provider is busy, and a
retry is reasonable. Builds that name the exhaustion properly print
[`Daily free-model quota exhausted`](#daily-free-model-quota-exhausted)
instead of this message, so if you got that one, use its entry.

### The same exhaustion, reported as HTTP 402

Worth recognising because it names a provider you did not choose:

```text
HTTP 402 :: is_byok=true, provider_name="Google AI Studio"
            "Your prepayment credits are depleted"
            previous_errors: NINE x 429 free-models-per-day
```

That is the OpenRouter **Free Models Router** walking its list of free endpoints,
getting a 429 from each one, and finally falling through to a bring-your-own-key
provider whose credits are also empty. Nine 429s then one 402 is one exhausted
allowance, reported twice. Fix the allowance, not the provider.

You may see this one as a bare error rather than a rate-limit message, because
the 402 carries no rate-limit headers for MvgeOS to read:

```text
Error: Your prepayment credits are depleted
```

Same cause, same fix. The allowance is gone; retrying will not change that.

### A run fails but the file it wrote is correct

The engine now reports work that already landed when a run exits non-zero,
because a failed turn is not always a useless turn:

```text
Wrote 1 file before the run failed.
  hello.txt
```

This happens when the model call dies after a Spell has already cast. The file
is real and usually correct. Check it before re-running rather than assuming the
failure lost everything.

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

### `Upstream error from <provider>: Service temporarily overloaded`

```text
Error: Upstream error from Nvidia: Service temporarily overloaded
```

The provider refused the request. Your install is fine, your key is fine, and
this is not a MvgeOS bug — it is the model endpoint being full.

**Check whether the work already landed before you retry.** The engine writes
each Spell result to disk as it happens, so a run that dies on the model call
*after* a `write` can leave a correct file behind and still exit non-zero:

```bash
ls -l hello.txt && cat hello.txt
```

If it keeps failing, name a different model:

```bash
mvgeos -m nvidia/nemotron-3-super-120b-a12b:free --agent-name coding_mvge \
  "Create a file named hello.txt containing exactly the text: hello from mvgeos"
```

To see what you can choose from before you are stuck, see
[`Error: Unknown model`](#error-unknown-model) — the list is not "every model
OpenRouter serves".

### `Error: Unknown model`

```text
$ mvgeos -m qwen/qwen3.8-27b:free --agent-name coding_mvge "say hi"
Error: Unknown model: qwen/qwen3.8-27b:free
```

That model genuinely exists on OpenRouter today. `-m` does not accept it because
on a clean machine the model list is the **static baseline shipped in the
repository**, at `mvgeos-provider/src/mvgeos_provider/models.json` — 19 `:free`
entries and 391 paid ones. Nothing in the CLI refreshes it: the live-catalog
refresh exists in `mvgeos_provider.refresh_models()` but no `mvgeos` subcommand
calls it, so `~/.agents/models.json` stays absent unless something else writes
it.

The list is also a snapshot and drifts. One baseline entry,
`openai/gpt-oss-20b:free`, resolves but then fails:

```text
Error: This model is unavailable for free. The paid version is available now -
use this slug instead: openai/gpt-oss-20b
```

So a baseline `:free` id is a starting point, not a promise. Read the list, pick
one, and be ready for the next one:

```bash
python3 -c "import json;print('\n'.join(e[0] for e in json.load(open('mvgeos-provider/src/mvgeos_provider/models.json'))['free']))"
```

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
engine packages you already installed in step 1. Re-running with confirmation
changes nothing measurable — the resolved Spell set is the same nine either way.

Both install commands take the same flag since `v0.6.7`, and it matters only
when the dependency is *not* already covered by the engine:

```bash
mvgeos mvge install --confirm-python-deps coding_mvge
mvgeos rune install openrouter-realm --confirm-python-deps
```

On `mvge install` the same message means the Mvge has a dependency you have not
approved. On `rune install` it means the Rune does. Pass the flag when you trust
the manifest — and read the manifest first, because a dependency is an
instruction to fetch and run code.

### `Could not parse manifest in .venv` in the Diagnostics table

```text
Kind          │ Target │ Name  │ Scope │ Message
parse_warning │ rune   │ .venv │ user  │ Could not parse manifest in .venv
```

Cosmetic, and you will see it on a correct install. `mvgeos rune install`
creates `~/.agents/extensions/.venv` to hold a Rune's Python dependencies. The
Rune loader scans everything under `~/.agents/extensions/` looking for
`manifest.json`, finds the virtualenv directory instead, and reports it as an
unparseable Rune.

Nothing is broken — the `openrouter-realm` Rune alongside it loaded correctly,
which is why `mvgeos info --agent-name coding_mvge` shows `Model:` and a full
Spell table in the same run. Ignore the row, or delete `~/.agents/extensions/.venv`
if you want it gone; the next `rune install` recreates it.

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