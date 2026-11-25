#!/usr/bin/env python3
"""Failure-injection tests of the safeguards of the harness.

Each test produces one of the failures that the harness must not read as a
repair, and checks what the released code does with it. Nothing here calls the
model or Defects4J: the `defects4j` command is replaced by a stub script whose
output and exit status the test sets, and the model client by an object that
fails or answers as the test says. The code under test is the released one
(src/agentic_apr.py, src/run_benchmark.py, analysis/make_figures.py,
run_all.sh, scripts/check_env.sh).

    python3 -m unittest discover -s tests -v

Requires the packages of requirements.txt and a Unix shell (bash). No API key
is needed; a placeholder is set below because the harness refuses to be
imported without one.
"""
import contextlib
import io
import logging
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "analysis"))

os.environ.pop("APR_API_KEYS", None)
os.environ["GEMINI_API_KEY"] = "placeholder-no-request-is-sent"
os.environ["APR_ABLATION"] = "full"

import agentic_apr as apr            # noqa: E402
import make_figures as mf            # noqa: E402
import run_benchmark as rb           # noqa: E402

logging.disable(logging.CRITICAL)    # the harness logs every refusal it is made to meet

STUB = textwrap.dedent("""\
    #!/usr/bin/env bash
    # stand-in for framework/bin/defects4j: prints the file and returns the status
    # that the test has put next to it
    d="$(cd "$(dirname "$0")" && pwd)"
    case "$1" in
      compile|test)
        [ -f "$d/$1.sleep" ] && sleep "$(cat "$d/$1.sleep")"
        [ -f "$d/$1.out" ] && cat "$d/$1.out"
        [ -f "$d/$1.rc" ] && exit "$(cat "$d/$1.rc")"
        exit 0 ;;
      checkout)
        exit 0 ;;
    esac
    exit 0
    """)

JAVA = "public class A {\n    int f(int x) {\n        return x + 1;\n    }\n}\n"
PATCHED = JAVA.replace("x + 1", "x + 2")


class StubbedDefects4J(unittest.TestCase):
    """A temporary D4J_HOME whose defects4j command is the stub, and a project
    directory with one source file."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name
        self.bin = os.path.join(self.home, "framework", "bin")
        os.makedirs(self.bin)
        cmd = os.path.join(self.bin, "defects4j")
        with open(cmd, "w") as fh:
            fh.write(STUB)
        os.chmod(cmd, os.stat(cmd).st_mode | stat.S_IXUSR)
        self.project = os.path.join(self.home, "Lang_1")
        os.makedirs(self.project)
        self.source = os.path.join(self.project, "A.java")
        with open(self.source, "w") as fh:
            fh.write(JAVA)
        self._env = mock.patch.dict(os.environ, {"D4J_HOME": self.home})
        self._env.start()
        self._home = mock.patch.object(rb, "D4J_HOME", self.home)     # read once, at import
        self._home.start()

    def tearDown(self):
        self._home.stop()
        self._env.stop()
        self._tmp.cleanup()

    def stub(self, command, out="", rc=0):
        with open(os.path.join(self.bin, command + ".out"), "w") as fh:
            fh.write(out)
        with open(os.path.join(self.bin, command + ".rc"), "w") as fh:
            fh.write(str(rc))

    def run_tests(self, triggers=("a.B::c",)):
        return apr.TestRunner.run_defects4j_tests(self.project, "Lang", trigger_tests=list(triggers))

    def state(self, **over):
        s = dict(iteration=0, language="java", project_name="Lang", project_path=self.project,
                 trigger_tests=["a.B::c"], buggy_file_path=self.source, buggy_file_paths=[self.source],
                 per_file_sources={}, per_file_patches={}, current_patch=PATCHED,
                 full_buggy_code=JAVA, history=[], conversation_log=[], _thread_id="test")
        s.update(over)
        return s


# ── the tests ran ────────────────────────────────────────────────────────────

class TheTestsRan(StubbedDefects4J):

    def test_control_zero_failures_is_a_pass(self):
        self.stub("test", "Failing tests: 0\n")
        tr = self.run_tests()
        self.assertTrue(tr.passed)

    def test_missing_summary_is_not_a_pass(self):
        # the build or the test harness failed: Defects4J prints no summary
        # line, and the exit status is 0
        self.stub("test", "Running ant (compile.tests)... FAIL\n", rc=0)
        tr = self.run_tests()
        self.assertFalse(tr.passed)
        self.assertEqual(tr.failing_tests, [])
        self.assertIn("failure", tr.error_message.lower())

    def test_empty_output_is_not_a_pass(self):
        self.stub("test", "", rc=0)
        self.assertFalse(self.run_tests().passed)

    def test_failing_tests_are_listed(self):
        self.stub("test", "Failing tests: 2\n  - a.B::c\n  - d.E::f\n")
        tr = self.run_tests()
        self.assertFalse(tr.passed)
        self.assertEqual(tr.failing_tests, ["a.B::c", "d.E::f"])

    def test_a_regression_alone_is_not_a_pass(self):
        # the trigger test passes, another relevant test fails
        self.stub("test", "Failing tests: 1\n  - d.E::f\n")
        self.assertFalse(self.run_tests().passed)

    def test_declared_failures_that_cannot_be_parsed_are_not_a_pass(self):
        self.stub("test", "Failing tests: 3\n")
        tr = self.run_tests()
        self.assertFalse(tr.passed)

    def test_test_run_over_its_time_limit_is_not_a_pass(self):
        real = subprocess.run

        def run(cmd, *a, **kw):
            if cmd[1:] == ["test", "-r"]:
                raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 600))
            return real(cmd, *a, **kw)
        self.stub("test", "Failing tests: 0\n")
        with mock.patch.object(apr.subprocess, "run", side_effect=run):
            tr = self.run_tests()
        self.assertFalse(tr.passed)
        self.assertIn("timed out", tr.error_message)

    def test_candidate_without_a_test_summary_is_not_plausible(self):
        self.stub("test", "", rc=0)
        s = apr.test_node(self.state())
        self.assertFalse(s["test_result"].passed)
        self.assertFalse(s.get("plausible_patch"))
        self.assertFalse(s.get("baseline_relative_pass"))

    def test_control_candidate_with_zero_failures_is_plausible(self):
        self.stub("test", "Failing tests: 0\n")
        s = apr.test_node(self.state())
        self.assertTrue(s["test_result"].passed)
        self.assertEqual(s["plausible_patch"], PATCHED)
        self.assertEqual(s["plausible_iteration"], 0)


# ── the candidate compiled ───────────────────────────────────────────────────

class TheCandidateCompiled(StubbedDefects4J):

    def test_build_failure_with_exit_status_zero(self):
        # `defects4j compile` can exit successfully on a failed build
        self.stub("compile", "Running ant (compile)... \nBUILD FAILED\n", rc=0)
        self.stub("test", "Failing tests: 0\n")       # must not be consulted
        tr = self.run_tests()
        self.assertFalse(tr.passed)
        self.assertEqual(tr.error_message, "Compilation failed")

    def test_compiler_error_with_exit_status_zero(self):
        self.stub("compile", "A.java:3: error: cannot find symbol\n", rc=0)
        self.stub("test", "Failing tests: 0\n")
        tr = self.run_tests()
        self.assertFalse(tr.passed)
        self.assertEqual(tr.error_message, "Compilation failed")

    def test_nonzero_exit_status(self):
        self.stub("compile", "", rc=1)
        self.stub("test", "Failing tests: 0\n")
        self.assertFalse(self.run_tests().passed)

    def test_compile_over_its_time_limit(self):
        real = subprocess.run

        def run(cmd, *a, **kw):
            if cmd[1:] == ["compile"]:
                raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 180))
            return real(cmd, *a, **kw)
        self.stub("test", "Failing tests: 0\n")
        with mock.patch.object(apr.subprocess, "run", side_effect=run):
            tr = self.run_tests()
        self.assertFalse(tr.passed)

    def test_non_compiling_candidate_is_not_plausible(self):
        self.stub("compile", "BUILD FAILED\n", rc=0)
        self.stub("test", "Failing tests: 0\n")
        s = apr.test_node(self.state())
        self.assertFalse(s.get("plausible_patch"))


# ── the bug is reproduced before repair ──────────────────────────────────────

def row(session="20260101_000000", status="completed", verdict="needs_revision", baseline="1", plausible="False"):
    return (session, dict(bug_id="Lang_1", status=status, verdict=verdict,
                          baseline_failing_count=baseline, plausible=plausible))


class TheBugIsReproduced(StubbedDefects4J):

    def test_unpatched_checkout_that_does_not_build(self):
        # a missing build dependency: the build stops, here with status 0
        self.stub("compile", "BUILD FAILED\nCould not resolve the Gradle distribution\n", rc=0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(rb.Defects4JBenchmark._baseline_compiles(self.project, "Mockito"))

    def test_control_unpatched_checkout_that_builds(self):
        self.stub("compile", "Running ant (compile)... OK\n", rc=0)
        self.assertTrue(rb.Defects4JBenchmark._baseline_compiles(self.project, "Mockito"))

    def test_execution_with_an_empty_baseline_is_invalid(self):
        self.assertFalse(mf.valid_completed(row(baseline="0", plausible="True")[1]))
        self.assertTrue(mf.valid_completed(row(baseline="1")[1]))

    def test_empty_baseline_is_never_canonical(self):
        # a "repair" recorded on a checkout that did not reproduce the bug
        only = mf.canonical({"Lang_1": [row(baseline="0", plausible="True")]}, "first")["Lang_1"]
        self.assertIsNone(only["row"])
        self.assertIn("empty baseline", only["excluded"])
        both = mf.canonical({"Lang_1": [row("20260101_000000", baseline="0", plausible="True"),
                                        row("20260102_000000", baseline="1", plausible="False")]}, "first")["Lang_1"]
        self.assertEqual(both["session"], "20260102_000000")

    def test_record_that_did_not_complete_is_not_an_execution(self):
        e = mf.canonical({"Lang_1": [row(status="build_broken", baseline="")]}, "first")["Lang_1"]
        self.assertIsNone(e["row"])
        self.assertEqual(e["excluded"], "build_broken")


# ── one record per bug, chosen without regard to outcome ─────────────────────

class OneRecordPerBug(unittest.TestCase):

    def pick(self, *rows, **kw):
        return mf.canonical({"Lang_1": list(rows)}, "first", **kw)["Lang_1"]["session"]

    def test_the_earliest_valid_execution_whatever_the_outcomes(self):
        for first, second in (("True", "False"), ("False", "True"), ("True", "True"), ("False", "False")):
            self.assertEqual(self.pick(row("20260101_000000", plausible=first),
                                       row("20260102_000000", plausible=second)), "20260101_000000")

    def test_a_completed_execution_outranks_an_aborted_one(self):
        self.assertEqual(self.pick(row("20260101_000000", status="checkout_failed"),
                                   row("20260102_000000")), "20260102_000000")

    def test_an_execution_that_ended_on_a_judge_error_is_not_valid(self):
        self.assertEqual(self.pick(row("20260101_000000", verdict="error", plausible="True"),
                                   row("20260102_000000")), "20260102_000000")

    def test_sessions_that_shared_a_working_directory_are_set_aside(self):
        shared = ("20260101_000000", "20260101_000500")
        self.assertEqual(self.pick(row(shared[0], plausible="True"), row(shared[1], plausible="True"),
                                   row("20260201_000000", plausible="False"), set_aside=shared), "20260201_000000")


# ── the model answered ───────────────────────────────────────────────────────

def answer(text):
    usage = types.SimpleNamespace(prompt_token_count=10, candidates_token_count=5, total_token_count=15)
    part = types.SimpleNamespace(text=text)
    cand = types.SimpleNamespace(content=types.SimpleNamespace(parts=[part]), finish_reason="STOP")
    return types.SimpleNamespace(candidates=[cand], usage_metadata=usage)


class FakeClient:
    """A model client that raises or answers as scripted, and counts the requests."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = 0
        self.models = types.SimpleNamespace(generate_content=self._generate)

    def _generate(self, **_kw):
        self.requests += 1
        step = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(step, Exception):
            raise step
        return step


class TheModelAnswered(unittest.TestCase):

    def call(self, script, agent=None, **kw):
        client = FakeClient(script)
        agent = agent or apr.GeminiAgent("stub-model")
        with mock.patch.object(apr.KEY_POOL, "client", return_value=client), \
                mock.patch.object(apr.time, "sleep"):
            out = agent._call("prompt", **kw)
        return out, client.requests

    def test_http_503_is_retried(self):
        (text, usage), n = self.call([Exception("503 UNAVAILABLE. The model is overloaded."),
                                      Exception("503 UNAVAILABLE. The model is overloaded."), answer("ok")])
        self.assertEqual((text, n), ("ok", 3))
        self.assertEqual(usage["total_tokens"], 15)

    def test_dns_failure_is_retried(self):
        # the error that the first client classified as permanent
        (text, _), n = self.call([OSError("[Errno 8] nodename nor servname provided, or not known"), answer("ok")])
        self.assertEqual((text, n), ("ok", 2))

    def test_an_answer_without_content_is_retried(self):
        empty = types.SimpleNamespace(candidates=[], usage_metadata=None)
        (text, _), n = self.call([empty, answer("ok")])
        self.assertEqual((text, n), ("ok", 2))

    def test_six_refusals_give_no_text(self):
        (text, usage), n = self.call([Exception("503 UNAVAILABLE. The model is overloaded.")])
        self.assertEqual((text, usage, n), ("", {}, 6))

    def test_a_permanent_error_is_not_retried(self):
        for message in ("400 INVALID_ARGUMENT. Request contains an invalid argument.",
                        "API key not valid. Please pass a valid API key.", "404 NOT_FOUND. model not found"):
            (text, _), n = self.call([Exception(message)])
            self.assertEqual((text, n), ("", 1), message)

    def test_repair_attempt_without_model_output_tests_the_unchanged_file(self):
        agent = apr.RepairAgent("stub-model")
        with mock.patch.object(agent, "_call", return_value=("", {})) as call:
            patch, md = agent.generate_fix(full_buggy_code=JAVA, error_info="Lang-1")
        self.assertEqual(patch, JAVA)                       # no edit was invented
        self.assertEqual(call.call_count, apr.MAX_GENERATION_RETRIES + 1)
        self.assertEqual(md["generation_attempts"], apr.MAX_GENERATION_RETRIES + 1)
        self.assertTrue(md["generation_rejected"])
        self.assertEqual(md["blocks_applied"], 0)

    def test_an_edit_that_does_not_apply_is_refused(self):
        agent = apr.RepairAgent("stub-model")
        bad = "<<<<<<< SEARCH\nreturn x + 7;\n=======\nreturn x;\n>>>>>>> REPLACE\n"
        with mock.patch.object(agent, "_call", return_value=(bad, {})):
            patch, md = agent.generate_fix(full_buggy_code=JAVA, error_info="Lang-1")
        self.assertEqual(patch, JAVA)
        self.assertTrue(md["generation_rejected"])


# ── the review is not a pass, and a lost review is not a verdict ─────────────

class TheReview(StubbedDefects4J):

    def judged(self, raw, test_output):
        """One iteration: test the candidate with the stub, then have it reviewed by a
        Judge whose model returns `raw`."""
        self.stub("test", test_output)
        apr._get_single_detector("test").reset()
        s = apr.test_node(self.state())
        with mock.patch.object(apr.judge_agent, "_call", return_value=(raw, {})):
            s = apr.judge_node(s)
        return s

    def test_control_passing_candidate_with_a_correct_verdict_is_accepted(self):
        s = self.judged('{"verdict": "correct", "reason": "ok"}', "Failing tests: 0\n")
        self.assertEqual(apr.decide_next(s), "accept")

    def test_correct_verdict_on_a_failing_run_is_overridden(self):
        s = self.judged('{"verdict": "correct", "reason": "looks right"}', "Failing tests: 1\n  - a.B::c\n")
        self.assertEqual(s["judge_verdict"], "needs_revision")
        self.assertIn("Overridden by acceptance gate", s["judge_reason"])
        self.assertEqual(apr.decide_next(s), "continue")

    def test_correct_verdict_without_a_test_summary_is_overridden(self):
        s = self.judged('{"verdict": "correct", "reason": "looks right"}', "")
        self.assertNotEqual(apr.decide_next(s), "accept")
        self.assertFalse(s.get("plausible_patch"))

    def test_gate_refuses_a_correct_verdict_on_a_failing_run(self):
        failing = apr.TestResult(False, "", None, ["a.B::c"])
        self.assertEqual(apr.decide_next(dict(judge_verdict="correct", test_result=failing, iteration=0)), "reject")

    def test_empty_judge_response_is_a_lost_review(self):
        s = self.judged("", "Failing tests: 0\n")
        last = s["history"][-1]
        self.assertEqual(last["action"], "judge")
        self.assertIn("judge_error", last["metadata"])         # recorded as lost
        self.assertNotIn("model", last["metadata"])
        self.assertNotEqual(apr.decide_next(s), "accept")      # not read as a verdict
        self.assertEqual(s["plausible_patch"], PATCHED)        # the test outcome stands

    def test_unparseable_judge_response_is_not_a_verdict(self):
        s = self.judged("the patch looks fine to me", "Failing tests: 0\n")
        self.assertEqual(s["judge_verdict"], "error")
        self.assertNotEqual(apr.decide_next(s), "accept")
        self.assertEqual(s["plausible_patch"], PATCHED)


# ── one session per working directory ────────────────────────────────────────

LOCK_DRIVER = textwrap.dedent("""\
    log() { printf '%s\\n' "$*"; }
    held_locks=()
    eval "$(sed -n '/^_unlock() {/,/^}/p; /^take_lock() {/,/^}/p' "$1")"
    take_lock "$2" full
    echo LOCKED
    [ "${3:-}" = hold ] && read -r _
    exit 0
    """)


class OneSessionPerWorkingDirectory(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.lock = os.path.join(self._tmp.name, ".supervisor.lock")
        self.script = os.path.join(ROOT, "run_all.sh")

    def tearDown(self):
        self._tmp.cleanup()

    def supervisor(self, *extra, **kw):
        return subprocess.Popen(["bash", "-c", LOCK_DRIVER, "driver", self.script, self.lock, *extra],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)

    def test_second_session_is_refused_and_a_stale_lock_is_taken_over(self):
        first = self.supervisor("hold")
        try:
            self.assertEqual(first.stdout.readline().strip(), "LOCKED")
            with open(os.path.join(self.lock, "pid")) as fh:
                self.assertEqual(int(fh.read()), first.pid)
            second = self.supervisor()
            out, _ = second.communicate(timeout=30)
            self.assertEqual(second.returncode, 1)
            self.assertIn("FATAL", out)
            self.assertNotIn("LOCKED", out)
        finally:
            first.kill()
            first.wait()
            first.stdout.close()
            first.stdin.close()
        # the first supervisor is dead and its lock directory is still there
        self.assertTrue(os.path.isdir(self.lock))
        third = self.supervisor()
        out, _ = third.communicate(timeout=30)
        self.assertEqual(third.returncode, 0)
        self.assertIn("stale lock", out)
        self.assertIn("LOCKED", out)


# ── the environment is checked before a run ──────────────────────────────────

class TheEnvironmentIsChecked(StubbedDefects4J):

    def check(self, java="11.0.30", **env):
        bindir = os.path.join(self.home, "bin")
        os.makedirs(bindir, exist_ok=True)
        fake = os.path.join(bindir, "java")
        with open(fake, "w") as fh:
            fh.write('#!/usr/bin/env bash\necho \'openjdk version "%s" 2026-01-20\' >&2\n' % java)
        os.chmod(fake, 0o755)
        e = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"], JAVA_HOME="/nowhere",
                 TZ="America/Los_Angeles", _JAVA_OPTIONS="-Duser.language=en -Duser.country=US", D4J_HOME=self.home)
        e.update(env)
        return subprocess.run(["bash", os.path.join(ROOT, "scripts", "check_env.sh")],
                              env=e, capture_output=True, text=True, timeout=60)

    def test_control_environment_as_required(self):
        self.stub("test", "Failing tests: 1\n  - com.google.javascript.jscomp.TypeCheckTest::testBadInterfaceExtendsNonExistentInterfaces\n")
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Failing tests: 1", r.stdout)

    def test_jvm_locale_not_pinned(self):
        r = self.check(_JAVA_OPTIONS="")
        self.assertEqual(r.returncode, 1)
        self.assertIn("user.language=en", r.stdout)

    def test_time_zone_not_set(self):
        self.assertEqual(self.check(TZ="Europe/Paris").returncode, 1)

    def test_wrong_java_version(self):
        self.assertEqual(self.check(java="17.0.9").returncode, 1)

    def test_defects4j_not_installed(self):
        self.assertEqual(self.check(D4J_HOME=os.path.join(self.home, "missing")).returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
