#!/usr/bin/env python3
"""
Cross-model Judge pilot.

Replays the EXACT Judge prompt from the full-system run against a second model
(via any OpenAI-compatible endpoint) on the patches your Gemini judge already
ruled on, then reports agreement.

No repair, no test execution — the Judge is a pure function of
(patch, diff, test status), so only the judging step is re-run.

    export JUDGE_API_KEY=...               # read from the environment only
    export JUDGE_BASE_URL=https://<openai-compatible-endpoint>/v1
    python3 judge_swap.py results_arm_full --model deepseek-v4-flash

    # cheap smoke test first
    python3 judge_swap.py results_arm_full --model deepseek-v4-flash --limit 5

Output: judge_swap.csv  +  an agreement summary (Cohen's kappa, confusion matrix).
Resumable: re-running skips bugs already in the CSV.
"""
import argparse, csv, glob, json, os, subprocess, sys, tempfile, time, collections, difflib, shutil

csv.field_size_limit(10**9)


def build_prompt(original, patched, test_status, test_output, diff_text):
    """Byte-identical to JudgeAgent.evaluate_patch, so verdicts are comparable."""
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
        "DECISION RULES\n"
        "1. PASS → verdict MUST be 'correct' (unless compilation failed).\n"
        "2. FAIL → 'incorrect' (wrong direction) or 'needs_revision' "
        "(right direction, structural problem).\n"
        "3. NOT_RUN → evaluate structural integrity only.\n\n"
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


def original_source(bug_id, modified_classes, cache="/tmp/js_orig"):
    """Check out the BUGGY version and return the source of the modified class.

    Without this the second judge sees only the patched file and reviews the
    whole file blind — it cannot tell which lines are the patch, and invents
    defects in pre-existing code.
    """
    os.makedirs(cache, exist_ok=True)
    cp = os.path.join(cache, bug_id + ".java")
    if os.path.exists(cp):
        return open(cp, encoding="utf-8", errors="replace").read()

    proj, num = bug_id.rsplit("_", 1)
    cls = (modified_classes or "").split("|")[0].split(",")[0].strip().strip("[]'\" ")
    if not cls:
        return ""
    w = tempfile.mkdtemp(prefix=f"js_{bug_id}_")
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


def load_results(d):
    rows = []
    for f in glob.glob(os.path.join(d, "**", "*.csv"), recursive=True):
        for x in csv.DictReader(open(f, encoding="utf-8", errors="replace")):
            x["_m"] = os.path.getmtime(f)
            rows.append(x)
    best = {}
    for r in rows:
        b = r.get("bug_id")
        if b and (b not in best or r["_m"] > best[b]["_m"]):
            best[b] = r
    return best


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--base-url", default=os.environ.get("JUDGE_BASE_URL", ""))
    ap.add_argument("--out", default="judge_swap.csv")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--only-plausible", action="store_true", default=True)
    args = ap.parse_args()

    key = os.environ.get("JUDGE_API_KEY")
    if not key:
        sys.exit("set JUDGE_API_KEY (and JUDGE_BASE_URL or --base-url) in the environment")

    from openai import OpenAI
    client = OpenAI(api_key=key, base_url=args.base_url)

    best = load_results(args.results_dir)
    todo = [r for r in best.values()
            if (not args.only_plausible) or r.get("plausible") == "True"]
    todo.sort(key=lambda r: (r["bug_id"].rsplit("_", 1)[0],
                             int(r["bug_id"].rsplit("_", 1)[1])))

    done = set()
    if os.path.exists(args.out):
        done = {r["bug_id"] for r in csv.DictReader(open(args.out))}
        print(f"resuming — {len(done)} already judged")
    todo = [r for r in todo if r["bug_id"] not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"judging {len(todo)} patch(es) with {args.model}\n")

    new = not os.path.exists(args.out)
    fh = open(args.out, "a", newline="")
    w = csv.DictWriter(fh, fieldnames=[
        "bug_id", "project", "test_status", "gemini_verdict",
        "second_verdict", "agree", "second_reason", "seconds"])
    if new: w.writeheader()

    for i, r in enumerate(todo, 1):
        bug = r["bug_id"]
        step = final_judge_step(r)
        if not step:
            print(f"[{i}/{len(todo)}] {bug}: no judge step, skipped"); continue
        md = step.get("metadata") or {}
        status = md.get("test_status_observed") or "NOT_RUN"
        patched = (r.get("plausible_patch") or "").strip() or (r.get("patch") or "")
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
        prompt = build_prompt(original, patched, status, test_summary, diff_text)

        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            txt = resp.choices[0].message.content.strip()
            txt = txt.replace("```json", "").replace("```", "").strip()
            verdict = str(json.loads(txt).get("verdict", "error")).lower()
            reason = str(json.loads(txt).get("reason", ""))[:300]
        except Exception as e:
            verdict, reason = "error", str(e)[:200]

        gem = r.get("verdict", "")
        row = {"bug_id": bug, "project": bug.rsplit("_", 1)[0],
               "test_status": status, "gemini_verdict": gem,
               "second_verdict": verdict, "agree": int(verdict == gem),
               "second_reason": reason, "seconds": round(time.time() - t0, 1)}
        w.writerow(row); fh.flush()
        flag = "=" if row["agree"] else "≠"
        print(f"[{i}/{len(todo)}] {bug:14s} gemini={gem:15s} {args.model[:12]}={verdict:15s} {flag}")

    fh.close()

    rows = list(csv.DictReader(open(args.out)))
    rows = [r for r in rows if r["second_verdict"] != "error"]
    if not rows:
        print("\nno usable rows"); return
    pairs = [(r["gemini_verdict"], r["second_verdict"]) for r in rows]
    print(f"\n=== agreement over {len(rows)} patches ===")
    print(f"raw agreement : {100*sum(1 for a,b in pairs if a==b)/len(pairs):.1f}%")
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


if __name__ == "__main__":
    main()
