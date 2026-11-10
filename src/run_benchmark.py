"""
SV-ARP Defects4J Benchmark Runner
==================================
Drives the Defects4J evaluation loop:
  1. Checkout buggy version via `defects4j checkout`
  2. Check that the buggy version compiles and record which tests fail on it
  3. Extract modified classes and trigger tests
  4. Call AgenticRepairSystem.repair_bug()
  5. Record results to CSV + per-bug JSON log

Routing is automatic:
  len(per_file_sources) == 1  →  single-file strategy
  len(per_file_sources)  > 1  →  multi-file  strategy

Usage
-----
  # Full benchmark
  python run_benchmark.py --bug-list benchmark/versions.txt

  # Single bug
  python run_benchmark.py --bug Lang_1

  # Resume interrupted run
  python run_benchmark.py --bug-list benchmark/versions.txt --resume

Environment variables
---------------------
  D4J_HOME          Path to Defects4J installation (required)
  GEMINI_API_KEY    Google Gemini API key (required)
  APR_RESULTS_DIR   Output directory for CSV/JSON results (default: results)
  APR_WORK_DIR      Checkout working directory (default: /tmp/d4j_benchmark)
  APR_PATCH_DIR     Where accepted patches are written (default: patches)
  APR_MAPPING_FILE  Optional bug_id,source_path CSV for patch file names
  APR_ABLATION, APR_MAX_ITERATIONS, APR_TEMPERATURE: see agentic_apr.py
"""

import os
import sys
import csv
import json
import time
import shutil
import subprocess
import re
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Always load the agent module from source, never from a stale .pyc file.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"   # suppress new .pyc creation
_apr_module_name = "agentic_apr"
if _apr_module_name in sys.modules:
    importlib.reload(sys.modules[_apr_module_name])

from agentic_apr import (
    AgenticRepairSystem,
    TestResult,
    TestRunner,
    get_localized_context,
    PROJECT_SRC_DIRS,
    PROJECT_TEST_DIRS,
    NEEDS_COMPILE,
    print_result,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

D4J_HOME      = os.environ.get("D4J_HOME", "")
# Per-worker scratch root: set APR_WORK_DIR when running several workers so
# that they cannot touch the same checkout directory.
WORK_DIR      = os.environ.get("APR_WORK_DIR", "/tmp/d4j_benchmark")
# Per-configuration results dir. `--resume` matches on bug_id alone, so one
# directory must not be shared across configurations.
RESULTS_DIR   = os.environ.get("APR_RESULTS_DIR", "results")
BUG_LIST_FILE = "benchmark/versions.txt"
MAPPING_FILE  = os.environ.get("APR_MAPPING_FILE", "mapping.csv")

PROJECT_PACKAGE_PREFIXES = {
    "Chart":   "org.jfree",
    "Lang":    "org.apache.commons.lang",
    "Math":    "org.apache.commons.math",
    "Time":    "org.joda.time",
    "Closure": "com.google.javascript",
    "Mockito": "org.mockito",
}


def _d4j_cmd() -> str:
    cmd = os.path.join(D4J_HOME, "framework", "bin", "defects4j")
    return cmd if os.path.exists(cmd) else "defects4j"


# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK RUNNER
# ─────────────────────────────────────────────────────────────────────────────

class Defects4JBenchmark:
    PATCH_ROOT = os.environ.get("APR_PATCH_DIR", "patches")

    def __init__(self, resume: bool = False):
        self.system  = AgenticRepairSystem()
        self.results: List[Dict] = []
        self.resume  = resume
        os.makedirs(WORK_DIR,        exist_ok=True)
        os.makedirs(RESULTS_DIR,     exist_ok=True)
        os.makedirs(self.PATCH_ROOT, exist_ok=True)

    # ── Source-dir resolution ────────────────────────────────────────────────

    def _resolve_src_dir(self, project_path: str, project: str) -> str:
        d4j = _d4j_cmd()
        for prop in ["dir.src.classes", "dir.src", "src.dir"]:
            try:
                r = subprocess.run(
                    [d4j, "export", "-p", prop], cwd=project_path,
                    capture_output=True, text=True, timeout=15, env=os.environ
                )
                if r.returncode == 0 and r.stdout.strip():
                    candidate = r.stdout.strip()
                    if os.path.isdir(os.path.join(project_path, candidate)):
                        return candidate
            except Exception:
                pass

        for hint in PROJECT_SRC_DIRS.get(project, ["src/main/java", "src"]):
            if os.path.isdir(os.path.join(project_path, hint)):
                return hint

        for root, _, files in os.walk(project_path):
            if any(f.endswith(".java") for f in files):
                rel   = os.path.relpath(root, project_path)
                parts = Path(rel).parts
                for i, p in enumerate(parts):
                    if p in ("src", "source", "java"):
                        return str(Path(*parts[: i + 1]))
                break
        return "src"

    # ── File resolution ──────────────────────────────────────────────────────

    def _find_java_file(
        self, project_path: str, src_dir: str, fqn: str
    ) -> Optional[str]:
        relative   = fqn.replace(".", "/") + ".java"
        candidates = [
            os.path.join(project_path, src_dir, relative),
            os.path.join(project_path, "src", relative),
            os.path.join(project_path, "source", relative),
            os.path.join(project_path, "src/main/java", relative),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        filename = relative.split("/")[-1]
        for root, _, files in os.walk(project_path):
            if filename in files:
                full = os.path.join(root, filename)
                if relative.replace("/", os.sep) in full:
                    return full
        return None

    # ── Checkout ─────────────────────────────────────────────────────────────

    def checkout_bug(self, project: str, bug_id: int) -> Optional[str]:
        bug_version = f"{bug_id}b"
        work_path   = os.path.join(WORK_DIR, f"{project}_{bug_id}")
        d4j         = _d4j_cmd()

        def _has_java(path: str) -> bool:
            return bool(list(Path(path).rglob("*.java")))

        # Always check out fresh. Reusing an existing directory would read the
        # previous run's patched source as if it were the buggy version.
        # Set APR_REUSE_CHECKOUTS=1 only for debugging a single bug.
        if os.path.exists(work_path):
            if os.environ.get("APR_REUSE_CHECKOUTS") == "1" and _has_java(work_path):
                print(f"  ✓ Reusing checkout (APR_REUSE_CHECKOUTS=1): {work_path}")
                return work_path
            shutil.rmtree(work_path, ignore_errors=True)

        for attempt in range(1, 3):
            print(f"  Checking out {project} {bug_version} (attempt {attempt}) …")
            try:
                r = subprocess.run(
                    [d4j, "checkout", "-p", project, "-v", bug_version,
                     "-w", work_path],
                    capture_output=True, text=True, timeout=300, env=os.environ
                )
                if r.returncode != 0:
                    print(f"  ✗ Checkout failed: {r.stderr[:300]}")
                    if os.path.exists(work_path):
                        shutil.rmtree(work_path, ignore_errors=True)
                    continue
                if _has_java(work_path):
                    return work_path
                print("  ✗ Checkout OK but no Java files found.")
                shutil.rmtree(work_path, ignore_errors=True)
            except subprocess.TimeoutExpired:
                print("  ✗ Checkout timed out.")
                if os.path.exists(work_path):
                    shutil.rmtree(work_path, ignore_errors=True)
        return None

    # ── Extract bug info ─────────────────────────────────────────────────────

    def extract_bug_info(
        self, project_path: str, project: str, bug_id: int
    ) -> Tuple[Optional[str], List[str], List[str], List[str], Dict[str, str]]:
        """
        Returns:
            primary_source   – text of the first modified file
            failing_tests    – tests.trigger list
            buggy_file_paths – all modified file paths on disk
            modified_classes – FQN list from defects4j
            per_file_sources – { filepath: source_text } for every modified file

        The APR system uses len(per_file_sources) to route automatically:
            == 1  →  single-file strategy
            >  1  →  multi-file strategy  (per-file repair + oscillation guard)
        """
        d4j     = _d4j_cmd()
        src_dir = self._resolve_src_dir(project_path, project)

        modified_classes: List[str] = []
        try:
            r = subprocess.run(
                [d4j, "export", "-p", "classes.modified"],
                cwd=project_path, capture_output=True, text=True,
                timeout=15, env=os.environ
            )
            if r.returncode == 0:
                modified_classes = [
                    c.strip() for c in r.stdout.strip().splitlines() if c.strip()
                ]
            print(f"  Modified classes: {modified_classes}")
        except Exception as e:
            print(f"  Export classes.modified failed: {e}")

        buggy_file_paths: List[str] = []
        for cls in modified_classes:
            fp = self._find_java_file(project_path, src_dir, cls)
            if fp:
                buggy_file_paths.append(fp)
            else:
                print(f"  ⚠ Cannot locate file for class: {cls}")

        if not buggy_file_paths:
            java_files = list(Path(project_path).rglob("*.java"))
            if java_files:
                buggy_file_paths = [str(java_files[0])]
                print(f"  Fallback file: {buggy_file_paths[0]}")
            else:
                print("  No Java files found.")
                return None, [], [], modified_classes, {}

        per_file_sources: Dict[str, str] = {}
        for fp in buggy_file_paths:
            try:
                per_file_sources[fp] = Path(fp).read_text(encoding="utf-8")
            except Exception as e:
                print(f"  ⚠ Could not read {fp}: {e}")

        primary_source = (
            per_file_sources[buggy_file_paths[0]]
            if buggy_file_paths and buggy_file_paths[0] in per_file_sources
            else None
        )

        strategy = "multi-file" if len(per_file_sources) > 1 else "single-file"
        print(f"  Strategy: {strategy} ({len(per_file_sources)} file(s))")

        failing_tests: List[str] = []
        try:
            r = subprocess.run(
                [d4j, "export", "-p", "tests.trigger"],
                cwd=project_path, capture_output=True, text=True,
                timeout=15, env=os.environ
            )
            if r.returncode == 0 and r.stdout.strip():
                failing_tests = [
                    t.strip() for t in r.stdout.strip().splitlines() if t.strip()
                ]
            print(f"  Failing tests: {failing_tests}")
        except Exception as e:
            print(f"  Export tests.trigger failed: {e}")

        return (
            primary_source,
            failing_tests,
            buggy_file_paths,
            modified_classes,
            per_file_sources,
        )

    # ── Build error_info ─────────────────────────────────────────────────────

    @staticmethod
    def _build_error_info(
        project:          str,
        bug_id:           int,
        failing_tests:    List[str],
        modified_classes: List[str],
    ) -> str:
        pkg   = PROJECT_PACKAGE_PREFIXES.get(project, "")
        lines = [f"Defects4J {project} bug #{bug_id}."]
        if pkg:
            lines.append(f"Package prefix: {pkg}.*")
        if modified_classes:
            lines.append(f"Modified class(es): {', '.join(modified_classes)}")
        if failing_tests:
            lines.append("Failing tests (trigger):")
            for t in failing_tests:
                method = t.split("::")[-1] if "::" in t else t
                lines.append(f"  - {t}  (method: {method})")
        else:
            lines.append(
                "No specific test info available — fix based on code analysis."
            )
        return "\n".join(lines)

    # ── Backup / restore ─────────────────────────────────────────────────────

    @staticmethod
    def _backup(file_paths: List[str]) -> Dict[str, str]:
        backups: Dict[str, str] = {}
        for fp in file_paths:
            if fp and os.path.exists(fp):
                bak = fp + ".apr.bak"
                shutil.copy2(fp, bak)
                backups[fp] = bak
        return backups

    @staticmethod
    def _restore(backups: Dict[str, str]):
        for orig, bak in backups.items():
            if os.path.exists(bak):
                shutil.copy2(bak, orig)
                os.remove(bak)

    # ── Baseline compile check ────────────────────────────────────────────────

    @staticmethod
    def _baseline_compiles(project_path: str, project: str) -> bool:
        if project not in NEEDS_COMPILE:
            return True
        d4j = _d4j_cmd()
        try:
            r = subprocess.run(
                [d4j, "compile"], cwd=project_path,
                capture_output=True, text=True, timeout=180, env=os.environ
            )
            # `defects4j compile` can exit 0 on a failed build, so read the
            # output too.
            out = r.stdout + r.stderr
            if (r.returncode != 0 or "BUILD FAILED" in out
                    or re.search(r"\berror:|cannot find symbol|incompatible types", out)):
                print(f"  x Baseline compile failed:\n{out[:600]}")
                return False
            return True
        except Exception:
            return False

    # ── Run a single bug ─────────────────────────────────────────────────────

    def run_single_bug(self, project: str, bug_id: int) -> Dict:
        bug_str = f"{project}_{bug_id}"
        print(f"\n{'─'*60}")
        print(f"🔧 {bug_str}")
        print(f"{'─'*60}")

        project_path = self.checkout_bug(project, bug_id)
        if not project_path:
            return self._fail_record(bug_str, "checkout_failed", "Checkout failed")

        if not self._baseline_compiles(project_path, project):
            print(f"  ✗ Baseline compile failed — skipping {bug_str}")
            return self._fail_record(
                bug_str, "build_broken", "Baseline does not compile"
            )

        (
            primary_source,
            failing_tests,
            buggy_file_paths,
            modified_classes,
            per_file_sources,
        ) = self.extract_bug_info(project_path, project, bug_id)

        if primary_source is None:
            return self._fail_record(
                bug_str, "extraction_failed", "Could not extract buggy code"
            )

        is_multi_file = len(per_file_sources) > 1

        if failing_tests:
            localized = get_localized_context(primary_source, failing_tests, project)
            print(f"  Localised: {len(primary_source):,} → {len(localized):,} chars")
        else:
            localized = primary_source[:8000]
            print("  No failing tests — using first 8 000 chars.")

        error_info = self._build_error_info(
            project, bug_id, failing_tests, modified_classes
        )

        backups = self._backup(buggy_file_paths)

        print("  🧪 Baseline test on buggy version …")
        baseline = TestRunner.run_defects4j_tests(
            project_path, project,
            trigger_tests=failing_tests or None,
        )
        print(
            f"  Baseline failing: {len(baseline.failing_tests)} "
            f"(trigger: {len(failing_tests)})"
        )
        self._restore(backups)
        backups = self._backup(buggy_file_paths)

        try:
            result = self.system.repair_bug(
                buggy_code       = localized,
                full_buggy_code  = primary_source,
                buggy_file_path  = buggy_file_paths[0] if buggy_file_paths else None,
                buggy_file_paths = buggy_file_paths,
                per_file_sources = per_file_sources,
                project_name     = project,
                error_info       = error_info,
                language         = "java",
                project_path     = project_path,
                failing_tests    = failing_tests,
                trigger_tests    = failing_tests,
                thread_id        = bug_str,
            )

            per_file_patch_info = {
                os.path.basename(fp): (
                    "patched" if fp in result.final_patches else "unchanged"
                )
                for fp in buggy_file_paths
            }

            # has_patch: check both final_patch and final_patches
            has_patch = (
                result.final_patch is not None
                or bool(result.final_patches)
            )

            # `plausible` (the tests passed at some iteration) and the first
            # test-passing patch are persisted separately from the Judge
            # verdict and the finally accepted patch.
            record = {
                "bug_id":            bug_str,
                "status":            "completed",
                "verdict":           result.judge_verdict.value,
                "ablation":          os.environ.get("APR_ABLATION", "full"),
                "plausible":         bool(result.plausible),
                "baseline_failing_count": len(baseline.failing_tests),
                "baseline_failing_tests": ";".join(baseline.failing_tests),
                "accepted":          (
                    result.judge_verdict.value == "correct"
                    and bool(result.plausible)
                ),
                "plausible_patch":   result.plausible_patch or "",
                "plausible_iteration": (
                    result.plausible_iteration
                    if result.plausible_iteration is not None else -1
                ),
                "reason":            result.judge_reason,
                "iterations":        result.iteration_count,
                "has_patch":         has_patch,
                "patch":             result.final_patch or "",
                "per_file_patches":  json.dumps(per_file_patch_info),
                "is_multi_file":     is_multi_file,
                "strategy":          "multi-file" if is_multi_file else "single-file",
                "time_seconds":      round(result.execution_time, 2),
                "total_tokens":      result.cost_estimate.get("total_tokens", 0),
                "estimated_usd":     result.cost_estimate.get("estimated_usd", 0.0),
                "failing_tests":     "|".join(failing_tests),
                "modified_classes":  "|".join(modified_classes),
                "oscillation_abort": any(
                    h.get("metadata", {}).get("oscillation", False)
                    for h in result.history
                ),
                "history":           json.dumps(result.history, default=str),
                "error":             "",
            }

            self._write_json_log(bug_str, record, result.history)

            if record["accepted"]:
                if result.final_patches:
                    for fp, patch_text in result.final_patches.items():
                        rel = os.path.relpath(fp, project_path)
                        self._write_patch(bug_str, patch_text, rel)
                elif result.final_patch:
                    src = self._load_source_paths(MAPPING_FILE).get(bug_str)
                    if src:
                        self._write_patch(bug_str, result.final_patch, src)
            elif result.plausible and result.plausible_patch:
                # Suite passed but the Judge vetoed it: keep the patch so the
                # plausible count is auditable and the patch is not lost.
                src = self._load_source_paths(MAPPING_FILE).get(bug_str)
                if src:
                    self._write_patch(
                        bug_str, result.plausible_patch, src + ".plausible"
                    )

            return record

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._fail_record(bug_str, "failed", str(e))
        finally:
            self._restore(backups)
            # Delete this bug's checkout now that we are done with it. Without
            # this every checkout of the pass stays on disk (a Closure tree is
            # ~300 MB), so something else has to clean up while the run is in
            # progress - which races with the rmtree calls above.
            if project_path:
                _root = os.path.abspath(WORK_DIR) + os.sep
                if os.path.abspath(project_path).startswith(_root):
                    shutil.rmtree(project_path, ignore_errors=True)
            time.sleep(8)

    # ── Full benchmark ────────────────────────────────────────────────────────

    def run_benchmark(self, bug_list: List[str]):
        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(RESULTS_DIR, f"results_{timestamp}.csv")

        done: set = set()
        if self.resume:
            done = self._load_done_bugs(RESULTS_DIR)
            print(f"  Resume mode: {len(done)} bugs already done, skipping.")

        print(f"\n{'═'*60}")
        print(f"🚀  SV-ARP benchmark — {len(bug_list)} bugs")
        print(f"    configuration: {os.environ.get('APR_ABLATION', 'full')}")
        print(f"Results → {results_file}")
        print(f"{'═'*60}\n")

        for i, bug_str in enumerate(bug_list, 1):
            print(f"\n[{i}/{len(bug_list)}]", end=" ")

            if bug_str in done:
                print(f"SKIP {bug_str} (already done)")
                continue

            try:
                project, bid_str = bug_str.split("_", 1)
                bug_id = int(bid_str)
            except ValueError:
                print(f"❌ Invalid format: {bug_str}")
                continue

            # Stop cleanly when the API quota is spent, so --resume can
            # continue later instead of recording a run of failures.
            try:
                record = self.run_single_bug(project, bug_id)
            except Exception as e:
                if type(e).__name__ == "QuotaExhausted":
                    print(f"\n⛔ API quota exhausted at {bug_str}. "
                          f"Stopping cleanly — re-run with --resume.")
                    self._save_csv(results_file)
                    print(f"Completed {len(self.results)} bug(s) this session.")
                    return
                raise
            self.results.append(record)
            self._save_csv(results_file)

            status   = record.get("status", "?")
            verdict  = record.get("verdict", "")
            strategy = record.get("strategy", "?")
            if status == "completed":
                osc  = " ⚠OSC" if record.get("oscillation_abort") else ""
                pfp  = record.get("per_file_patches", "{}")
                try:
                    pfp_info = json.loads(pfp)
                    npatched = sum(1 for v in pfp_info.values() if v == "patched")
                    multi    = (f" ({npatched}/{len(pfp_info)} files)"
                                if len(pfp_info) > 1 else "")
                except Exception:
                    multi = ""
                print(
                    f"  → {bug_str}: {verdict}{multi} [{strategy}] "
                    f"({record.get('iterations', 0)} iters, "
                    f"{record.get('time_seconds', 0):.0f}s){osc}"
                )
            else:
                print(
                    f"  → {bug_str}: {status} — {record.get('error','')[:80]}"
                )

        print(f"\n{'═'*60}")
        print("✅  Benchmark complete!")
        print(f"Results: {results_file}")
        self._print_summary()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fail_record(bug_id: str, status: str, error: str) -> Dict:
        return {
            "bug_id":            bug_id,
            "status":            status,
            "verdict":           "",
            "ablation":          os.environ.get("APR_ABLATION", "full"),
            "plausible":         False,
            "accepted":          False,
            "plausible_patch":   "",
            "plausible_iteration": -1,
            "reason":            "",
            "iterations":        0,
            "has_patch":         False,
            "patch":             "",
            "per_file_patches":  "{}",
            "is_multi_file":     False,
            "strategy":          "unknown",
            "time_seconds":      0,
            "total_tokens":      0,
            "estimated_usd":     0.0,
            "failing_tests":     "",
            "modified_classes":  "",
            "oscillation_abort": False,
            "history":           "[]",
            "error":             error,
        }

    def _write_json_log(self, bug_id: str, record: Dict, history: List[Dict]):
        log_dir  = os.path.join(RESULTS_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{bug_id}.json")
        payload  = {**record, "history": history}
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    def _write_patch(self, bug_id: str, patch_text: str, source_path: str):
        if not patch_text.strip():
            return
        out_dir  = os.path.join(self.PATCH_ROOT, bug_id, os.path.dirname(source_path))
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(self.PATCH_ROOT, bug_id, source_path)
        Path(out_file).write_text(patch_text, encoding="utf-8")
        print(f"  📝 Patch → {out_file}")

    def _save_csv(self, filename: str):
        if not self.results:
            return
        fieldnames = sorted({k for r in self.results for k in r})
        for r in self.results:                      # keep rows uniform
            for k in fieldnames:
                r.setdefault(k, "")
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)

    @staticmethod
    def _load_source_paths(mapping_file: str) -> Dict[str, str]:
        paths: Dict[str, str] = {}
        if not os.path.isfile(mapping_file):
            return paths
        try:
            with open(mapping_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if "bug_id" in row and "source_path" in row:
                        paths[row["bug_id"].strip()] = row["source_path"].strip()
        except Exception as e:
            print(f"Error reading mapping: {e}")
        return paths

    @staticmethod
    def _load_done_bugs(results_dir: str) -> set:
        done: set = set()
        for csv_path in Path(results_dir).glob("results_*.csv"):
            try:
                with open(csv_path, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        bid = row.get("bug_id", "").strip()
                        if not bid or row.get("status") != "completed":
                            continue
                        # verdict == "error" means the model returned nothing -
                        # a network failure, not a judgement. Retry it, do not
                        # skip it, or --resume and the supervisor disagree and
                        # the arm stalls with those bugs never re-run.
                        if (row.get("verdict") or "").strip().lower() == "error":
                            continue
                        done.add(bid)
            except Exception:
                pass
        return done

    def _print_summary(self):
        total       = len(self.results)
        completed   = sum(1 for r in self.results if r.get("status") == "completed")
        # A fix requires BOTH a passing test run and a correct verdict.
        correct     = sum(
            1 for r in self.results
            if r.get("verdict") == "correct" and r.get("plausible")
        )
        plausible   = sum(1 for r in self.results if r.get("plausible"))
        judge_only  = sum(
            1 for r in self.results
            if r.get("verdict") == "correct" and not r.get("plausible")
        )
        vetoed      = sum(
            1 for r in self.results
            if r.get("plausible") and r.get("verdict") != "correct"
        )
        osc_aborts  = sum(1 for r in self.results if r.get("oscillation_abort"))
        broken      = sum(1 for r in self.results if r.get("status") == "build_broken")

        correct_single = sum(
            1 for r in self.results
            if r.get("verdict") == "correct" and r.get("plausible")
            and not r.get("is_multi_file")
        )
        correct_multi = sum(
            1 for r in self.results
            if r.get("verdict") == "correct" and r.get("plausible")
            and r.get("is_multi_file")
        )

        print("\n📊  SUMMARY")
        print("─" * 52)
        print(f"{'Total bugs:':34s} {total}")
        if total:
            print(f"{'Completed:':34s} {completed}  ({completed/total*100:.1f}%)")
            print(f"{'Plausible (suite passes):':34s} {plausible}  ({plausible/total*100:.1f}%)")
            print(f"{'Correctly fixed (plaus+judge):':34s} {correct}  ({correct/total*100:.1f}%)")
            print(f"{'  ↳ Judge said correct, tests FAILED:':34s} {judge_only}  (rejected by gate)")
            print(f"{'  ↳ tests passed, Judge vetoed:':34s} {vetoed}  (retained as plausible)")
            print(f"{'  ↳ single-file:':34s} {correct_single}")
            print(f"{'  ↳ multi-file:':34s} {correct_multi}")
            print(f"{'Oscillation aborts (multi only):':34s} {osc_aborts}")
            print(f"{'Build broken (skipped):':34s} {broken}")
        if completed:
            avg_iters = sum(r.get("iterations", 0) for r in self.results) / completed
            avg_time  = sum(r.get("time_seconds", 0) for r in self.results) / completed
            ttl_tok   = sum(r.get("total_tokens", 0) for r in self.results)
            ttl_usd   = sum(r.get("estimated_usd", 0.0) for r in self.results)
            print(f"{'Avg iterations:':34s} {avg_iters:.2f}")
            print(f"{'Avg time / bug:':34s} {avg_time:.0f} s")
            print(f"{'Total tokens:':34s} {ttl_tok:,}")
            print(f"{'Estimated cost:':34s} ${ttl_usd:.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def load_bug_list(filename: str) -> List[str]:
    bugs: List[str] = []
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                bugs.append(line)
    return bugs


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SV-ARP Defects4J benchmark runner")
    parser.add_argument("--bug-list", default=BUG_LIST_FILE)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--bug", default=None,
                        help="Run a single bug, e.g. Closure_103")
    args = parser.parse_args()

    if not D4J_HOME or not os.path.exists(D4J_HOME):
        print(f"❌  D4J_HOME not set or not found: {D4J_HOME!r}")
        sys.exit(1)

    benchmark = Defects4JBenchmark(resume=args.resume)

    if args.bug:
        try:
            project, bid = args.bug.split("_", 1)
            record = benchmark.run_single_bug(project, int(bid))
            print(json.dumps(record, indent=2, default=str))
        except Exception as e:
            print(f"❌  {e}")
            sys.exit(1)
    else:
        if not os.path.exists(args.bug_list):
            print(f"❌  Bug list not found: {args.bug_list}")
            sys.exit(1)
        bug_list = load_bug_list(args.bug_list)
        print(f"📋  Loaded {len(bug_list)} bugs from {args.bug_list}")
        benchmark.run_benchmark(bug_list)
