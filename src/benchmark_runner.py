"""
SV-APR Defects4J Benchmark Runner
==================================
Drives the full Defects4J evaluation loop:
  1. Checkout buggy version via `defects4j checkout`
  2. Extract modified classes and trigger tests
  3. Call AgenticRepairSystem.repair_bug()
  4. Record results to CSV + per-bug JSON log

Routing is automatic:
  len(per_file_sources) == 1  →  single-file strategy
  len(per_file_sources)  > 1  →  multi-file  strategy

Usage
-----
  # Full benchmark
  python benchmark_runner.py --bug-list benchmark/versions.txt

  # Single bug
  python benchmark_runner.py --bug Lang_1

  # Resume interrupted run
  python benchmark_runner.py --bug-list benchmark/versions.txt --resume

Environment variables
---------------------
  D4J_HOME          Path to Defects4J installation (required)
  GEMINI_API_KEY    Google Gemini API key (required)
  RESULTS_DIR       Output directory for CSV/JSON results (default: results)
  WORK_DIR          Checkout working directory (default: /tmp/d4j_benchmark)
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

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_APR_MODULE = "sv_apr"
if _APR_MODULE in sys.modules:
    importlib.reload(sys.modules[_APR_MODULE])

from sv_apr import (
    AgenticRepairSystem,
    TestResult,
    TestRunner,
    get_localized_context,
    PROJECT_SRC_DIRS,
    PROJECT_TEST_DIRS,
    NEEDS_COMPILE,
    print_result,
)


# ---------------------------------------------------------------------------
# Configuration (overridable via environment variables)
# ---------------------------------------------------------------------------

D4J_HOME    = os.environ.get("D4J_HOME", "")
WORK_DIR    = os.environ.get("WORK_DIR", "/tmp/d4j_benchmark")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "results")
PATCH_ROOT  = "patches"

PROJECT_PACKAGE_PREFIXES: Dict[str, str] = {
    "Chart":   "org.jfree",
    "Lang":    "org.apache.commons.lang",
    "Math":    "org.apache.commons.math",
    "Time":    "org.joda.time",
    "Closure": "com.google.javascript",
    "Mockito": "org.mockito",
}


def _d4j_cmd() -> str:
    if D4J_HOME:
        cmd = os.path.join(D4J_HOME, "framework", "bin", "defects4j")
        if os.path.exists(cmd):
            return cmd
    return "defects4j"


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

class Defects4JBenchmark:

    def __init__(self, resume: bool = False) -> None:
        self.system  = AgenticRepairSystem()
        self.results: List[Dict] = []
        self.resume  = resume
        os.makedirs(WORK_DIR,    exist_ok=True)
        os.makedirs(RESULTS_DIR, exist_ok=True)
        os.makedirs(PATCH_ROOT,  exist_ok=True)

    # -----------------------------------------------------------------------
    # Source-dir resolution
    # -----------------------------------------------------------------------

    def _resolve_src_dir(self, project_path: str, project: str) -> str:
        d4j = _d4j_cmd()
        for prop in ("dir.src.classes", "dir.src", "src.dir"):
            try:
                r = subprocess.run(
                    [d4j, "export", "-p", prop],
                    cwd=project_path, capture_output=True, text=True,
                    timeout=15, env=os.environ,
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

    # -----------------------------------------------------------------------
    # File resolution
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # Checkout
    # -----------------------------------------------------------------------

    def checkout_bug(self, project: str, bug_id: int) -> Optional[str]:
        bug_version = f"{bug_id}b"
        work_path   = os.path.join(WORK_DIR, f"{project}_{bug_id}")
        d4j         = _d4j_cmd()

        def _has_java(path: str) -> bool:
            return bool(list(Path(path).rglob("*.java")))

        if os.path.exists(work_path):
            if _has_java(work_path):
                print(f"  Already checked out: {work_path}")
                return work_path
            shutil.rmtree(work_path)

        for attempt in range(1, 3):
            print(f"  Checking out {project} {bug_version} (attempt {attempt}) …")
            try:
                r = subprocess.run(
                    [d4j, "checkout", "-p", project, "-v", bug_version, "-w", work_path],
                    capture_output=True, text=True, timeout=300, env=os.environ,
                )
                if r.returncode != 0:
                    print(f"  Checkout failed: {r.stderr[:300]}")
                    if os.path.exists(work_path):
                        shutil.rmtree(work_path)
                    continue
                if _has_java(work_path):
                    return work_path
                shutil.rmtree(work_path)
            except subprocess.TimeoutExpired:
                print("  Checkout timed out.")
                if os.path.exists(work_path):
                    shutil.rmtree(work_path)
        return None

    # -----------------------------------------------------------------------
    # Bug info extraction
    # -----------------------------------------------------------------------

    def extract_bug_info(
        self, project_path: str, project: str, bug_id: int
    ) -> Tuple[Optional[str], List[str], List[str], List[str], Dict[str, str]]:
        """
        Returns
        -------
        primary_source   : text of the first modified file
        failing_tests    : tests.trigger list
        buggy_file_paths : all modified file paths on disk
        modified_classes : FQN list from defects4j export
        per_file_sources : {filepath: source_text} for every modified file

        Strategy selection (handled automatically in AgenticRepairSystem):
          len(per_file_sources) == 1  →  single-file
          len(per_file_sources)  > 1  →  multi-file
        """
        d4j     = _d4j_cmd()
        src_dir = self._resolve_src_dir(project_path, project)

        modified_classes: List[str] = []
        try:
            r = subprocess.run(
                [d4j, "export", "-p", "classes.modified"],
                cwd=project_path, capture_output=True, text=True,
                timeout=15, env=os.environ,
            )
            if r.returncode == 0:
                modified_classes = [
                    c.strip() for c in r.stdout.strip().splitlines() if c.strip()
                ]
            print(f"  Modified classes: {modified_classes}")
        except Exception as exc:
            print(f"  Export classes.modified failed: {exc}")

        buggy_file_paths: List[str] = []
        for cls in modified_classes:
            fp = self._find_java_file(project_path, src_dir, cls)
            if fp:
                buggy_file_paths.append(fp)
            else:
                print(f"  Cannot locate file for class: {cls}")

        if not buggy_file_paths:
            java_files = list(Path(project_path).rglob("*.java"))
            if java_files:
                buggy_file_paths = [str(java_files[0])]
                print(f"  Fallback file: {buggy_file_paths[0]}")
            else:
                return None, [], [], modified_classes, {}

        per_file_sources: Dict[str, str] = {}
        for fp in buggy_file_paths:
            try:
                per_file_sources[fp] = Path(fp).read_text(encoding="utf-8")
            except Exception as exc:
                print(f"  Could not read {fp}: {exc}")

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
                timeout=15, env=os.environ,
            )
            if r.returncode == 0 and r.stdout.strip():
                failing_tests = [
                    t.strip() for t in r.stdout.strip().splitlines() if t.strip()
                ]
            print(f"  Failing tests: {failing_tests}")
        except Exception as exc:
            print(f"  Export tests.trigger failed: {exc}")

        return primary_source, failing_tests, buggy_file_paths, modified_classes, per_file_sources

    # -----------------------------------------------------------------------
    # Error info builder
    # -----------------------------------------------------------------------

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
            lines.append("No specific test info available — fix based on code analysis.")
        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Backup / restore
    # -----------------------------------------------------------------------

    @staticmethod
    def _backup(file_paths: List[str]) -> Dict[str, str]:
        backups: Dict[str, str] = {}
        for fp in file_paths:
            if fp and os.path.exists(fp):
                bak = fp + ".bak"
                shutil.copy2(fp, bak)
                backups[fp] = bak
        return backups

    @staticmethod
    def _restore(backups: Dict[str, str]) -> None:
        for orig, bak in backups.items():
            if os.path.exists(bak):
                shutil.copy2(bak, orig)
                os.remove(bak)

    # -----------------------------------------------------------------------
    # Baseline compile check
    # -----------------------------------------------------------------------

    @staticmethod
    def _baseline_compiles(project_path: str, project: str) -> bool:
        if project not in NEEDS_COMPILE:
            return True
        d4j = _d4j_cmd()
        try:
            r = subprocess.run(
                [d4j, "compile"],
                cwd=project_path, capture_output=True, text=True,
                timeout=180, env=os.environ,
            )
            return r.returncode == 0
        except Exception:
            return False

    # -----------------------------------------------------------------------
    # Single-bug runner
    # -----------------------------------------------------------------------

    def run_single_bug(self, project: str, bug_id: int) -> Dict:
        bug_str = f"{project}_{bug_id}"
        print(f"\n{'─' * 60}")
        print(f"  {bug_str}")
        print(f"{'─' * 60}")

        project_path = self.checkout_bug(project, bug_id)
        if not project_path:
            return self._fail_record(bug_str, "checkout_failed", "Checkout failed")

        if not self._baseline_compiles(project_path, project):
            return self._fail_record(bug_str, "build_broken", "Baseline does not compile")

        (
            primary_source,
            failing_tests,
            buggy_file_paths,
            modified_classes,
            per_file_sources,
        ) = self.extract_bug_info(project_path, project, bug_id)

        if primary_source is None:
            return self._fail_record(bug_str, "extraction_failed", "Could not extract buggy code")

        is_multi_file = len(per_file_sources) > 1

        if failing_tests:
            localized = get_localized_context(primary_source, failing_tests, project)
        else:
            localized = primary_source[:8_000]

        error_info = self._build_error_info(project, bug_id, failing_tests, modified_classes)
        backups    = self._backup(buggy_file_paths)

        print("  Baseline test on buggy version …")
        baseline = TestRunner.run_defects4j_tests(
            project_path, project, trigger_tests=failing_tests or None,
        )
        print(f"  Baseline failing: {len(baseline.failing_tests)}")
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

            has_patch = result.final_patch is not None or bool(result.final_patches)

            record = {
                "bug_id":            bug_str,
                "status":            "completed",
                "verdict":           result.judge_verdict.value,
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

            if result.judge_verdict.value == "correct":
                if result.final_patches:
                    for fp, patch_text in result.final_patches.items():
                        rel = os.path.relpath(fp, project_path)
                        self._write_patch(bug_str, patch_text, rel)
                elif result.final_patch and buggy_file_paths:
                    rel = os.path.relpath(buggy_file_paths[0], project_path)
                    self._write_patch(bug_str, result.final_patch, rel)

            return record

        except Exception as exc:
            import traceback
            traceback.print_exc()
            return self._fail_record(bug_str, "failed", str(exc))
        finally:
            self._restore(backups)
            time.sleep(8)

    # -----------------------------------------------------------------------
    # Full benchmark runner
    # -----------------------------------------------------------------------

    def run_benchmark(self, bug_list: List[str]) -> None:
        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(RESULTS_DIR, f"results_{timestamp}.csv")

        done: set = set()
        if self.resume:
            done = self._load_done_bugs(RESULTS_DIR)
            print(f"  Resume mode: {len(done)} bugs already completed, skipping.")

        print(f"\n{'=' * 60}")
        print(f"  SV-APR Benchmark — {len(bug_list)} bugs")
        print(f"  Results → {results_file}")
        print(f"{'=' * 60}\n")

        for i, bug_str in enumerate(bug_list, 1):
            print(f"\n[{i}/{len(bug_list)}]", end=" ")

            if bug_str in done:
                print(f"SKIP {bug_str} (already done)")
                continue

            try:
                project, bid_str = bug_str.split("_", 1)
                bug_id = int(bid_str)
            except ValueError:
                print(f"Invalid format: {bug_str}")
                continue

            record = self.run_single_bug(project, bug_id)
            self.results.append(record)
            self._save_csv(results_file)

            status   = record.get("status", "?")
            verdict  = record.get("verdict", "")
            strategy = record.get("strategy", "?")
            if status == "completed":
                osc  = " [oscillation-abort]" if record.get("oscillation_abort") else ""
                print(
                    f"  {bug_str}: {verdict} [{strategy}] "
                    f"({record.get('iterations', 0)} iters, "
                    f"{record.get('time_seconds', 0):.0f} s){osc}"
                )
            else:
                print(f"  {bug_str}: {status} — {record.get('error', '')[:80]}")

        print(f"\n{'=' * 60}")
        print("  Benchmark complete")
        print(f"  Results: {results_file}")
        self._print_summary()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _fail_record(bug_id: str, status: str, error: str) -> Dict:
        return {
            "bug_id":            bug_id,
            "status":            status,
            "verdict":           "",
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

    def _write_json_log(self, bug_id: str, record: Dict, history: List[Dict]) -> None:
        log_dir = os.path.join(RESULTS_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        payload = {**record, "history": history}
        with open(os.path.join(log_dir, f"{bug_id}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    def _write_patch(self, bug_id: str, patch_text: str, source_path: str) -> None:
        if not patch_text.strip():
            return
        out_dir  = os.path.join(PATCH_ROOT, bug_id, os.path.dirname(source_path))
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(PATCH_ROOT, bug_id, source_path)
        Path(out_file).write_text(patch_text, encoding="utf-8")
        print(f"  Patch → {out_file}")

    def _save_csv(self, filename: str) -> None:
        if not self.results:
            return
        fieldnames = sorted({k for r in self.results for k in r})
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)

    @staticmethod
    def _load_done_bugs(results_dir: str) -> set:
        done: set = set()
        for csv_path in Path(results_dir).glob("results_*.csv"):
            try:
                with open(csv_path, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        bid = row.get("bug_id", "").strip()
                        if bid and row.get("status") == "completed":
                            done.add(bid)
            except Exception:
                pass
        return done

    def _print_summary(self) -> None:
        total     = len(self.results)
        completed = sum(1 for r in self.results if r.get("status") == "completed")
        correct   = sum(1 for r in self.results if r.get("verdict") == "correct")
        osc       = sum(1 for r in self.results if r.get("oscillation_abort"))
        broken    = sum(1 for r in self.results if r.get("status") == "build_broken")

        correct_single = sum(
            1 for r in self.results
            if r.get("verdict") == "correct" and not r.get("is_multi_file")
        )
        correct_multi = sum(
            1 for r in self.results
            if r.get("verdict") == "correct" and r.get("is_multi_file")
        )

        print("\n  SUMMARY")
        print("  " + "─" * 50)
        print(f"  {'Total bugs:':32s} {total}")
        if total:
            print(f"  {'Completed:':32s} {completed}  ({completed / total * 100:.1f}%)")
            print(f"  {'Correctly fixed:':32s} {correct}  ({correct / total * 100:.1f}%)")
            print(f"  {'  single-file:':32s} {correct_single}")
            print(f"  {'  multi-file:':32s} {correct_multi}")
            print(f"  {'Oscillation aborts:':32s} {osc}")
            print(f"  {'Build broken (skipped):':32s} {broken}")
        if completed:
            avg_iters = sum(r.get("iterations", 0) for r in self.results) / completed
            avg_time  = sum(r.get("time_seconds", 0) for r in self.results) / completed
            ttl_tok   = sum(r.get("total_tokens", 0) for r in self.results)
            ttl_usd   = sum(r.get("estimated_usd", 0.0) for r in self.results)
            print(f"  {'Avg iterations:':32s} {avg_iters:.2f}")
            print(f"  {'Avg time / bug:':32s} {avg_time:.0f} s")
            print(f"  {'Total tokens:':32s} {ttl_tok:,}")
            print(f"  {'Estimated cost:':32s} ${ttl_usd:.4f}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _load_bug_list(filename: str) -> List[str]:
    bugs: List[str] = []
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                bugs.append(line)
    return bugs


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SV-APR Defects4J Benchmark Runner")
    parser.add_argument(
        "--bug-list", default="benchmark/versions.txt",
        help="Path to newline-separated bug list file",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip bugs already in a results CSV in RESULTS_DIR",
    )
    parser.add_argument(
        "--bug", default=None, metavar="PROJECT_ID",
        help="Run a single bug, e.g. --bug Lang_1",
    )
    args = parser.parse_args()

    if not D4J_HOME or not os.path.exists(D4J_HOME):
        print(
            "ERROR: D4J_HOME is not set or does not exist.\n"
            "  export D4J_HOME=/path/to/defects4j"
        )
        sys.exit(1)

    benchmark = Defects4JBenchmark(resume=args.resume)

    if args.bug:
        try:
            project, bid = args.bug.split("_", 1)
            record = benchmark.run_single_bug(project, int(bid))
            print(json.dumps(record, indent=2, default=str))
        except Exception as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
    else:
        if not os.path.exists(args.bug_list):
            print(f"ERROR: Bug list not found: {args.bug_list}")
            sys.exit(1)
        bug_list = _load_bug_list(args.bug_list)
        print(f"  Loaded {len(bug_list)} bugs from {args.bug_list}")
        benchmark.run_benchmark(bug_list)
