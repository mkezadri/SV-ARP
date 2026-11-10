#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Supervisor for long unattended SV-ARP runs.
#
#   ./run_all.sh                 # all four configurations, in order
#   ./run_all.sh full            # one configuration
#   ./run_all.sh full no_judge   # a subset
#   ./run_all.sh sample_t045a    # a single-attempt resampling pass at temperature
#                                # 0.45 (name pattern sample_tNNN[a-z]; accepts on
#                                # the tests alone, one iteration per bug)
#   ./run_all.sh --status        # where every configuration stands
#
# Survives: network drops, laptop sleep, API quota exhaustion, crashes,
# terminal closure, SSH disconnection. Picks up where it left off.
#
# Start it with:
#   nohup ./run_all.sh > supervisor.log 2>&1 &
#   tail -f supervisor.log
#
# Stop it with:
#   touch STOP        # finishes the current bug, then exits cleanly
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

ALL_ARMS=(full no_semantic binary_only no_judge)

STATUS_ONLY=0
if [ "${1:-}" = "--status" ]; then
    STATUS_ONLY=1
    ARMS=("${ALL_ARMS[@]}")
else
    [ $# -gt 0 ] && ARMS=("$@") || ARMS=("${ALL_ARMS[@]}")
fi

BUG_LIST="${BUG_LIST:-benchmark/versions.txt}"
RUNNER="${RUNNER:-src/run_benchmark.py}"  # set this if your runner has another name
PASS_SLEEP="${PASS_SLEEP:-1800}"     # wait between passes when work remains (30 min)
QUOTA_SLEEP="${QUOTA_SLEEP:-7200}"   # wait after quota exhaustion (2 h)
MAX_PASSES="${MAX_PASSES:-500}"
MAX_BUG_ATTEMPTS="${MAX_BUG_ATTEMPTS:-4}"  # stop requeueing a bug after N tries
MAX_STALLS="${MAX_STALLS:-6}"        # give up on an arm after N passes with no progress
VERBOSE="${VERBOSE:-1}"              # 1 = mirror the runner's output to the terminal
                                     # 0 = quiet, only the per-pass summary lines
MIN_FREE_GB="${MIN_FREE_GB:-15}"     # below this, reclaim space before the next pass
ABORT_FREE_GB="${ABORT_FREE_GB:-5}"  # below this, stop cleanly rather than crash
MAX_LOG_MB="${MAX_LOG_MB:-200}"      # rotate and gzip an arm log past this size
WORK_ROOT="${WORK_ROOT:-/tmp}"       # where scratch checkouts go; point this at an
                                     # external disk if the boot volume is tight
CLEAN_WORK="${CLEAN_WORK:-1}"        # 1 = wipe the arm's work dir after every pass
HANG_MINUTES="${HANG_MINUTES:-30}"   # restart the pass if the arm log goes quiet this long
HANG_CHECK_EVERY="${HANG_CHECK_EVERY:-120}"   # how often the hang monitor looks, seconds
WATCHDOG="${WATCHDOG:-0}"            # 1 = prune checkouts DURING a pass. Off by default:
                                     # the runner now deletes each checkout when it is
                                     # done, and pruning concurrently races with its own
                                     # rmtree and crashes the pass.
PRUNE_EVERY="${PRUNE_EVERY:-300}"    # how often to look for abandoned checkouts, seconds
PRUNE_IDLE_MIN="${PRUNE_IDLE_MIN:-60}"       # idle minutes before a checkout is prunable
PRUNE_IDLE_URGENT="${PRUNE_IDLE_URGENT:-15}" # same, once free space is short

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

wd=""
hm=""
_cleanup() {
    for _c in "${wd:-}" "${hm:-}"; do
        [ -n "$_c" ] || continue
        pkill -P "$_c" >/dev/null 2>&1
        kill "$_c"     >/dev/null 2>&1
    done
}
trap _cleanup EXIT INT TERM

# ── preflight ────────────────────────────────────────────────────────────────
[ -f "$BUG_LIST" ] || { log "FATAL: $BUG_LIST not found"; exit 1; }
[ "$STATUS_ONLY" = "1" ] || [ -f "$RUNNER" ] || {
    log "FATAL: runner '$RUNNER' not found in $(pwd)"
    log "       set RUNNER=path/to/runner.py, or cd to where it lives"
    exit 1
}

if [ "$STATUS_ONLY" = "0" ]; then
    # A STOP file left over from the previous arm would make this exit at once,
    # which is easy to misread as "the arm finished".
    if [ -f STOP ]; then
        log "FATAL: a STOP file is present, left over from an earlier run."
        log "       rm STOP   then launch again"
        exit 1
    fi
    : "${D4J_HOME:?FATAL: D4J_HOME not set — source apr-env.sh first}"
    if [ -z "${APR_API_KEYS:-}" ] && [ -z "${GEMINI_API_KEY:-}" ]; then
        log "FATAL: set APR_API_KEYS (comma-separated) or GEMINI_API_KEY"; exit 1
    fi
    java -version 2>&1 | grep -q 'version "11' || log "WARNING: Java 11 expected"
    echo "${_JAVA_OPTIONS:-}" | grep -q 'user.language=en' \
        || { log "FATAL: _JAVA_OPTIONS must set -Duser.language=en -Duser.country=US"; exit 1; }

    # keep the Mac awake for the whole run
    if command -v caffeinate >/dev/null 2>&1; then
        caffeinate -dimsu -w $$ &
        log "caffeinate attached to PID $$"
    fi
fi

NET_URL="${NET_URL:-https://generativelanguage.googleapis.com}"

wait_for_network() {
    local n=0
    until curl -s --max-time 10 -o /dev/null "$NET_URL"; do
        n=$((n+1))
        log "no network (attempt $n) — retrying in 60s"
        sleep 60
        [ -f STOP ] && { log "STOP file present; exiting"; exit 0; }
    done
    [ $n -gt 0 ] && log "network restored after $n attempt(s)"
}

# ── count how many bugs of an arm are still outstanding ──────────────────────
remaining() {
    local arm="$1"
    local dir="results_arm_${arm}"
    python3 - "$BUG_LIST" "$dir" "$MAX_BUG_ATTEMPTS" <<'PY'
import csv, glob, os, sys
from collections import Counter
csv.field_size_limit(10**9)
bug_list, results_dir = sys.argv[1], sys.argv[2]
max_attempts = int(sys.argv[3])
wanted = [l.strip() for l in open(bug_list) if l.strip()]
best = {}
attempts = Counter()
for f in glob.glob(os.path.join(results_dir, "**", "*.csv"), recursive=True):
    for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
        b = r.get("bug_id")
        if not b:
            continue
        attempts[b] += 1
        m = os.path.getmtime(f)
        if b not in best or m > best[b][0]:
            best[b] = (m, r)

def done(r):
    """A bug is done unless it was killed by quota or never ran."""
    it  = int(float(r["iterations"]))   if r.get("iterations")   else 0
    tok = int(float(r["total_tokens"])) if r.get("total_tokens") else 0
    if r.get("status") == "failed" and it == 0 and tok == 0:
        return False                      # quota kill — retry
    if r.get("verdict") == "error":
        return False
    return True

# A bug that keeps failing deterministically must not pin the whole arm, so
# stop requeueing it after max_attempts tries. Give-ups are listed in
# .gaveup.txt so they are visible rather than silently missing.
todo, gaveup = [], []
for b in wanted:
    if b in best and done(best[b][1]):
        continue
    if attempts[b] >= max_attempts:
        gaveup.append("%s (%d attempts)" % (b, attempts[b]))
        continue
    todo.append(b)

with open(os.path.join(results_dir, ".todo.txt"), "w") as fh:
    fh.write("\n".join(todo) + ("\n" if todo else ""))
with open(os.path.join(results_dir, ".gaveup.txt"), "w") as fh:
    fh.write("\n".join(gaveup) + ("\n" if gaveup else ""))
print(len(todo))
PY
}

# ── ./run_all.sh --status : where every arm stands, and nothing else ────────
if [ "$STATUS_ONLY" = "1" ]; then
    printf '  %-14s %-12s %s\n' arm outstanding results
    for a in "${ARMS[@]}"; do
        d="results_arm_${a}"
        if [ -d "$d" ]; then
            printf '  %-14s %-12s %s\n' "$a" "$(remaining "$a")" \
                   "$(find "$d" -name '*.csv' | wc -l | tr -d ' ') csv"
        else
            printf '  %-14s %-12s %s\n' "$a" "-" "not started"
        fi
    done
    exit 0
fi

# ── disk ─────────────────────────────────────────────────────────────────────
free_gb() {   # free_gb <path>   -> whole GB available on that volume
    python3 - "$1" <<'PY'
import os, shutil, sys
p = os.path.abspath(sys.argv[1])
while not os.path.isdir(p):
    q = os.path.dirname(p)
    if q == p: break
    p = q
try:
    print(shutil.disk_usage(p).free // (1024 ** 3))
except Exception:
    print(9999)          # unknown: never block the run on a failed measurement
PY
}

rotate_logs() {
    local f sz
    for f in ./*.log; do
        [ -f "$f" ] || continue
        sz=$(wc -c < "$f" 2>/dev/null || echo 0)
        if [ "$sz" -gt $(( MAX_LOG_MB * 1024 * 1024 )) ]; then
            local stamp; stamp=$(date '+%Y%m%d-%H%M%S')
            mv "$f" "${f%.log}-${stamp}.log" \
                && gzip -f "${f%.log}-${stamp}.log" \
                && log "rotated $f -> ${f%.log}-${stamp}.log.gz"
        fi
    done
}

# Wipe an arm's scratch checkouts. Safe ONLY between passes, when no bug is
# being worked on — the runner recreates each checkout from scratch.
wipe_work() {   # wipe_work <arm>
    local arm="$1" sz
    local work="${WORK_ROOT}/d4j_${arm}"
    [ -d "$work" ] || return 0
    sz=$(du -sm "$work" 2>/dev/null | awk '{print $1}')
    rm -rf "${work:?}"/* 2>/dev/null
    [ -n "${sz:-}" ] && [ "$sz" -gt 1 ] && log "cleaned $work (${sz} MB)"
    return 0
}

# Prune checkouts that look abandoned, while a pass is running. Conservative
# on purpose: a directory is removed only if NOTHING under it has been touched
# for <idle> minutes, and the <keep> most recently touched are never removed.
# Deleting a checkout mid-test would record a false failure for that bug.
prune_work() {   # prune_work <dir> <idle_minutes> <keep>
    python3 - "$1" "$2" "$3" <<'PY'
import os, shutil, sys, time
root, idle, keep = sys.argv[1], float(sys.argv[2]) * 60, int(sys.argv[3])
cut = time.time() - idle
try:
    subs = [e.path for e in os.scandir(root) if e.is_dir(follow_symlinks=False)]
except (FileNotFoundError, NotADirectoryError):
    sys.exit(0)

def newest(p):
    """Newest mtime anywhere under p, returning early once we know it is active."""
    best = 0.0
    for dirpath, _dirnames, filenames in os.walk(p):
        for name in (dirpath,) + tuple(os.path.join(dirpath, f) for f in filenames):
            try:
                m = os.stat(name).st_mtime
            except OSError:
                continue
            if m > best:
                best = m
                if best > cut:        # active: stop walking
                    return best
    return best

scored = sorted(((newest(p), p) for p in subs), reverse=True)
protected = {p for _, p in scored[:keep]}
for m, p in scored:
    if p in protected or m >= cut:
        continue
    shutil.rmtree(p, ignore_errors=True)
    print("removed %s" % os.path.basename(p))
PY
}

# A pass can run all 388 bugs, so waiting for the gap between passes is not
# enough if the runner leaves its checkouts behind. This watches during the
# pass and removes only checkout dirs untouched for 20 minutes — the bug being
# worked on right now is, by definition, the recently-modified one.
disk_watchdog() {   # disk_watchdog <arm> <supervisor pid>
    local arm="$1" boss="$2" f idle keep n
    local work="${WORK_ROOT}/d4j_${arm}"
    # Stop as soon as the supervisor is gone. Without this the subshell is
    # orphaned by `pkill -f run_all.sh` and keeps pruning /tmp forever.
    while kill -0 "$boss" 2>/dev/null; do
        sleep "$PRUNE_EVERY"
        [ -d "$work" ] || continue
        f=$(free_gb .)
        if [ "$f" -lt "$MIN_FREE_GB" ]; then
            idle="$PRUNE_IDLE_URGENT"; keep=1
        else
            idle="$PRUNE_IDLE_MIN"; keep=2
        fi
        n=$(prune_work "$work" "$idle" "$keep" 2>/dev/null | grep -c '^removed ')
        if [ "${n:-0}" -gt 0 ]; then
            log "watchdog: pruned $n checkout(s) idle >${idle} min, $(free_gb .) GB free"
        fi
        rotate_logs
    done
}

# A hung API call raises nothing and returns nothing: the runner stays alive
# and silent forever. This only reads a timestamp and kills the runner, so it
# cannot race with anything the way the disk pruner did. The supervisor then
# starts a fresh pass and --resume picks up where it stopped.
hang_monitor() {   # hang_monitor <arm> <supervisor pid>
    local arm="$1" boss="$2" lg="${arm}.log" age now mt
    while kill -0 "$boss" 2>/dev/null; do
        sleep "$HANG_CHECK_EVERY"
        [ -f "$lg" ] || continue
        now=$(date +%s)
        mt=$(python3 -c 'import os,sys; print(int(os.path.getmtime(sys.argv[1])))' "$lg" 2>/dev/null) || continue
        age=$(( now - mt ))
        if [ "$age" -gt $(( HANG_MINUTES * 60 )) ]; then
            log "hang monitor: ${lg} silent for $(( age / 60 )) min — restarting the pass"
            pkill -f "[r]un_benchmark.py --bug-list results_arm_${arm}/.todo.txt"
            sleep 30
        fi
    done
}

check_disk() {   # check_disk <arm>   -- returns 1 if the run must stop
    local arm="$1" f
    f=$(free_gb .)
    if [ "$f" -lt "$MIN_FREE_GB" ]; then
        log "only ${f} GB free (want ${MIN_FREE_GB}) — reclaiming"
        for a in "${ARMS[@]}"; do wipe_work "$a"; done   # safe: between passes
        rotate_logs
        f=$(free_gb .)
        log "after reclaiming: ${f} GB free"
    fi
    if [ "$f" -lt "$ABORT_FREE_GB" ]; then
        log "FATAL: ${f} GB free, below the ${ABORT_FREE_GB} GB floor."
        log "Stopping now so a half-written CSV cannot corrupt the results."
        log "Free space, then relaunch — --resume picks up where this left off."
        return 1
    fi
    DISK_FREE="$f"
    return 0
}

# ── one pass of one arm ──────────────────────────────────────────────────────
run_pass() {
    local arm="$1" dir="$2"
    # Create the scratch root here rather than relying on the runner: after a
    # reset the directory is gone, and /tmp is also periodically cleaned by the
    # OS, so the runner can start with a missing parent and die on makedirs.
    local work="${WORK_ROOT}/d4j_${arm}"
    if ! mkdir -p "$work" 2>/dev/null; then
        log "FATAL: cannot create work dir $work"
        log "       check that ${WORK_ROOT} exists and is writable, or set WORK_ROOT"
        return 1
    fi
    local ablation="$arm" temp="${APR_TEMPERATURE:-0.1}" maxit="${APR_MAX_ITERATIONS:-4}"
    case "$arm" in
        sample_t*) ablation="no_judge"; maxit=1
                   temp="$(printf '%s' "$arm" | sed -E 's/^sample_t([0-9])([0-9]{2})[a-z]*$/\1.\2/')" ;;
    esac
    APR_ABLATION="$ablation" \
    APR_TEMPERATURE="$temp" \
    APR_MAX_ITERATIONS="$maxit" \
    APR_RESULTS_DIR="$dir" \
    APR_PATCH_DIR="patches_${arm}" \
    APR_WORK_DIR="${WORK_ROOT}/d4j_${arm}" \
        python3 -u "$RUNNER" --bug-list "$dir/.todo.txt" --resume
}

# ── main loop ────────────────────────────────────────────────────────────────
log "supervisor starting — arms: ${ARMS[*]}"
log "bug list: $BUG_LIST"

for arm in "${ARMS[@]}"; do
    dir="results_arm_${arm}"
    mkdir -p "$dir"
    pass=0
    stalls=0

    while :; do
        [ -f STOP ] && { log "STOP file present; exiting"; exit 0; }
        pass=$((pass+1))
        [ $pass -gt "$MAX_PASSES" ] && { log "$arm: pass limit reached"; break; }

        wait_for_network
        left=$(remaining "$arm")
        if ! [[ "$left" =~ ^[0-9]+$ ]]; then
            log "$arm: could not compute remaining ($left) — retrying in 60s"
            sleep 60; continue
        fi
        if [ "$left" -eq 0 ]; then
            log "$arm: COMPLETE"
            break
        fi

        check_disk "$arm" || exit 1

        log "$arm: pass $pass — $left bug(s) outstanding, ${DISK_FREE} GB free"
        gu="$dir/.gaveup.txt"
        [ -s "$gu" ] && log "$arm: gave up on $(grep -c . "$gu") bug(s) — see $gu"

        wd=""
        [ "$WATCHDOG" = "1" ] && { disk_watchdog "$arm" $$ & wd=$!; }
        hang_monitor "$arm" $$ & hm=$!
        if [ "$VERBOSE" = "1" ]; then
            # -u matters: without it Python buffers and the terminal stays
            # blank for minutes at a time.
            run_pass "$arm" "$dir" 2>&1 | tee -a "${arm}.log"
            rc=${PIPESTATUS[0]}
        else
            run_pass "$arm" "$dir" >> "${arm}.log" 2>&1
            rc=$?
        fi
        if [ -n "$wd" ]; then
            pkill -P "$wd" >/dev/null 2>&1; kill "$wd" >/dev/null 2>&1
            wait "$wd" 2>/dev/null
        fi
        if [ -n "${hm:-}" ]; then
            pkill -P "$hm" >/dev/null 2>&1; kill "$hm" >/dev/null 2>&1
            wait "$hm" 2>/dev/null
        fi

        # the pass is over, so nothing is mid-test: the work dir is disposable
        [ "$CLEAN_WORK" = "1" ] && wipe_work "$arm"
        rotate_logs

        after=$(remaining "$arm")
        log "$arm: pass $pass finished (exit $rc), $after remaining, $(free_gb .) GB free"

        [ "$after" -eq 0 ] && { log "$arm: COMPLETE"; break; }

        if [ "$after" -eq "$left" ]; then
            stalls=$((stalls+1))
            if [ "$stalls" -ge "$MAX_STALLS" ]; then
                log "$arm: $stalls passes with no progress — giving up, $after bug(s) unresolved"
                log "$arm: see $dir/.todo.txt and ${arm}.log"
                break
            fi
            log "$arm: no progress (stall $stalls/$MAX_STALLS) — sleeping ${QUOTA_SLEEP}s"
            sleep "$QUOTA_SLEEP"
        else
            stalls=0
            sleep "$PASS_SLEEP"
        fi
    done
done

for arm in "${ARMS[@]}"; do wipe_work "$arm"; done
rmdir "${WORK_ROOT}"/d4j_* 2>/dev/null

log "ALL ARMS COMPLETE"
for arm in "${ARMS[@]}"; do
    printf '  %-14s %s\n' "$arm" "$(remaining "$arm") outstanding"
done
log "$(free_gb .) GB free"
