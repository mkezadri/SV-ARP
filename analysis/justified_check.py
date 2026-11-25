"""Which plausible records of the corrected Binary-Only and No-Judge executions
have a label backed by a written justification?

A label is backed when the record itself was labelled with a note (override row
with a note), or when a record with the identical complete patch text (Java
token sequence) carries a label with a written justification: Full, No-Semantic
and the control passes (verification files with notes), and override rows with
a note. The October Binary-Only and No-Judge verification files hold labels
without notes, so they back nothing by themselves.

It also counts the records labelled in November (the corrected executions of
Binary-Only and No-Judge, and the bugs of a list given as third argument, in
Full, No-Semantic and the control passes): those labelled on their own text
(an override row with a reason of its own) and those that take the label of an
identical labelled text.

usage, from the repository folder, after the preparation steps of the README:
    python3 analysis/justified_check.py data data/canonical benchmark/mockito_gradle_15.txt
(RAW_DIR CANON_DIR [BUG_LIST [VERIFICATION_DIR]]; the verification files, the
second verification and overrides_all.csv are read from RAW_DIR unless a
fourth argument names another folder)
"""
import csv
import glob
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_figures as mf  # noqa: E402

csv.field_size_limit(10 ** 9)
RAW, CANON = sys.argv[1], sys.argv[2]
BUG_LIST = sys.argv[3] if len(sys.argv) > 3 else None
VER = sys.argv[4] if len(sys.argv) > 4 else RAW
NOTE_COLS = ("Reviewer notes", "Review 3 rationale", "Execution evidence (2026-11-09)",
             "Execution re-check (JDK 21)", "Verification notes", "Re-verification", "Log audit notes")
REAL = ("Correct", "Overfitting", "Incorrect")


def notes_of(row):
    return " ".join((row.get(c) or "").strip() for c in NOTE_COLS if row and (row.get(c) or "").strip())


ov_s, ov_u = {}, defaultdict(dict)
PROVENANCE_ONLY = ("Patch of the re-execution of 10 November 2026",)
for r in csv.DictReader(open(os.path.join(VER, "overrides_all.csv"), encoding="utf-8")):
    if (r.get("note") or "").startswith(PROVENANCE_ONLY):
        r = dict(r, note="")
    if (r.get("which") or "first").strip() == "delivered":
        continue
    if (r.get("session") or "").strip():
        ov_s[(r["arm"], r["bug_id"], r["session"])] = r
    else:
        ov_u[r["arm"]][r["bug_id"]] = r

justified = defaultdict(dict)      # bug -> {text: where}


def add(b, text, where):
    if text:
        justified[b].setdefault(text, where)


# Full and No-Semantic: canonical records of the report, notes from either verification file
recs = {}
for arm in mf.ARMS:
    per, _ = mf.load_arm(RAW, arm)
    recs[arm] = per
for arm in ("full", "no_semantic"):
    v1 = mf.load_verification(os.path.join(VER, f"verification_{arm}.csv"))
    v2 = mf.load_verification(os.path.join(VER, "second_verification", f"verification_{arm}.csv"))
    for t in csv.DictReader(open(os.path.join(CANON, f"canonical_{arm}.csv"), encoding="utf-8")):
        if t.get("plausible") != "True" or not (t.get("semantic_label") or "").startswith(REAL):
            continue
        b, s = t["bug_id"], t["session"]
        row = next((r for ss, r in recs[arm][b] if ss == s), None)
        if row is None:
            continue
        o = ov_s.get((arm, b, s)) or ov_u[arm].get(b)
        has = bool((o or {}).get("note", "").strip()) if o else bool(notes_of(v1.get(b)) or notes_of(v2.get(b)))
        if has:
            add(b, mf._patch_text(row), f"{arm} {s}")

# control passes
for d in sorted(glob.glob(os.path.join(RAW, "results_arm_sample_*"))):
    name = os.path.basename(d).replace("results_arm_", "")
    per = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(d, "results_*.csv")), key=mf.session_key):
        s = mf.session_key(f)
        for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
            per[(r.get("bug_id") or "").strip()].append((s, r))
    cs = mf.canonical(per, "first")
    ver = mf.load_verification(os.path.join(VER, f"verification_{name}.csv"))
    for b, e in cs.items():
        if not e or e["excluded"] or not mf.truthy(e["row"].get("plausible")):
            continue
        o = ov_u[name].get(b)
        if (o and o.get("note", "").strip()) or notes_of(ver.get(b)):
            add(b, mf._patch_text(e["row"]), f"control {name}")

# records labelled in November with a note, and unbound overrides of the October records
for (arm, b, s), o in ov_s.items():
    if o.get("note", "").strip():
        row = next((r for ss, r in recs.get(arm, {}).get(b, []) if ss == s), None)
        if row is not None:
            add(b, mf._patch_text(row), f"{arm} {s} (November label)")
for arm in ("binary_only", "no_judge"):
    for b, o in ov_u[arm].items():
        if not o.get("note", "").strip():
            continue
        for s, r in recs[arm].get(b, []):
            if mf.valid_completed(r) and mf.truthy(r.get("plausible")) and s < "20261101":
                add(b, mf._patch_text(r), f"{arm} {s} (override with note)")
                break

for arm in ("binary_only", "no_judge"):
    rows = [t for t in csv.DictReader(open(os.path.join(CANON, f"canonical_{arm}.csv"), encoding="utf-8"))
            if t.get("plausible") == "True"]
    unbacked = []
    for t in rows:
        b, s = t["bug_id"], t["session"]
        row = next(r for ss, r in recs[arm][b] if ss == s)
        txt = mf._patch_text(row)
        if txt not in justified.get(b, {}):
            unbacked.append((b, t["semantic_label"], t["label_source"]))
    print(f"{arm}: plausible {len(rows)}; backed by a written justification {len(rows) - len(unbacked)}; "
          f"not backed {len(unbacked)}")
    for u in unbacked:
        print("   ", *u)


# ── records labelled in November: on their own text, or by an identical labelled text ──
def own_reason(o):
    note = (o or {}).get("note", "").strip()
    return bool(note) and not note.startswith("Same patch text")


print()
tot = [0, 0]
for arm in ("binary_only", "no_judge"):
    rows = [t for t in csv.DictReader(open(os.path.join(CANON, f"canonical_{arm}.csv"), encoding="utf-8"))
            if t.get("plausible") == "True"]
    own = sum(own_reason(ov_s.get((arm, t["bug_id"], t["session"]))) for t in rows)
    tot[0] += own
    tot[1] += len(rows) - own
    print(f"{arm}: plausible {len(rows)}; labelled on their own text {own}; label of an identical labelled text {len(rows) - own}")
print(f"the two corrected executions: plausible {sum(tot)}; labelled on their own text {tot[0]}; label of an identical labelled text {tot[1]}")

if BUG_LIST:
    bugs = set(open(BUG_LIST, encoding="utf-8").read().split())
    n = own = 0
    for arm in ("full", "no_semantic"):
        for t in csv.DictReader(open(os.path.join(CANON, f"canonical_{arm}.csv"), encoding="utf-8")):
            if t.get("plausible") == "True" and t["bug_id"] in bugs:
                n += 1
                own += own_reason(ov_s.get((arm, t["bug_id"], t["session"])))
    for d in sorted(glob.glob(os.path.join(RAW, "results_arm_sample_*"))):
        name = os.path.basename(d).replace("results_arm_", "")
        per = defaultdict(list)
        for f in sorted(glob.glob(os.path.join(d, "results_*.csv")), key=mf.session_key):
            for r in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
                per[(r.get("bug_id") or "").strip()].append((mf.session_key(f), r))
        for b, e in mf.canonical(per, "first").items():
            if b in bugs and e and not e["excluded"] and mf.truthy(e["row"].get("plausible")):
                n += 1
                own += own_reason(ov_u[name].get(b))
    print(f"the {len(bugs)} bugs of {os.path.basename(BUG_LIST)} in full, no_semantic and the control passes: "
          f"plausible records {n}; labelled on their own text {own}; label of an identical labelled text {n - own}")
