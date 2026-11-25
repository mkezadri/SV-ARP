#!/usr/bin/env bash
# Execute the 15 Gradle-built Mockito bugs (benchmark/mockito_gradle_15.txt) in
# the configurations given, wherever they have no completed execution yet,
# without touching the results that exist.
#
# Nothing is changed in the runner, the code or the settings: each bug gets one
# more execution under the same limits as every other bug. A bug whose baseline
# does not build within the runner's limit is recorded as such and is not tried
# again by this script.
#
# For each configuration, one after the other:
#   1. the bugs of the list to execute are written to
#      results_mockito15/todo_<configuration>.txt: those with no completed
#      execution in results_arm_<configuration> and no record from this script
#      in results_mockito15/;
#   2. the existing folder results_arm_<configuration> is set aside (a rename;
#      nothing is copied or deleted);
#   3. ./run_all.sh runs those bugs into a fresh results_arm_<configuration>,
#      exactly as it runs the full list;
#   4. the fresh folder is moved to results_mockito15/ and the existing folder
#      is put back under its name.
#
# Usage, from the SV-ARP folder, with no other run in progress:
#
#     source apr-env.sh
#     nohup bash scripts/topup_mockito15.sh full no_semantic binary_only no_judge \
#           sample_t010 sample_t045a sample_t045b sample_t085 \
#           > supervisor_mockito15.log 2>&1 &
#     tail -f supervisor_mockito15.log
#
# If it is interrupted, start the same command again: it continues with the
# bugs that have no record yet. A bug cut in the middle leaves no record.
# To stop it:  pkill -9 -f run_all.sh; pkill -f run_benchmark.py
set -u
LIST="benchmark/mockito_gradle_15.txt"
OUT="results_mockito15"

say() { printf '%s  [mockito15] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { say "STOP: $*"; exit 1; }

[ $# -gt 0 ] || die "name the configurations, for example: full no_semantic binary_only no_judge sample_t010"
[ -f ./run_all.sh ] || die "run this from the SV-ARP folder (run_all.sh not found here)"
[ -f "$LIST" ] || die "$LIST not found"
[ "$(grep -c . "$LIST")" = "15" ] || die "$LIST must hold 15 bug names"
: "${D4J_HOME:?STOP: D4J_HOME not set (source apr-env.sh first)}"
DIST="$D4J_HOME/framework/lib/build_systems/gradle/dists/gradle-4.9-bin.zip"
[ -f "$DIST" ] || die "Gradle is not unpacked: $DIST is missing"
[ -n "${APR_BASELINE_COMPILE_TIMEOUT:-}" ] && die "APR_BASELINE_COMPILE_TIMEOUT is set in this terminal; open a new one (it must not be set)"

RUNNER_FILE="${RUNNER:-}"
if [ -z "$RUNNER_FILE" ]; then
    if [ -f run_benchmark.py ]; then RUNNER_FILE="run_benchmark.py"
    elif [ -f src/run_benchmark.py ]; then RUNNER_FILE="src/run_benchmark.py"
    fi
fi
[ -n "$RUNNER_FILE" ] && [ -f "$RUNNER_FILE" ] || die "run_benchmark.py not found"
CODE_FILE="$(dirname "$RUNNER_FILE")/agentic_apr.py"
hash256() { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -c1-16; else sha256sum "$1" | cut -c1-16; fi; }

if pgrep -f "python.*run_benchmark\.py" >/dev/null 2>&1 || pgrep -f "bash .*run_all\.sh" >/dev/null 2>&1; then
    die "another run is in progress on this machine; wait until it has finished"
fi
[ -f STOP ] && die "a STOP file is present; remove it first (rm STOP)"

for arm in "$@"; do
    case "$arm" in
        full|no_semantic|binary_only|no_judge|sample_t[0-9][0-9][0-9]|sample_t[0-9][0-9][0-9][a-z]) ;;
        *) die "unknown configuration '$arm'" ;;
    esac
    [ -d "results_arm_${arm}" ] || die "results_arm_${arm} not found"
    [ -e "results_arm_${arm}.aside" ] && die "results_arm_${arm}.aside exists: an earlier run was cut short. \
If results_arm_${arm} holds only Mockito bugs, move it away, then: mv results_arm_${arm}.aside results_arm_${arm}"
done
mkdir -p "$OUT"

# A record is final unless the bug was cut by the API quota before any attempt
# or ended on an unusable Judge answer (the supervisor's own rule).
# missing ARM FILE: write to FILE the bugs of the list with no completed
# execution in results_arm_ARM and no final record in OUT; print how many
missing() {
    python3 - "$LIST" "$1" "$OUT" "$2" <<'PY'
import csv, glob, os, sys
csv.field_size_limit(10**9)
lst, arm, out, target = sys.argv[1:5]
wanted = [l.strip() for l in open(lst) if l.strip()]
def final(r):
    it = int(float(r["iterations"])) if r.get("iterations") else 0
    tok = int(float(r["total_tokens"])) if r.get("total_tokens") else 0
    if r.get("status") == "failed" and it == 0 and tok == 0:
        return False
    return r.get("verdict") != "error"
def completed(r):
    return (r.get("status") == "completed" and r.get("verdict") != "error"
            and (r.get("baseline_failing_count") or "").strip() != "0")
have = set()
for f in glob.glob(os.path.join(f"results_arm_{arm}", "results_*.csv")):
    for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
        if completed(r):
            have.add(r.get("bug_id"))
for d in glob.glob(os.path.join(out, f"results_arm_{arm}*")):
    for f in glob.glob(os.path.join(d, "results_*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
            if final(r):
                have.add(r.get("bug_id"))
todo = [b for b in wanted if b not in have]
with open(target, "w") as fh:
    fh.write("\n".join(todo) + ("\n" if todo else ""))
print(len(todo))
PY
}

# recorded FOLDER FILE: of the bugs in FILE, how many have a final record, and
# how many of those are completed executions
recorded() {
    python3 - "$2" "$1" <<'PY'
import csv, glob, os, sys
csv.field_size_limit(10**9)
wanted = {l.strip() for l in open(sys.argv[1]) if l.strip()}
def final(r):
    it = int(float(r["iterations"])) if r.get("iterations") else 0
    tok = int(float(r["total_tokens"])) if r.get("total_tokens") else 0
    if r.get("status") == "failed" and it == 0 and tok == 0:
        return False
    return r.get("verdict") != "error"
fin, comp = set(), set()
for f in glob.glob(os.path.join(sys.argv[2], "results_*.csv")):
    for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
        b = r.get("bug_id")
        if b in wanted and final(r):
            fin.add(b)
            if r.get("status") == "completed":
                comp.add(b)
print(len(fin), len(comp))
PY
}

aside=""; ran=""
put_back() {
    [ -n "$aside" ] || return 0
    local arm="$aside" fresh="results_arm_${aside}" stamp dest
    stamp="$(date '+%Y%m%d_%H%M%S')"
    if [ -n "$ran" ] && [ -d "$fresh" ]; then
        rm -rf "$fresh/.supervisor.lock"
        if [ "${1:-}" = "complete" ]; then
            dest="$OUT/results_arm_${arm}"
            [ -e "$dest" ] && dest="$OUT/results_arm_${arm}.again_${stamp}"
        else
            dest="$OUT/results_arm_${arm}.interrupted_${stamp}"
        fi
        mv "$fresh" "$dest"
        say "$arm: new records are in $dest"
    fi
    if [ -d "results_arm_${arm}.aside" ]; then
        mv "results_arm_${arm}.aside" "results_arm_${arm}"
        say "$arm: existing results are back in results_arm_${arm}"
    fi
    aside=""; ran=""
}
trap 'put_back interrupted' EXIT
trap 'exit 130' INT TERM

say "configurations: $*"
say "runner: $RUNNER_FILE (sha256 $(hash256 "$RUNNER_FILE")...); code: $CODE_FILE (sha256 $( [ -f "$CODE_FILE" ] && hash256 "$CODE_FILE")...)"
summary=""
for arm in "$@"; do
    todo="$OUT/todo_${arm}.txt"
    n="$(missing "$arm" "$todo")"
    case "$n" in ''|*[!0-9]*) die "$arm: could not list the bugs to execute" ;; esac
    if [ "$n" = "0" ]; then
        say "$arm: every bug of the list has a completed execution or a record from this script; nothing to do"
        continue
    fi
    say "$arm: $n bug(s) to execute: $(tr '\n' ' ' < "$todo")"
    aside="$arm"; ran=""
    mv "results_arm_${arm}" "results_arm_${arm}.aside" || die "cannot set results_arm_${arm} aside"
    say "$arm: existing results set aside (results_arm_${arm}.aside)"
    ran=1
    BUG_LIST="$todo" ./run_all.sh "$arm"
    rc=$?
    if pgrep -f "python.*run_benchmark\.py" >/dev/null 2>&1; then
        say "$arm: the runner is still alive after the supervisor ended; stopping it"
        pkill -f "python.*run_benchmark\.py" >/dev/null 2>&1
        sleep 5
    fi
    read -r n_rec n_done <<EOF
$(recorded "results_arm_${arm}" "$todo")
EOF
    say "$arm: supervisor ended (exit $rc); $n_rec of $n bug(s) recorded, $n_done completed"
    if [ "${n_rec:-0}" = "$n" ]; then
        put_back complete
        summary="$summary $arm:$n_done/$n"
        [ "$n_done" != "$n" ] && say "$arm: $((n - n_done)) bug(s) recorded as not building; they are not tried again"
    else
        put_back interrupted
        die "$arm: not every bug was recorded (interrupted, or out of quota). Start the same command again later."
    fi
done
say "ALL DONE (completed/executed per configuration):$summary"
say "send the folder $OUT and this log"
