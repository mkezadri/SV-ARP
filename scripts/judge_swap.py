#!/usr/bin/env python3
"""
Offline review of test-passing patches by a second model.

Replays the Judge prompt of the full system against another model, through any
OpenAI-compatible endpoint, on the plausible patches of one configuration, and
records the verdicts. No repair and no test execution: only the review is run.
The buggy file is read from a Defects4J checkout (D4J_HOME must be set) and
cached; for a bug that modifies several files the reviewer is shown the first
modified file only, as the in-loop Judge is.

    CAN=data/canonical/canonical_full.csv     # written by analysis/make_figures.py
    # keys are read from the environment only: --api-key-env names the variable

    # Gemini 3.5 Flash Lite (the in-loop model, run offline)
    python3 scripts/judge_swap.py results_arm_full --canonical $CAN \
        --model gemini-3.5-flash-lite \
        --base-url https://generativelanguage.googleapis.com/v1beta/openai/ \
        --api-key-env GEMINI_API_KEY

    # Claude Sonnet 5.5. The model rejects a temperature setting, so none is sent,
    # and it reasons before answering, so the output limit is set explicitly.
    python3 scripts/judge_swap.py results_arm_full --canonical $CAN \
        --model claude-sonnet-5-5 --base-url https://api.anthropic.com/v1/ \
        --api-key-env ANTHROPIC_API_KEY --temperature default --max-tokens 16000

    Add --limit 5 for a smoke test. For a long run, start it in the background so
    that it survives a closed terminal, and follow the log:
        nohup python3 -u scripts/judge_swap.py ... > review.log 2>&1 &
        tail -f review.log

--prompt-mode
    identical : the in-loop prompt, byte for byte. Rule 1 says a passing
                patch MUST be judged correct, so on plausible patches this
                measures instruction-following, not judgement.
    semantic  : the same prompt with the test result presented as evidence
                rather than a mandate. Measures whether the reviewer can tell an
                overfitting patch from a real fix. This is the mode of the paper.

--canonical
    The canonical per-bug table of the configuration. The patch judged for each
    bug is the one of its canonical execution. Without the table the newest
    record of each bug is judged. The session of the judged record is written to
    the output in both cases, and the analysis scores a verdict only if that
    record's patch is the canonical one.

--ground-truth
    A verification CSV to score against, for a first look. The figures of the
    paper are computed by analysis/make_figures.py (--judge-swap) against the
    final labels.

Output: judge_swap_<model>_<mode>.csv  +  a summary. Resumable: a patch text
that already has a verdict in the output file is not judged again (the first
verdict on a text stands); an error is retried.
"""
import argparse, csv, glob, json, os, re, subprocess, sys, tempfile, time, collections, difflib, shutil

csv.field_size_limit(10**9)


RULES_IDENTICAL = (
    "DECISION RULES\n"
    "1. PASS → verdict MUST be 'correct' (unless compilation failed).\n"
    "2. FAIL → 'incorrect' (wrong direction) or 'needs_revision' "
    "(right direction, structural problem).\n"
    "3. NOT_RUN → evaluate structural integrity only.\n\n"
)

# Same prompt, but the test result is evidence rather than a verdict. Without
# this change every plausible patch is accepted by instruction and the pilot
# measures nothing.
RULES_SEMANTIC = (
    "DECISION RULES\n"
    "1. The test result is evidence, not a verdict. A patch that passes the "
    "tests may still be wrong: it may special-case the failing inputs, "
    "suppress the symptom, or fix a different defect than the one the "
    "tests expose. Judge the patch against the developer intent visible in "
    "the code and the trigger tests.\n"
    "2. 'correct'        → fixes the underlying defect in a way a maintainer "
    "would accept.\n"
    "3. 'incorrect'      → passes the tests but does not fix the defect "
    "(overfits the tests or masks the symptom).\n"
    "4. 'needs_revision' → right direction, but incomplete or structurally "
    "flawed.\n\n"
)


def build_prompt(original, patched, test_status, test_output, diff_text,
                 rules=RULES_IDENTICAL):
    """With rules=RULES_IDENTICAL this is byte-identical to
    JudgeAgent.evaluate_patch; with RULES_SEMANTIC only the rules block differs."""
    return (
        "You are a Principal Software Engineer reviewing an automated patch.\n\n"
        "══════════════════════════\nORIGINAL FILE\n══════════════════════════\n"
        f"```java\n{original}\n```\n\n"
        "══════════════════════════\nPATCHED FILE\n══════════════════════════\n"
        f"```java\n{patched}\n```\n\n"
        "══════════════════════════\nUNIFIED DIFF (original → patch)\n══════════════════════════\n"
        f"```diff\n{diff_text or '(diff not available)'}\n```\n\n"
        f"══════════════════════════\nTEST STATUS: {test_status}\n══════════════════════════\n"
        f"{test_output}\n\n"
        + rules +
        "CRITICAL: Each 'suggestions' entry MUST follow EXACTLY this format:\n"
        "  'In [MethodName](): change [exact original code fragment] to "
        "[exact replacement code] because [specific reason]'\n"
        "  BAD (forbidden): 'Investigate the getLine() method'.\n\n"
        "Return ONLY a JSON object (no markdown):\n"
        "{\n"
        '  "verdict": "correct" | "incorrect" | "needs_revision",\n'
        '  "reason": "one paragraph",\n'
        '  "issues": ["specific issue 1"],\n'
        '  "suggestions": ["In X(): change Y to Z because ..."],\n'
        '  "problematic_lines": [123, 456]\n'
        "}"
    )


D4J = os.environ.get("D4J_HOME", "")
BIN = os.path.join(D4J, "framework", "bin", "defects4j") if D4J else "defects4j"


# Scratch space goes under WORK_ROOT, the same place the runs use (/tmp proved
# unreliable on the machine of the published runs).
SCRATCH = os.path.join(os.environ.get("WORK_ROOT", os.path.expanduser("~/apr_work")),
                       "judge_swap")


def original_source(bug_id, modified_classes, cache=None):
    """Check out the BUGGY version and return the source of the modified class.

    Without this the second judge sees only the patched file and reviews the
    whole file blind — it cannot tell which lines are the patch, and invents
    defects in pre-existing code.
    """
    cache = cache or os.path.join(SCRATCH, "orig")
    os.makedirs(cache, exist_ok=True)
    cp = os.path.join(cache, bug_id + ".java")
    if os.path.exists(cp):
        return open(cp, encoding="utf-8", errors="replace").read()

    proj, num = bug_id.rsplit("_", 1)
    cls = (modified_classes or "").split("|")[0].split(",")[0].strip().strip("[]'\" ")
    if not cls:
        return ""
    os.makedirs(SCRATCH, exist_ok=True)
    w = tempfile.mkdtemp(prefix=f"js_{bug_id}_", dir=SCRATCH)
    try:
        r = subprocess.run([BIN, "checkout", "-p", proj, "-v", f"{num}b", "-w", w],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return ""
        sd = subprocess.run([BIN, "export", "-p", "dir.src.classes"], cwd=w,
                            capture_output=True, text=True, timeout=120)
        srcdir = [l.strip() for l in sd.stdout.splitlines() if l.strip()
                  and not l.startswith("Running")]
        srcdir = srcdir[-1] if srcdir else "src"
        path = os.path.join(w, srcdir, cls.replace(".", "/") + ".java")
        if not os.path.exists(path):
            hits = glob.glob(os.path.join(w, "**", cls.split(".")[-1] + ".java"),
                             recursive=True)
            if not hits:
                return ""
            path = hits[0]
        txt = open(path, encoding="utf-8", errors="replace").read()
        open(cp, "w", encoding="utf-8").write(txt)
        return txt
    finally:
        shutil.rmtree(w, ignore_errors=True)


def session_of(path):
    m = re.search(r"results_(\d{8}_\d{6})", os.path.basename(path))
    return m.group(1) if m else os.path.basename(path)


def load_canonical(path):
    """bug_id -> session of the canonical execution, for the bugs whose canonical
    execution produced a plausible patch (per-bug table of analysis/make_figures.py)."""
    can = {}
    for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
        b = (r.get("bug_id") or "").strip()
        if not b or (r.get("excluded") or "").strip():
            continue
        if (r.get("plausible") or "").strip() != "True":
            continue
        ses = (r.get("session") or "").strip()
        if not ses:
            sys.exit(f"{path}: no session recorded for {b}")
        can[b] = ses
    return can


def load_results(d, canonical=None):
    """bug_id -> the record whose patch is judged.

    With the canonical table: the record of the canonical session of every bug
    listed there. Without it: the record of the newest session that contains
    the bug."""
    per = collections.defaultdict(dict)
    for f in sorted(glob.glob(os.path.join(d, "**", "results_*.csv"), recursive=True)):
        ses = session_of(f)
        for x in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
            b = x.get("bug_id")
            if b:
                x["_session"] = ses
                per[b].setdefault(ses, x)
    best = {}
    if canonical is None:
        for b, by in per.items():
            best[b] = by[max(by)]
    else:
        for b, ses in canonical.items():
            if ses not in per.get(b, {}):
                sys.exit(f"{b}: no record of session {ses} under {d} "
                         "(the canonical table and the result files do not match)")
            best[b] = per[b][ses]
    return best, per


VERDICTS = ("correct", "incorrect", "needs_revision")


def parse_review(txt, finish_reason=None):
    """(verdict, reason) from the reviewer's answer. The answer is a JSON object;
    text around it is dropped, and an object that states one verdict but does
    not parse (a stray backslash or quote in the rationale) is read by its
    verdict field. Anything else raises ValueError."""
    txt = txt.replace("```json", "").replace("```", "").strip()
    a, z = txt.find("{"), txt.rfind("}")
    for cand in [txt] + ([txt[a:z + 1]] if 0 <= a < z else []):
        try:
            parsed = json.loads(cand)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            v = str(parsed.get("verdict", "")).strip().lower()
            if v not in VERDICTS:
                raise ValueError(f"unexpected verdict {v!r}")
            return v, str(parsed.get("reason", ""))[:300]
    found = {v.lower() for v in re.findall(r'"verdict"\s*:\s*"([A-Za-z_]+)"', txt)}
    if len(found) == 1 and next(iter(found)) in VERDICTS:
        m = re.search(r'"reason"\s*:\s*"(.*?)"\s*,\s*"issues"', txt, flags=re.S)
        return next(iter(found)), (m.group(1) if m else "(rationale not parseable)")[:300]
    raise ValueError(f"no usable JSON object in the response (finish_reason={finish_reason})")


def patched_text(r):
    """The patch text shown to the reviewer for a record."""
    return (r.get("plausible_patch") or "").strip() or (r.get("patch") or "")


def judged_text(row, per):
    """The patch text an earlier output row was given on, or None if its record
    is not among the result files."""
    rec = per.get(row.get("bug_id"), {}).get((row.get("session") or "").strip())
    return patched_text(rec) if rec is not None else None


def final_judge_step(rec):
    h = rec.get("history") or "[]"
    if isinstance(h, str):
        try: h = json.loads(h)
        except Exception: return None
    js = [s for s in h if isinstance(s, dict) and s.get("action") == "judge"]
    return js[-1] if js else None


def kappa(pairs):
    """Cohen's kappa over (a, b) label pairs."""
    n = len(pairs)
    if not n: return 0.0
    labels = sorted({x for p in pairs for x in p})
    po = sum(1 for a, b in pairs if a == b) / n
    ca = collections.Counter(a for a, _ in pairs)
    cb = collections.Counter(b for _, b in pairs)
    pe = sum((ca[l]/n) * (cb[l]/n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def load_ground_truth(path):
    """bug_id -> 'correct' | 'bad', from the human verification CSV."""
    gt = {}
    for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
        b = (r.get("Bug_id") or r.get("bug_id") or "").strip()
        v = (r.get("Reviewer Semantic verdict") or "").strip()
        if not b or not v or v.startswith("N/A"):
            continue
        # only patches the suite accepted: that is the set being judged
        if (r.get("Logged plausible by the suite") or "Yes").strip() != "Yes":
            continue
        gt[b] = "correct" if v.startswith("Correct") else "bad"
    return gt


def score_against_humans(rows, gt, model):
    """Treat the model as a classifier: did it veto the patches humans found bad?"""
    scored = [(r["bug_id"], "correct" if r["second_verdict"] == "correct" else "bad",
               gt[r["bug_id"]]) for r in rows if r["bug_id"] in gt]
    if not scored:
        print("\nno rows overlap the ground truth"); return
    n = len(scored)
    bad = [s for s in scored if s[2] == "bad"]
    good = [s for s in scored if s[2] == "correct"]
    caught = sum(1 for _, m, _h in bad if m == "bad")
    false_veto = sum(1 for _, m, _h in good if m == "bad")
    pairs = [(m, h) for _, m, h in scored]
    print(f"\n=== {model} vs HUMAN verification, {n} plausible patches ===")
    print(f"human: {len(good)} correct, {len(bad)} bad (overfitting/incorrect)")
    print(f"model vetoed                 : {sum(1 for _, m, _h in scored if m == 'bad')}")
    print(f"bad patches caught           : {caught}/{len(bad)}"
          f"  ({100*caught/len(bad):.0f}% recall)" if bad else "")
    print(f"correct patches wrongly vetoed: {false_veto}/{len(good)}"
          f"  ({100*false_veto/len(good):.1f}%)" if good else "")
    vet = [s for s in scored if s[1] == "bad"]
    if vet:
        print(f"precision of a veto          : {sum(1 for s in vet if s[2]=='bad')}/{len(vet)}")
    print(f"Cohen's kappa vs human       : {kappa(pairs):.3f}")
    print("\nbad patches the model MISSED:",
          ", ".join(b for b, m, _h in bad if m == "correct") or "none")
    print("correct patches it VETOED   :",
          ", ".join(b for b, m, _h in good if m == "bad") or "none")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument("--base-url", default=os.environ.get("JUDGE_BASE_URL", ""),
                    help="OpenAI-compatible endpoint (default: $JUDGE_BASE_URL)")
    ap.add_argument("--canonical", default=None,
                    help="canonical per-bug table (data/canonical/canonical_<configuration>.csv)")
    ap.add_argument("--out", default=None,
                    help="default: judge_swap_<model>_<mode>.csv")
    ap.add_argument("--api-key-env", default="JUDGE_API_KEY",
                    help="env var holding the key for --base-url")
    ap.add_argument("--prompt-mode", choices=["identical", "semantic"],
                    default="semantic")
    ap.add_argument("--ground-truth", default=None,
                    help="human verification CSV to score against")
    ap.add_argument("--retries", type=int, default=5,
                    help="attempts per patch before recording an error")
    ap.add_argument("--sleep", type=float, default=2.0,
                    help="seconds between calls, to stay under per-minute limits")
    ap.add_argument("--temperature", default="0.0",
                    help="sampling temperature; 'default' sends none, for models "
                         "that reject the parameter")
    ap.add_argument("--max-tokens", type=int, default=0,
                    help="output limit sent with each call; 0 sends none")
    ap.add_argument("--timeout", type=float, default=600.0,
                    help="seconds to wait for one answer before the call counts as failed")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--only-plausible", action="store_true", default=True)
    args = ap.parse_args()

    key = os.environ.get(args.api_key_env)
    if not key:
        sys.exit(f"set {args.api_key_env} in the environment")
    if not args.base_url:
        sys.exit("give --base-url (or set JUDGE_BASE_URL)")
    temperature = (None if args.temperature.strip().lower() in ("default", "none")
                   else float(args.temperature))
    if args.out is None:
        safe = "".join(c if c.isalnum() else "_" for c in args.model)
        args.out = f"judge_swap_{safe}_{args.prompt_mode}.csv"
    rules = RULES_SEMANTIC if args.prompt_mode == "semantic" else RULES_IDENTICAL
    gt = load_ground_truth(args.ground_truth) if args.ground_truth else {}

    from openai import OpenAI
    # no silent retries inside the client: every failed attempt is reported below
    client = OpenAI(api_key=key, base_url=args.base_url,
                    timeout=args.timeout, max_retries=0)

    canonical = load_canonical(args.canonical) if args.canonical else None
    best, per = load_results(args.results_dir, canonical)
    if canonical is None:
        print("note: no --canonical table; judging the newest record of each bug")
    else:
        odd = sorted(b for b, r in best.items() if r.get("plausible") != "True")
        if odd:
            sys.exit("the canonical table lists a plausible patch where the record has none: "
                     + ", ".join(odd))
    todo = [r for r in best.values()
            if (not args.only_plausible) or r.get("plausible") == "True"]
    todo.sort(key=lambda r: (r["bug_id"].rsplit("_", 1)[0],
                             int(r["bug_id"].rsplit("_", 1)[1])))

    FIELDS = ["bug_id", "project", "test_status", "gemini_verdict",
              "second_verdict", "agree", "second_reason", "seconds",
              "session", "prompt_tokens", "completion_tokens", "model_reported"]
    done = set()
    if os.path.exists(args.out):
        with open(args.out, newline="", encoding="utf-8", errors="replace") as fh0:
            rd = csv.DictReader(fh0)
            if "session" not in (rd.fieldnames or []):
                sys.exit(f"{args.out} was written by an earlier version of this script and "
                         "has no 'session' column; use the copy in data/offline_review/")
            prev = list(rd)
        # a patch text that already has a verdict is not judged again, whichever
        # execution it was first judged on: the first verdict on a text stands
        for r in prev:
            if r["second_verdict"] != "error":
                done.add((r["bug_id"], judged_text(r, per)))
        wanted = {(r["bug_id"], patched_text(r)) for r in todo}
        errs = sorted({r["bug_id"] for r in prev if r["second_verdict"] == "error"
                       and (r["bug_id"], judged_text(r, per)) in wanted - done})
        print(f"resuming — {len(done & wanted)} of {len(wanted)} already judged"
              + (f", retrying {len(errs)} error(s): {', '.join(errs)}" if errs else ""))
    todo = [r for r in todo if (r["bug_id"], patched_text(r)) not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"judging {len(todo)} patch(es) with {args.model}\n")

    new = not os.path.exists(args.out)
    fh = open(args.out, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    if new: w.writeheader()

    kwargs = {"model": args.model}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if args.max_tokens:
        kwargs["max_tokens"] = args.max_tokens
    judged_now = refused_now = 0
    print("request options:", {**kwargs, "base_url": args.base_url}, "\n")

    for i, r in enumerate(todo, 1):
        bug = r["bug_id"]
        step = final_judge_step(r)
        if not step:
            print(f"[{i}/{len(todo)}] {bug}: no judge step, skipped"); continue
        md = step.get("metadata") or {}
        status = md.get("test_status_observed") or "NOT_RUN"
        if r.get("plausible") == "True":
            # the patch judged is the first plausible candidate, which passed the
            # tests; the last Judge step may belong to a later, failing candidate
            status = "PASS"
        patched = patched_text(r)
        original = r.get("buggy_code") or original_source(
            bug, r.get("modified_classes", ""))
        if not original:
            print(f"[{i}/{len(todo)}] {bug}: could not recover original — SKIPPED")
            continue
        diff_text = "\n".join(difflib.unified_diff(
            original.splitlines(), patched.splitlines(),
            fromfile="original", tofile="patched", lineterm="", n=3))
        # The trigger tests failed BEFORE the patch. Labelling them plainly
        # "Failing tests:" next to "TEST STATUS: PASS" reads as a contradiction,
        # and the judge resolves it by inventing failures the patch supposedly
        # caused. Say explicitly which side of the patch each fact belongs to.
        test_summary = (
            f"Trigger tests for this bug (these FAILED on the ORIGINAL, "
            f"unpatched code): {r.get('failing_tests','')}\n"
            f"After applying the patch, the full relevant test suite result "
            f"is: {status}.\n"
            + ("All of the above trigger tests now pass and no other test "
               "regressed. Do not assume any test is failing.\n"
               if status == "PASS" else
               "At least one test is still failing.\n")
        )
        prompt = build_prompt(original, patched, status, test_summary, diff_text,
                              rules=rules)

        t0 = time.time()
        verdict, reason = "error", "no attempt"
        ptok = ctok = mrep = ""
        refused = False
        print(f"[{i}/{len(todo)}] {bug}: asking {args.model} "
              f"({len(prompt) // 1000}k characters, {time.strftime('%H:%M:%S')}) ...", flush=True)
        for attempt in range(args.retries):
            try:
                resp = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}], **kwargs)
                usage = getattr(resp, "usage", None)
                ptok = getattr(usage, "prompt_tokens", "") if usage else ""
                ctok = getattr(usage, "completion_tokens", "") if usage else ""
                mrep = getattr(resp, "model", "") or ""
                choice = resp.choices[0]
                txt = (choice.message.content or "").strip()
                if not txt:
                    raise ValueError(f"empty response (finish_reason={choice.finish_reason})")
                verdict, reason = parse_review(txt, choice.finish_reason)
                break
            except Exception as e:
                verdict = "error"
                err = str(e)
                reason = err[:200]
                # a request the endpoint refuses as such will be refused again
                if getattr(e, "status_code", None) in (400, 401, 403, 404, 422):
                    refused = True
                    print(f"    refused, not retried: {err[:160]}", flush=True)
                    break
                limited = "429" in err or "rate" in err.lower() or "quota" in err.lower()
                if attempt < args.retries - 1:
                    # rate limits need a real pause; everything else a short one
                    wait = (30 * (attempt + 1)) if limited else (5 * (attempt + 1))
                    print(f"    retry {attempt+1}/{args.retries} in {wait}s: {err[:80]}", flush=True)
                    time.sleep(wait)
        time.sleep(args.sleep)

        gem = r.get("verdict", "")
        row = {"bug_id": bug, "project": bug.rsplit("_", 1)[0],
               "test_status": status, "gemini_verdict": gem,
               "second_verdict": verdict, "agree": int(verdict == gem),
               "second_reason": reason, "seconds": round(time.time() - t0, 1),
               "session": r["_session"], "prompt_tokens": ptok,
               "completion_tokens": ctok, "model_reported": mrep}
        w.writerow(row); fh.flush()
        judged_now += verdict != "error"
        refused_now += refused
        if judged_now == 0 and refused_now >= 3:
            fh.close()
            sys.exit("\nthe endpoint refused the first three requests of this run; check the "
                     "model name, the key and the options (a model that rejects a temperature "
                     "setting needs --temperature default).\n" + reason)
        flag = "=" if row["agree"] else "≠"
        print(f"[{i}/{len(todo)}] {bug:14s} gemini={gem:15s} {args.model[:12]}={verdict:15s} {flag}"
              + (f"   tokens in/out {ptok}/{ctok}" if ptok != "" else ""), flush=True)

    fh.close()

    first = {}
    for r in csv.DictReader(open(args.out, encoding="utf-8", errors="replace")):
        b = r["bug_id"]
        if (r["second_verdict"] != "error" and b in best and b not in first
                and judged_text(r, per) == patched_text(best[b])):
            first[b] = r                            # the first verdict on a text stands
    rows = list(first.values())
    if not rows:
        print("\nno usable rows"); return
    pairs = [(r["gemini_verdict"], r["second_verdict"]) for r in rows]
    print(f"\n=== agreement with the IN-LOOP Gemini verdict, {len(rows)} patches ===")
    print(f"raw agreement : {100*sum(1 for a,b in pairs if a==b)/len(pairs):.1f}%")
    if len({a for a, _ in pairs}) < 2:
        print("Cohen's kappa : not reported — the in-loop verdict is constant "
              "(every plausible patch was accepted), so kappa is undefined")
    else:
        print(f"Cohen's kappa : {kappa(pairs):.3f}")
    print("\nconfusion (rows = Gemini, cols = second model):")
    labs = sorted({x for p in pairs for x in p})
    print(f'{"":16s}' + "".join(f"{l[:14]:>16s}" for l in labs))
    for a in labs:
        print(f"{a[:14]:16s}" + "".join(
            f"{sum(1 for x,y in pairs if x==a and y==b):16d}" for b in labs))
    gv = collections.Counter(a for a, _ in pairs)
    sv = collections.Counter(b for _, b in pairs)
    print(f"\nGemini vetoed (not 'correct'): {sum(v for k,v in gv.items() if k!='correct')}")
    print(f"{args.model} vetoed          : {sum(v for k,v in sv.items() if k!='correct')}")

    if gt:
        score_against_humans(rows, gt, args.model)


if __name__ == "__main__":
    main()
