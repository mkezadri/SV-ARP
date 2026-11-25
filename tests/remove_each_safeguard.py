#!/usr/bin/env python3
"""A check on the failure-injection tests themselves.

Each entry below removes one safeguard from a copy of the code (the text on the
left is replaced by the text on the right) and runs tests/test_safeguards.py on
that copy. A removal that no test notices would mean that the safeguard is not
tested; the script exits with status 1 if there is one. The repository itself
is not modified: every removal is made in a temporary directory.

    python3 tests/remove_each_safeguard.py

Takes about a minute. Requires what tests/test_safeguards.py requires.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REMOVALS = [
    ("missing test summary read as a pass", "src/agentic_apr.py",
     '''                return TestResult(False, output,
                                  "Build or test-harness failure", [])''',
     '''                return TestResult(True, output, None, [])'''),
    ("build failure read from the exit status only (test runner)", "src/agentic_apr.py",
     '''                failed = (r.returncode != 0
                          or "BUILD FAILED" in out
                          or re.search(r"\\berror:|cannot find symbol|"
                                       r"incompatible types|method .* cannot be applied",
                                       out))''',
     '''                failed = (r.returncode != 0)'''),
    ("declared failures that cannot be parsed read as a pass", "src/agentic_apr.py",
     '''                return TestResult(False, output,
                                  f"Parse failure: {declared} failing tests "
                                  f"reported but none extracted", [])''',
     '''                return TestResult(True, output, None, [])'''),
    ("test run over its time limit read as a pass", "src/agentic_apr.py",
     '''            return TestResult(False, "", "Test timed out (600 s)", [])''',
     '''            return TestResult(True, "", None, [])'''),
    ("correct verdict on a failing run not overridden", "src/agentic_apr.py",
     '''REQUIRE_TESTS_PASS_TO_ACCEPT = True''',
     '''REQUIRE_TESTS_PASS_TO_ACCEPT = False'''),
    ("gate accepts a correct verdict whatever the tests", "src/agentic_apr.py",
     '''        if tr is not None and tr.passed:
            return "accept"''',
     '''        if True:
            return "accept"'''),
    ("empty Judge response read as a correct verdict", "src/agentic_apr.py",
     '''            raise EmptyModelResponse(
                "Judge returned no content after all retries (network or API failure)"
            )''',
     '''            return Verdict.CORRECT, "", {"model": self.model_name}'''),
    ("unparseable Judge response read as a correct verdict", "src/agentic_apr.py",
     '''            return Verdict.ERROR, f"JSON parse error: {e}", {}''',
     '''            return Verdict.CORRECT, "", {}'''),
    ("errors retried only when they match a keyword list", "src/agentic_apr.py",
     '''                    if not permanent and attempt < max_retries - 1:
                        wait = min(300, (2 ** attempt) * 15 + random.uniform(1, 10))
                        self.logger.warning(
                            "Transient API/network error''',
     '''                    permanent = not any(k in err for k in ("503", "unavailable", "timeout", "deadline"))
                    if not permanent and attempt < max_retries - 1:
                        wait = min(300, (2 ** attempt) * 15 + random.uniform(1, 10))
                        self.logger.warning(
                            "Transient API/network error'''),
    ("HTTP 503 not retried", "src/agentic_apr.py",
     '''                    if not permanent and attempt < max_retries - 1:
                        wait = min(300, (2 ** attempt) * 15 + random.uniform(1, 10))
                        self.logger.warning(
                            "Transient API/network error''',
     '''                    if False:
                        wait = min(300, (2 ** attempt) * 15 + random.uniform(1, 10))
                        self.logger.warning(
                            "Transient API/network error'''),
    ("answer without content not retried", "src/agentic_apr.py",
     '''                    if not permanent and attempt < max_retries - 1:
                        wait = min(300, (2 ** attempt) * 15 + random.uniform(1, 10))
                        self.logger.warning(
                            "Empty response''',
     '''                    if False:
                        wait = min(300, (2 ** attempt) * 15 + random.uniform(1, 10))
                        self.logger.warning(
                            "Empty response'''),
    ("permanent errors retried like the others", "src/agentic_apr.py",
     '''                    permanent = bool(
                        re.match(r"^\\s*(400|401|403|404)\\b", se)
                    ) or any(k in err for k in (
                        "api key not valid", "api_key_invalid",
                        "permission denied", "invalid_argument",
                        "invalid argument", "unsupported", "model not found",
                        "unregistered callers",
                    ))''',
     '''                    permanent = False'''),
    ("unusable generation returned as an empty patch", "src/agentic_apr.py",
     '''        if not cleaned or is_noop_patch(full_buggy_code, cleaned):
            cleaned = full_buggy_code
''',
     '''        if not cleaned or is_noop_patch(full_buggy_code, cleaned):
            cleaned = ""
'''),
    ("baseline build read from the exit status only (benchmark runner)", "src/run_benchmark.py",
     '''            if (r.returncode != 0 or "BUILD FAILED" in out
                    or re.search(r"\\berror:|cannot find symbol|incompatible types", out)):''',
     '''            if (r.returncode != 0):'''),
    ("empty baseline accepted as a valid execution", "analysis/make_figures.py",
     '''    if (r.get("baseline_failing_count") or "").strip() == "0":
        return False
''',
     ''''''),
    ("execution that ended on a Judge error accepted as valid", "analysis/make_figures.py",
     '''    if (r.get("verdict") or "").strip().lower() == "error":
        return False
''',
     ''''''),
    ("canonical record prefers a plausible execution", "analysis/make_figures.py",
     '''            pick = pref[0] if rule == "first" else pref[-1]''',
     '''            pick = next((x for x in pref if truthy(x[1].get("plausible"))), pref[0])'''),
    ("concurrent sessions not set aside", "analysis/make_figures.py",
     '''            pref = [(s, r) for s, r in comp if s not in set_aside] or comp''',
     '''            pref = comp'''),
    ("aborted record taken as an execution", "analysis/make_figures.py",
     '''        comp = [(s, r) for s, r in lst if valid_completed(r)]''',
     '''        comp = [(s, r) for s, r in lst]'''),
    ("second supervisor not refused", "run_all.sh",
     '''            log "       If PID $other is not a supervisor of this arm:  rm -rf $lock"
            exit 1''',
     '''            log "       If PID $other is not a supervisor of this arm:  rm -rf $lock"'''),
    ("JVM locale not checked", "scripts/check_env.sh",
     '''    echo "  ! _JAVA_OPTIONS must include -Duser.language=en -Duser.country=US"; fail=1; }''',
     '''    echo "  ! _JAVA_OPTIONS must include -Duser.language=en -Duser.country=US"; }'''),
    ("time zone not checked", "scripts/check_env.sh",
     '''{ echo "  ! TZ must be America/Los_Angeles"; fail=1; }''',
     '''{ echo "  ! TZ must be America/Los_Angeles"; }'''),
    ("Java version not checked", "scripts/check_env.sh",
     '''{ echo "  ! Java 11 required"; fail=1; }''',
     '''{ echo "  ! Java 11 required"; }'''),
    ("Defects4J installation not checked", "scripts/check_env.sh",
     '''{ echo "  ! defects4j not found"; fail=1; }''',
     '''{ echo "  ! defects4j not found"; }'''),
]


def run_tests(directory):
    r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
                       cwd=directory, capture_output=True, text=True, timeout=900)
    last = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ""
    return r.returncode, last, sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+)", r.stderr, re.M)))


def copy_of_the_code(directory):
    shutil.rmtree(directory, ignore_errors=True)
    shutil.copytree(ROOT, directory, ignore=shutil.ignore_patterns(
        ".git", "data", "figures_out", "__pycache__", "venv", ".venv", "results*", "patches*"))


def main():
    undetected = 0
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "copy")
        copy_of_the_code(work)
        status, last, _ = run_tests(work)
        print("unmodified copy:", last)
        if status != 0:
            sys.exit("the tests do not pass on the unmodified code; nothing was removed")
        for name, path, old, new in REMOVALS:
            copy_of_the_code(work)
            target = os.path.join(work, path)
            with open(target, encoding="utf-8") as fh:
                text = fh.read()
            if text.count(old) != 1:
                print("%-66s TEXT TO REMOVE NOT FOUND (%d occurrences)" % (name, text.count(old)))
                undetected += 1
                continue
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text.replace(old, new))
            status, last, failed = run_tests(work)
            undetected += (status == 0)
            print("%-66s %s" % (name, "NOT DETECTED" if status == 0 else
                                "detected by %d test(s): %s" % (len(failed), ", ".join(failed))))
    print("\n%d removals, %d not detected" % (len(REMOVALS), undetected))
    sys.exit(1 if undetected else 0)


if __name__ == "__main__":
    main()
