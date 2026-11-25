#!/usr/bin/env python3
"""
Regenerate every number in the paper from the raw result CSVs and the
verification files. Nothing is typed in by hand; every figure traces to a
line here and a row in a raw file.

    python3 make_figures.py --raw results_csvs --rule first  > report.md

Inputs
  --raw DIR          directory holding results_arm_<arm>/results_*.csv
  --verification     verification files, as  arm=path  (repeatable); if absent,
                     verification_<arm>.csv is looked for in the arm dir, the
                     raw dir and the current directory
  --rule             which execution is canonical when a bug completed more
                     than once:  first | last   (default: first)
  --overrides FILE   extra semantic labels: columns  arm,bug_id,semantic_verdict[,which],note
                     which = first (default: the first plausible candidate) or
                     delivered (the patch the loop finally accepted, when it differs)
  --samples DIR      a single-attempt resampling run (results_arm_sample_*), repeatable;
                     if none is given, results_arm_sample_* under --raw are used
  --fixed-baseline F fixed_baseline.csv from fixed_baseline.py (developer-fixed versions)
  --judge-swap FILE  judge-pilot CSVs from judge_swap.py (repeatable)
  --bug-list FILE    the benchmark list (default: union of bugs seen)
  --outdir DIR       where canonical_<arm>.csv tables are written (default: figures_out)

Canonical-record rule
  A bug's canonical record is one of its VALID completed executions
  (status == completed and verdict != error). With --rule first that is the
  execution from the earliest-started session, with --rule last the latest.
  A completed execution always outranks an aborted one (checkout_failed,
  build_broken, failed, extraction_failed) regardless of order. A completed
  execution whose baseline observed zero failing trigger tests is NOT valid:
  plausibility is baseline-relative and an empty baseline makes it vacuous.
  A bug with no valid completed execution is excluded and listed with its reason.

Correctness
  A canonical record counts as correct only if it is plausible AND a human
  label applies to THAT execution's patch. For bugs with several completed
  executions, the verification file's "Reviewed iteration" identifies which
  execution was reviewed; if the canonical execution was not the reviewed one
  and no override supplies a label, the bug is reported as PENDING and is not
  counted as correct.
"""
import argparse, csv, glob, json, math, os, random, re, sys
from collections import Counter, defaultdict, OrderedDict

csv.field_size_limit(10**9)
ARMS = ["full", "no_semantic", "binary_only", "no_judge"]
RICHNESS = {"full": 3, "no_semantic": 2, "binary_only": 1, "no_judge": 0}
PROJECTS = ["Chart", "Closure", "Lang", "Math", "Mockito", "Time"]


# ─────────────────────────────────────────────────────────────────────────────
# loading
# ─────────────────────────────────────────────────────────────────────────────

def session_key(path):
    m = re.search(r"results_(\d{8}_\d{6})", os.path.basename(path))
    return m.group(1) if m else os.path.basename(path)


def load_arm(raw, arm):
    """bug -> list of (session, row) in session order."""
    d = os.path.join(raw, f"results_arm_{arm}")
    files = sorted(glob.glob(os.path.join(d, "results_*.csv")), key=session_key)
    if not files:
        sys.exit(f"no results_*.csv under {d}")
    per = defaultdict(list)
    for f in files:
        s = session_key(f)
        for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
            b = (r.get("bug_id") or "").strip()
            if b:
                per[b].append((s, r))
    return per, [session_key(f) for f in files]


def find_verification(raw, arm, explicit):
    if arm in explicit:
        return explicit[arm]
    cands = [os.path.join(raw, f"results_arm_{arm}", f"verification_{arm}.csv"),
             os.path.join(raw, f"verification_{arm}.csv"),
             f"verification_{arm}.csv"]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def load_verification(path):
    out = {}
    if not path:
        return out
    for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
        b = (r.get("Bug_id") or r.get("bug_id") or "").strip()
        if b:
            out[b] = r
    return out


def order_key(b):
    p, _, n = b.rpartition("_")
    return (PROJECTS.index(p) if p in PROJECTS else 99, int(n) if n.isdigit() else 0)


def truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def fnum(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def valid_completed(r):
    """A usable execution: it completed, the Judge call did not fail, and the
    baseline run observed the trigger tests failing. With an empty baseline
    the plausibility criterion is vacuous (any patch 'passes'), which is what
    a damaged checkout produces."""
    if (r.get("status") or "").strip() != "completed":
        return False
    if (r.get("verdict") or "").strip().lower() == "error":
        return False
    if (r.get("baseline_failing_count") or "").strip() == "0":
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# canonical records
# ─────────────────────────────────────────────────────────────────────────────

def _no_output(step):
    """A repair attempt that received no model output: every generation of every
    file came back without output tokens, so no edit was applied and the
    unchanged file was tested (the model API refused or could not be reached)."""
    md = step.get("metadata") or {}
    parts = [md]
    if md.get("files"):
        try:
            import ast
            fl = ast.literal_eval(md["files"]) if isinstance(md["files"], str) else md["files"]
            if fl and isinstance(fl[0], dict):
                parts = fl
        except Exception:
            pass
    return all(int(fnum(p.get("candidate_tokens"), 0)) == 0 and int(fnum(p.get("changed_lines"), 0)) == 0
               and int(fnum(p.get("blocks_applied"), 0)) == 0 for p in parts)


def lost_attempts(r):
    """(attempts without model output made before the first plausible candidate,
    attempts without model output made after it), as 1-based attempt numbers."""
    pit = int(fnum(r.get("plausible_iteration"), -1)) if truthy(r.get("plausible")) else None
    before, after = [], []
    for st in _history(r):
        if st.get("action") != "repair" or not _no_output(st):
            continue
        it = int(fnum(st.get("iteration"), -1))
        (after if pit is not None and it > pit else before).append(it + 1)
    return before, after


def canonical(per_bug, rule, set_aside=()):
    """bug -> dict(session, row, all_completed=[(session,row)...], excluded_reason)

    set_aside: sessions that shared their working directory with another session.
    Their executions of a bug are canonical only if the bug has no valid execution
    in any other session."""
    out = {}
    for b, lst in per_bug.items():
        comp = [(s, r) for s, r in lst if valid_completed(r)]
        # every completed execution, valid or not: the human review may have
        # been performed on one that is now ruled invalid
        comp_all = [(s, r) for s, r in lst if (r.get("status") or "").strip() == "completed"]
        if comp:
            pref = [(s, r) for s, r in comp if s not in set_aside] or comp
            pick = pref[0] if rule == "first" else pref[-1]
            out[b] = dict(session=pick[0], row=pick[1], completed=comp, eligible=pref,
                          completed_all=comp_all, excluded=None)
        else:
            # no valid execution: report the most informative aborted status
            statuses = [(r.get("status") or "").strip() for _, r in lst]
            reason = next((s for s in statuses if s and s != "completed"), "no record")
            if any((r.get("verdict") or "").strip().lower() == "error" for _, r in lst):
                reason = "judge error on every execution"
            if any((r.get("status") or "") == "completed" and
                   (r.get("baseline_failing_count") or "").strip() == "0" for _, r in lst):
                reason = "empty baseline on every completed execution (damaged checkout) - RE-RUN"
            out[b] = dict(session=None, row=None, completed=[], completed_all=comp_all,
                          excluded=reason)
    return out


def verified_session(bug, entry, ver_row):
    """Which completed execution did the human review? None if undeterminable."""
    comp = entry["completed_all"]
    if len(comp) == 1:
        return comp[0][0]
    if not ver_row:
        return None
    ri = (ver_row.get("Reviewed iteration") or "").strip()
    vp = (ver_row.get("Logged plausible by the suite") or "").strip().lower() == "yes"
    if vp and ri != "":
        hits = [s for s, r in comp if truthy(r.get("plausible")) and
                (r.get("plausible_iteration") or "").strip() == ri]
        if len(hits) == 1:
            return hits[0]
    if not vp:
        hits = [s for s, r in comp if not truthy(r.get("plausible"))]
        if len(hits) == 1:
            return hits[0]
    # the per-bug JSON log is written at completion, so the reviewed record is
    # whichever execution finished last; the latest session is the best proxy
    return comp[-1][0]


_JAVA_TOKEN = re.compile(
    r"(?P<bc>/\*.*?\*/)"                          # block comment
    r"|(?P<lc>//[^\n]*)"                           # line comment
    r'|(?P<s>"(?:\\.|[^"\\\n])*")'                 # string literal
    r"|(?P<c>'(?:\\.|[^'\\\n])*')"                 # character literal
    r"|(?P<w>[A-Za-z_$][A-Za-z0-9_$]*|[0-9][0-9A-Za-z_.]*)"
    r"|(?P<o>>>>=|<<=|>>=|>>>|\.\.\.|->|::|\+\+|--|&&|\|\||==|!=|<=|>=|\+=|-=|\*=|/=|&=|\|=|\^=|%=|<<|>>)"
    r"|(?P<x>\S)", re.S)


def _norm_text(t):
    """Layout-insensitive identity of Java source: the sequence of its tokens.
    Whitespace between tokens is ignored; string and character literals are kept
    verbatim (so ' ' and '' differ), a line comment ends at its line break, and
    comments are compared without their internal whitespace."""
    out = []
    for m in _JAVA_TOKEN.finditer(t or ""):
        tok = m.group(0)
        if m.lastgroup in ("bc", "lc"):
            tok = re.sub(r"\s+", "", tok)
        out.append(tok)
    return "\x1f".join(out)


def _step_text(step):
    """Complete text of one candidate: every file of a multi-file candidate, in
    file-name order (the row-level patch fields hold the first file only)."""
    pf = (step or {}).get("per_file_patches")
    if isinstance(pf, dict) and pf:
        return "\n".join("\x1d%s\x1d\n%s" % (os.path.basename(k), pf[k] or "")
                         for k in sorted(pf, key=os.path.basename))
    return (step or {}).get("patch") or ""


def _candidate_text(r, which="first"):
    """Complete text of the first plausible candidate ('first') or of the last
    candidate of the execution ('final'), read from the per-iteration history."""
    reps = [e for e in _history(r) if e.get("action") == "repair"]
    if which == "first" and truthy(r.get("plausible")):
        pit = int(fnum(r.get("plausible_iteration"), -1))
        hit = [e for e in reps if int(fnum(e.get("iteration"), -2)) == pit]
        if hit:
            return _step_text(hit[0])
        return r.get("plausible_patch") or r.get("patch") or ""
    if reps:
        return _step_text(reps[-1])
    return r.get("patch") or ""


def _patch_text(r):
    """Identity key of an execution's patch: the first plausible candidate if
    there is one, otherwise the last candidate."""
    return _norm_text(_candidate_text(r, "first"))


def _display_text(t):
    """Readable form of a complete candidate text (file separators of multi-file patches)."""
    return re.sub("\x1d([^\x1d]*)\x1d", lambda m: "// ===== FILE: %s =====" % m.group(1), t or "")


def _candidate_outcomes(r):
    """[(attempt, normalised complete text, 'PASS' | 'FAIL' | None)] for every
    tested candidate of one execution. The test status is the one the Judge
    step recorded; without it, the first plausible attempt passed and every
    attempt before it (or every attempt of an execution without a plausible
    candidate) failed."""
    h = _history(r)
    plaus = truthy(r.get("plausible")); pit = int(fnum(r.get("plausible_iteration"), -1))
    judges = {int(fnum(e.get("iteration"), -1)): e for e in h if e.get("action") == "judge"}
    out = []
    for e in h:
        if e.get("action") != "repair":
            continue
        it = int(fnum(e.get("iteration"), -1))
        st = ((judges.get(it) or {}).get("metadata") or {}).get("test_status_observed")
        if plaus and it == pit:
            res = "PASS"
        elif st in ("PASS", "FAIL"):
            res = st
        elif not plaus or it < pit:
            res = "FAIL"
        else:
            res = None
        out.append((it + 1, _norm_text(_step_text(e)), res))
    return out


def _history(r):
    try:
        h = json.loads(r.get("history") or "[]")
        return h if isinstance(h, list) else []
    except Exception:
        return []


def _step_temperature(md):
    """temperature actually used by a repair step (multi-file steps keep it per file)."""
    t = md.get("temperature_used")
    if t is None:
        files = md.get("files")
        try:
            import ast
            fl = ast.literal_eval(files) if isinstance(files, str) else files
            if fl and isinstance(fl[0], dict):
                t = fl[0].get("temperature_used")
        except Exception:
            t = None
    try:
        return float(t)
    except (TypeError, ValueError):
        return None


def _step_parts(md):
    """Per-generation records of a repair step: one dict per file for a
    multi-file bug, otherwise the step's own metadata."""
    files = md.get("files")
    if files:
        try:
            import ast
            fl = ast.literal_eval(files) if isinstance(files, str) else files
            if fl and isinstance(fl[0], dict):
                return fl
        except Exception:
            pass
    return [md]


def _repair_calls(r):
    """Repair Agent requests of one execution: one per file and per generation attempt."""
    n = 0
    for e in _history(r):
        if e.get("action") == "repair":
            n += sum(int(fnum(p.get("generation_attempts"), 1) or 1) for p in _step_parts(e.get("metadata") or {}))
    return n


def _step_tokens(md):
    """(prompt, output) tokens of a step; multi-file repair steps sum their files."""
    pt = md.get("prompt_tokens"); ct = md.get("candidate_tokens")
    if (pt is None or ct is None) and md.get("files"):
        try:
            import ast
            fl = ast.literal_eval(md["files"]) if isinstance(md["files"], str) else md["files"]
            pt = sum(int(f.get("prompt_tokens") or 0) for f in fl)
            ct = sum(int(f.get("candidate_tokens") or 0) for f in fl)
        except Exception:
            pass
    return int(fnum(pt)), int(fnum(ct))


def holm(pvals):
    """Holm step-down adjusted p-values, same order as input."""
    m = len(pvals); order = sorted(range(m), key=lambda i: pvals[i]); adj = [0.0] * m; run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * pvals[i]); adj[i] = min(1.0, run)
    return adj


def bootstrap_kappa(pairs, n=2000, seed=1):
    rnd = random.Random(seed); ks = []
    for _ in range(n):
        smp = [pairs[rnd.randrange(len(pairs))] for _ in range(len(pairs))]
        k = kappa(smp)
        if k == k: ks.append(k)
    ks.sort()
    return (ks[int(0.025 * len(ks))], ks[int(0.975 * len(ks)) - 1]) if ks else (float("nan"),) * 2


def same_patch(entry, other_session):
    """True if the canonical execution's patch is textually identical to the
    patch of the execution in other_session (whitespace-normalised)."""
    mine = _patch_text(entry["row"])
    for s, r in entry["completed_all"]:
        if s == other_session:
            return bool(mine) and mine == _patch_text(r)
    return False


def label_of(ver_row):
    v = (ver_row.get("Reviewer Semantic verdict") or "").strip() if ver_row else ""
    return v


def is_correct_label(v):
    return v.startswith("Correct")


# ─────────────────────────────────────────────────────────────────────────────
# statistics
# ─────────────────────────────────────────────────────────────────────────────

def mcnemar_exact(a, b):
    """a, b: sets of successes on the same items. Returns (a_only, b_only, n, p)."""
    x = len(a - b); y = len(b - a); n = x + y; k = min(x, y)
    if n == 0:
        return x, y, 0, 1.0
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return x, y, n, min(1.0, p)


def mcnemar_power(n, d, alpha=0.05):
    """Power of the exact two-sided McNemar test, conditional on n discordant pairs,
    when the expected difference between the two discordant counts is d."""
    def p_of(k):
        kk = min(k, n - k)
        return min(1.0, 2 * sum(math.comb(n, i) for i in range(kk + 1)) / 2 ** n)
    if n == 0:
        return 0.0
    px = (n + d) / (2 * n)
    return sum(math.comb(n, k) * px ** k * (1 - px) ** (n - k) for k in range(n + 1) if p_of(k) <= alpha)


def cochran_q(sets, items):
    k = len(sets)
    G = [sum(1 for i in items if i in s) for s in sets]
    L = [sum(1 for s in sets if i in s) for i in items]
    den = k * sum(L) - sum(l * l for l in L)
    if den == 0:
        return 0.0, 1.0
    Q = (k - 1) * (k * sum(g * g for g in G) - sum(G) ** 2) / den
    # chi-square survival with df = k-1; closed forms for df 3, else Wilson-Hilferty
    df = k - 1
    if df == 3:
        p = math.erfc(math.sqrt(Q / 2)) + math.sqrt(2 * Q / math.pi) * math.exp(-Q / 2)
    else:
        z = ((Q / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
        p = 0.5 * math.erfc(z / math.sqrt(2))
    return Q, p


def trend_permutation(sets_by_arm, items, n_perm=20000, seed=1, order=None):
    """Page-type test for an ordered alternative: later arms in `order` are
    expected to have more successes. Exact by permuting arm labels within
    each bug (block). `order` defaults to the arms sorted by RICHNESS."""
    arms = list(order) if order else sorted(sets_by_arm, key=lambda a: RICHNESS[a])
    score = {a: i for i, a in enumerate(arms)}
    rows = [[1 if i in sets_by_arm[a] else 0 for a in arms] for i in items]
    def T(rs):
        return sum(score[a] * v for r in rs for a, v in zip(arms, r))
    obs = T(rows)
    try:
        import numpy as np                     # fast path
        M = np.array(rows, dtype=np.int64); w = np.arange(len(arms))
        rng = np.random.default_rng(seed); ge = 0
        for _ in range(n_perm):
            idx = np.argsort(rng.random(M.shape), axis=1)
            if int((np.take_along_axis(M, idx, axis=1) * w).sum()) >= obs:
                ge += 1
        return obs, (ge + 1) / (n_perm + 1)
    except ImportError:
        pass
    rnd = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        perm = []
        for r in rows:
            r2 = r[:]; rnd.shuffle(r2); perm.append(r2)
        if T(perm) >= obs:
            ge += 1
    return obs, (ge + 1) / (n_perm + 1)


def kappa(pairs):
    n = len(pairs)
    if not n:
        return float("nan")
    labels = sorted({x for p in pairs for x in p})
    po = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs); cb = Counter(b for _, b in pairs)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--verification", action="append", default=[], metavar="ARM=FILE")
    ap.add_argument("--rule", choices=["first", "last"], default="first")
    ap.add_argument("--overrides", default=None)
    ap.add_argument("--judge-swap", action="append", default=[])
    ap.add_argument("--bug-list", default=None)
    ap.add_argument("--outdir", default="figures_out")
    ap.add_argument("--perms", type=int, default=20000)
    ap.add_argument("--export-canonical-patches", action="store_true",
                    help="write <outdir>/canonical_patches_<arm>.csv with every canonical plausible patch")
    ap.add_argument("--samples", action="append", default=[])
    ap.add_argument("--fixed-baseline", default=None)
    ap.add_argument("--false-negatives", default=None,
                    help="CSV arm,bug_id,note: candidates logged as failing that pass when re-executed (sensitivity only)")
    ap.add_argument("--concurrent", action="append", default=[], metavar="ARM=SESSION_A+SESSION_B",
                    help="two sessions of one configuration that ran at the same time in the same working directory")
    ap.add_argument("--rerun", action="append", default=[], metavar="ARM=SESSION[+SESSION]",
                    help="sessions executed after the configuration was verified; their records take the label "
                         "of a labelled patch with the same text, or of an override row that names the session")
    ap.add_argument("--discard-session", action="append", default=[], metavar="ARM=SESSION[+SESSION]",
                    help="sessions that were discarded in full before analysis (a disturbed run); their "
                         "records are ignored if the files are present")
    ap.add_argument("--reexecuted", action="append", default=[], metavar="ARM=SESSION[+SESSION]",
                    help="sessions that executed the whole configuration again with corrected code; only they "
                         "are canonical for that configuration. The earlier sessions stay in the data: their "
                         "labelled patches label identical texts of the new sessions, and they are compared "
                         "with them in section 4f")
    ap.add_argument("--without-bugs", action="append", default=[], metavar="FILE",
                    help="a list of bugs (one per line): section 14c repeats the paired comparisons without them")
    ap.add_argument("--second-verification", default=None, metavar="DIR",
                    help="directory with the second-verification files verification_<arm>.csv (tallies only)")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    explicit = dict(v.split("=", 1) for v in args.verification)
    overrides = defaultdict(dict)
    delivered_overrides = defaultdict(dict)
    overrides_s = defaultdict(dict)             # rows that name the session they label
    delivered_overrides_s = defaultdict(dict)
    if args.overrides:
        for r in csv.DictReader(open(args.overrides, encoding="utf-8")):
            which = (r.get("which") or "first").strip().lower()
            ses = (r.get("session") or "").strip()
            if ses:
                tgt = delivered_overrides_s if which == "delivered" else overrides_s
                tgt[r["arm"].strip()][(r["bug_id"].strip(), ses)] = r
            else:
                tgt = delivered_overrides if which == "delivered" else overrides
                tgt[r["arm"].strip()][r["bug_id"].strip()] = r
    conc = {}
    for spec in args.concurrent:
        a_, ss = spec.split("=", 1); conc[a_.strip()] = tuple(x.strip() for x in ss.split("+"))
    rerun = {}
    for spec in args.rerun:
        a_, ss = spec.split("=", 1); rerun[a_.strip()] = tuple(x.strip() for x in ss.split("+"))
    discard = {}
    for spec in args.discard_session:
        a_, ss = spec.split("=", 1); discard[a_.strip()] = tuple(x.strip() for x in ss.split("+"))
    reexec = {}
    for spec in args.reexecuted:
        a_, ss = spec.split("=", 1); reexec[a_.strip()] = tuple(x.strip() for x in ss.split("+"))
    for a_ in reexec:
        if a_ in rerun:
            sys.exit(f"--reexecuted and --rerun name the same configuration ({a_})")

    P = print
    P(f"# SV-ARP figures — regenerated from raw files\n")
    P(f"rule for repeated executions: **{args.rule} session**\n")

    # ── load everything ─────────────────────────────────────────────────────
    per = {}; sessions = {}; ver = {}; can = {}; per_review = {}; can_review = {}
    dropped = []
    for arm in ARMS:
        per[arm], sessions[arm] = load_arm(args.raw, arm)
        drop = set(discard.get(arm, ()))
        if drop:
            # a session discarded in full: its records take no part in anything below
            for sx in sorted(drop):
                n_ = sum(1 for lst in per[arm].values() for s2, _ in lst if s2 == sx)
                dropped.append(f"`{arm}` {sx} ({n_} records ignored)" if n_ else f"`{arm}` {sx} (file not present)")
            per[arm] = defaultdict(list, {b: l2 for b, l2 in ((b, [(s2, r) for s2, r in lst if s2 not in drop])
                                                              for b, lst in per[arm].items()) if l2})
            sessions[arm] = [s2 for s2 in sessions[arm] if s2 not in drop]
        vpath = find_verification(args.raw, arm, explicit)
        ver[arm] = load_verification(vpath)
        new_s = set(reexec.get(arm, ()))
        if new_s:
            # the configuration was executed again in full with corrected code: only the new
            # sessions are canonical; the earlier ones are what was verified
            absent = sorted(new_s - set(sessions[arm]))
            if absent:
                sys.exit(f"--reexecuted {arm}: session(s) not found: {', '.join(absent)}")
            per_review[arm] = defaultdict(list, {b: l2 for b, l2 in ((b, [(sx, r) for sx, r in lst if sx not in new_s])
                                                                   for b, lst in per[arm].items()) if l2})
            can_review[arm] = canonical(per_review[arm], args.rule, conc.get(arm, ()))
            per[arm] = defaultdict(list, {b: l2 for b, l2 in ((b, [(sx, r) for sx, r in lst if sx in new_s])
                                                            for b, lst in per[arm].items()) if l2})
            can[arm] = canonical(per[arm], args.rule, ())
            P(f"- `{arm}`: executed again in full in session(s) {', '.join(sorted(new_s))}; the earlier session(s) "
              f"{', '.join(s2 for s2 in sessions[arm] if s2 not in new_s)} are kept for labels and comparison only")
            sessions[arm] = [s2 for s2 in sessions[arm] if s2 in new_s]
            P(f"- `{arm}`: {len(sessions[arm])} session(s), {sum(len(v) for v in per[arm].values())} rows, "
              f"{len(per[arm])} bugs; verification of the earlier sessions: `{vpath or 'NONE'}` ({len(ver[arm])} rows)")
            continue
        can[arm] = canonical(per[arm], args.rule, conc.get(arm, ()))
        # the sessions that existed when the configuration was verified
        late = set(rerun.get(arm, ()))
        if late:
            per_review[arm] = defaultdict(list, {b: [(sx, r) for sx, r in lst if sx not in late]
                                                 for b, lst in per[arm].items()})
            can_review[arm] = canonical(per_review[arm], args.rule, conc.get(arm, ()))
        else:
            per_review[arm] = per[arm]; can_review[arm] = can[arm]
        P(f"- `{arm}`: {len(sessions[arm])} session(s), {sum(len(v) for v in per[arm].values())} rows, "
          f"{len(per[arm])} bugs; verification: `{vpath or 'NONE'}` ({len(ver[arm])} rows)")

    if args.bug_list:
        bugs = [l.strip() for l in open(args.bug_list) if l.strip()]
    else:
        bugs = sorted(set().union(*[set(p) for p in per.values()]),
                      key=lambda b: (b.rsplit("_", 1)[0], int(b.rsplit("_", 1)[1])))
    if dropped:
        P("\nsessions discarded in full (--discard-session): " + "; ".join(dropped))
    P(f"\nbenchmark: {len(bugs)} bugs\n")

    # ── per-arm canonical tables ───────────────────────────────────────────
    # rec[arm][bug] = dict(...) with plausible / correct / pending / excluded
    rec = {}
    pending = defaultdict(list)
    known = {}          # (bug, complete patch text) -> (label, where that text was labelled)
    REAL = ("Correct", "Overfitting", "Incorrect")

    def assign(arm, b, e, e_old):
        """Label of the canonical execution e. e_old is the canonical execution among the
        sessions that existed when the configuration was verified (e itself if nothing
        was executed afterwards). A row of the verification file or an override without
        a session was written for one text and applies to that text only."""
        r = e["row"]; vr = ver[arm].get(b)
        has_old = bool(e_old and not e_old["excluded"])
        vs = verified_session(b, e_old, vr) if has_old else None
        plaus = truthy(r.get("plausible"))
        changed = (not has_old) or e["session"] != e_old["session"]
        same_first = not changed
        if changed and has_old and plaus and truthy(e_old["row"].get("plausible")):
            same_first = _patch_text(r) == _patch_text(e_old["row"])
        label = ""; label_src = ""
        ov_s = overrides_s.get(arm, {}).get((b, e["session"]))
        ov = overrides.get(arm, {}).get(b) if same_first else None
        if ov_s:
            label = ov_s["semantic_verdict"].strip(); label_src = "labelled after the re-execution"
        elif ov:
            label = ov["semantic_verdict"].strip()
            label_src = "override" if not changed else "override (identical patch)"
        elif vr is not None and vs == e["session"]:
            label = label_of(vr); label_src = "verification"
        elif vr is not None and vs is not None and same_patch(e, vs):
            # a different execution was reviewed, but it produced the
            # byte-identical patch, so the label applies to this one too
            label = label_of(vr); label_src = "verification (identical patch)"
        elif not plaus and (vr is not None or changed):
            label = "N/A (not plausible)"; label_src = "n/a"
        return dict(label=label, label_src=label_src, vs=vs, plaus=plaus, changed=changed, vr=vr)

    for arm in ARMS:
        rec[arm] = {}
        for b in bugs:
            e = can[arm].get(b)
            if e is None:
                rec[arm][b] = dict(excluded="not run"); continue
            if e["excluded"]:
                rec[arm][b] = dict(excluded=e["excluded"]); continue
            r = e["row"]
            e_old = can_review[arm].get(b)
            a = assign(arm, b, e, e_old)
            vr = a["vr"]; vs = a["vs"]; plaus = a["plaus"]; changed = a["changed"]
            label = a["label"]; label_src = a["label_src"]
            judge = (r.get("verdict") or "").strip().lower()
            accepted = plaus and judge == "correct"
            if changed and e_old and not e_old["excluded"] and truthy(e_old["row"].get("plausible")):
                # the labelled text of the record that was canonical when the labels were given
                a0 = assign(arm, b, e_old, e_old)
                if a0["label"].startswith(REAL):
                    known[(b, _patch_text(e_old["row"]))] = (a0["label"], "%s, session %s" % (arm, e_old["session"]))
            if plaus and not label.startswith(REAL):
                pending[arm].append(b)
                label = "PENDING"; label_src = "none"
            # the patch the loop finally accepted ("delivered") may differ from
            # the first plausible candidate when the Judge withheld acceptance
            first_txt = _norm_text(_candidate_text(r, "first")) if plaus else ""
            final_txt = _norm_text(_candidate_text(r, "final"))
            delivered_label = ""
            if accepted:
                dov = delivered_overrides_s.get(arm, {}).get((b, e["session"]))
                if not dov and (not changed or (e_old and not e_old["excluded"] and
                                                final_txt == _norm_text(_candidate_text(e_old["row"], "final")))):
                    dov = delivered_overrides.get(arm, {}).get(b)
                if dov:
                    delivered_label = dov["semantic_verdict"].strip()
                elif not final_txt or final_txt == first_txt:
                    delivered_label = label
                else:
                    delivered_label = "PENDING-delivered"
            rec[arm][b] = dict(
                excluded=None, session=e["session"], n_exec=len(e["completed"]),
                verified_session=vs, plausible=plaus, judge=judge, accepted=accepted,
                label=label, label_src=label_src, changed=changed,
                correct=plaus and is_correct_label(label),
                overfit=plaus and label == "Overfitting",
                delivered_differs=bool(accepted and final_txt and final_txt != first_txt),
                delivered_label=delivered_label,
                delivered_correct=accepted and is_correct_label(delivered_label),
                first_txt=first_txt, final_txt=final_txt, row=r,
                reviewed_same_text=bool(vr is not None and (vs == e["session"] or (vs is not None and same_patch(e, vs)))),
                iterations=int(fnum(r.get("iterations"))),
                plausible_iteration=int(fnum(r.get("plausible_iteration"), -1)),
                tokens=int(fnum(r.get("total_tokens"))), usd=fnum(r.get("estimated_usd")),
                secs=fnum(r.get("time_seconds")), baseline_failing=int(fnum(r.get("baseline_failing_count"))),
                project=b.rsplit("_", 1)[0],
            )

    # Records executed after the verification take the label of a labelled patch with the
    # same complete text: a canonical patch of any configuration, a patch of a control
    # pass, or the record that was canonical when the labels were given.
    known_conflicts = []
    superseded = []     # labels of the verification file replaced by a session-bound override

    def learn(b, txt, lab, where):
        if not txt or not lab.startswith(REAL):
            return
        if (b, txt) in known:
            if is_correct_label(known[(b, txt)][0]) != is_correct_label(lab):
                known_conflicts.append("%s (%s: %s; %s: %s)" % (b, known[(b, txt)][1], known[(b, txt)][0], where, lab))
            elif known[(b, txt)][0] == "Correct" and lab.startswith("Correct ("):
                # the same verdict, with its kind; the first source stays named
                known[(b, txt)] = (lab, "%s; kind from %s" % (known[(b, txt)][1], where))
            return
        known[(b, txt)] = (lab, where)

    for arm in ARMS:
        for b in bugs:
            x = rec[arm][b]
            if not x["excluded"] and x["plausible"]:
                learn(b, x["first_txt"], x["label"], "%s, session %s" % (arm, x["session"]))
                if x["delivered_differs"]:
                    learn(b, x["final_txt"], x["delivered_label"], "%s, session %s, accepted patch" % (arm, x["session"]))
    for d in (args.samples or sorted(glob.glob(os.path.join(args.raw, "results_arm_sample_*")))):
        name = os.path.basename(d.rstrip("/")).replace("results_arm_", "")
        per_s = defaultdict(list)
        for f in sorted(glob.glob(os.path.join(d, "results_*.csv")), key=session_key):
            for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
                bb = (r.get("bug_id") or "").strip()
                if bb: per_s[bb].append((session_key(f), r))
        cs = canonical(per_s, "first")
        ver_s = load_verification(find_verification(args.raw, name, explicit))
        for b in bugs:
            e = cs.get(b)
            if not e or e["excluded"] or not truthy(e["row"].get("plausible")):
                continue
            ov = overrides.get(name, {}).get(b); vr = ver_s.get(b)
            vlab = label_of(vr) if vr and (vr.get("Logged plausible by the suite") or "").strip().lower() == "yes" else ""
            learn(b, _patch_text(e["row"]), ov["semantic_verdict"].strip() if ov else vlab, "control pass %s" % name)
    for arm in ARMS:
        for b in bugs:
            eo = can_review[arm].get(b); vr = ver[arm].get(b)
            if not eo or eo["excluded"] or vr is None:
                continue
            vs = verified_session(b, eo, vr)
            if vs and vs != eo["session"] and not same_patch(eo, vs):
                rr = next((row for s_, row in eo["completed_all"] if s_ == vs), None)
                if rr is not None and truthy(rr.get("plausible")):
                    # an override row that names the reviewed session replaces the label
                    # the verification file gives to that execution's text
                    ovr = overrides_s.get(arm, {}).get((b, vs))
                    if ovr:
                        superseded.append("%s %s, session %s: %s in the verification file, %s by override"
                                          % (arm, b, vs, label_of(vr), ovr["semantic_verdict"].strip()))
                        learn(b, _patch_text(rr), ovr["semantic_verdict"].strip(),
                              "%s, session %s, override of the verification file" % (arm, vs))
                    else:
                        learn(b, _patch_text(rr), label_of(vr), "%s, session %s, as read by the verification file" % (arm, vs))
    relabelled = []
    for arm in ARMS:
        for b in bugs:
            x = rec[arm][b]
            if x["excluded"] or not x["changed"]:
                continue
            if x["plausible"] and x["label"] == "PENDING" and (b, x["first_txt"]) in known:
                lab, where = known[(b, x["first_txt"])]
                x["label"] = lab; x["label_src"] = "identical labelled patch (%s)" % where
                x["correct"] = is_correct_label(lab); x["overfit"] = lab == "Overfitting"
                pending[arm].remove(b)
                if x["accepted"] and not x["delivered_differs"]:
                    x["delivered_label"] = lab; x["delivered_correct"] = is_correct_label(lab)
            if x["delivered_label"] == "PENDING-delivered" and (b, x["final_txt"]) in known:
                x["delivered_label"] = known[(b, x["final_txt"])][0]
                x["delivered_correct"] = is_correct_label(x["delivered_label"])
            relabelled.append((arm, b))

    for arm in ARMS:
        # write the canonical table
        with open(os.path.join(args.outdir, f"canonical_{arm}.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["bug_id", "excluded", "session", "executions", "verified_session", "plausible",
                        "judge_verdict", "accepted", "semantic_label", "label_source", "correct",
                        "delivered_label", "delivered_correct",
                        "iterations", "plausible_iteration", "total_tokens", "estimated_usd", "time_seconds",
                        "baseline_failing"])
            for b in bugs:
                x = rec[arm][b]
                if x["excluded"]:
                    w.writerow([b, x["excluded"]] + [""] * 17); continue
                w.writerow([b, "", x["session"], x["n_exec"], x["verified_session"], x["plausible"], x["judge"],
                            x["accepted"], x["label"], x["label_src"], x["correct"],
                            x["delivered_label"], x["delivered_correct"], x["iterations"],
                            x["plausible_iteration"], x["tokens"], x["usd"], x["secs"], x["baseline_failing"]])

    if args.export_canonical_patches:
        for arm in ARMS:
            path = os.path.join(args.outdir, f"canonical_patches_{arm}.csv")
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["bug_id", "session", "plausible", "verdict", "test_status", "failing_tests",
                            "modified_classes", "plausible_iteration", "patch"])
                for b in bugs:
                    e = can[arm].get(b)
                    if not e or e["excluded"] or not truthy(e["row"].get("plausible")):
                        continue
                    r = e["row"]
                    w.writerow([b, e["session"], r.get("plausible"), r.get("verdict"), "PASS",
                                r.get("failing_tests", ""), r.get("modified_classes", ""),
                                r.get("plausible_iteration", ""),
                                _display_text(_candidate_text(r, "first"))])
        P(f"canonical plausible patches exported to `{args.outdir}/canonical_patches_<arm>.csv`\n")

    # ── 1. exclusions ───────────────────────────────────────────────────────
    P("## 1. Evaluable bugs and exclusions\n")
    excl = {arm: {b: rec[arm][b]["excluded"] for b in bugs if rec[arm][b]["excluded"]} for arm in ARMS}
    same = all(set(excl[a]) == set(excl[ARMS[0]]) for a in ARMS)
    P(f"- excluded per arm: " + ", ".join(f"{a}={len(excl[a])}" for a in ARMS)
      + ("  (identical set in every arm)" if same else "  **(sets differ between arms!)**"))
    evaluable = [b for b in bugs if all(not rec[a][b]["excluded"] for a in ARMS)]
    P(f"- evaluable in all four arms (the paired set): **{len(evaluable)}**")
    for arm in ARMS:
        if excl[arm]:
            byreason = defaultdict(list)
            for b, why in excl[arm].items():
                byreason[why].append(b)
            for why, bs in byreason.items():
                P(f"  - `{arm}` {why}: {', '.join(bs)}")
    P()

    # ── 2. repeated executions ─────────────────────────────────────────────
    P("## 2. Bugs executed more than once (appendix table)\n")
    for arm in ARMS:
        multi = [(b, can[arm][b]) for b in bugs if len(can[arm].get(b, {}).get("completed", [])) > 1]
        if not multi:
            P(f"- `{arm}`: none"); continue
        flips = [b for b, e in multi if len({truthy(r.get("plausible")) for _, r in e["completed"]}) > 1]
        P(f"- `{arm}`: {len(multi)} bug(s) with >1 valid execution; plausibility differs in {len(flips)}")
        P(f"\n  | bug | " + " | ".join(f"exec {i+1}" for i in range(max(len(e['completed']) for _, e in multi)))
          + " | canonical | reviewed | label applies |")
        P("  |---|" + "---|" * (max(len(e['completed']) for _, e in multi) + 3))
        for b, e in multi:
            cells = []
            for s, r in e["completed"]:
                cells.append(f"{s[-6:]}: {'P' if truthy(r.get('plausible')) else 'np'}/it{r.get('plausible_iteration')}/{r.get('iterations')}")
            x = rec[arm][b]
            P(f"  | {b} | " + " | ".join(cells) + f" | {x['session'][-6:]} | "
              f"{(x['verified_session'] or '?')[-6:]} | {x['label_src']} |")
        P()
    P("Records that are never canonical:\n")
    for arm in ARMS:
        why = defaultdict(list)
        for b in bugs:
            for sx, r in per[arm].get(b, []):
                st = (r.get("status") or "").strip()
                if st == "completed" and (r.get("verdict") or "").strip().lower() == "error":
                    why["completed but ended on an unparseable Judge verdict (re-queued)"].append(b)
                elif st == "completed" and (r.get("baseline_failing_count") or "").strip() == "0":
                    why["completed with an empty baseline"].append(b)
                elif st != "completed" and not rec[arm][b]["excluded"]:
                    why[f"aborted ({st}: {(r.get('error') or '')[:40]})"].append(b)
        for k, v in why.items():
            P(f"- `{arm}`: {k}: {len(v)} ({', '.join(v[:25])}{' ...' if len(v) > 25 else ''})")
    P()
    for arm in ARMS:
        if pending[arm]:
            P(f"**PENDING verification under rule `{args.rule}` in `{arm}`: "
              f"{', '.join(pending[arm])}** — plausible, but the canonical patch was never reviewed. "
              f"Not counted as correct until a label is supplied via --overrides.\n")

    # ── 2b. executions made after the verification ─────────────────────────
    if rerun or reexec:
        P("## 2b. Executions made after the verification\n")
        P("Sessions set aside (they shared a working directory): " + (", ".join("`%s` %s" % (a_, " and ".join(ss)) for a_, ss in conc.items()) or "none")
          + ". A set-aside execution is canonical only for a bug without a valid execution in another session.\n")
        todo_rows = []
        for arm in ARMS:
            if arm not in rerun and arm not in reexec:
                continue
            ch = [b for b in bugs if not rec[arm][b]["excluded"] and rec[arm][b]["changed"]]
            if arm in rerun:
                P(f"- `{arm}`: session(s) {', '.join(rerun[arm])} executed after the verification; canonical record changed for {len(ch)} bugs\n")
            else:
                P(f"- `{arm}`: executed again in full with corrected code (session(s) {', '.join(reexec[arm])}); "
                  f"{len(ch)} completed records, listed below when either execution is plausible\n")
            P("  | bug | record when the labels were given | re-execution | label | source of the label |")
            P("  |---|---|---|---|---|")
            trans = Counter()
            for b in ch:
                x = rec[arm][b]; eo = can_review[arm].get(b)
                if eo and not eo["excluded"]:
                    ro = eo["row"]; a0 = assign(arm, b, eo, eo)
                    o_pl = truthy(ro.get("plausible"))
                    o_txt = ("plausible at attempt %d, %s" % (int(fnum(ro.get("plausible_iteration"))) + 1, a0["label"] or "unlabelled")) if o_pl else "not plausible"
                    o_k = ("correct" if is_correct_label(a0["label"]) else "not correct") if o_pl else "not plausible"
                else:
                    o_txt = "none"; o_k = "none"
                n_k = (("correct" if x["correct"] else ("pending" if x["label"] == "PENDING" else "not correct")) if x["plausible"] else "not plausible")
                trans[(o_k, n_k)] += 1
                if x["plausible"] or o_k not in ("not plausible", "none"):
                    P(f"  | {b} | {o_txt} | {('plausible at attempt %d' % (x['plausible_iteration'] + 1)) if x['plausible'] else 'not plausible'} | "
                      f"{x['label']} | {x['label_src']} |")
                if x["plausible"] and (x["label"] == "PENDING" or x["label"] == "Correct"):
                    todo_rows.append((arm, b, x["session"], x["plausible_iteration"] + 1,
                                      "label" if x["label"] == "PENDING" else "kind of correct patch",
                                      _display_text(_candidate_text(x["row"], "first"))))
                if x["delivered_label"] == "PENDING-delivered":
                    todo_rows.append((arm, b, x["session"], x["iterations"], "label of the accepted patch",
                                      _display_text(_candidate_text(x["row"], "final"))))
            P()
            P("  " + "; ".join("%s -> %s: %d" % (k[0], k[1], v) for k, v in sorted(trans.items())) + "\n")
        if known_conflicts:
            P("**labelled texts with conflicting labels:** " + "; ".join(known_conflicts) + "\n")
        else:
            P("labelled texts with conflicting labels: none\n")
        if superseded:
            P("labels of a verification file replaced by an override row that names the reviewed session "
              "(the execution is not canonical; the row keeps one label per patch text): " + "; ".join(superseded) + "\n")
        with open(os.path.join(args.outdir, "rerun_labels_todo.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["arm", "bug_id", "session", "attempt", "needed", "patch"]); w.writerows(todo_rows)
        P(f"re-executed records that still need a label or the kind of a correct patch: {len(todo_rows)} "
          f"({', '.join('%s %s' % (t[1], '[' + t[4] + ']') for t in todo_rows) or 'none'}); see `{args.outdir}/rerun_labels_todo.csv`\n")

    # ── 2c. attempts that received no model output ─────────────────────────
    P("## 2c. Repair attempts that received no model output\n")
    P("An attempt received no model output when every generation came back without output tokens "
      "(requests refused by the model API or not reaching it), so the unchanged file was tested and the "
      "attempt spent. These executions are kept as recorded.\n")
    P("| configuration | bug | session | attempts without output, before / after the first plausible candidate | canonical |")
    P("|---|---|---|---|---|")
    n_lost_rows = 0
    affected = set()          # bugs whose canonical execution in some configuration has such an attempt

    def _lost_rows(name, per_, can_):
        rows_ = []
        for b in sorted(per_, key=order_key):
            for sx, r in per_[b]:
                if not valid_completed(r):
                    continue
                bef, aft = lost_attempts(r)
                if bef or aft:
                    e = can_.get(b)
                    rows_.append(f"| {name} | {b} | {sx} | {bef or '-'} / {aft or '-'} | "
                                 f"{'yes' if e and e.get('session') == sx else 'no'} |")
                    if name in ARMS and e and e.get("session") == sx:
                        affected.add(b)
        return rows_

    for arm in ARMS:
        for row_ in _lost_rows(arm, per[arm], can[arm]):
            P(row_); n_lost_rows += 1
    for d in sorted(glob.glob(os.path.join(args.raw, "results_arm_sample_*"))):
        name = os.path.basename(d.rstrip("/")).replace("results_arm_", "")
        per_s = defaultdict(list)
        for f in sorted(glob.glob(os.path.join(d, "results_*.csv")), key=session_key):
            for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
                bb = (r.get("bug_id") or "").strip()
                if bb:
                    per_s[bb].append((session_key(f), r))
        for row_ in _lost_rows(name, per_s, canonical(per_s, "first")):
            P(row_); n_lost_rows += 1
    P(f"\nexecutions with an attempt that received no model output: {n_lost_rows}\n")
    if affected:
        kept = [b for b in evaluable if b not in affected]
        P(f"Sensitivity: the paired comparisons on the {len(kept)} evaluable bugs without the bugs whose canonical "
          f"execution in some configuration has such an attempt ({', '.join(sorted(affected, key=order_key))}):\n")
        def _set(arm, key):
            return {b for b in kept if rec[arm][b][key]}
        for arm in ARMS[1:]:
            fo, ao, _, pc = mcnemar_exact(_set("full", "correct"), _set(arm, "correct"))
            fp, ap, _, pp = mcnemar_exact(_set("full", "plausible"), _set(arm, "plausible"))
            P(f"- full vs {arm}: correct {fo} vs {ao} (p = {pc:.4f}); plausible {fp} vs {ap} (p = {pp:.4f})")
        P()

    # ── 3. headline ────────────────────────────────────────────────────────
    P("## 3. Headline, paired set\n")
    P("plausible = a test-passing candidate was found; accepted = the loop ended with an accepted patch; "
      "correct = the first plausible candidate is labelled correct; delivered correct = the accepted patch is labelled correct.\n")
    P("| arm | plausible | accepted | correct | delivered correct | pending | precision (correct/plausible) | overfitting |")
    P("|---|---|---|---|---|---|---|---|")
    S_pl = {}; S_co = {}; S_acc = {}; S_dc = {}
    for arm in ARMS:
        S_pl[arm] = {b for b in evaluable if rec[arm][b]["plausible"]}
        S_acc[arm] = {b for b in evaluable if rec[arm][b]["accepted"]}
        S_co[arm] = {b for b in evaluable if rec[arm][b]["correct"]}
        S_dc[arm] = {b for b in evaluable if rec[arm][b]["delivered_correct"]}
        pend = sum(1 for b in evaluable if rec[arm][b]["label"] == "PENDING")
        pend_d = sum(1 for b in evaluable if rec[arm][b]["delivered_label"] == "PENDING-delivered")
        ov = sum(1 for b in evaluable if rec[arm][b]["overfit"])
        pl = len(S_pl[arm]); co = len(S_co[arm])
        P(f"| {arm} | {pl} | {len(S_acc[arm])} | {co} | {len(S_dc[arm])}{' (+%d pending)' % pend_d if pend_d else ''} | {pend} | {100*co/pl:.1f}% | {ov} |")
    P()
    for arm in ARMS:
        diff = [b for b in evaluable if rec[arm][b]["delivered_differs"]]
        held = [b for b in evaluable if rec[arm][b]["plausible"] and not rec[arm][b]["accepted"]]
        if diff or held:
            P(f"- `{arm}`: Judge withheld the first plausible candidate and the loop delivered a different patch: "
              f"{', '.join(diff) or 'none'}; plausible candidate found but no patch accepted: {', '.join(held) or 'none'}")
    labs = Counter(rec["full"][b]["label"] for b in S_pl["full"])
    P(f"\nfull arm label split: {dict(sorted(labs.items()))}\n")

    # ── 3b. identical patch texts across configurations ────────────────────
    P("## 3b. Identical patch texts across configurations (same Java token sequence; complete multi-file patches)\n")
    groups = defaultdict(list)
    for arm in ARMS:
        for b in evaluable:
            x = rec[arm][b]
            if x["plausible"]:
                groups[(b, x["first_txt"])].append((arm, x["label"]))
    recurring = {k: v for k, v in groups.items() if len(v) >= 2}
    conflicts = sorted({k[0] for k, v in recurring.items() if len({is_correct_label(l) for _, l in v}) > 1})
    P(f"- plausible records: {sum(len(v) for v in groups.values())}; distinct patch texts: {len(groups)}; "
      f"texts recurring in two or more configurations: {len(recurring)} ({sum(len(v) for v in recurring.values())} records); "
      f"texts produced by all four: {sum(1 for v in recurring.values() if len(v) == 4)}")
    P(f"- recurring texts whose final labels differ between configurations: {', '.join(conflicts) or 'none'}\n")

    # ── 4. tests ───────────────────────────────────────────────────────────
    P("## 4. Statistical comparison (paired on bug identity)\n")
    P("McNemar exact test against `full`; p two-sided, p1 one-sided (full > arm), Holm over the three correct-fix comparisons:\n")
    P("| arm | correct: full-only | arm-only | discordant | p | p1 | Holm p | plausible: full-only | arm-only | discordant | p | delivered correct: full-only | arm-only | p |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    rows4 = []
    for arm in ARMS[1:]:
        x, y, n, p = mcnemar_exact(S_co["full"], S_co[arm])
        x2, y2, n2, p2 = mcnemar_exact(S_pl["full"], S_pl[arm])
        x3, y3, n3, p3 = mcnemar_exact(S_dc["full"], S_dc[arm])
        rows4.append((arm, x, y, n, p, x2, y2, n2, p2, x3, y3, p3))
    hp = holm([r[4] for r in rows4])
    for (arm, x, y, n, p, x2, y2, n2, p2, x3, y3, p3), h in zip(rows4, hp):
        P(f"| {arm} | {x} | {y} | {n} | {p:.4f} | {p/2:.4f} | {h:.4f} | {x2} | {y2} | {n2} | {p2:.4f} | {x3} | {y3} | {p3:.4f} |")
    P("\nPairwise among ablations (correct):\n")
    for a, b in (("no_semantic", "binary_only"), ("binary_only", "no_judge"), ("no_semantic", "no_judge")):
        x, y, n, p = mcnemar_exact(S_co[a], S_co[b])
        P(f"- {a} vs {b}: {a}-only={x}, {b}-only={y}, p={p:.4f}")
    Q, pq = cochran_q([S_co[a] for a in ARMS], evaluable)
    P(f"\nCochran's Q across the four arms (correct): Q={Q:.2f}, df=3, p={pq:.4f}")
    P("(no ordered-trend test: with three nested arms the Page statistic reduces to the one-sided "
      "full-vs-no_judge comparison, and the four-arm orderings are not implied by prompt-content inclusion)")
    n_nj = mcnemar_exact(S_co["full"], S_co["no_judge"])[2]
    d_obs = abs(len(S_co["full"]) - len(S_co["no_judge"]))
    P(f"\nPower of the exact McNemar test (two-sided, alpha 0.05), conditional on the {n_nj} discordant pairs of "
      f"full vs no_judge: {mcnemar_power(n_nj, 20):.2f} for a true difference of 20 correct fixes, "
      f"{mcnemar_power(n_nj, d_obs):.2f} for a difference of {d_obs}, the one observed")
    L = Counter(sum(1 for a in ARMS if b in S_co[a]) for b in evaluable)
    P(f"\nBugs fixed by k of 4 arms: " + ", ".join(f"k={k}: {L[k]}" for k in range(5))
      + f" → outcome depends on the arm for {sum(L[k] for k in (1,2,3))} bugs\n")

    # ── 4b. iteration-1 replication ────────────────────────────────────────
    P("## 4b. First attempts are four replications of the same procedure\n")
    P("The first-attempt prompt is identical in every arm (feedback exists only after a failure), "
      "so iteration-1 outcomes replicate one stochastic procedure four times.\n")
    P("| arm | iter-1 plausible | iter-1 correct | gained at iterations 2-4: plausible | correct | bugs without a first-attempt plausible | later plausible among them |")
    P("|---|---|---|---|---|---|---|")
    I_pl = {}; I_co = {}
    for arm in ARMS:
        I_pl[arm] = {b for b in S_pl[arm] if rec[arm][b]["plausible_iteration"] == 0}
        I_co[arm] = {b for b in I_pl[arm] if rec[arm][b]["correct"]}
        rest = [b for b in evaluable if b not in I_pl[arm]]
        later = [b for b in rest if b in S_pl[arm]]
        P(f"| {arm} | {len(I_pl[arm])} | {len(I_co[arm])} | {len(S_pl[arm]) - len(I_pl[arm])} | "
          f"{len(S_co[arm]) - len(I_co[arm])} | {len(rest)} | {len(later)} ({100*len(later)/len(rest):.1f}%) |")
    P("\nPairwise discordance at iteration 1 (bugs correct in exactly one of the two arms):\n")
    import itertools as _it
    for a, b in _it.combinations(ARMS, 2):
        x, y, n, p = mcnemar_exact(I_co[a], I_co[b]); x2, y2, n2, p2 = mcnemar_exact(I_pl[a], I_pl[b])
        P(f"- {a} vs {b}: correct {x}/{y} ({100*n/len(evaluable):.1f}% of bugs), plausible {x2}/{y2} ({100*n2/len(evaluable):.1f}%)")
    U_pl = set().union(*I_pl.values()); U_co = set().union(*I_co.values())
    proxy_pl = set(); proxy_co = set()
    for b in evaluable:
        for arm in ARMS:            # first plausible first attempt wins, in arm order
            if b in I_pl[arm]:
                proxy_pl.add(b)
                if b in I_co[arm]: proxy_co.add(b)
                break
    P(f"\nFour first attempts combined (proxy for best-of-4 resampling at the first-attempt temperature): "
      f"union plausible={len(U_pl)}, union correct={len(U_co)}; first-plausible-wins plausible={len(proxy_pl)}, correct={len(proxy_co)}\n")
    P("| arm (full loop) | vs first-plausible-wins proxy: plausible full-only/proxy-only, p | correct, p | vs union correct, p |")
    P("|---|---|---|---|")
    for arm in ARMS:
        x, y, n, p = mcnemar_exact(S_pl[arm], proxy_pl); x2, y2, n2, p2 = mcnemar_exact(S_co[arm], proxy_co)
        x3, y3, n3, p3 = mcnemar_exact(S_co[arm], U_co)
        P(f"| {arm} | {x}/{y}, p={p:.4f} | {x2}/{y2}, p={p2:.4f} | {x3}/{y3}, p={p3:.4f} |")
    P()
    P("Attempts 2 to 4, on the bugs whose first attempt is plausible in neither of the two configurations compared "
      "(both loops start their feedback from a failed first attempt):\n")
    P("| pair | bugs | plausible later: first / second | only first / only second, p | correct later: first / second | only first / only second, p |")
    P("|---|---|---|---|---|---|")
    for a, b in _it.combinations(ARMS, 2):
        sub = {x_ for x_ in evaluable if x_ not in I_pl[a] and x_ not in I_pl[b]}
        la, lb = S_pl[a] & sub, S_pl[b] & sub
        ca, cb = S_co[a] & sub, S_co[b] & sub
        x, y, n, p = mcnemar_exact(la, lb); x2, y2, n2, p2 = mcnemar_exact(ca, cb)
        P(f"| {a} vs {b} | {len(sub)} | {len(la)} / {len(lb)} | {x}/{y}, p={p:.4f} | {len(ca)} / {len(cb)} | {x2}/{y2}, p={p2:.4f} |")
    P()

    # ── 4c. resampling control from single-attempt runs ───────────────────
    sample_dirs = args.samples or sorted(glob.glob(os.path.join(args.raw, "results_arm_sample_*")))
    if sample_dirs:
        P("## 4c. Equal-budget control: independent single attempts (best-of-k resampling)\n")
        text_label = {}
        text_label_indep = {}       # without the labels that were themselves taken from a control patch
        for arm in ARMS:
            for b in evaluable:
                x = rec[arm][b]
                if x["plausible"] and x["label"] not in ("PENDING", ""):
                    text_label[(b, x["first_txt"])] = x["label"]
                    if not x["label_src"].startswith("identical labelled patch (control pass"):
                        text_label_indep[(b, x["first_txt"])] = x["label"]
        # texts whose only arm label was itself taken from a control patch
        from_control = sorted({k[0] for k in text_label if k not in text_label_indep},
                              key=lambda b: (b.rsplit("_", 1)[0], int(b.rsplit("_", 1)[1])))
        samples = []; per_samples = {}
        for d in sample_dirs:
            name = os.path.basename(d.rstrip("/")).replace("results_arm_", "")
            m = re.search(r"sample_t(\d{3})", name)
            temp = int(m.group(1)) / 100 if m else 9.9
            per_s = defaultdict(list)
            for f in sorted(glob.glob(os.path.join(d, "results_*.csv")), key=session_key):
                for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
                    bb = (r.get("bug_id") or "").strip()
                    if bb: per_s[bb].append((session_key(f), r))
            cs = canonical(per_s, "first")
            per_samples[name] = per_s
            vpath_s = find_verification(args.raw, name, explicit)
            ver_s = load_verification(vpath_s)
            info = {}
            agree = disagree = 0; disagreements = []
            for b in evaluable:
                e = cs.get(b)
                if not e or e["excluded"]:
                    info[b] = dict(plausible=False, label="", txt="", excluded=True); continue
                r = e["row"]; pl = truthy(r.get("plausible")); txt = _patch_text(r)
                lab = ""; src = ""
                if pl:
                    ov = overrides.get(name, {}).get(b)
                    vr = ver_s.get(b)
                    vlab = label_of(vr) if vr and (vr.get("Logged plausible by the suite") or "").strip().lower() == "yes" else ""
                    tlab = text_label.get((b, txt), "")
                    if ov:
                        lab, src = ov["semantic_verdict"].strip(), "override"
                    elif vlab.startswith(("Correct", "Overfitting", "Incorrect")):
                        lab, src = vlab, "verification"
                    elif tlab:
                        lab, src = tlab, "identical patch in an arm"
                    else:
                        lab, src = "PENDING", "none"
                    # consistency: the sample's own label vs the label of a textually identical arm patch
                    # (only arm labels that were given independently of the control)
                    ilab = text_label_indep.get((b, txt), "")
                    if vlab and ilab:
                        if is_correct_label(vlab) == is_correct_label(ilab): agree += 1
                        else: disagree += 1; disagreements.append(f"{b} ({vlab} vs arm {ilab})")
                info[b] = dict(plausible=pl, label=lab, txt=txt, excluded=False, row=r, src=src)
            samples.append((temp, name, info))
            if vpath_s:
                rev = sum(1 for b in evaluable if info[b]["plausible"] and ((ver_s.get(b) or {}).get("Re-verification") or "").strip())
                P(f"- `{name}`: verification file `{vpath_s}`; textually identical to an independently labelled arm patch for {agree + disagree} bugs, "
                  f"label agreement {agree}/{agree + disagree}" + (f"; disagreements: {', '.join(disagreements)}" if disagreements else "")
                  + f"; plausible patches with a recorded execution-based re-verification: {rev}")
        if from_control:
            P(f"  (arm patches whose only label was taken from an identical control patch, left out of this check: {', '.join(from_control)})")
        P()
        samples.sort(key=lambda t: (t[0], t[1]))
        P("| sample | temperature | evaluable bugs run | plausible | correct | pending labels | label sources |")
        P("|---|---|---|---|---|---|---|")
        pending_rows = []
        for temp, name, info in samples:
            run = sum(1 for b in evaluable if not info[b]["excluded"])
            pl = sum(1 for b in evaluable if info[b]["plausible"])
            co = sum(1 for b in evaluable if info[b]["plausible"] and is_correct_label(info[b]["label"]))
            pe = [b for b in evaluable if info[b]["plausible"] and info[b]["label"] == "PENDING"]
            srcs = Counter(info[b].get("src", "") for b in evaluable if info[b]["plausible"])
            for b in pe:
                pending_rows.append((name, b, _display_text(_candidate_text(info[b]["row"], "first"))))
            P(f"| {name} | {temp} | {run} | {pl} | {co} | {len(pe)} | {dict(srcs)} |")
        if pending_rows:
            with open(os.path.join(args.outdir, "pending_sample_labels.csv"), "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh); w.writerow(["sample", "bug_id", "patch"]); w.writerows(pending_rows)
            P(f"\n{len(pending_rows)} sample patches have no label yet (no textually identical labelled patch in the four arms): "
              f"see `{args.outdir}/pending_sample_labels.csv`; add rows with arm=<sample name> to --overrides.")
        P("\nBest-of-k in temperature order (first plausible sample wins):\n")
        P("| k | samples | plausible | correct | pending | vs full: plausible full-only/ctrl-only, p | correct, p | vs no_judge: plausible, p | correct, p |")
        P("|---|---|---|---|---|---|---|---|---|")
        ctrl_sets = {}
        for k in range(1, len(samples) + 1):
            c_pl = set(); c_co = set(); c_pe = set()
            for b in evaluable:
                for temp, name, info in samples[:k]:
                    if info[b]["plausible"]:
                        c_pl.add(b)
                        if is_correct_label(info[b]["label"]): c_co.add(b)
                        elif info[b]["label"] == "PENDING": c_pe.add(b)
                        break
            ctrl_sets[k] = (c_pl, c_co)
            x, y, n, pp = mcnemar_exact(S_pl["full"], c_pl); x2, y2, n2, pc = mcnemar_exact(S_co["full"], c_co)
            x3, y3, n3, pp3 = mcnemar_exact(S_pl["no_judge"], c_pl); x4, y4, n4, pc4 = mcnemar_exact(S_co["no_judge"], c_co)
            P(f"| {k} | {', '.join(nm for _, nm, _ in samples[:k])} | {len(c_pl)} | {len(c_co)} | {len(c_pe)} | "
              f"{x}/{y}, p={pp:.4f} | {x2}/{y2}, p={pc:.4f} | {x3}/{y3}, p={pp3:.4f} | {x4}/{y4}, p={pc4:.4f} |")
        if ctrl_sets:
            kmax = max(ctrl_sets); c_pl, c_co = ctrl_sets[kmax]
            P(f"\nBest-of-{kmax} control vs every configuration (McNemar exact, two-sided):\n")
            P("| configuration | plausible: conf-only/ctrl-only, p | correct: conf-only/ctrl-only, p |")
            P("|---|---|---|")
            for arm in ARMS:
                x, y, n, pp = mcnemar_exact(S_pl[arm], c_pl); x2, y2, n2, pc = mcnemar_exact(S_co[arm], c_co)
                P(f"| {arm} | {x}/{y}, p={pp:.4f} | {x2}/{y2}, p={pc:.4f} |")
            # tokens and cost of the control
            tk = us = 0.0
            for temp, name, info in samples[:kmax]:
                for b in evaluable:
                    if not info[b]["excluded"]:
                        tk += fnum(info[b]["row"].get("total_tokens")); us += fnum(info[b]["row"].get("estimated_usd"))
            sc = sum(fnum(info[b]["row"].get("time_seconds")) for _, _, info in samples[:kmax] for b in evaluable if not info[b]["excluded"])
            cand = sum(1 for _, _, info in samples[:kmax] for b in evaluable if not info[b]["excluded"])
            rcalls = sum(_repair_calls(info[b]["row"]) for _, _, info in samples[:kmax] for b in evaluable if not info[b]["excluded"])
            P(f"\ncontrol cost over the {kmax} samples: {cand} tested candidates, {rcalls} repair calls, {int(tk):,} tokens, ${us:.2f} "
              f"(${us/len(evaluable):.4f} per bug, ${us/max(len(c_co),1):.4f} per correct fix), {sc/3600:.1f} h, {sc/len(evaluable):.0f} s per bug")
            P("  per sample: " + "; ".join(
                f"{name}: {sum(_repair_calls(info[b]['row']) for b in evaluable if not info[b]['excluded'])} calls, "
                f"{sum(fnum(info[b]['row'].get('total_tokens')) for b in evaluable if not info[b]['excluded'])/1e6:.2f}M tokens, "
                f"{sum(fnum(info[b]['row'].get('time_seconds')) for b in evaluable if not info[b]['excluded'])/3600:.2f} h"
                for _, name, info in samples[:kmax]))
            # the same control when each bug stops at its first plausible sample, as the loop does
            e_tk = e_us = e_sc = 0.0; e_cand = e_calls = 0
            for b in evaluable:
                for _, _, info in samples[:kmax]:
                    if info[b]["excluded"]:
                        continue
                    r = info[b]["row"]
                    e_tk += fnum(r.get("total_tokens")); e_us += fnum(r.get("estimated_usd")); e_sc += fnum(r.get("time_seconds"))
                    e_cand += 1; e_calls += _repair_calls(r)
                    if info[b]["plausible"]:
                        break
            P(f"control stopping each bug at its first plausible sample: {e_cand} tested candidates, {e_calls} repair calls, {int(e_tk):,} tokens, "
              f"${e_us:.2f} (${e_us/len(evaluable):.4f} per bug, ${e_us/max(len(c_co),1):.4f} per correct fix), {e_sc/3600:.1f} h, {e_sc/len(evaluable):.0f} s per bug")
            P(f"control precision: {100*len(c_co)/max(len(c_pl),1):.1f}%")
            # order sensitivity of the first-plausible-wins rule, and the union (oracle) bound
            import itertools
            union_co = {b for b in evaluable if any(info[b]["plausible"] and is_correct_label(info[b]["label"]) for _, _, info in samples)}
            counts = []
            for perm in itertools.permutations(samples):
                co = 0
                for b in evaluable:
                    for _, _, info in perm:
                        if info[b]["plausible"]:
                            co += is_correct_label(info[b]["label"]); break
                counts.append(co)
            P(f"first-plausible-wins correct over all {len(counts)} sample orderings: min {min(counts)}, max {max(counts)}, mean {sum(counts)/len(counts):.1f}; "
              f"union (a correct patch in at least one sample): {len(union_co)}")
        P()

    # ── 4d. identical candidate texts, recorded outcomes ───────────────────
    P("## 4d. Candidates with the same text: are the recorded test outcomes the same?\n")
    P("Every tested candidate of every completed execution (all sessions of the four configurations and the control passes"
      + (", the sessions made before the correction of " + " and ".join(a_ for a_ in ARMS if a_ in reexec) + " included" if reexec else "")
      + "), compared by its complete text (Java token sequence).\n")
    conc = {}
    for spec in args.concurrent:
        a_, ss = spec.split("=", 1); conc[a_.strip()] = tuple(x.strip() for x in ss.split("+"))
    cand = defaultdict(lambda: defaultdict(list))
    sources = [(arm, per[arm]) for arm in ARMS]
    for arm in ARMS:
        if arm in reexec:
            nm_ = arm + ", before the correction"
            sources.append((nm_, per_review[arm]))
            sessions[nm_] = sorted({sx for lst in per_review[arm].values() for sx, _ in lst})
    if sample_dirs:
        sources += sorted(per_samples.items())
    for src_name, per_src in sources:
        for b in evaluable:
            for sx, r in per_src.get(b, []):
                if (r.get("status") or "").strip() != "completed":
                    continue
                ok = valid_completed(r)
                for att, txt, res in _candidate_outcomes(r):
                    if res:
                        cand[b][txt].append((src_name, sx, att, res, ok))
    n_all = sum(1 for b in cand for L in cand[b].values() for o in L if o[4])
    n_txt = sum(1 for b in cand for L in cand[b].values() if any(o[4] for o in L))
    rec_txt = [(b, L) for b in sorted(cand, key=order_key) for L in cand[b].values() if sum(1 for o in L if o[4]) > 1]
    n_rec = sum(sum(1 for o in L if o[4]) for _, L in rec_txt)
    mixed = [(b, L) for b in sorted(cand, key=order_key) for L in cand[b].values() if len({o[3] for o in L}) > 1]
    mixed_valid = [(b, L) for b, L in mixed if len({o[3] for o in L if o[4]}) > 1]
    P(f"- tested candidates in valid executions: {n_all}; distinct texts: {n_txt}; texts tested more than once: {len(rec_txt)} ({n_rec} candidates)")
    P(f"- texts recorded both as passing and as failing: {len(mixed)}, of which {len(mixed_valid)} within valid executions "
      f"({', '.join(b for b, _ in mixed_valid) or 'none'})\n")
    if mixed:
        P("| bug | where it passed | where it failed |")
        P("|---|---|---|")
        for b, L in mixed:
            def cell(res):
                return "; ".join("%s%s attempt %d%s" % (o[0], (" (" + o[1][-6:] + ")") if len(sessions.get(o[0], [])) > 1 else "",
                                                           o[2], "" if o[4] else " [invalid execution]")
                                 for o in L if o[3] == res)
            P(f"| {b} | {cell('PASS')} | {cell('FAIL')} |")
        P()
    conc_bugs = {}
    for a_, (s1, s2) in conc.items():
        both = [b for b in evaluable if {s1, s2} <= {sx for sx, _ in per[a_].get(b, [])}]
        conc_bugs[a_] = both
        can_in = [b for b in both if rec[a_][b]["session"] in (s1, s2)]
        # every valid execution the two sessions made on these bugs, against what was
        # recorded for the same candidate text in executions outside the two sessions
        nexec = tot = wit = same = 0; wbugs = set(); diffs = []
        for b in both:
            for sx, r in per[a_].get(b, []):
                if sx not in (s1, s2) or not valid_completed(r):
                    continue
                nexec += 1
                for att, txt, res in _candidate_outcomes(r):
                    if not res:
                        continue
                    tot += 1
                    others = [o for o in cand[b].get(txt, []) if o[4] and not (o[0] == a_ and o[1] in (s1, s2))]
                    if others:
                        wit += 1; wbugs.add(b)
                        if all(x[3] == res for x in others): same += 1
                        else: diffs.append("%s (%s) attempt %d (%s here; %s)" % (b, sx[-6:], att, res, ", ".join(sorted({"%s %s" % (x[0], x[3]) for x in others}))))
        P(f"- `{a_}`: sessions {s1} and {s2} ran at the same time in one working directory; bugs with a record in both: {len(both)} "
          f"({both[0]} to {both[-1]}); canonical execution taken from one of the two: {len(can_in)} bugs. "
          f"Valid executions of the two sessions on these bugs: {nexec}, {tot} tested candidates; "
          f"candidates whose text was also tested in an execution outside the two sessions: {wit} ({len(wbugs)} bugs), same recorded outcome: {same}"
          + (f"; different: {'; '.join(diffs)}" if diffs else ""))
        st_ = Counter()
        for b in both:
            for sx, r in per[a_].get(b, []):
                if sx in (s1, s2):
                    stt = (r.get("status") or "").strip()
                    st_["valid" if valid_completed(r) else ("empty baseline" if stt == "completed" else "aborted: " + stt)] += 1
        P(f"  records of the two sessions on these bugs: {dict(sorted(st_.items()))}")
    P()

    # ── 4e. the re-execution against the earlier executions of the same bugs ──
    if rerun:
        P("## 4e. The re-execution against the earlier executions of the same bugs\n")
        import itertools as _it2

        def _first_cand(r):
            co = _candidate_outcomes(r) if r is not None else []
            return co[0] if co else None

        def _first_step(r, action):
            for e in _history(r):
                if e.get("action") == action and int(fnum(e.get("iteration"), -1)) == 0:
                    return e
            return None

        for a_, late in rerun.items():
            aside = conc.get(a_, ())
            rbugs = [b for b in evaluable if rec[a_][b]["changed"]]

            def _valid_of(session, b):
                return next((r for sx, r in per[a_].get(b, []) if sx == session and valid_completed(r)), None)

            execs = {}          # name -> {bug: row of a valid execution, or None}
            execs["re-execution"] = {b: next((r for r in (_valid_of(s_, b) for s_ in late) if r is not None), None) for b in rbugs}
            for s_ in aside:
                execs["%s %s" % (a_, s_)] = {b: _valid_of(s_, b) for b in rbugs}
            for arm in ARMS:
                if arm != a_:
                    execs[arm] = {b: (rec[arm][b]["row"] if not rec[arm][b]["excluded"] else None) for b in rbugs}
            first_temp = []     # control passes at the temperature of a first attempt
            if sample_dirs:
                for name, per_s in sorted(per_samples.items()):
                    cs_ = canonical(per_s, "first")
                    execs[name] = {b: (cs_[b]["row"] if cs_.get(b) and not cs_[b]["excluded"] else None) for b in rbugs}
                    m_ = re.search(r"sample_t(\d{3})", name)
                    if m_ and int(m_.group(1)) == 10:
                        first_temp.append(name)
            P(f"`{a_}`: {len(rbugs)} bugs whose canonical record is a re-execution (session {', '.join(late)}).\n")

            # (1) the re-execution and the set-aside sessions, pair by pair
            trio = ["re-execution"] + ["%s %s" % (a_, s_) for s_ in aside]
            P("| pair | bugs with a valid execution in both | plausible in both | plausibility differs | first candidate has the same text | "
              "... with the same recorded outcome | candidate texts tested in both | ... with the same recorded outcome |")
            P("|---|---|---|---|---|---|---|---|")
            for x_, y_ in _it2.combinations(trio, 2):
                both = [b for b in rbugs if execs[x_][b] is not None and execs[y_][b] is not None]
                px = {b for b in both if truthy(execs[x_][b].get("plausible"))}; py = {b for b in both if truthy(execs[y_][b].get("plausible"))}
                f_same = f_out = t_both = t_same = 0
                for b in both:
                    cx, cy = _first_cand(execs[x_][b]), _first_cand(execs[y_][b])
                    if cx and cy and cx[1] == cy[1]:
                        f_same += 1; f_out += cx[2] == cy[2]
                    dx = defaultdict(set); dy = defaultdict(set)
                    for _, t_, o_ in _candidate_outcomes(execs[x_][b]): dx[t_].add(o_)
                    for _, t_, o_ in _candidate_outcomes(execs[y_][b]): dy[t_].add(o_)
                    for t_ in set(dx) & set(dy):
                        t_both += 1; t_same += dx[t_] == dy[t_]
                P(f"| {x_} vs {y_} | {len(both)} | {len(px & py)} | {len(px ^ py)} ({100*len(px ^ py)/len(both):.0f}%; "
                  f"only the first: {', '.join(sorted(px - py, key=order_key)) or 'none'}; only the second: {', '.join(sorted(py - px, key=order_key)) or 'none'}) | "
                  f"{f_same} | {f_out} | {t_both} | {t_same} |")
            P()
            for n_ in trio:
                v_ = [r for r in execs[n_].values() if r is not None]
                P(f"- {n_}: valid executions {len(v_)}, plausible {sum(1 for r in v_ if truthy(r.get('plausible')))}, "
                  f"tested candidates {sum(len(_candidate_outcomes(r)) for r in v_)}")
            pats = Counter(tuple(truthy(execs[n_][b].get("plausible")) for n_ in trio) for b in rbugs if all(execs[n_][b] is not None for n_ in trio))
            P(f"- bugs with a valid execution in all {len(trio)}: {sum(pats.values())}; same plausibility in all: "
              f"{sum(v for k, v in pats.items() if len(set(k)) == 1)}; plausibility differs between at least two valid executions: "
              f"{sum(1 for b in rbugs if len({truthy(execs[n_][b].get('plausible')) for n_ in trio if execs[n_][b] is not None}) > 1)} bugs\n")

            # (2) first candidates: the first-attempt prompt is the same in every configuration and in the control
            comp = trio + [arm for arm in ARMS if arm != a_] + first_temp
            def _ident(x_, y_):
                both = [b for b in rbugs if _first_cand(execs[x_][b]) and _first_cand(execs[y_][b])]
                return sum(1 for b in both if _first_cand(execs[x_][b])[1] == _first_cand(execs[y_][b])[1]), len(both)
            mine = [(o_,) + _ident("re-execution", o_) for o_ in comp[1:]]
            rest = [(x_, y_) + _ident(x_, y_) for x_, y_ in _it2.combinations(comp[1:], 2)]
            P("First candidate with the same text (same Java token sequence), on these bugs:\n")
            P("- re-execution against each other execution: " + "; ".join("%s %d/%d" % m_ for m_ in mine)
              + f" (range {min(m_[1] for m_ in mine)} to {max(m_[1] for m_ in mine)})")
            P(f"- between two of the other executions: range {min(r_[2] for r_ in rest)} to {max(r_[2] for r_ in rest)} "
              f"of {min(r_[3] for r_ in rest)} to {max(r_[3] for r_ in rest)} bugs ("
              + "; ".join("%s vs %s %d/%d" % r_ for r_ in rest) + ")")
            passes = [(n_, sum(1 for b in rbugs if (_first_cand(execs[n_][b]) or (0, "", ""))[2] == "PASS")) for n_ in comp]
            P("- first candidates that pass: " + "; ".join("%s %d" % p_ for p_ in passes)
              + f" (others: {min(p_[1] for p_ in passes[1:])} to {max(p_[1] for p_ in passes[1:])})\n")

            # (3) recorded prompt sizes: the same prompts were sent
            comp_all = trio[1:] + [arm for arm in ARMS if arm != a_] + (sorted(per_samples) if sample_dirs else [])
            lines = []; n_lo = 10**9; n_hi = 0; all_equal = True; j_tot = j_eq = 0
            for o_ in comp_all:
                n_ = eq_ = jn_ = jeq_ = 0; dif_ = []
                for b in rbugs:
                    r1, r2 = execs["re-execution"][b], execs[o_][b]
                    if r1 is None or r2 is None:
                        continue
                    s1_, s2_ = _first_step(r1, "repair"), _first_step(r2, "repair")
                    if not s1_ or not s2_:
                        continue
                    m1, m2 = s1_.get("metadata") or {}, s2_.get("metadata") or {}
                    if m1.get("is_multi_file") or m2.get("is_multi_file") or m1.get("generation_attempts") != 1 or m2.get("generation_attempts") != 1:
                        continue
                    n_ += 1
                    if m1.get("prompt_tokens") == m2.get("prompt_tokens"): eq_ += 1
                    else: dif_.append(b)
                    j1, j2 = _first_step(r1, "judge"), _first_step(r2, "judge")
                    if j1 and j2 and _norm_text(_step_text(s1_)) == _norm_text(_step_text(s2_)):
                        p1 = (j1.get("metadata") or {}).get("prompt_tokens"); p2 = (j2.get("metadata") or {}).get("prompt_tokens")
                        st1 = (j1.get("metadata") or {}).get("test_status_observed"); st2 = (j2.get("metadata") or {}).get("test_status_observed")
                        if p1 is not None and p2 is not None and st1 == st2 == "PASS":
                            jn_ += 1; jeq_ += p1 == p2
                lines.append(f"{o_} {eq_}/{n_}" + (f" (differs: {', '.join(dif_)})" if dif_ else "") + (f", Judge {jeq_}/{jn_}" if jn_ else ""))
                n_lo = min(n_lo, n_); n_hi = max(n_hi, n_); all_equal = all_equal and eq_ == n_
                j_tot += jn_; j_eq += jeq_
            P("Recorded size of the first Repair Agent prompt (single-file bugs whose first generation was usable in both executions), "
              "re-execution against each other execution, equal/compared; and of the first Judge prompt where the first candidate has the same text and passes:\n")
            P("- " + "; ".join(lines))
            P(f"- bugs compared per execution: {n_lo} to {n_hi}; first Repair Agent prompt of equal size in every comparison: {'yes' if all_equal else 'NO'}; "
              f"first Judge prompt of equal size: {j_eq}/{j_tot}\n")

    # ── 4f. configurations executed again in full with corrected code ──────
    if reexec:
        P("## 4f. Configurations executed again in full with corrected code\n")

        def _fc(r):
            co_ = _candidate_outcomes(r) if r is not None else []
            return co_[0] if co_ else None

        def _fstep(r, action, it=0):
            for e in _history(r):
                if e.get("action") == action and int(fnum(e.get("iteration"), -1)) == it:
                    return e
            return None

        def _loop_stats(rows):
            st = Counter(); temps = Counter()
            for r in rows:
                reps = [e for e in _history(r) if e.get("action") == "repair"]
                st["attempts"] += len(reps)
                st["attempts after a failed one"] += max(0, len(reps) - 1)
                for e in reps[1:]:
                    t_ = _step_temperature(e.get("metadata") or {})
                    temps["n/a" if t_ is None else "%.2f" % t_] += 1
                st["stagnation aborts"] += truthy(r.get("oscillation_abort"))
                st["Repair Agent calls"] += _repair_calls(r)
                st["tokens"] += int(fnum(r.get("total_tokens")))
                st["usd"] += fnum(r.get("estimated_usd"))
            return st, temps

        for a_, new_ in reexec.items():
            def _old(b):
                eo = can_review[a_].get(b)
                return eo if eo and not eo["excluded"] else None
            both = [b for b in bugs if not rec[a_][b]["excluded"] and _old(b)]
            only_new = [b for b in bugs if not rec[a_][b]["excluded"] and not _old(b)]
            only_old = [b for b in bugs if rec[a_][b]["excluded"] and _old(b)]
            P(f"`{a_}`, corrected code in session(s) {', '.join(new_)}. Bugs with a valid execution under both the earlier and "
              f"the corrected code: {len(both)}; only under the corrected code: {len(only_new)} ({', '.join(only_new) or 'none'}); "
              f"only under the earlier code: {len(only_old)} ({', '.join(only_old) or 'none'})\n")
            old_lab = {b: assign(a_, b, _old(b), _old(b))["label"] for b in both if truthy(_old(b)["row"].get("plausible"))}
            po = {b for b in both if truthy(_old(b)["row"].get("plausible"))}
            pn = {b for b in both if rec[a_][b]["plausible"]}
            co_ = {b for b in po if is_correct_label(old_lab.get(b, ""))}
            cn = {b for b in pn if rec[a_][b]["correct"]}
            pend = [b for b in both if rec[a_][b]["label"] == "PENDING"]
            P("| on the bugs valid under both | earlier code | corrected code | both | only earlier | only corrected |")
            P("|---|---|---|---|---|---|")
            P(f"| plausible | {len(po)} | {len(pn)} | {len(po & pn)} | {len(po - pn)} | {len(pn - po)} |")
            P(f"| correct (first plausible candidate) | {len(co_)} | {len(cn)}" + (f" + {len(pend)} pending" if pend else "")
              + f" | {len(co_ & cn)} | {len(co_ - cn)} | {len(cn - co_)} |")
            P()
            P(f"- plausible only under the earlier code: {', '.join(sorted(po - pn, key=order_key)) or 'none'}")
            P(f"- plausible only under the corrected code: {', '.join(sorted(pn - po, key=order_key)) or 'none'}\n")
            fb = {b for b in both if not rec["full"][b]["excluded"]}
            f_pl = {b for b in fb if rec["full"][b]["plausible"]}; f_co = {b for b in fb if rec["full"][b]["correct"]}
            x1, y1, _n, p1 = mcnemar_exact(f_co, co_ & fb); x2, y2, _n, p2 = mcnemar_exact(f_co, cn & fb)
            x3, y3, _n, p3 = mcnemar_exact(f_pl, po & fb); x4, y4, _n, p4 = mcnemar_exact(f_pl, pn & fb)
            P(f"`full` against `{a_}` on these {len(fb)} bugs (full: {len(f_pl)} plausible, {len(f_co)} correct), full-only/other-only: "
              f"correct, earlier code {x1}/{y1} (p={p1:.4f}), corrected code {x2}/{y2} (p={p2:.4f}); "
              f"plausible, earlier code {x3}/{y3} (p={p3:.4f}), corrected code {x4}/{y4} (p={p4:.4f})\n")
            x5, y5, _n, p5 = mcnemar_exact(cn, co_); x6, y6, _n, p6 = mcnemar_exact(pn, po)
            P(f"corrected against earlier code of `{a_}`, corrected-only/earlier-only: correct {x5}/{y5} (p={p5:.4f}); plausible {x6}/{y6} (p={p6:.4f})\n")

            # the first attempt does not depend on the correction: a measure of run-to-run variation
            f_both = f_same = fp_o = fp_n = fp_both = pt_n = pt_eq = 0; pt_dif = []
            for b in both:
                ro, rn = _old(b)["row"], rec[a_][b]["row"]
                c1, c2 = _fc(ro), _fc(rn)
                if c1 and c2:
                    f_both += 1; f_same += c1[1] == c2[1]
                    fp_o += c1[2] == "PASS"; fp_n += c2[2] == "PASS"; fp_both += (c1[2] == "PASS" and c2[2] == "PASS")
                s1, s2 = _fstep(ro, "repair"), _fstep(rn, "repair")
                if s1 and s2:
                    m1, m2 = s1.get("metadata") or {}, s2.get("metadata") or {}
                    if not (m1.get("is_multi_file") or m2.get("is_multi_file")) and m1.get("generation_attempts") == 1 \
                            and m2.get("generation_attempts") == 1:
                        pt_n += 1
                        if m1.get("prompt_tokens") == m2.get("prompt_tokens"):
                            pt_eq += 1
                        else:
                            pt_dif.append(b)
            P(f"First attempt, whose prompt the correction does not touch: first candidate with the same text {f_same}/{f_both}; "
              f"first candidate passes under the earlier code {fp_o}, under the corrected code {fp_n}, under both {fp_both}; "
              f"first Repair Agent prompt of equal recorded size {pt_eq}/{pt_n} (single-file bugs whose first generation was usable "
              f"in both)" + (f"; differs: {', '.join(pt_dif)}" if pt_dif else "") + "\n")

            # second attempt after the same failed first candidate: the prompts differ by the corrected sections
            # (and by the Judge's review where there is one, which is sampled)
            d2 = []
            for b in both:
                ro, rn = _old(b)["row"], rec[a_][b]["row"]
                c1, c2 = _fc(ro), _fc(rn)
                if not (c1 and c2 and c1[1] == c2[1] and c1[2] == c2[2] == "FAIL"):
                    continue
                s1, s2 = _fstep(ro, "repair", 1), _fstep(rn, "repair", 1)
                if not (s1 and s2):
                    continue
                m1, m2 = s1.get("metadata") or {}, s2.get("metadata") or {}
                if m1.get("is_multi_file") or m2.get("is_multi_file"):
                    continue
                if m1.get("generation_attempts") != 1 or m2.get("generation_attempts") != 1:
                    continue
                p1, p2 = m1.get("prompt_tokens"), m2.get("prompt_tokens")
                if p1 is not None and p2 is not None:
                    d2.append(int(p2) - int(p1))
            if d2:
                d2s = sorted(d2)
                P(f"Second attempt after the same failed first candidate (single-file, first generation usable): {len(d2)} bugs; "
                  f"recorded prompt size, corrected minus earlier: median {d2s[len(d2s) // 2]:+d} tokens, larger in "
                  f"{sum(1 for x_ in d2 if x_ > 0)}, equal in {sum(1 for x_ in d2 if x_ == 0)}, smaller in "
                  f"{sum(1 for x_ in d2 if x_ < 0)}\n")

            # loop behaviour on the same bugs
            so, to = _loop_stats([_old(b)["row"] for b in both])
            sn, tn = _loop_stats([rec[a_][b]["row"] for b in both])
            P("| on the bugs valid under both | earlier code | corrected code |")
            P("|---|---|---|")
            for k_ in ("attempts", "attempts after a failed one", "stagnation aborts", "Repair Agent calls"):
                P(f"| {k_} | {so[k_]} | {sn[k_]} |")
            P(f"| tokens (M) | {so['tokens'] / 1e6:.1f} | {sn['tokens'] / 1e6:.1f} |")
            P(f"| estimated cost (USD) | {so['usd']:.2f} | {sn['usd']:.2f} |")
            levels = sorted(set(to) | set(tn), key=lambda k_: (k_ == "n/a", float(k_) if k_ != "n/a" else 0))
            for k_ in levels:
                P(f"| attempts after a failed one at temperature {k_} | {to.get(k_, 0)} | {tn.get(k_, 0)} |")
            P()

        # how often two complete executions start from the same first candidate: the first attempt has the
        # same prompt in every configuration, so this compares executions by their dates and not by their code
        runs_ = []          # (name, {bug: row}) for executions made in one stretch
        for arm in ARMS:
            if arm in reexec:
                runs_.append((arm + ", earlier code", {b: can_review[arm][b]["row"] for b in bugs
                                                         if can_review[arm].get(b) and not can_review[arm][b]["excluded"]}))
                runs_.append((arm + ", corrected code", {b: rec[arm][b]["row"] for b in bugs if not rec[arm][b]["excluded"]}))
            elif arm not in rerun and arm not in conc:
                runs_.append((arm, {b: rec[arm][b]["row"] for b in bugs if not rec[arm][b]["excluded"]}))
        common_ = set(bugs)
        for a_, new_ in reexec.items():
            common_ &= {b for b in bugs if can_review[a_].get(b) and not can_review[a_][b]["excluded"] and not rec[a_][b]["excluded"]}
        P(f"First candidate with the same text, between complete executions, on the {len(common_)} bugs valid before and after "
          "the correction (the first attempt has the same prompt in every configuration; executions of configurations with "
          "re-executed or set-aside sessions are left out):\n")
        import itertools as _it3
        for (n1, r1), (n2, r2) in _it3.combinations(runs_, 2):
            cb = [b for b in common_ if b in r1 and b in r2 and _fc(r1[b]) and _fc(r2[b])]
            same_ = sum(1 for b in cb if _fc(r1[b])[1] == _fc(r2[b])[1])
            P(f"- {n1} vs {n2}: {same_}/{len(cb)} ({100 * same_ / max(len(cb), 1):.1f}%)")
        P()

    # ── 5. per project ─────────────────────────────────────────────────────
    P("## 5. Per project (plausible / correct)\n")
    P("| project | n | " + " | ".join(ARMS) + " |")
    P("|---|---|" + "---|" * len(ARMS))
    for proj in PROJECTS:
        bs = [b for b in evaluable if b.startswith(proj + "_")]
        cells = [f"{sum(1 for b in bs if rec[a][b]['plausible'])} / {sum(1 for b in bs if rec[a][b]['correct'])}" for a in ARMS]
        P(f"| {proj} | {len(bs)} | " + " | ".join(cells) + " |")
    P()

    # ── 6. iterations ──────────────────────────────────────────────────────
    P("## 6. Iteration at which the first plausible candidate was produced\n")
    P("| arm | plausible by attempt 1/2/3/4 | correct by attempt 1/2/3/4 |")
    P("|---|---|---|")
    for arm in ARMS:
        cp = Counter(rec[arm][b]["plausible_iteration"] for b in S_pl[arm])
        cc = Counter(rec[arm][b]["plausible_iteration"] for b in S_co[arm])
        P(f"| {arm} | {' / '.join(str(cp[k]) for k in range(4))} | {' / '.join(str(cc[k]) for k in range(4))} |")
    cp = Counter(rec["full"][b]["plausible_iteration"] for b in S_pl["full"])
    cc = Counter(rec["full"][b]["plausible_iteration"] for b in S_co["full"])
    tot = sum(cp.values()); run = 0
    P("\nfull arm:\n")
    P("| attempt | plausible | share | cumulative | correct | precision |")
    P("|---|---|---|---|---|---|")
    for k in sorted(cp):
        run += cp[k]
        P(f"| {k+1 if k >= 0 else 'unrecorded'} | {cp[k]} | {100*cp[k]/tot:.1f}% | {100*run/tot:.1f}% | {cc[k]} | {100*cc[k]/cp[k]:.1f}% |")
    nco = len(S_co["full"])
    P(f"\nfull arm, found after the first attempt: plausible {tot - cp[0]} ({100*(tot-cp[0])/tot:.1f}%), correct {nco - cc[0]} ({100*(nco-cc[0])/nco:.1f}%)")
    P("full arm, share of each project's plausible patches found at the first attempt: " + ", ".join(
        f"{pr} {sum(1 for b in S_pl['full'] if b.startswith(pr + '_') and rec['full'][b]['plausible_iteration'] == 0)}/"
        f"{sum(1 for b in S_pl['full'] if b.startswith(pr + '_'))} = "
        f"{100*sum(1 for b in S_pl['full'] if b.startswith(pr + '_') and rec['full'][b]['plausible_iteration'] == 0)/max(sum(1 for b in S_pl['full'] if b.startswith(pr + '_')),1):.1f}%"
        for pr in PROJECTS))
    P(f"mean iterations, full arm, all evaluable bugs: "
      f"{sum(rec['full'][b]['iterations'] for b in evaluable)/len(evaluable):.2f}")
    npl = [b for b in evaluable if not rec["full"][b]["plausible"]]
    osc = [b for b in evaluable if truthy(rec["full"][b]["row"].get("oscillation_abort"))]
    osc_txt = ", ".join("%s (after %d iterations, plausible=%s)" % (b, rec["full"][b]["iterations"], rec["full"][b]["plausible"]) for b in osc) or "none"
    P(f"full arm, bugs without a plausible patch: {len(npl)}; iterations used: "
      f"{dict(sorted(Counter(rec['full'][b]['iterations'] for b in npl).items()))}; stagnation aborts: {osc_txt}")
    mf = [b for b in evaluable if truthy(rec["full"][b]["row"].get("is_multi_file"))]
    sf = [b for b in evaluable if b not in set(mf)]
    P(f"full arm, multi-file bugs: {len(mf)}, plausible {sum(rec['full'][b]['plausible'] for b in mf)}, correct {sum(rec['full'][b]['correct'] for b in mf)} "
      f"({100*sum(rec['full'][b]['correct'] for b in mf)/max(len(mf),1):.1f}%); single-file bugs: {len(sf)}, correct {sum(rec['full'][b]['correct'] for b in sf)} "
      f"({100*sum(rec['full'][b]['correct'] for b in sf)/max(len(sf),1):.1f}%)")
    P("full arm, correct per project as a share of evaluable bugs: " + ", ".join(
        f"{pr} {sum(1 for b in S_co['full'] if b.startswith(pr + '_'))}/{sum(1 for b in evaluable if b.startswith(pr + '_'))} = "
        f"{100*sum(1 for b in S_co['full'] if b.startswith(pr + '_'))/sum(1 for b in evaluable if b.startswith(pr + '_')):.1f}%" for pr in PROJECTS))
    P("full arm, overfitting per project: " + ", ".join(
        f"{pr} {sum(1 for b in S_pl['full'] - S_co['full'] if b.startswith(pr + '_'))}" for pr in PROJECTS) + "\n")

    # ── 6b. adaptive-mechanism activity ────────────────────────────────────
    P("## 6b. Adaptive-mechanism activity (repair attempts made after a failed attempt)\n")
    P("Multi-file bugs take no part in the mechanisms (their attempts run at the base temperature); they are counted in the attempts.\n")
    P("| arm | attempts after a failure | of which multi-file | temperature > 0.1 | at 0.45 | at 0.85 (surgical mode) | other levels | bugs reaching surgical mode | at exactly 0.30 |")
    P("|---|---|---|---|---|---|---|---|---|")
    by_attempt = {}
    for arm in ARMS:
        tot = esc = t45 = t85 = oth = t30 = nmf = 0; surg_bugs = set(); by_attempt[arm] = defaultdict(Counter)
        for b in evaluable:
            for e in _history(rec[arm][b]["row"]):
                if e.get("action") != "repair":
                    continue
                md = e.get("metadata") or {}
                parts = _step_parts(md)
                multi = len(parts) > 1 or truthy(md.get("is_multi_file"))
                t = fnum(parts[0].get("temperature_used"), None)
                it = int(fnum(e.get("iteration")))
                if not multi and t is not None:
                    by_attempt[arm][it + 1][round(t, 2)] += 1
                if it == 0:
                    continue
                tot += 1; nmf += multi
                if t is not None and t > 0.1001:
                    esc += 1
                    if abs(t - 0.45) < 1e-6: t45 += 1
                    elif abs(t - 0.85) < 1e-6: t85 += 1; surg_bugs.add(b)
                    else:
                        oth += 1
                        if abs(t - 0.30) < 1e-6: t30 += 1
        P(f"| {arm} | {tot} | {nmf} | {esc} ({100*esc/max(tot,1):.0f}%) | {t45} | {t85} | {oth} | {len(surg_bugs)} | {t30} |")
    P("\n(0.45 is the no-op rule plus the near-identical-and-failed rule firing together; 0.85 is surgical mode, reachable only at the "
      "fourth attempt; 0.30 is the repeated-rationale rule firing alone"
      + ("; in the no_judge sessions executed before the correction it fired on the constant placeholder rationale, see section 4f)\n"
         if "no_judge" in reexec else ", which in no_judge is triggered by the constant placeholder rationale)\n"))
    P("Temperature of single-file attempts, by attempt number:\n")
    for arm in ARMS:
        P(f"- `{arm}`: " + "; ".join(f"attempt {k}: " + ", ".join(f"{t:g}: {n}" for t, n in sorted(v.items())) for k, v in sorted(by_attempt[arm].items())))
    P()

    # ── 6c. generation statistics ──────────────────────────────────────────
    P("## 6c. Candidates, Repair Agent calls and regenerations (all attempts)\n")
    P("| arm | tested candidates | of which multi-file | file generations | repair calls | regeneration calls | single-file attempts left without a usable edit | multi-file attempts with a file left unchanged |")
    P("|---|---|---|---|---|---|---|---|")
    gen_stats = {}
    def gen_row(name, rows_):
        steps = msteps = gens = calls = bad_single = bad_multi = 0; reasons = Counter()
        for r in rows_:
            for e in _history(r):
                if e.get("action") != "repair":
                    continue
                md = e.get("metadata") or {}; parts = _step_parts(md)
                multi = len(parts) > 1 or truthy(md.get("is_multi_file"))
                steps += 1; msteps += multi; gens += len(parts)
                calls += sum(int(fnum(p.get("generation_attempts"), 1) or 1) for p in parts)
                rej = [(p.get("generation_rejected") or "").strip() for p in parts]
                if any(rej):
                    if multi: bad_multi += 1
                    else:
                        bad_single += 1
                        reasons[re.sub(r"matches \d+ times", "matches N times", re.sub(r"block \d+: ", "", rej[0]))] += 1
        gen_stats[name] = dict(steps=steps, calls=calls)
        P(f"| {name} | {steps} | {msteps} | {gens} | {calls} | {calls - gens} ({100*(calls-gens)/max(calls,1):.1f}%) | "
          f"{bad_single} of {steps - msteps} ({dict(sorted(reasons.items()))}) | {bad_multi} |")
    for arm in ARMS:
        gen_row(arm, [rec[arm][b]["row"] for b in evaluable])
    if sample_dirs:
        for _, name, info in samples:
            gen_row(name, [info[b]["row"] for b in evaluable if not info[b]["excluded"]])
    P()

    # ── 6d. Judge reviews: lost, and declined test-passing candidates ──────
    P("## 6d. Judge reviews lost, and test-passing candidates not accepted\n")
    P("| arm | Judge invocations | parsed reviews | unparseable responses | empty responses | skipped (stagnation abort) |")
    P("|---|---|---|---|---|---|")
    declined = []
    for arm in ARMS:
        if arm == "no_judge":
            continue
        parsed = unp = emp = osc_n = 0
        for b in evaluable:
            x = rec[arm][b]; h = _history(x["row"])
            reps = {int(fnum(e.get("iteration"))): e for e in h if e.get("action") == "repair"}
            for e in h:
                if e.get("action") != "judge":
                    continue
                md = e.get("metadata") or {}; it = int(fnum(e.get("iteration")))
                kind = "parsed"
                if md.get("oscillation"): osc_n += 1; continue
                if (e.get("verdict") or "") == "error": unp += 1; kind = "unparseable response"
                elif md.get("judge_error"): emp += 1; kind = "empty response"
                else: parsed += 1
                passed = (md.get("test_status_observed") == "PASS") or (
                    md.get("test_status_observed") is None and x["plausible"] and x["plausible_iteration"] == it)
                if passed and (e.get("verdict") or "") != "correct":
                    same = _norm_text(_step_text(reps.get(it))) == _norm_text(_candidate_text(x["row"], "final"))
                    outcome = ("no patch accepted" if not x["accepted"] else
                               ("the same text accepted later" if same else "a different patch accepted later"))
                    declined.append((arm, b, it + 1, kind if kind != "parsed" else f"verdict {e.get('verdict')}",
                                     x["label"], outcome, x["delivered_label"]))
        P(f"| {arm} | {parsed + unp + emp} | {parsed} | {unp} | {emp} | {osc_n} |")
    P("\nTest-passing candidates that were not accepted on the spot:\n")
    P("| arm | bug | attempt | Judge outcome | label of that candidate | what followed | label of the accepted patch |")
    P("|---|---|---|---|---|---|---|")
    for row in declined:
        P("| " + " | ".join(str(c) for c in row) + " |")
    veto = [d for d in declined if d[3].startswith("verdict")]
    P(f"\ngenuine vetoes (a parsed verdict other than correct on a passing candidate): {len(veto)} "
      f"({sum(1 for d in veto if is_correct_label(d[4]))} labelled correct, {sum(1 for d in veto if not is_correct_label(d[4]))} overfitting; "
      f"{sum(1 for d in veto if d[5] != 'no patch accepted')} followed by an accepted patch, {sum(1 for d in veto if d[5] == 'no patch accepted')} not); "
      f"reviews lost on a passing candidate: {len(declined) - len(veto)}\n")

    # ── 7. cost ────────────────────────────────────────────────────────────
    P("## 7. Cost and time (canonical executions, evaluable set)\n")
    P("| arm | tested candidates | repair calls | total tokens | total USD | mean USD/bug | median USD/bug | max USD/bug | USD per correct fix | mean s/bug | hours | mean s (accepted) | mean s (not plausible) |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    import statistics as _st
    g_us = g_h = 0.0
    for arm in ARMS:
        xs = [rec[arm][b] for b in evaluable]
        tk = sum(x["tokens"] for x in xs); us = sum(x["usd"] for x in xs); sc = sum(x["secs"] for x in xs)
        acc = [x["secs"] for x in xs if x["accepted"]]; npl = [x["secs"] for x in xs if not x["plausible"]]
        g_us += us; g_h += sc / 3600
        P(f"| {arm} | {gen_stats[arm]['steps']} | {gen_stats[arm]['calls']} | {tk:,} | ${us:.2f} | ${us/len(xs):.4f} | "
          f"${_st.median(x['usd'] for x in xs):.4f} | ${max(x['usd'] for x in xs):.4f} | ${us/max(len(S_co[arm]),1):.4f} | {sc/len(xs):.0f} | {sc/3600:.1f} | "
          f"{sum(acc)/len(acc) if acc else 0:.0f} | {sum(npl)/len(npl) if npl else 0:.0f} |")
    P(f"\nfour configurations together: ${g_us:.2f}, {g_h:.1f} machine-hours")
    for nm, sel in (("found at the first attempt", lambda x: x["plausible_iteration"] == 0), ("found after iteration", lambda x: x["plausible_iteration"] > 0)):
        xs = [rec["full"][b] for b in S_pl["full"] if sel(rec["full"][b])]
        P(f"full arm, plausible patches {nm}: n={len(xs)}, median tokens {_st.median(x['tokens'] for x in xs):,.0f}, "
          f"median seconds {_st.median(x['secs'] for x in xs):.1f}, median USD {_st.median(x['usd'] for x in xs):.4f}")
    P()

    # ── 7b. token split ────────────────────────────────────────────────────
    P("## 7b. Token split per arm (canonical executions, evaluable set)\n")
    P("| arm | repair calls | repair prompt tokens | repair output tokens | judge calls | judge prompt tokens | judge output tokens | judge share of all tokens |")
    P("|---|---|---|---|---|---|---|---|")
    for arm in ARMS:
        rc = jc = 0; rp = ro = jp = jo = 0
        for b in evaluable:
            for e in _history(rec[arm][b]["row"]):
                md = e.get("metadata") or {}
                if e.get("action") == "repair":
                    rc += 1; pt, ct = _step_tokens(md); rp += pt; ro += ct
                elif e.get("action") == "judge" and md.get("model"):
                    jc += 1; pt, ct = _step_tokens(md); jp += pt; jo += ct
        tot = rp + ro + jp + jo
        P(f"| {arm} | {rc} | {rp:,} | {ro:,} | {jc} | {jp:,} | {jo:,} | {100*(jp+jo)/max(tot,1):.1f}% |")
    P()

    # ── 8. baseline failing counts ─────────────────────────────────────────
    P("## 8. Baseline failing-test counts (full arm)\n")
    bf = Counter(min(rec["full"][b]["baseline_failing"], 10) for b in evaluable)
    P(", ".join(f"{k if k < 10 else '10+'} tests: {bf[k]} bugs" for k in sorted(bf)) + "\n")

    # ── 8b. non-trigger baseline failures and the fixed-version audit ──────
    P("## 8b. Pre-existing failures beyond the trigger tests (B \\ Tg)\n")
    def triggers_of(r):
        return [t.strip() for t in re.split(r"[;,|]", r.get("failing_tests") or "") if t.strip()]
    P("| arm | bugs with extra baseline failures | extra failing tests in total | per project (bugs) | bugs |")
    P("|---|---|---|---|---|")
    no_trig = []
    for arm in ARMS:
        n = 0; tot = 0; per_p = Counter(); names = []
        for b in evaluable:
            r = rec[arm][b]["row"]
            if not triggers_of(r):
                no_trig.append(f"{arm}: {b} (plausible={rec[arm][b]['plausible']}, label={rec[arm][b]['label']})"); continue
            extra = rec[arm][b]["baseline_failing"] - len(triggers_of(r))
            if extra > 0:
                n += 1; tot += extra; per_p[b.rsplit("_", 1)[0]] += 1; names.append(f"{b} (+{extra}, plausible={rec[arm][b]['plausible']})")
        P(f"| {arm} | {n} | {tot} | " + ", ".join(f"{pr} {per_p[pr]}" for pr in PROJECTS) + f" | {', '.join(names)} |")
    P(f"\ncanonical records whose trigger-test list is empty (repaired without trigger-test information): {'; '.join(no_trig) or 'none'}")
    if sample_dirs:
        for _, name, info in samples:
            ok = 0; extra_t = Counter(); tot_ = 0
            for b in evaluable:
                if info[b]["excluded"]: continue
                r = info[b]["row"]; tot_ += 1
                B = set(t for t in (r.get("baseline_failing_tests") or "").split(";") if t); Tg = set(triggers_of(r))
                ok += Tg <= B
                for t in B - Tg: extra_t[(b, t)] += 1
            P(f"- `{name}` (baseline set logged): every trigger test fails at baseline for {ok}/{tot_} bugs; baseline failures outside the trigger tests: "
              + (", ".join(f"{b}: {t.split('.')[-1]}" for (b, t) in sorted(extra_t)) or "none"))
    # exact sets: the single-attempt runs record baseline_failing_tests; the fixed-version audit gives F
    B_set = {}
    for d in sample_dirs if sample_dirs else []:
        for f in sorted(glob.glob(os.path.join(d, "results_*.csv")), key=session_key):
            for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
                bb = (r.get("bug_id") or "").strip()
                if bb in B_set or not bb or (r.get("baseline_failing_tests") or "") == "":
                    continue
                if (r.get("status") or "") == "completed":
                    B_set[bb] = (set(t for t in r["baseline_failing_tests"].split(";") if t), triggers_of(r))
    if args.fixed_baseline and B_set:
        F = {}
        for r in csv.DictReader(open(args.fixed_baseline, encoding="utf-8", errors="replace")):
            if (r.get("status") or "") == "ok":
                F[r["bug_id"]] = set(t for t in (r.get("failing_tests") or "").split(";") if t)
        both = [b for b in evaluable if b in B_set and b in F]
        extra_bugs = [b for b in both if B_set[b][0] - set(B_set[b][1])]
        covered = [b for b in extra_bugs if (B_set[b][0] - set(B_set[b][1])) <= F[b]]
        viol = [(b, sorted((B_set[b][0] - set(B_set[b][1])) - F[b])) for b in extra_bugs if b not in covered]
        trig_ok = sum(1 for b in both if set(B_set[b][1]) <= B_set[b][0])
        fix_ok = sum(1 for b in both if not (set(B_set[b][1]) & F[b]))
        P(f"\nFixed-version audit: {len(both)} bugs with both a recorded buggy baseline set and a fixed-version run; "
          f"{len(extra_bugs)} have extra baseline failures; in {len(covered)} of them every extra failing test also fails on the developer-fixed version "
          f"(environment failure, not a hidden regression); trigger tests fail at baseline for {trig_ok}/{len(both)} and pass on the fixed version for {fix_ok}/{len(both)}.")
        if viol:
            P("  - extra baseline failures that PASS on the fixed version (a patch could have hidden a regression there): "
              + "; ".join(f"{b}: {', '.join(ts)}" for b, ts in viol[:40]))
    elif args.fixed_baseline:
        P("\n(fixed-version audit skipped: no run with a `baseline_failing_tests` column found; re-run with the updated runner)")
    P()

    # ── 9. inter-rater agreement ───────────────────────────────────────────
    P("## 9. Inter-rater agreement on the full arm's plausible patches\n")
    vf = ver["full"]
    def binl(v):
        v = (v or "").strip()
        if v.startswith("Correct"): return "correct"
        if v in ("Overfitting", "Incorrect"): return "not"
        return None
    other_text = sorted((b for b in S_pl["full"] if not rec["full"][b]["reviewed_same_text"]), key=order_key)
    P(f"Bugs whose blind passes reviewed the patch of another execution, excluded here: {len(other_text)} ({', '.join(other_text)})\n")
    for col in ("Independent review 2 (blind)", "Independent review 3 (blind)"):
        pairs = []; dis = []
        for b in sorted(S_pl["full"], key=order_key):
            if not rec["full"][b]["reviewed_same_text"]: continue
            r = vf.get(b)
            if not r or col not in r: continue
            final = (rec["full"][b].get("label") or r.get("Reviewer Semantic verdict") or "")
            a, c2 = binl(final), binl(r.get(col))
            if a and c2:
                pairs.append((a, c2))
                if a != c2: dis.append(f"{b} (final {final}; pass {r.get(col)})")
        if pairs:
            agree = sum(1 for a, c2 in pairs if a == c2)
            lo, hi = bootstrap_kappa(pairs)
            P(f"- final label vs {col}: n={len(pairs)}, agreement={100*agree/len(pairs):.1f}%, "
              f"κ={kappa(pairs):.3f} [95% bootstrap CI {lo:.2f}, {hi:.2f}], disagreements={len(pairs)-agree}"
              + (f": {'; '.join(dis)}" if dis else ""))
    P()

    # ── 9b. second verification ────────────────────────────────────────────
    if args.second_verification:
        P("## 9b. Second verification (labels given again, with execution where the project could be rebuilt)\n")
        def b2(v):
            v = (v or "").strip().lower()
            if v.startswith(("correct", "identical", "equivalent")): return "correct"
            if v.startswith(("overfitting", "incorrect")): return "not"
            return None
        tot_cov = 0
        for arm in ARMS:
            path2 = os.path.join(args.second_verification, f"verification_{arm}.csv")
            if not os.path.exists(path2):
                P(f"- `{arm}`: no file"); continue
            v2 = load_verification(path2)
            cols = list(next(iter(v2.values())).keys()) if v2 else []
            lp = [b for b in evaluable if (v2.get(b, {}).get("Logged plausible by the suite") or "").strip().lower() == "yes"]
            vp = Counter((v2[b].get("Verified plausible") or "").strip() for b in lp)
            def _reviewed(b, arm=arm):
                # is the canonical patch the text this file reviewed?
                if arm == "full":
                    return rec[arm][b]["reviewed_same_text"]
                if arm in reexec:
                    eo = can_review[arm].get(b)
                    return bool(eo and not eo["excluded"] and truthy(eo["row"].get("plausible"))
                                and _patch_text(eo["row"]) == rec[arm][b]["first_txt"])
                return True
            covered = [b for b in S_pl[arm] if b in v2 and _reviewed(b)]
            tot_cov += len(covered)
            first_diff = sorted((b for b in lp if b in ver[arm] and b2(label_of(ver[arm][b])) and b2(label_of(v2[b]))
                                 and b2(label_of(ver[arm][b])) != b2(label_of(v2[b]))), key=order_key)
            final_diff = sorted((b for b in covered if b2(label_of(v2[b])) and b2(label_of(v2[b])) != ("correct" if rec[arm][b]["correct"] else "not")), key=order_key)
            P(f"- `{arm}`: {len(lp)} patches logged plausible in the file"
              + (" (the sessions executed before the correction)" if arm in reexec else "")
              + f"; canonical plausible patches whose text it reviewed: {len(covered)} of {len(S_pl[arm])}")
            P(f"  - label differs from the first verification file: {len(first_diff)} ({', '.join('%s: %s -> %s' % (b, label_of(ver[arm][b]), label_of(v2[b])) for b in first_diff) or 'none'})")
            P(f"  - label differs from the final label: {len(final_diff)} ({', '.join('%s: %s, final %s' % (b, label_of(v2[b]), rec[arm][b]['label']) for b in final_diff) or 'none'})")
            P(f"  - 'Verified plausible' of the logged-plausible patches: {dict(sorted(vp.items()))}")
            if "Tests rerun" in cols:
                def cat(b):
                    t = (v2[b].get("Tests rerun") or "").strip()
                    ev = " ".join((v2[b].get(c) or "") for c in cols if c.startswith("Execution evidence"))
                    if re.match(r"JDK\s*\d+ rerun", t): return re.match(r"(JDK\s*\d+) rerun", t).group(1) + " re-run of the relevant tests"
                    if t.lower().startswith("not rerun"): return "not re-run (project could not be rebuilt)"
                    if not t and "token-identical" in ev.lower(): return "token-identical to the developer fix, not re-executed"
                    return "other"
                P(f"  - execution of the logged-plausible patches: {dict(sorted(Counter(cat(b) for b in lp).items()))}")
            notpl = [b for b in evaluable if b in v2 and b not in lp and (v2[b].get("Verified plausible") or "").strip().lower().startswith("yes")]
            if notpl:
                P(f"  - logged as failing, passing when re-executed: {', '.join(sorted(notpl, key=order_key))}")
        P(f"\ncanonical plausible patches of the four configurations whose text the second verification reviewed: {tot_cov} of {sum(len(S_pl[a]) for a in ARMS)}\n")

    # ── 10. judge pilot ────────────────────────────────────────────────────
    if args.judge_swap:
        P("## 10. Offline judge pilot vs human labels (full arm, plausible set)\n")
        gt = {b: ("correct" if rec["full"][b]["correct"] else "bad")
              for b in S_pl["full"] if rec["full"][b]["label"] != "PENDING"}
        P("Scored only on patches whose judged text is the canonical, labelled text; bugs judged on the text of another "
          "execution are listed and excluded.\n")
        P("| model | judged on canonical text | vetoed | overfitting caught | correct wrongly vetoed | veto precision | κ vs labels [95% bootstrap CI] | excluded: other execution's text | not judged |")
        P("|---|---|---|---|---|---|---|---|---|")
        both_veto = None; both_caught = None
        for path in args.judge_swap:
            by_bug = defaultdict(list)                 # usable verdicts, in file order (later = newer)
            for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
                if r.get("second_verdict") not in ("error", "", None):
                    by_bug[r["bug_id"]].append(r)
            model = os.path.basename(path).replace("judge_swap_", "").replace(".csv", "")
            # A verdict counts if the record it was given on (the session written by
            # judge_swap.py) has the canonical patch text; a file without the session
            # column judged the newest execution of each bug. The first usable verdict
            # on a text stands: a later one on the same text is not used.
            rows = {}; notcanon = []
            for b in sorted(by_bug, key=order_key):
                e = can["full"].get(b)
                if not e or e["excluded"] or b not in gt:
                    continue
                want = _patch_text(e["row"])
                for r in by_bug[b]:
                    ses = (r.get("session") or "").strip()
                    if ses:
                        judged = next((row for s_, row in e["completed_all"] if s_ == ses), None)
                    else:
                        judged = e["completed_all"][-1][1] if e["completed_all"] else None
                    if judged is not None and _patch_text(judged) == want:
                        rows[b] = r
                        break
                if b not in rows:
                    notcanon.append(b)
            scored = [(b, "correct" if rows[b]["second_verdict"] == "correct" else "bad", gt[b])
                      for b in sorted(rows, key=order_key)]
            bad = [x for x in scored if x[2] == "bad"]; good = [x for x in scored if x[2] == "correct"]
            caught = sum(1 for _, m, _h in bad if m == "bad"); fv = sum(1 for _, m, _h in good if m == "bad")
            vet = sum(1 for _, m, _h in scored if m == "bad")
            missing = sorted(set(gt) - set(by_bug), key=order_key)
            kp = [(m, h) for _, m, h in scored]; lo, hi = bootstrap_kappa(kp)
            P(f"| {model} | {len(scored)} | {vet} | {caught}/{len(bad)} | {fv}/{len(good)} | "
              f"{caught}/{vet if vet else 1} | {kappa(kp):.3f} [{lo:.2f}, {hi:.2f}] | "
              f"{len(notcanon)} ({', '.join(notcanon)}) | {len(missing)} ({', '.join(missing)}) |")
            vset = {b for b, m, _h in scored if m == "bad"}; cset = {b for b, m, h in scored if m == "bad" and h == "bad"}
            both_veto = vset if both_veto is None else both_veto & vset
            both_caught = cset if both_caught is None else both_caught & cset
            P(f"  - vetoed, overfitting: {', '.join(b for b, m, h in scored if m == 'bad' and h == 'bad') or 'none'}")
            vc_txt = ", ".join("%s [%s]" % (b, rec["full"][b]["label"]) for b, m, h in scored if m == "bad" and h == "correct") or "none"
            P(f"  - vetoed, correct: {vc_txt}")
        if both_veto is not None:
            P(f"\nvetoed by every reviewer: {', '.join(sorted(both_veto, key=order_key)) or 'none'}; "
              f"overfitting caught by every reviewer: {', '.join(sorted(both_caught, key=order_key)) or 'none'}")
        P()

    # ── 12. file sizes, and what the no_judge diff section contained ───────
    P("## 12. Size of the modified files, and the diff section of the no_judge prompt\n")
    import statistics as _st2
    sizes = {}
    for b in evaluable:
        first = next((e for e in _history(rec["full"][b]["row"]) if e.get("action") == "repair"), None)
        sizes[b] = [int(fnum(p.get("line_count"))) for p in _step_parts((first or {}).get("metadata") or {})]
    single = [b for b in evaluable if len(sizes[b]) == 1]
    vals = sorted(sizes[b][0] for b in single)
    q = _st2.quantiles(vals, n=4)
    P(f"- single-file bugs: {len(single)}; lines in the modified file: median {_st2.median(vals):.0f}, quartiles {q[0]:.0f} / {q[2]:.0f}; "
      f"{sum(v >= 150 for v in vals)} ({100*sum(v >= 150 for v in vals)/len(vals):.1f}%) have 150 lines or more, "
      f"{sum(v >= 1000 for v in vals)} ({100*sum(v >= 1000 for v in vals)/len(vals):.1f}%) have 1,000 or more")
    P("- median lines per project (single-file bugs): " + ", ".join(
        f"{pr} {_st2.median([sizes[b][0] for b in single if b.startswith(pr + '_')]):.0f}" for pr in PROJECTS))
    if "no_judge" in reexec:
        # the sessions executed before the correction, where the diff section was computed against the excerpt
        old_nj = can_review["no_judge"]
        need = [b for b in evaluable if old_nj.get(b) and not old_nj[b]["excluded"]
                and not (truthy(old_nj[b]["row"].get("plausible")) and int(fnum(old_nj[b]["row"].get("plausible_iteration"), -1)) == 0)]
        big = [b for b in need if max(sizes[b]) >= 150]
        P(f"- no_judge, sessions executed before the correction: bugs that received feedback (first attempt not plausible): {len(need)}; of these, "
          f"bugs with a modified file of 150 lines or more, for which the diff section was computed against the localized excerpt instead of "
          f"the original file: {len(big)} ({100*len(big)/max(len(need),1):.0f}%). The corrected code computes it against the original file "
          f"(section 4f).\n")
    else:
        need = [b for b in evaluable if not (rec["no_judge"][b]["plausible"] and rec["no_judge"][b]["plausible_iteration"] == 0)]
        big = [b for b in need if max(sizes[b]) >= 150]
        P(f"- no_judge: bugs that received feedback (first attempt not plausible): {len(need)}; of these, bugs with a modified file of 150 lines or more, "
          f"for which the diff section was computed against the localized excerpt instead of the original file: {len(big)} ({100*len(big)/max(len(need),1):.0f}%)\n")

    # ── 13. compilation failures, by the Judge's rationale ─────────────────
    P("## 13. Candidates that did not compile, by the Judge's rationale (full arm, proxy)\n")
    P("A failed candidate is counted when the Judge's rationale mentions compilation; the test result itself is not stored per iteration.\n")
    P("| project | failed candidates reviewed | rationale mentions compilation | share | bugs with at least one |")
    P("|---|---|---|---|---|")
    tf = tc = 0
    for pr in PROJECTS:
        nf = nc = nb = 0
        for b in evaluable:
            if not b.startswith(pr + "_"): continue
            had = False
            for e in _history(rec["full"][b]["row"]):
                if e.get("action") == "judge" and (e.get("metadata") or {}).get("test_status_observed") == "FAIL":
                    nf += 1
                    if re.search(r"compil", e.get("reason") or "", re.I): nc += 1; had = True
            nb += had
        tf += nf; tc += nc
        P(f"| {pr} | {nf} | {nc} | {100*nc/max(nf,1):.0f}% | {nb} |")
    P(f"| all | {tf} | {tc} | {100*tc/max(tf,1):.0f}% | |\n")

    # ── 14. sensitivity: harness false negatives ───────────────────────────
    if args.false_negatives:
        P("## 14. Sensitivity: candidates logged as failing that pass when re-executed\n")
        fneg = defaultdict(list)
        for r in csv.DictReader(open(args.false_negatives, encoding="utf-8")):
            fneg[r["arm"].strip()].append(r["bug_id"].strip())
        P("Counted as plausible and correct (their patches are identical or equivalent to the developer fix); the reported figures do not include them.\n")
        P("| arm | added | plausible | correct | vs full, correct: full-only/arm-only, p |")
        P("|---|---|---|---|---|")
        pl2 = {a: set(S_pl[a]) | set(fneg.get(a, [])) for a in ARMS}; co2 = {a: set(S_co[a]) | set(fneg.get(a, [])) for a in ARMS}
        for arm in ARMS:
            clash = sorted(set(fneg.get(arm, [])) & S_pl[arm])
            cell = ""
            if arm != "full":
                x, y, n, pp = mcnemar_exact(co2["full"], co2[arm]); cell = f"{x}/{y}, p={pp:.4f}"
            P(f"| {arm} | {', '.join(fneg.get(arm, [])) or 'none'}{' (ALREADY PLAUSIBLE: ' + ', '.join(clash) + ')' if clash else ''} | {len(pl2[arm])} | {len(co2[arm])} | {cell} |")
        if sample_dirs and ctrl_sets:
            kmax = max(ctrl_sets); c_pl, c_co = ctrl_sets[kmax]
            cp2 = set(c_pl) | set(fneg.get("control", [])); cc2 = set(c_co) | set(fneg.get("control", []))
            x, y, n, pp = mcnemar_exact(co2["full"], cc2); x2, y2, n2, pp2 = mcnemar_exact(co2["no_judge"], cc2)
            P(f"| control (best of {kmax}) | {', '.join(fneg.get('control', [])) or 'none'} | {len(cp2)} | {len(cc2)} | {x}/{y}, p={pp:.4f} (vs no_judge {x2}/{y2}, p={pp2:.4f}) |")
        P()

    # ── 14c. sensitivity: without a given list of bugs ─────────────────────
    for path_ in args.without_bugs:
        drop_ = {l.strip() for l in open(path_) if l.strip()}
        keep_ = [b for b in evaluable if b not in drop_]
        P(f"## 14c. Sensitivity: without the {len(drop_ & set(evaluable))} bugs of `{os.path.basename(path_)}`\n")
        P(f"Paired set restricted to the other {len(keep_)} bugs; McNemar exact against `full`, Holm over the three correct-fix comparisons.\n")
        P("| arm | plausible | correct | correct: full-only/arm-only | p | Holm p | plausible: full-only/arm-only | p |")
        P("|---|---|---|---|---|---|---|---|")
        ks = set(keep_)
        tests_ = {a: mcnemar_exact(S_co["full"] & ks, S_co[a] & ks) for a in ARMS if a != "full"}
        order_ = sorted(tests_, key=lambda a: tests_[a][3]); run_ = 0.0; holm_ = {}
        for rank_, a in enumerate(order_):
            run_ = max(run_, min(1.0, (len(order_) - rank_) * tests_[a][3])); holm_[a] = run_
        P(f"| full | {len(S_pl['full'] & ks)} | {len(S_co['full'] & ks)} | | | | | |")
        for a in ARMS:
            if a == "full":
                continue
            x, y, n, pp = tests_[a]; x2, y2, n2, pp2 = mcnemar_exact(S_pl["full"] & ks, S_pl[a] & ks)
            P(f"| {a} | {len(S_pl[a] & ks)} | {len(S_co[a] & ks)} | {x}/{y} | {pp:.4f} | {holm_[a]:.4f} | {x2}/{y2} | {pp2:.4f} |")
        P(f"\non the {len(drop_ & set(evaluable))} bugs themselves (plausible / correct): "
          + "; ".join(f"{a} {len(S_pl[a] & drop_)} / {len(S_co[a] & drop_)}" for a in ARMS))
        if sample_dirs and ctrl_sets:
            kmax = max(ctrl_sets); c_pl, c_co = ctrl_sets[kmax]
            x, y, n, pp = mcnemar_exact(S_co["full"] & ks, c_co & ks); x2, y2, n2, pp2 = mcnemar_exact(S_co["no_judge"] & ks, c_co & ks)
            P(f"control (best of {kmax}) on the {len(keep_)} bugs: plausible {len(c_pl & ks)}, correct {len(c_co & ks)}; "
              f"full vs control correct {x}/{y}, p={pp:.4f}; no_judge vs control correct {x2}/{y2}, p={pp2:.4f}; "
              f"on the {len(drop_ & set(evaluable))} bugs: plausible {len(c_pl & drop_)}, correct {len(c_co & drop_)}")
        P()

    # ── 14b. sensitivity: without the bugs executed by two concurrent sessions ──
    for a_, both in conc_bugs.items():
        P(f"## 14b. Sensitivity: without the {len(both)} bugs that two concurrent `{a_}` sessions executed\n")
        sub = [b for b in evaluable if b not in set(both)]
        P(f"Paired set restricted to the other {len(sub)} bugs; McNemar exact against `full`, Holm over the three correct-fix comparisons.\n")
        P("| arm | plausible | correct | correct: full-only/arm-only | p | p1 | Holm p | plausible: full-only/arm-only | p |")
        P("|---|---|---|---|---|---|---|---|---|")
        subs = set(sub); rows_s = []
        for arm in ARMS[1:]:
            x, y, n, pp = mcnemar_exact(S_co["full"] & subs, S_co[arm] & subs)
            x2, y2, n2, pp2 = mcnemar_exact(S_pl["full"] & subs, S_pl[arm] & subs)
            rows_s.append((arm, x, y, pp, x2, y2, pp2))
        hs = holm([r_[3] for r_ in rows_s])
        P(f"| full | {len(S_pl['full'] & subs)} | {len(S_co['full'] & subs)} | | | | | | |")
        for (arm, x, y, pp, x2, y2, pp2), h_ in zip(rows_s, hs):
            P(f"| {arm} | {len(S_pl[arm] & subs)} | {len(S_co[arm] & subs)} | {x}/{y} | {pp:.4f} | {pp/2 if x >= y else 1 - pp/2:.4f} | {h_:.4f} | {x2}/{y2} | {pp2:.4f} |")
        if sample_dirs and ctrl_sets:
            kmax = max(ctrl_sets); c_pl, c_co = ctrl_sets[kmax]
            x, y, n, pp = mcnemar_exact(S_co["full"] & subs, c_co & subs); x2, y2, n2, pp2 = mcnemar_exact(S_pl["full"] & subs, c_pl & subs)
            x3, y3, n3, pp3 = mcnemar_exact(S_co["no_judge"] & subs, c_co & subs)
            P(f"| control (best of {kmax}) | {len(c_pl & subs)} | {len(c_co & subs)} | {x}/{y} | {pp:.4f} | | | {x2}/{y2} | {pp2:.4f} |")
            P(f"\ncontrol vs no_judge on this subset, correct: {x3}/{y3}, p={pp3:.4f}")
        bs = set(both)
        P(f"\non the {len(both)} bugs themselves (plausible / correct): " + ", ".join(
            f"{arm} {len(S_pl[arm] & bs)} / {len(S_co[arm] & bs)}" for arm in ARMS)
          + (f", control {len(ctrl_sets[max(ctrl_sets)][0] & bs)} / {len(ctrl_sets[max(ctrl_sets)][1] & bs)}" if sample_dirs and ctrl_sets else "") + "\n")

    # ── 11. counts under other choices among repeated executions ──────────
    P("## 11. Sensitivity to the choice among repeated executions (full arm)\n")
    for arm in ARMS:
        for b in evaluable:
            x = rec[arm][b]
            if x["plausible"]:
                learn(b, x["first_txt"], x["label"], "%s, session %s" % (arm, x["session"]))
    if rerun.get("full"):
        variants = [("as reported (set-aside sessions last, then earliest)", per["full"], args.rule, conc.get("full", ())),
                    ("records made before the re-execution, earliest valid", per_review["full"], "first", ()),
                    ("records made before the re-execution, latest valid", per_review["full"], "last", ())]
    else:
        variants = [("rule `first`", per["full"], "first", ()), ("rule `last`", per["full"], "last", ())]
    for vname, per_x, rule, aside in variants:
        c2 = canonical(per_x, rule, aside)
        pls = set(); cos = set(); pend_b = []
        for b in evaluable:
            e = c2.get(b)
            if not e or e["excluded"]: continue
            r = e["row"]
            if not truthy(r.get("plausible")): continue
            pls.add(b)
            # the label of this execution's own text: a labelled patch with the same
            # text, otherwise the verification row if it reviewed this execution
            vr = ver["full"].get(b); eo = can_review["full"].get(b)
            vs = verified_session(b, eo, vr) if eo and not eo["excluded"] else None
            lab = known.get((b, _patch_text(r)), ("", ""))[0]
            if not lab and vr and vs == e["session"]:
                lab = label_of(vr)
            if is_correct_label(lab): cos.add(b)
            elif not lab.startswith(("Overfitting", "Incorrect")): pend_b.append(b)
        tests = "; ".join("%s %d/%d p=%.3f" % ((arm,) + mcnemar_exact(cos, S_co[arm])[:2] + (mcnemar_exact(cos, S_co[arm])[3],)) for arm in ARMS[1:])
        hmin = min(holm([mcnemar_exact(cos, S_co[arm])[3] for arm in ARMS[1:]]))
        redo = {b for b in evaluable if rec["full"][b]["changed"]}
        on_redo = (f"; on the {len(redo)} re-executed bugs: plausible={len(pls & redo)}, correct={len(cos & redo)}" if redo else "")
        P(f"- {vname}: plausible={len(pls)}, correct={len(cos)}, pending={len(pend_b)}" + (f" ({', '.join(pend_b)})" if pend_b else "")
          + on_redo
          + f"; correct fixes against the reduced configurations (full-only/other-only, McNemar): {tests}; smallest Holm-adjusted value {hmin:.3f}")
    strict_pl = sum(1 for b in evaluable if can["full"][b]["completed"] and
                    all(truthy(r.get("plausible")) for _, r in can["full"][b]["completed"]))
    P(f"- strict (plausible in every execution): plausible={strict_pl}\n")
    P(f"canonical per-bug tables written to `{args.outdir}/canonical_<arm>.csv`")


if __name__ == "__main__":
    main()
