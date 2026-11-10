#!/usr/bin/env python3
"""
fixed_baseline.py: run the relevant tests on the DEVELOPER-FIXED version of
every bug, in the same environment as the repair runs, and record which tests
fail there. Compared with the buggy-version baseline, this tells whether the
pre-existing failures (B \\ Tg) are environment failures that the developer
fix does not clear either, which is what the baseline-relative plausibility
criterion assumes.

    source apr-env.sh               # D4J_HOME, _JAVA_OPTIONS, TZ as for the runs
    python3 fixed_baseline.py --bug-list benchmark/versions.txt \
        --out fixed_baseline.csv --work ~/apr_work/d4j_fixed

Resumable: bugs already in --out are skipped. One checkout at a time; each
checkout is deleted when done. Output columns:
    bug_id, status (ok | checkout_failed | compile_failed | test_failed),
    failing_count, failing_tests (';'-separated), seconds
"""
import argparse, csv, os, re, shutil, subprocess, time

NEEDS_COMPILE = {"Chart", "Closure", "Lang", "Math", "Mockito", "Time"}


def d4j_cmd():
    home = os.environ.get("D4J_HOME")
    if home:
        cmd = os.path.join(home, "framework", "bin", "defects4j")
        if os.path.exists(cmd):
            return cmd
    return "defects4j"


def parse_failing(output):
    failing = []
    for line in output.splitlines():
        s = line.strip()
        if s.startswith("- ") and "::" in s:
            failing.append(s[2:].strip())
    return list(dict.fromkeys(failing))


def run(cmd, cwd, timeout):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=os.environ)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bug-list", required=True, help="one Project_N per line")
    ap.add_argument("--out", default="fixed_baseline.csv")
    ap.add_argument("--work", default=os.path.expanduser("~/apr_work/d4j_fixed"))
    args = ap.parse_args()

    bugs = [l.strip() for l in open(args.bug_list) if l.strip() and not l.startswith("#")]
    done = set()
    if os.path.exists(args.out):
        done = {r["bug_id"] for r in csv.DictReader(open(args.out))}
    os.makedirs(args.work, exist_ok=True)
    d4j = d4j_cmd()
    new_file = not os.path.exists(args.out)
    out = open(args.out, "a", newline="")
    w = csv.writer(out)
    if new_file:
        w.writerow(["bug_id", "status", "failing_count", "failing_tests", "seconds"])
        out.flush()

    todo = [b for b in bugs if b not in done]
    print(f"{len(todo)} bugs to do, {len(done)} already done", flush=True)
    for i, bug in enumerate(todo, 1):
        project, num = bug.rsplit("_", 1)
        path = os.path.join(args.work, bug)
        t0 = time.time()
        status, failing = "ok", []
        try:
            shutil.rmtree(path, ignore_errors=True)
            rc, o = run([d4j, "checkout", "-p", project, "-v", f"{num}f", "-w", path], None, 600)
            if rc != 0 or not os.path.isdir(path):
                status = "checkout_failed"
            else:
                if project in NEEDS_COMPILE:
                    rc, o = run([d4j, "compile"], path, 600)
                    if rc != 0 or "BUILD FAILED" in o or re.search(r"\berror:|cannot find symbol|incompatible types", o):
                        status = "compile_failed"
                if status == "ok":
                    rc, o = run([d4j, "test", "-r"], path, 1800)
                    m = re.search(r"Failing tests:\s*(\d+)", o)
                    if not m:
                        status = "test_failed"
                    else:
                        failing = parse_failing(o)
                        if int(m.group(1)) != len(failing):
                            print(f"  {bug}: header says {m.group(1)} failing, parsed {len(failing)}", flush=True)
        except subprocess.TimeoutExpired:
            status = "test_failed"
        except Exception as e:
            status = f"error: {e}"[:80]
        finally:
            shutil.rmtree(path, ignore_errors=True)
        secs = round(time.time() - t0, 1)
        w.writerow([bug, status, len(failing), ";".join(failing), secs])
        out.flush()
        print(f"[{i}/{len(todo)}] {bug}: {status}, {len(failing)} failing, {secs}s", flush=True)
    out.close()


if __name__ == "__main__":
    main()
