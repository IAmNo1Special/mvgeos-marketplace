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
# Requires OPENROUTER_API_KEY, or ~/.agents/auth/openrouter.json on this machine.
set -u

RUNS="${RUNS:-10}"
SPEC="${SPEC:-git+https://github.com/IAmNo1Special/mvgeos#subdirectory=mvgeos-cli}"
TASK="${TASK:-Create a file named hello.txt containing exactly the text: hello from mvgeos}"
EXPECT_BYTES="${EXPECT_BYTES:-17}"
EXPECT_CONTENT="${EXPECT_CONTENT:-hello from mvgeos}"
DEFAULT_MODEL="${DEFAULT_MODEL:-nvidia/nemotron-3-ultra-550b-a55b:free}"
MODELS="${MODELS:-$DEFAULT_MODEL}"
OUTDIR="${OUTDIR:-$(mktemp -d "${TMPDIR:-/tmp}/mvgeos-quickstart-verify.XXXXXX")}"

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
# Absolute, captured before any run rewrites HOME. Reading it relative to the
# mutated HOME is how the first version of this staged credentials into the
# wrong home and every run failed with "API key required".
AUTH_SRC="$HOME/.agents/auth/openrouter.json"
[ -s "$AUTH_SRC" ] || AUTH_SRC=""

stage_auth() {
  local dest_home="$1"
  mkdir -p "$dest_home/.agents/auth"
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    python3 -c 'import json,os,sys; json.dump({"api_key": os.environ["OPENROUTER_API_KEY"]}, open(sys.argv[1],"w"))' \
      "$dest_home/.agents/auth/openrouter.json"
    chmod 600 "$dest_home/.agents/auth/openrouter.json"
    return 0
  fi
  if [ -n "$AUTH_SRC" ] && [ -s "$AUTH_SRC" ]; then
    install -m 600 "$AUTH_SRC" "$dest_home/.agents/auth/openrouter.json"
    return 0
  fi
  return 1
}

clean_env() {
  # Empty HOME, empty XDG. Nothing may survive between runs: a leftover
  # ~/.agents/models.json or an already-installed Rune would make run 2 easier
  # than run 1 and the split would flatter us.
  local home="$1"
  rm -rf "$home"
  mkdir -p "$home/work" "$home/.local/share" "$home/.config" "$home/.local/state"
  export HOME="$home"
  export XDG_CACHE_HOME="$home/.cache"
  export XDG_CONFIG_HOME="$home/.config"
  export XDG_DATA_HOME="$home/.local/share"
  export XDG_STATE_HOME="$home/.local/state"
  # Shared on purpose, and only this. See the note above on what may be shared.
  export UV_CACHE_DIR="$SHARED_UV_CACHE"
  export UV_TOOL_DIR="$PROVISION_HOME/toolbin"
  export UV_TOOL_BIN_DIR="$PROVISION_HOME/toolbin/bin"
  # Credentials go in the home the run will actually use. The realm is what
  # reads them, and a run whose only failure is "API key required" measures
  # nothing about the five-minute promise.
  stage_auth "$home" || return 1
  return 0
}

# A clean machine has no Realm and no Mvge. The run installs both, which is
# steps 3 and 4 of the quickstart and part of the five minutes.
provision_run() {
  local runhome="$1"
  local log="$runhome/provision.log"
  "$MV" rune install openrouter-realm --confirm-python-deps >> "$log" 2>&1 \
    || { echo "  rune install FAILED (see $log)"; return 1; }
  "$MV" mvge install coding_mvge >> "$log" 2>&1 \
    || { echo "  mvge install FAILED (see $log)"; return 1; }
  return 0
}

MV=""
provision() {
  echo "=== provision once: install + realm + mvge ==="
  clean_env "$PROVISION_HOME" || { echo "FAIL: no OpenRouter credentials"; exit 2; }
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
  "$MV" rune install openrouter-realm --confirm-python-deps > "$OUTDIR/rune.log" 2>&1
  echo "rune install exit=$?"
  "$MV" mvge install coding_mvge > "$OUTDIR/mvge.log" 2>&1
  echo "mvge install exit=$?"
  echo "--- provisioned model ---"
  "$MV" info --agent-name coding_mvge 2>&1 | grep -iE "model|rune" | head -4
}

# What the CLI actually printed, reduced to the lines a reader would act on.
# The CLI prints its errors on stdout, not stderr. Reading only stderr made
# every single failure classify as "silent" and hid the cause entirely.
classify() {
  local runhome="$1"
  local err="$runhome/err.txt"
  local outf="$runhome/out.txt"
  if grep -qi "quota exhausted" "$outf" "$err"; then echo "spent_allowance"
  elif grep -qi "temporarily overloaded\|upstream provider overloaded" "$outf" "$err"; then echo "capacity"
  elif grep -qi "exceeds your current quota" "$outf" "$err"; then echo "mana_exhausted"
  elif grep -qi "unknown model" "$outf" "$err"; then echo "unknown_model"
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
  echo "=== model: $model ==="
  # -m is passed explicitly so the recorded model is the model under test rather
  # than whatever the shipped default happens to be on the day of the run.
  case "$model" in
    */*|*:*) model_arg=(-m "$model") ;;
    *)      model_arg=(-m "$model") ;;
  esac

  i=1
  while [ "$i" -le "$RUNS" ]; do
    RUNHOME="$OUTDIR/run-$i"
    clean_env "$RUNHOME" || { echo "FAIL: could not stage credentials"; exit 2; }

    # Steps 3 and 4, on the run's own clean machine, timed separately so the
    # task's wall clock is not quietly carrying the install cost.
    pstart=$(date +%s)
    if ! provision_run "$RUNHOME"; then
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

    cause=$(classify "$RUNHOME")
    # A file that is right on disk is a success even when the exit code says
    # otherwise, but the exit code is recorded too, because the disagreement is
    # the bug PR #174 exists to fix and a reader hitting it deserves both facts.
    if [ "$present" = yes ] && [ "$correct" = true ]; then
      outcome=success
    else
      outcome=failure
    fi

    python3 - "$RESULTS" "$i" "$model" "$rc" "$secs" "$present" "$correct" \
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