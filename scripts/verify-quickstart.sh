#!/usr/bin/env bash
# Re-verify the quickstart step-5 task on a clean machine, N times.
#
# This exists because the quickstart makes a promise a reader can time, and a
# promise nobody re-checks is a promise that quietly stops being true. It runs
# the documented command verbatim, on a machine that has never seen MvgeOS,
# and records enough per run to tell the failure causes apart:
#
#   - a spent account-wide free allowance (resets 00:00 UTC, retry is pointless)
#   - endpoint capacity saturation (clears on its own, retry is right)
#   - the work landing on disk even though the process exited non-zero
#
# Those three need different advice, and one success/failure split cannot tell
# them apart. Exit code alone is not enough: a run can exit 1 with a correct
# hello.txt already written, and a Summoner who retries without checking can
# overwrite work they already completed.
#
# Usage:
#   scripts/verify-quickstart.sh                 # 10 runs, documented model
#   RUNS=25 scripts/verify-quickstart.sh         # more runs
#   MODELS="openrouter/free" scripts/verify-quickstart.sh
#   SPEC="git+https://github.com/IAmNo1Special/mvgeos@main#subdirectory=mvgeos-cli" \
#     scripts/verify-quickstart.sh               # verify a branch, not main
#
# The documented default is whatever main ships. Overriding SPEC is how you
# check a PR before you document it, which is the only safe time to document it.
#
# Credentials: the Realm decides both which Rune is installed and which variable
# or file the key is read from, so the harness derives them from the model's
# prefix instead of assuming OpenRouter. Hardcoding OpenRouter here is not a
# simplification, it is a bug that already shipped once: DEFAULT_MODEL moved from
# an OpenRouter slug to opencode/space-bunny-free while this script went on
# testing a stale string that no longer named the default at all.
#
# Requires the key for each Realm under test: OPENROUTER_API_KEY or
# ~/.agents/auth/openrouter.json, and OPENCODE_API_KEY or
# ~/.agents/auth/opencode.json. The opencode Realm is the one exception -- it
# sends no Authorization header when there is no key, so it can be tested
# keyless with USE_ENV=0.
set -u

RUNS="${RUNS:-10}"
SPEC="${SPEC:-git+https://github.com/IAmNo1Special/mvgeos#subdirectory=mvgeos-cli}"
TASK="${TASK:-Create a file named hello.txt containing exactly the text: hello from mvgeos}"
EXPECT_BYTES="${EXPECT_BYTES:-17}"
EXPECT_CONTENT="${EXPECT_CONTENT:-hello from mvgeos}"
# USE_ENV=1 exports the Realm's key variable for the run. The CLI reads the
# Realm's own variable before the on-disk credential, and for a routed slug like
# nvidia/... the Realm it looks up is the provider, not the gateway serving it --
# so the on-disk ~/.agents/auth/openrouter.json is never read for those models.
# USE_ENV=0 drops the export and measures only the credential file, which is the
# path step 4 of the quickstart recommends.
USE_ENV="${USE_ENV:-1}"
MODELS="${MODELS:-__default__}"
OUTDIR="${OUTDIR:-$(mktemp -d "${TMPDIR:-/tmp}/mvgeos-quickstart-verify.XXXXXX")}"

# The Rune that provides each Realm, mirroring REALM_RUNES in
# mvgeos-provider/src/mvgeos_provider/realms.py.
realm_of() {
  case "$1" in
    */*) printf '%s' "${1%%/*}" ;;
    *)   printf '%s' "$1" ;;
  esac
}

rune_for_realm() {
  case "$1" in
    openrouter) printf 'openrouter-realm' ;;
    opencode)   printf 'opencode-realm' ;;
    *)          printf '%s-realm' "$1" ;;
  esac
}

# The credential file the CLI reads for a Realm, and the variable it reads first.
auth_env_for_realm() {
  case "$1" in
    openrouter) printf 'OPENROUTER_API_KEY' ;;
    opencode)   printf 'OPENCODE_API_KEY' ;;
    *)          printf '%s_API_KEY' "$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')" ;;
  esac
}

# What is shared across runs, and why.
#
# Shared: the uv package cache and the installed tool. These only save download
# and install time, which is not what step 5 claims, and re-downloading the
# world ten times would spend the whole run budget on `uv`.
#
# NOT shared, and this is the part that matters: every run gets a brand new
# HOME. No installed Rune, no installed Mvge, no cached model catalog, no
# sessions, no config. Anything the run needs it has to provision for itself,
# exactly as the quickstart tells a reader to. An earlier version staged the
# Realm once in a shared home, and every run then failed with "No Realm factory
# registered" -- which measured the harness, not the product.
PROVISION_HOME="$OUTDIR/.provision"
SHARED_UV_CACHE="$OUTDIR/.uv-cache"
# The realm whose Rune is installed in the provision home, and the realm a
# __default__ run is measured against. Defaults to opencode because that is
# DEFAULT_REALM in mvgeos-provider .../realms.py on main -- the realm that serves
# the shipped default model. Overridable so a branch whose default moved can be
# measured without editing the script.
PROVISION_REALM="${PROVISION_REALM:-opencode}"
# Absolute, captured before any run rewrites HOME. Reading it relative to the
# mutated HOME is how the first version of this staged credentials into the
# wrong home and every run failed with "API key required".
#
# Keyed by Realm, because the file the CLI reads is named after the Realm, and a
# single openrouter.json no longer covers the shipped default model.
# The caller's real HOME, captured before clean_env starts rewriting it, and
# read as an absolute path rather than through $HOME so a later export cannot
# move it. Reading it relative to $PWD instead pointed the lookup at the repo.
REALM_HOME="$(cd "$HOME" && pwd)"
auth_src_for() {
  local realm="$1" f="$REALM_HOME/.agents/auth/$1.json"
  if [ -s "$f" ]; then printf '%s' "$f"; fi
}

# Give the run the same credential the CLI would actually find, in the CLI's own
# order of precedence, because that order is the thing under test:
#
#   1. the Realm's own variable   (OPENROUTER_API_KEY / OPENCODE_API_KEY / ...)
#   2. OPENROUTER_API_KEY, as a fallback for any Realm
#   3. ~/.agents/auth/<realm>.json
#
# Step 2 is the CLI's, and it is why a routed slug like nvidia/... is usable
# from the environment but not from the credential file the quickstart tells you
# to write: the slug's Realm is its *provider* (nvidia), so step 1 asks for
# NVIDIA_API_KEY and step 3 reads ~/.agents/auth/nvidia.json. Both miss an
# OpenRouter key saved at ~/.agents/auth/openrouter.json. Only the env fallback
# connects them, so a documented path that works and a documented path that
# silently does not differ by one shell line.
#
# The opencode Realm is allowed to have no credential at all: it omits the
# Authorization header entirely when there is no key, which is its documented
# keyless free tier.
stage_auth() {
  local dest_home="$1" realm="$2"
  mkdir -p "$dest_home/.agents/auth"
  local env_name val
  env_name="$(auth_env_for_realm "$realm")"
  val="${!env_name:-}"
  # The fallback is skipped when the Realm's own variable is unset, which is
  # exactly when USE_ENV=0 is meant to isolate the credential-file path.
  if [ "$USE_ENV" = "1" ] && [ -z "$val" ]; then
    val="${OPENROUTER_API_KEY:-}"
  fi
  if [ -n "$val" ]; then
    KEY="$val" DEST="$dest_home/.agents/auth/$realm.json" python3 -c \
      'import json,os; json.dump({"api_key": os.environ["KEY"]}, open(os.environ["DEST"],"w"))'
    chmod 600 "$dest_home/.agents/auth/$realm.json"
    return 0
  fi
  local src; src="$(auth_src_for "$realm")"
  if [ -n "$src" ]; then
    install -m 600 "$src" "$dest_home/.agents/auth/$realm.json"
    return 0
  fi
  # Keyless is only legitimate for the opencode Realm.
  [ "$realm" = "opencode" ] && return 0
  return 1
}

clean_env() {
  # Empty HOME, empty XDG. Nothing may survive between runs: a leftover
  # ~/.agents/models.json or an already-installed Rune would make run 2 easier
  # than run 1 and the split would flatter us.
  local home="$1" realm="$2"
  rm -rf "$home"
  mkdir -p "$home/work" "$home/.local/share" "$home/.config" "$home/.local/state"
  export HOME="$home"
  export XDG_CACHE_HOME="$home/.cache"
  export XDG_CONFIG_HOME="$home/.config"
  export XDG_DATA_HOME="$home/.local/share"
  export XDG_STATE_HOME="$home/.local/state"
  # The caller's TMPDIR is stripped. This is not tidiness: an inherited TMPDIR
  # pointed a run's relative write at the caller's scratch directory instead of
  # the run's working directory, so the Mvge reported success, exited 0, and put
  # a correct hello.txt two directories above where it belonged. Scored as a
  # failure here, and it would have been scored as a failure for a reader too if
  # their shell exported one.
  unset TMPDIR TMP TEMP 2>/dev/null || true
  # Shared on purpose, and only this. See the note above on what may be shared.
  export UV_CACHE_DIR="$SHARED_UV_CACHE"
  export UV_TOOL_DIR="$PROVISION_HOME/toolbin"
  export UV_TOOL_BIN_DIR="$PROVISION_HOME/toolbin/bin"
  # USE_ENV=0 measures the credential-file path alone, so the Realm's variable
  # is cleared for the run. Without this the file is never exercised, because
  # the variable is read first and wins.
  if [ "$USE_ENV" != "1" ]; then
    unset "$(auth_env_for_realm "$realm")" 2>/dev/null || true
  fi
  # Credentials go in the home the run will actually use. The realm is what
  # reads them, and a run whose only failure is "API key required" measures
  # nothing about the five-minute promise.
  stage_auth "$home" "$realm" || return 1
  return 0
}

# A clean machine has no Realm and no Mvge. The run installs both, which is
# steps 3 and 4 of the quickstart and part of the five minutes.
provision_run() {
  local runhome="$1" realm="$2"
  local log="$runhome/provision.log"
  local rune; rune="$(rune_for_realm "$realm")"
  "$MV" rune install "$rune" --confirm-python-deps >> "$log" 2>&1 \
    || { echo "  rune install $rune FAILED (see $log)"; return 1; }
  "$MV" mvge install coding_mvge >> "$log" 2>&1 \
    || { echo "  mvge install FAILED (see $log)"; return 1; }
  return 0
}

MV=""
SHIPPED_DEFAULT=""
provision() {
  echo "=== provision once: install + realm + mvge ==="
  # The provision home only needs a home-shaped environment to install the
  # tool into. Credentials are staged per run, into that run's home.
  clean_env "$PROVISION_HOME" "${PROVISION_REALM}" || {
    echo "FAIL: no credential for realm '$PROVISION_REALM' on this machine"; exit 2; }
  uv tool install "$SPEC" > "$OUTDIR/install.log" 2>&1
  local rc=$?
  echo "uv tool install exit=$rc"
  if [ $rc -ne 0 ]; then
    echo "FAIL: the documented install line does not work. Do not document it."
    tail -20 "$OUTDIR/install.log"
    exit 2
  fi
  MV="$UV_TOOL_BIN_DIR/mvgeos"
  "$MV" --help > /dev/null 2>&1 || { echo "FAIL: mvgeos --help failed"; exit 2; }
  "$MV" rune install "$(rune_for_realm "$PROVISION_REALM")" --confirm-python-deps > "$OUTDIR/rune.log" 2>&1
  echo "rune install exit=$?"
  "$MV" mvge install coding_mvge > "$OUTDIR/mvge.log" 2>&1
  echo "mvge install exit=$?"
  # Read the default model off the installed engine rather than hardcoding it.
  # A hardcoded copy is how this harness came to test a slug that main had
  # already stopped shipping as its default: the string still parsed, still ran,
  # and quietly measured the wrong thing.
  SHIPPED_DEFAULT=$("$MV" info --agent-name coding_mvge 2>/dev/null \
    | sed -n 's/^Model:[[:space:]]*//p' | head -1)
  echo "--- shipped default model: ${SHIPPED_DEFAULT:-<unresolved>} ---"
}

# What the CLI actually printed, reduced to the lines a reader would act on.
# The CLI prints its errors on stdout, not stderr. Reading only stderr made
# every single failure classify as "silent" and hid the cause entirely.
#
# Only called for failures. A successful run has no cause to name, and running
# the greps on one anyway classified every success as "other", which then showed
# up in the per-cause breakdown as though it were a failure mode.
classify() {
  local runhome="$1"
  local err="$runhome/err.txt"
  local outf="$runhome/out.txt"
  # The gateway's own wording for a spent Zen free allowance, which arrives as
  # a generic 429 and is the failure that killed an automated run of the docs
  # owner outright.
  if grep -qi "free tier can only be used from within" "$outf" "$err"; then echo "zen_free_tier_gated"
  elif grep -qi "FreeUsageLimitError\|free usage limit" "$outf" "$err"; then echo "zen_free_usage_limit"
  elif grep -qi "quota exhausted" "$outf" "$err"; then echo "spent_allowance"
  elif grep -qi "temporarily overloaded\|upstream provider overloaded" "$outf" "$err"; then echo "capacity"
  elif grep -qi "exceeds your current quota" "$outf" "$err"; then echo "mana_exhausted"
  elif grep -qi "unknown model\|not a valid model id" "$outf" "$err"; then echo "unknown_model"
  elif grep -qiE "402|depleted|prepayment" "$outf" "$err"; then echo "upstream_402"
  elif grep -qiE "401|api key required" "$outf" "$err"; then echo "auth"
  elif grep -qis "." "$outf" "$err"; then echo "other"
  else echo "silent"
  fi
}

echo "OUTDIR=$OUTDIR"
provision

RESULTS="$OUTDIR/results.jsonl"
: > "$RESULTS"

for model in $MODELS; do
  echo
  # __default__ means "run the command exactly as the quickstart prints it",
  # with no -m at all, so what gets measured is the documented first run and not
  # a model this harness chose. The default can move between the moment the docs
  # were written and the moment a reader runs them, and only this form notices.
  if [ "$model" = "__default__" ]; then
    echo "=== model: (shipped default, no -m) ==="
    model_arg=()
    realm="${PROVISION_REALM}"
  else
    echo "=== model: $model ==="
    model_arg=(-m "$model")
    realm="$(realm_of "$model")"
    # REALM_OVERRIDE names the Realm that actually serves a model when the slug
    # does not. It is needed for routed slugs: realm_for_model_id("nvidia/...")
    # returns "nvidia", which is the *provider*, so the derived name is
    # "nvidia-realm" and no such Rune exists in the marketplace. The engine's
    # own comment on DEFAULT_REALM says as much -- "for a routed slug like
    # nvidia/... the id prefix is the provider and the Realm is openrouter" --
    # but the function it sits next to returns the provider anyway. Only the
    # OPENROUTER_API_KEY fallback keeps that path working.
    [ -n "${REALM_OVERRIDE:-}" ] && realm="$REALM_OVERRIDE"
  fi

  i=1
  while [ "$i" -le "$RUNS" ]; do
    RUNHOME="$OUTDIR/run-$i"
    clean_env "$RUNHOME" "$realm" || { echo "FAIL: could not stage credentials for realm '$realm'"; exit 2; }

    # Steps 3 and 4, on the run's own clean machine, timed separately so the
    # task's wall clock is not quietly carrying the install cost.
    pstart=$(date +%s)
    if ! provision_run "$RUNHOME" "$realm"; then
      echo "run $i: provisioning failed, skipping -- this measures the harness"
      i=$(( i + 1 )); continue
    fi
    pend=$(date +%s)
    psecs=$(( pend - pstart ))

    cd "$RUNHOME/work" || exit 2

    start=$(date +%s)
    "$MV" --agent-name coding_mvge "${model_arg[@]}" "$TASK" \
      > "$RUNHOME/out.txt" 2> "$RUNHOME/err.txt"
    rc=$?
    end=$(date +%s)
    secs=$(( end - start ))

    if [ -f "$RUNHOME/work/hello.txt" ]; then
      present=yes
      lsout=$(ls -l "$RUNHOME/work/hello.txt" 2>&1 | awk '{print $1, $5"B"}')
      content=$(cat "$RUNHOME/work/hello.txt" 2>&1)
      if [ "$(printf '%s' "$content" | wc -c)" -eq "$EXPECT_BYTES" ] \
         && [ "$content" = "$EXPECT_CONTENT" ]; then
        correct=true
      else
        correct=false
      fi
    else
      present=no; lsout=absent; content=""; correct=false
    fi

    # A file that is right on disk is a success even when the exit code says
    # otherwise, but the exit code is recorded too, because the disagreement is
    # the bug PR #174 exists to fix and a reader hitting it deserves both facts.
    if [ "$present" = yes ] && [ "$correct" = true ]; then
      outcome=success
    else
      outcome=failure
    fi

    # Only a failure has a cause. Classifying a success reads its ordinary
    # progress output as an error string and puts a bogus mode in the breakdown.
    if [ "$outcome" = success ]; then
      cause=none
    else
      cause=$(classify "$RUNHOME")
    fi

    # Record the model actually under test, not the literal token: a __default__
    # run is recorded as the slug the engine resolved, so the results file says
    # which model the documented command reached on the day it was measured.
    effective="$model"
    [ "$model" = "__default__" ] && effective="${SHIPPED_DEFAULT:-__default__}"

    python3 - "$RESULTS" "$i" "$effective" "$rc" "$secs" "$present" "$correct" \
             "$outcome" "$cause" "$lsout" "$RUNHOME" "$psecs" <<'PY'
import json, sys
(path, i, model, rc, secs, present, correct, outcome, cause, lsout,
 runhome, psecs) = sys.argv[1:13]
rec = {
    "run": int(i), "model": model, "exit_code": int(rc),
    "wall_clock_seconds": int(secs),
    "provision_seconds": int(psecs),
    "hello_txt_present": present == "yes",
    "hello_txt_correct": correct == "true", "outcome": outcome,
    "error_class": cause, "ls": lsout,
    "output_tail": (
        open(f"{runhome}/out.txt", errors="replace").read()
        + open(f"{runhome}/err.txt", errors="replace").read()
    )[-400:].strip(),
}
with open(path, "a") as fh:
    fh.write(json.dumps(rec) + "\n")
PY

    printf 'run %2s  exit=%s  %4ss (+%ss setup)  %-16s  %s\n' \
      "$i" "$rc" "$secs" "$psecs" "$outcome" "$cause"
    i=$(( i + 1 ))
  done
done

echo
echo "=== summary ==="
python3 - "$RESULTS" <<'PY'
import json, sys
from collections import Counter, defaultdict

path = sys.argv[1]
rows = [json.loads(l) for l in open(path) if l.strip()]
total = len(rows)
ok = [r for r in rows if r["outcome"] == "success"]
print(f"{len(ok)} successes / {total - len(ok)} failures  (of {total})")

by_model = defaultdict(lambda: [0, 0])
for r in rows:
    by_model[r["model"]][0 if r["outcome"] == "success" else 1] += 1
print("\nper model:")
for m, (s, f) in sorted(by_model.items()):
    print(f"  {m}: {s} success / {f} failure")

print("\nper error class:")
for cause, n in sorted(Counter(r["error_class"] for r in rows).items()):
    print(f"  {cause}: {n}")

secs = sorted(r["wall_clock_seconds"] for r in ok)
if secs:
    print(f"\nwall clock on success: min={secs[0]}s "
          f"median={secs[len(secs)//2]}s max={secs[-1]}s")

psecs = sorted(r["provision_seconds"] for r in rows)
if psecs:
    print(f"rune + mvge setup per run: min={psecs[0]}s "
          f"median={psecs[len(psecs)//2]}s max={psecs[-1]}s")
    if secs:
        print(f"worst case steps 3-5: "
              f"{psecs[-1] + secs[-1]}s "
              f"({(psecs[-1] + secs[-1]) / 60:.1f} min of the 5-minute budget)")

# The partial-work case is the one that changes what a reader should do next,
# so it is called out rather than left inside the failure count.
partial = [r for r in rows
           if r["hello_txt_correct"] and r["exit_code"] != 0]
if partial:
    print(f"\nNOTE: {len(partial)} run(s) wrote a correct hello.txt but exited "
          f"non-zero. Retrying without checking can overwrite completed work.")
PY
echo
echo "RESULTS: $RESULTS"