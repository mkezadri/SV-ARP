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

def canonical(per_bug, rule):
    """bug -> dict(session, row, all_completed=[(session,row)...], excluded_reason)"""
    out = {}
    for b, lst in per_bug.items():
        comp = [(s, r) for s, r in lst if valid_completed(r)]
        # every completed execution, valid or not: the human review may have
        # been performed on one that is now ruled invalid
        comp_all = [(s, r) for s, r in lst if (r.get("status") or "").strip() == "completed"]
        if comp:
            pick = comp[0] if rule == "first" else comp[-1]
            out[b] = dict(session=pick[0], row=pick[1], completed=comp,
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


def _patch_text(r):
    return re.sub(r"\s+", " ", (r.get("plausible_patch") or r.get("patch") or "")).strip()


def _norm_text(t):
    return re.sub(r"\s+", "", t or "")


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
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    explicit = dict(v.split("=", 1) for v in args.verification)
    overrides = defaultdict(dict)
    delivered_overrides = defaultdict(dict)
    if args.overrides:
        for r in csv.DictReader(open(args.overrides, encoding="utf-8")):
            which = (r.get("which") or "first").strip().lower()
            tgt = delivered_overrides if which == "delivered" else overrides
            tgt[r["arm"].strip()][r["bug_id"].strip()] = r

    P = print
    P(f"# SV-ARP figures — regenerated from raw files\n")
    P(f"rule for repeated executions: **{args.rule} session**\n")

    # ── load everything ─────────────────────────────────────────────────────
    per = {}; sessions = {}; ver = {}; can = {}
    for arm in ARMS:
        per[arm], sessions[arm] = load_arm(args.raw, arm)
        vpath = find_verification(args.raw, arm, explicit)
        ver[arm] = load_verification(vpath)
        can[arm] = canonical(per[arm], args.rule)
        P(f"- `{arm}`: {len(sessions[arm])} session(s), {sum(len(v) for v in per[arm].values())} rows, "
          f"{len(per[arm])} bugs; verification: `{vpath or 'NONE'}` ({len(ver[arm])} rows)")

    if args.bug_list:
        bugs = [l.strip() for l in open(args.bug_list) if l.strip()]
    else:
        bugs = sorted(set().union(*[set(p) for p in per.values()]),
                      key=lambda b: (b.rsplit("_", 1)[0], int(b.rsplit("_", 1)[1])))
    P(f"\nbenchmark: {len(bugs)} bugs\n")

    # ── per-arm canonical tables ───────────────────────────────────────────
    # rec[arm][bug] = dict(...) with plausible / correct / pending / excluded
    rec = {}
    pending = defaultdict(list)
    for arm in ARMS:
        rec[arm] = {}
        for b in bugs:
            e = can[arm].get(b)
            if e is None:
                rec[arm][b] = dict(excluded="not run"); continue
            if e["excluded"]:
                rec[arm][b] = dict(excluded=e["excluded"]); continue
            r = e["row"]
            vr = ver[arm].get(b)
            vs = verified_session(b, e, vr)
            plaus = truthy(r.get("plausible"))
            judge = (r.get("verdict") or "").strip().lower()
            accepted = plaus and judge == "correct"
            label = ""; label_src = ""
            ov = overrides.get(arm, {}).get(b)
            if ov:
                label = ov["semantic_verdict"].strip(); label_src = "override"
            elif vr is not None and vs == e["session"]:
                label = label_of(vr); label_src = "verification"
            elif vr is not None and vs is not None and same_patch(e, vs):
                # a different execution was reviewed, but it produced the
                # byte-identical patch, so the label applies to this one too
                label = label_of(vr); label_src = "verification (identical patch)"
            elif vr is not None and not plaus:
                label = "N/A (not plausible)"; label_src = "n/a"
            if plaus and not label.startswith(("Correct", "Overfitting", "Incorrect")):
                pending[arm].append(b)
                label = "PENDING"; label_src = "none"
            # the patch the loop finally accepted ("delivered") may differ from
            # the first plausible candidate when the Judge withheld acceptance
            first_txt = _norm_text(r.get("plausible_patch") or "")
            final_txt = _norm_text(r.get("patch") or "")
            delivered_label = ""
            if accepted:
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
                label=label, label_src=label_src,
                correct=plaus and is_correct_label(label),
                overfit=plaus and label == "Overfitting",
                delivered_differs=bool(accepted and final_txt and final_txt != first_txt),
                delivered_label=delivered_label,
                delivered_correct=accepted and is_correct_label(delivered_label),
                first_txt=first_txt, row=r,
                iterations=int(fnum(r.get("iterations"))),
                plausible_iteration=int(fnum(r.get("plausible_iteration"), -1)),
                tokens=int(fnum(r.get("total_tokens"))), usd=fnum(r.get("estimated_usd")),
                secs=fnum(r.get("time_seconds")), baseline_failing=int(fnum(r.get("baseline_failing_count"))),
                project=b.rsplit("_", 1)[0],
            )
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
                                r.get("plausible_patch") or r.get("patch") or ""])
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
    for arm in ARMS:
        if pending[arm]:
            P(f"**PENDING verification under rule `{args.rule}` in `{arm}`: "
              f"{', '.join(pending[arm])}** — plausible, but the canonical patch was never reviewed. "
              f"Not counted as correct until a label is supplied via --overrides.\n")

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
    strict = sum(v for k, v in labs.items() if k in ("Correct (identical)", "Correct (equivalent)"))
    P(f"\nfull arm label split: {dict(labs)}; strict correct (identical + equivalent) = {strict}, "
      f"lenient (plus alternative) = {len(S_co['full'])}; strict precision = {100*strict/len(S_pl['full']):.1f}%\n")

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

    # ── 4c. resampling control from single-attempt runs ───────────────────
    sample_dirs = args.samples or sorted(glob.glob(os.path.join(args.raw, "results_arm_sample_*")))
    if sample_dirs:
        P("## 4c. Equal-budget control: independent single attempts (best-of-k resampling)\n")
        text_label = {}
        for arm in ARMS:
            for b in evaluable:
                x = rec[arm][b]
                if x["plausible"] and x["label"] not in ("PENDING", ""):
                    text_label[(b, x["first_txt"])] = x["label"]
        samples = []
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
            vpath_s = find_verification(args.raw, name, explicit)
            ver_s = load_verification(vpath_s)
            info = {}
            agree = disagree = 0; disagreements = []
            for b in evaluable:
                e = cs.get(b)
                if not e or e["excluded"]:
                    info[b] = dict(plausible=False, label="", txt="", excluded=True); continue
                r = e["row"]; pl = truthy(r.get("plausible")); txt = _norm_text(r.get("plausible_patch") or r.get("patch") or "")
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
                    if vlab and tlab:
                        if is_correct_label(vlab) == is_correct_label(tlab): agree += 1
                        else: disagree += 1; disagreements.append(f"{b} ({vlab} vs arm {tlab})")
                info[b] = dict(plausible=pl, label=lab, txt=txt, excluded=False, row=r, src=src)
            samples.append((temp, name, info))
            if vpath_s:
                P(f"- `{name}`: verification file `{vpath_s}`; textually identical to a labelled arm patch for {agree + disagree} bugs, "
                  f"label agreement {agree}/{agree + disagree}" + (f"; disagreements: {', '.join(disagreements)}" if disagreements else ""))
        P()
        samples.sort(key=lambda t: (t[0], t[1]))
        P("| sample | temperature | evaluable bugs run | plausible | correct | strict correct (identical+equivalent) | pending labels | label sources |")
        P("|---|---|---|---|---|---|---|---|")
        pending_rows = []
        for temp, name, info in samples:
            run = sum(1 for b in evaluable if not info[b]["excluded"])
            pl = sum(1 for b in evaluable if info[b]["plausible"])
            co = sum(1 for b in evaluable if info[b]["plausible"] and is_correct_label(info[b]["label"]))
            st = sum(1 for b in evaluable if info[b]["plausible"] and info[b]["label"] in ("Correct (identical)", "Correct (equivalent)"))
            pe = [b for b in evaluable if info[b]["plausible"] and info[b]["label"] == "PENDING"]
            srcs = Counter(info[b].get("src", "") for b in evaluable if info[b]["plausible"])
            for b in pe:
                pending_rows.append((name, b, info[b]["row"].get("plausible_patch") or info[b]["row"].get("patch") or ""))
            P(f"| {name} | {temp} | {run} | {pl} | {co} | {st} | {len(pe)} | {dict(srcs)} |")
        if pending_rows:
            with open(os.path.join(args.outdir, "pending_sample_labels.csv"), "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh); w.writerow(["sample", "bug_id", "patch"]); w.writerows(pending_rows)
            P(f"\n{len(pending_rows)} sample patches have no label yet (no textually identical labelled patch in the four arms): "
              f"see `{args.outdir}/pending_sample_labels.csv`; add rows with arm=<sample name> to --overrides.")
        P("\nBest-of-k in temperature order (first plausible sample wins):\n")
        P("| k | samples | plausible | correct | strict correct | pending | vs full: plausible full-only/ctrl-only, p | correct, p | vs no_judge: plausible, p | correct, p |")
        P("|---|---|---|---|---|---|---|---|---|---|")
        ctrl_sets = {}
        for k in range(1, len(samples) + 1):
            c_pl = set(); c_co = set(); c_pe = set(); c_st = set()
            for b in evaluable:
                for temp, name, info in samples[:k]:
                    if info[b]["plausible"]:
                        c_pl.add(b)
                        if is_correct_label(info[b]["label"]): c_co.add(b)
                        elif info[b]["label"] == "PENDING": c_pe.add(b)
                        if info[b]["label"] in ("Correct (identical)", "Correct (equivalent)"): c_st.add(b)
                        break
            ctrl_sets[k] = (c_pl, c_co)
            x, y, n, pp = mcnemar_exact(S_pl["full"], c_pl); x2, y2, n2, pc = mcnemar_exact(S_co["full"], c_co)
            x3, y3, n3, pp3 = mcnemar_exact(S_pl["no_judge"], c_pl); x4, y4, n4, pc4 = mcnemar_exact(S_co["no_judge"], c_co)
            P(f"| {k} | {', '.join(nm for _, nm, _ in samples[:k])} | {len(c_pl)} | {len(c_co)} | {len(c_st)} | {len(c_pe)} | "
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
            P(f"\ncontrol cost over the {kmax} samples: {int(tk):,} tokens, ${us:.2f} (${us/len(evaluable):.4f} per bug)")
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
    P("## 6. Iteration at which the accepted patch was produced (full arm)\n")
    c = Counter(rec["full"][b]["plausible_iteration"] for b in S_acc["full"])
    tot = sum(c.values()); run = 0
    P("| attempt | accepted patches | share | cumulative |")
    P("|---|---|---|---|")
    for k in sorted(c):
        run += c[k]
        P(f"| {k+1 if k >= 0 else 'unrecorded'} | {c[k]} | {100*c[k]/tot:.1f}% | {100*run/tot:.1f}% |")
    P(f"\nmean iterations, full arm, all evaluable bugs: "
      f"{sum(rec['full'][b]['iterations'] for b in evaluable)/len(evaluable):.2f}\n")

    # ── 6b. adaptive-mechanism activity ────────────────────────────────────
    P("## 6b. Adaptive-mechanism activity (repair steps after a failed attempt)\n")
    P("| arm | later repair steps | temperature > 0.1 | at 0.45 | at 0.85 (surgical mode) | other levels | bugs reaching surgical mode | regenerations after unusable output | no-op echoes |")
    P("|---|---|---|---|---|---|---|---|---|")
    for arm in ARMS:
        tot = esc = t45 = t85 = oth = rej = noop = 0; surg_bugs = set(); levels = Counter()
        for b in evaluable:
            for e in _history(rec[arm][b]["row"]):
                if e.get("action") != "repair" or str(e.get("iteration")) == "0":
                    continue
                md = e.get("metadata") or {}
                tot += 1; t = _step_temperature(md)
                if t is not None and t > 0.1001:
                    esc += 1; levels[round(t, 2)] += 1
                    if abs(t - 0.45) < 1e-6: t45 += 1
                    elif abs(t - 0.85) < 1e-6: t85 += 1; surg_bugs.add(b)
                    else: oth += 1
                if (md.get("generation_rejected") or "").strip(): rej += 1
                if truthy(md.get("noop_detected")): noop += 1
        P(f"| {arm} | {tot} | {esc} ({100*esc/max(tot,1):.0f}%) | {t45} | {t85} | {oth} | {len(surg_bugs)} | {rej} | {noop} |")
    P("\n(the 0.45 level is the no-op rule plus the near-identical-and-failed rule firing together on a "
      "localized edit; 0.85 is surgical mode, reachable only at the fourth attempt)\n")

    # ── 7. cost ────────────────────────────────────────────────────────────
    P("## 7. Cost and time (canonical executions, evaluable set)\n")
    P("| arm | total tokens | total USD | mean USD/bug | mean s/bug | mean s (accepted) | mean s (not plausible) |")
    P("|---|---|---|---|---|---|---|")
    for arm in ARMS:
        xs = [rec[arm][b] for b in evaluable]
        tk = sum(x["tokens"] for x in xs); us = sum(x["usd"] for x in xs); sc = sum(x["secs"] for x in xs)
        acc = [x["secs"] for x in xs if x["accepted"]]; npl = [x["secs"] for x in xs if not x["plausible"]]
        P(f"| {arm} | {tk:,} | ${us:.2f} | ${us/len(xs):.4f} | {sc/len(xs):.0f} | "
          f"{sum(acc)/len(acc) if acc else 0:.0f} | {sum(npl)/len(npl) if npl else 0:.0f} |")
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
    P("| arm | bugs with extra baseline failures | extra failing tests in total | per project (bugs) |")
    P("|---|---|---|---|")
    for arm in ARMS:
        n = 0; tot = 0; per_p = Counter()
        for b in evaluable:
            r = rec[arm][b]["row"]; extra = rec[arm][b]["baseline_failing"] - len(triggers_of(r))
            if extra > 0:
                n += 1; tot += extra; per_p[b.rsplit("_", 1)[0]] += 1
        P(f"| {arm} | {n} | {tot} | " + ", ".join(f"{pr} {per_p[pr]}" for pr in PROJECTS) + " |")
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
    for col in ("Independent review 2 (blind)", "Independent review 3 (blind)"):
        pairs = []; dis = []
        for b in S_pl["full"]:
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

    # ── 10. judge pilot ────────────────────────────────────────────────────
    if args.judge_swap:
        P("## 10. Offline judge pilot vs human labels (full arm, plausible set)\n")
        gt = {b: ("correct" if rec["full"][b]["correct"] else "bad")
              for b in S_pl["full"] if rec["full"][b]["label"] != "PENDING"}
        P("| model | judged | vetoed | bad caught | correct wrongly vetoed | veto precision | κ vs human [95% bootstrap CI] | not canonical |")
        P("|---|---|---|---|---|---|---|---|")
        for path in args.judge_swap:
            rows = {}
            for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
                rows[r["bug_id"]] = r
            rows = {b: r for b, r in rows.items() if r.get("second_verdict") not in ("error", "", None)}
            model = os.path.basename(path).replace("judge_swap_", "").replace(".csv", "")
            scored = [(b, "correct" if r["second_verdict"] == "correct" else "bad", gt[b])
                      for b, r in rows.items() if b in gt]
            bad = [s for s in scored if s[2] == "bad"]; good = [s for s in scored if s[2] == "correct"]
            caught = sum(1 for _, m, _h in bad if m == "bad"); fv = sum(1 for _, m, _h in good if m == "bad")
            vet = sum(1 for _, m, _h in scored if m == "bad")
            # the pilot judged each bug's NEWEST recorded patch; flag bugs where
            # that text differs from the canonical execution's patch
            notcanon = []
            for b in rows:
                e = can["full"].get(b)
                if not e or e["excluded"] or b not in gt:
                    continue
                newest = e["completed_all"][-1][1] if e["completed_all"] else None
                if newest is not None and _patch_text(newest) != _patch_text(e["row"]):
                    notcanon.append(b)
            missing = sorted(set(gt) - set(rows))
            kp = [(m, h) for _, m, h in scored]; lo, hi = bootstrap_kappa(kp)
            P(f"| {model} | {len(scored)} | {vet} | {caught}/{len(bad)} | {fv}/{len(good)} | "
              f"{caught}/{vet if vet else 1} | {kappa(kp):.3f} [{lo:.2f}, {hi:.2f}] | "
              f"{len(notcanon)} ({', '.join(notcanon)}) |")
            if missing:
                P(f"  - not judged: {', '.join(missing)}")
            if notcanon or missing:
                P(f"  - re-judge on the canonical patches: {', '.join(sorted(set(notcanon) | set(missing)))}")
        P()

    # ── 11. counts under the other rule, for the appendix ─────────────────
    P("## 11. Sensitivity to the repeated-execution rule (full arm)\n")
    for rule in ("first", "last"):
        c2 = canonical(per["full"], rule)
        pl = co = pend = 0
        for b in evaluable:
            e = c2[b]
            if e["excluded"]: continue
            r = e["row"]; plaus = truthy(r.get("plausible"))
            if not plaus: continue
            pl += 1
            vr = ver["full"].get(b); vs = verified_session(b, e, vr)
            ov = overrides.get("full", {}).get(b)
            lab = ov["semantic_verdict"].strip() if ov else (
                label_of(vr) if (vr and (vs == e["session"] or (vs and same_patch(e, vs)))) else "")
            if is_correct_label(lab): co += 1
            elif not lab.startswith(("Overfitting", "Incorrect")): pend += 1
        P(f"- rule `{rule}`: plausible={pl}, correct={co}, pending={pend}")
    strict_pl = sum(1 for b in evaluable if can["full"][b]["completed"] and
                    all(truthy(r.get("plausible")) for _, r in can["full"][b]["completed"]))
    P(f"- strict (plausible in every execution): plausible={strict_pl}\n")
    P(f"canonical per-bug tables written to `{args.outdir}/canonical_<arm>.csv`")


if __name__ == "__main__":
    main()
