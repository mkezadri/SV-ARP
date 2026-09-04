"""
SV-ARP: Self-Verifying Agentic Repair Pipeline
=================================================
Architecture
------------
  RepairAgent  →  generates candidate patch (full file replacement)
  TestRunner   →  executes Defects4J test suite against the patch
  JudgeAgent   →  structured code review: verdict + line-level suggestions
  LangGraph    →  orchestrates the repair → test → judge loop (≤ MAX_ITERATIONS)

A patch is accepted only when it BOTH passes the test suite AND receives a
`correct` verdict from the JudgeAgent. The JudgeAgent evaluates every candidate,
including those whose tests pass, so it can reject plausible-but-incorrect
patches.

Five adaptive warning mechanisms respond to distinct failure modes:
  1. Compile-error specialisation   — rules to avoid inventing non-existent symbols
  2. Concrete judge suggestions     — line-level "change X to Y" format enforced
  3. Regression scoping             — targeted constraint when non-trigger tests break
  4. Surgical mode                  — micro-focused prompt after 3+ consecutive no-ops
  5. Oscillation / repetition guard — temperature escalation + explicit cycle warnings

Supported projects (Defects4J V1.2):
  Chart, Closure, Lang, Math, Mockito, Time
"""

import os
import json
import time
import logging
import difflib
import hashlib
import re
import random
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, TypedDict, Literal

import google.genai as genai
from google.genai import types

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("V_apr")

# ─────────────────────────────────────────────────────────────────────────────
# API client
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    raise ValueError("Set GEMINI_API_KEY before running.")

client = genai.Client(api_key=GEMINI_API_KEY)


class QuotaExhausted(RuntimeError):
    """The API quota has been exhausted for the day."""


available_models = [m.name for m in client.models.list()]
if "models/gemini-2.5-flash" in available_models:
    print("Model found!")
else:
    print("Model not found. Available names:", available_models)
    

REPAIR_MODEL = "gemini-3.1-flash-lite"
JUDGE_MODEL  = "gemini-3.1-flash-lite"

GENERATION_CONFIG = dict(temperature=0.1, top_p=0.95, top_k=40, max_output_tokens=20_000)

LARGE_FILE_LINE_THRESHOLD = 800
LARGE_FILE_MAX_TOKENS     = 32_000

MAX_ITERATIONS = 4

MAX_ITERATIONS_BY_PROJECT: Dict[str, int] = {
    "Closure": 4,
    "Chart":   4,
}

OSCILLATION_SIMILARITY = 0.99
OSCILLATION_WINDOW     = 3


# ─────────────────────────────────────────────────────────────────────────────
EDIT_MODE = os.environ.get("APR_EDIT_MODE", "search_replace")

# Number of extra generation attempts allowed when the model returns an
# unusable edit (no-op / unparseable / non-matching SEARCH block).
# These do NOT consume a repair iteration.
MAX_GENERATION_RETRIES = 2

# A localised bug should not rewrite half the file. Diffs larger than this are
# flagged to the Judge as suspicious drift.
DRIFT_LINE_THRESHOLD = 60


REQUIRE_TESTS_PASS_TO_ACCEPT = True

# ─────────────────────────────────────────────────────────────────────────────
# [ABLATION] Component switches. Default = full system; each flag removes ONE
# component so its contribution can be measured in isolation. All are read from
# the environment so no code edit is needed between arms.
#
#   APR_ABLATION=full            all components active (default)
#   APR_ABLATION=no_judge        accept on the test suite alone
#   APR_ABLATION=no_semantic     Judge gates, but its prose/suggestions are
#                                withheld from the repair prompt
#   APR_ABLATION=no_test_fb      test output withheld from the repair prompt
#                                (the suite still decides acceptance)
#   APR_ABLATION=whole_file      legacy whole-file regeneration (= FIX-A off)
#   APR_ABLATION=no_baseline     strict zero-failure scoring (= FIX-F off);
#                                measures the cost of the oracle defect
#   APR_ABLATION=single_iter     one iteration, no feedback loop at all
# ─────────────────────────────────────────────────────────────────────────────
ABLATION = os.environ.get("APR_ABLATION", "full").strip().lower()

_VALID_ABLATIONS = {
    "full", "no_judge", "no_semantic", "no_test_fb",
    "whole_file", "no_baseline", "single_iter",
    "binary_only",                                    # ← add
}
if ABLATION not in _VALID_ABLATIONS:
    raise SystemExit(
        f"APR_ABLATION={ABLATION!r} is not one of {sorted(_VALID_ABLATIONS)}"
    )

ABL_SKIP_JUDGE       = ABLATION == "no_judge"
ABL_BINARY_ONLY      = ABLATION == "binary_only"
ABL_NO_SEMANTIC_FB   = ABLATION == "no_semantic"
ABL_NO_TEST_FB       = ABLATION == "no_test_fb"
ABL_NO_BASELINE_SUB  = ABLATION == "no_baseline"
ABL_SINGLE_ITER      = ABLATION == "single_iter"

if ABLATION == "whole_file":
    EDIT_MODE = "whole_file"
if ABL_SINGLE_ITER:
    MAX_ITERATIONS = 1

PROJECT_SRC_DIRS: Dict[str, List[str]] = {
    "Chart":       ["source"],
    "Lang":        ["src/main/java", "src"],
    "Math":        ["src/main/java", "src"],
    "Time":        ["src/main/java", "src"],
    "Closure":     ["src"],
    "Mockito":     ["src/main/java", "src"],
    "Collections": ["src/main/java"],
}

PROJECT_TEST_DIRS: Dict[str, List[str]] = {
    "Chart":       ["tests", "test", "src/test/java"],
    "Lang":        ["src/test/java"],
    "Math":        ["src/test/java"],
    "Time":        ["src/test/java"],
    "Closure":     ["test"],
    "Mockito":     ["test", "src/test/java"],
    "Collections": ["src/test/java"],
}

NEEDS_COMPILE = {"Closure", "Chart"}


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

class Verdict(Enum):
    CORRECT        = "correct"
    INCORRECT      = "incorrect"
    NEEDS_REVISION = "needs_revision"
    ERROR          = "error"


@dataclass
class TestResult:
    passed:        bool
    output:        str
    error_message: Optional[str]
    failing_tests: List[str]


@dataclass
class RepairResult:
    buggy_code:      str
    final_patches:   Dict[str, str]
    final_patch:     Optional[str]
    iteration_count: int
    judge_verdict:   Verdict
    judge_reason:    str
    plausible:       bool
    history:         List[Dict]
    cost_estimate:   Dict[str, Any]
    execution_time:  float
    # [FIX-D] the retained test-passing patch (may differ from final_patch).
    # Defaulted fields must come last in a dataclass.
    plausible_patch:     Optional[str] = None
    plausible_iteration: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def unified_diff(original: str, patched: str,
                 fromfile: str = "original", tofile: str = "patched") -> str:
    orig_lines  = original.splitlines(keepends=True)
    patch_lines = patched.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, patch_lines,
                                fromfile=fromfile, tofile=tofile, lineterm="")
    return "".join(diff)[:8000]


def patch_similarity(a: str, b: str) -> float:
    a, b = a.strip(), b.strip()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def patch_fingerprint(patch: str) -> str:
    return hashlib.md5(patch.strip().encode()).hexdigest()


def combined_fingerprint(per_file_patches: Dict[str, str]) -> str:
    combined = "||".join(
        f"{fp}::{patch_fingerprint(text)}"
        for fp, text in sorted(per_file_patches.items())
    )
    return hashlib.md5(combined.encode()).hexdigest()


def extract_code_block(text: str, lang: str = "java") -> str:
    pattern = rf"```(?:{lang})?\n(.*?)\n```"
    match   = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def extract_json_block(text: str) -> str:
    text = text.strip()
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text.split(fence, 1)[1]
            text = text.rsplit("```", 1)[0]
            break
    text = text.strip()
    try:
        obj, _ = json.JSONDecoder().raw_decode(text)
        return json.dumps(obj)
    except (json.JSONDecodeError, ValueError):
        return text


def extract_focused_snippet(full_code: str, lines: List[int], context: int = 5) -> str:
    all_lines = full_code.splitlines()
    snippet_parts = []
    for line_num in sorted(set(lines)):
        lo = max(0, line_num - context)
        hi = min(len(all_lines), line_num + context + 1)
        snippet = "\n".join(all_lines[lo:hi])
        snippet_parts.append(f"// --- Focus around line {line_num+1} ---\n{snippet}")
    return "\n\n".join(snippet_parts)



def normalise_source(s: str) -> str:
    """Whitespace-insensitive normalisation for equality checks."""
    return re.sub(r"\s+", " ", s or "").strip()


def is_noop_patch(original: str, patched: str) -> bool:
    """True when the model returned the input unchanged (the 'echo' failure).

    The legacy length guard (output < 70% of original) cannot detect this:
    an exact copy is 100% of the original length.
    """
    if not patched:
        return True
    return normalise_source(original) == normalise_source(patched)


def count_changed_lines(original: str, patched: str) -> int:
    """Number of added+removed lines between two versions."""
    diff = difflib.unified_diff(
        original.splitlines(), patched.splitlines(), lineterm="", n=0
    )
    return sum(
        1 for l in diff
        if (l.startswith("+") or l.startswith("-"))
        and not l.startswith(("+++", "---"))
    )


SR_BLOCK_RE = re.compile(
    r"<{5,}\s*SEARCH\s*\n(.*?)\n={5,}\s*\n(.*?)\n>{5,}\s*REPLACE",
    re.DOTALL,
)


def parse_search_replace(text: str) -> List[Tuple[str, str]]:
    """Extract (search, replace) pairs from a model response."""
    return [(m.group(1), m.group(2)) for m in SR_BLOCK_RE.finditer(text or "")]


def apply_search_replace(
    original: str, blocks: List[Tuple[str, str]]
) -> Tuple[Optional[str], str]:
    """Apply SEARCH/REPLACE blocks to `original`.

    Returns (new_source, ""), or (None, reason) if any block cannot be applied
    unambiguously. Refusing ambiguous edits is deliberate: a silently
    mis-applied edit is far worse than a retry.
    """
    if not blocks:
        return None, "no SEARCH/REPLACE block found in response"

    out = original
    for i, (search, replace) in enumerate(blocks, 1):
        if not search.strip():
            return None, f"block {i}: empty SEARCH section"
        n = out.count(search)
        if n == 0:
            # tolerate trailing-whitespace differences before giving up
            loose = "\n".join(l.rstrip() for l in search.splitlines())
            out_l = "\n".join(l.rstrip() for l in out.splitlines())
            if out_l.count(loose) == 1:
                out = out_l.replace(loose, replace, 1)
                continue
            return None, f"block {i}: SEARCH text not found in source"
        if n > 1:
            return None, f"block {i}: SEARCH text matches {n} times (ambiguous)"
        out = out.replace(search, replace, 1)
    return out, ""


def build_search_replace_instructions() -> str:
    return (
        "═══════════════════════════════════════\n"
        "OUTPUT FORMAT — READ CAREFULLY\n"
        "═══════════════════════════════════════\n"
        "Do NOT output the whole file. Output ONLY the minimal edits, each as a\n"
        "SEARCH/REPLACE block in exactly this format:\n\n"
        "<<<<<<< SEARCH\n"
        "<lines copied EXACTLY from the original file>\n"
        "=======\n"
        "<the replacement lines>\n"
        ">>>>>>> REPLACE\n\n"
        "Rules:\n"
        "1. The SEARCH section must match the original file byte for byte,\n"
        "   including indentation. Copy it; do not retype it.\n"
        "2. The SEARCH section must be unique in the file. Include a few\n"
        "   surrounding lines if needed to disambiguate.\n"
        "3. Emit one block per edit site. Most bugs need exactly one.\n"
        "4. Change as little as possible. Do not reformat untouched code.\n"
        "5. Output nothing except the blocks — no prose, no markdown fences.\n\n"
        "EDITS:\n"
    )


# Helper: detect compile-only failures
def _is_compile_error(tr: Optional[TestResult]) -> bool:
    """Returns True when test runner reports a compile failure (no tests ran)."""
    if tr is None or tr.passed:
        return False
    return (
        not tr.failing_tests
        and tr.error_message in ("Compilation failed", "Compile timed out")
    )


# ─────────────────────────────────────────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────────────────────────────────────────

class TestRunner:

    @staticmethod
    def _d4j_cmd() -> str:
        d4j_home = os.environ.get("D4J_HOME", "")
        cmd = os.path.join(d4j_home, "framework", "bin", "defects4j")
        return cmd if os.path.exists(cmd) else "defects4j"

    @staticmethod
    def _detect_project(project_path: str) -> str:
        dirname = os.path.basename(project_path.rstrip("/\\"))
        for name in PROJECT_SRC_DIRS:
            if dirname.startswith(name):
                return name
        for name in PROJECT_SRC_DIRS:
            if name.lower() in project_path.lower():
                return name
        return ""

    @staticmethod
    def _parse_failing_tests(output: str) -> List[str]:
        failing: List[str] = []
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and "::" in stripped:
                failing.append(stripped[2:].strip())
        if failing:
            return list(dict.fromkeys(failing))
        sf_re = re.compile(r"(\w+)\(([^)]+)\).*?(?:FAILURE|ERROR)", re.I)
        for m in sf_re.finditer(output):
            failing.append(f"{m.group(2)}::{m.group(1)}")
        if failing:
            return list(dict.fromkeys(failing))
        for line in output.splitlines():
            if "FAILED" in line:
                m = re.search(r"([\w.]+(?:::|\.)\w+)", line)
                if m:
                    failing.append(m.group(1))
        return list(dict.fromkeys(failing))

    @classmethod
    def run_defects4j_tests(
        cls,
        project_path:  str,
        project_name:  str = "",
        trigger_tests: Optional[List[str]] = None,
    ) -> TestResult:
        d4j  = cls._d4j_cmd()
        proj = project_name or cls._detect_project(project_path)

        if proj in NEEDS_COMPILE:
            logger.info("Running 'defects4j compile' for %s …", proj)
            try:
                r = subprocess.run(
                    [d4j, "compile"], cwd=project_path,
                    capture_output=True, text=True, timeout=180, env=os.environ
                )
                out = r.stdout + r.stderr
                if r.returncode != 0:
                    logger.error("Compile FAILED:\n%s", out[:800])
                    return TestResult(False, out, "Compilation failed", [])
                logger.info("Compile OK")
            except subprocess.TimeoutExpired:
                return TestResult(False, "", "Compile timed out", [])
            except Exception as e:
                return TestResult(False, "", f"Compile error: {e}", [])

        try:
            r = subprocess.run(
                [d4j, "test", "-r"], cwd=project_path,
                capture_output=True, text=True, timeout=600, env=os.environ
            )
            output = r.stdout + r.stderr

            if r.returncode == 0 and re.search(r"Failing tests:\s*0", output):
                return TestResult(True, output, None, [])
            if r.returncode == 0 and "Failing tests:" not in output:
                return TestResult(True, output, None, [])

            all_failing = cls._parse_failing_tests(output)

            if trigger_tests:
                trigger_set    = set(trigger_tests)
                relevant_lines = [
                    line for line in output.splitlines()
                    if any(t.split("::")[-1] in line or t in line
                           for t in trigger_set)
                ]
                filtered_output   = "\n".join(relevant_lines) if relevant_lines else output[:3000]
                trigger_failing   = [f for f in all_failing if f in trigger_set]
                effective_failing = trigger_failing if trigger_failing else all_failing
                regressions_now   = [f for f in all_failing if f not in trigger_set]
                logger.info(
                    "Trigger filter: %d total failing → %d target, %d regression(s)",
                    len(all_failing), len(trigger_failing), len(regressions_now),
                )
                return TestResult(
                    passed        = len(effective_failing) == 0,
                    output        = filtered_output,
                    error_message = r.stderr or None,
                    # [FIX-E fix] Return EVERY failing test, not just the
                    # trigger subset. Previously, when the target test still
                    # failed, `effective_failing` dropped the regressions before
                    # anything downstream could see them — so the Judge was
                    # never told the patch had broken other tests.
                    # `passed` is unchanged: it is still driven by
                    # effective_failing.
                    failing_tests = all_failing,
                )

            return TestResult(False, output, r.stderr or None, all_failing)

        except subprocess.TimeoutExpired:
            return TestResult(False, "", "Test timed out (600 s)", [])
        except Exception as e:
            return TestResult(False, "", str(e), [])

    @staticmethod
    def run_python_tests(code: str, test_code: Optional[str] = None) -> TestResult:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "program.py").write_text(code)
            if test_code:
                tf = Path(tmp) / "test_program.py"
                tf.write_text(test_code)
                try:
                    r = subprocess.run(
                        ["pytest", str(tf), "-v", "--tb=short"],
                        cwd=tmp, capture_output=True, text=True, timeout=30
                    )
                    if r.returncode == 0:
                        return TestResult(True, r.stdout, None, [])
                    failing = [
                        ln.split()[0] for ln in r.stdout.splitlines()
                        if "FAILED" in ln and ln.split()
                    ]
                    return TestResult(False, r.stdout, r.stderr, failing)
                except subprocess.TimeoutExpired:
                    return TestResult(False, "", "Timed out", [])
                except FileNotFoundError:
                    return TestResult(False, "", "pytest not found", [])
            try:
                exec(code, {})
                return TestResult(True, "OK", None, [])
            except Exception as e:
                return TestResult(False, "", str(e), [])


# ─────────────────────────────────────────────────────────────────────────────
# TEST SOURCE FETCHER
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceFetcher:

    @staticmethod
    def _fqn_to_path(fqn: str) -> str:
        cls_name = fqn.split("::")[0] if "::" in fqn else fqn
        return cls_name.replace(".", "/") + ".java"

    @classmethod
    def fetch(
        cls,
        project_path:  str,
        project_name:  str,
        failing_tests: List[str],
        max_chars:     int = 4000,
    ) -> str:
        test_dirs = PROJECT_TEST_DIRS.get(project_name, ["test", "src/test/java"])
        collected: List[str] = []

        for test_fqn in failing_tests:
            rel_path    = cls._fqn_to_path(test_fqn)
            filename    = rel_path.split("/")[-1]
            method_name = test_fqn.split("::")[-1] if "::" in test_fqn else ""
            found_path: Optional[str] = None

            for tdir in test_dirs:
                candidate = os.path.join(project_path, tdir, rel_path)
                if os.path.exists(candidate):
                    found_path = candidate
                    break

            if not found_path:
                for root, _, files in os.walk(project_path):
                    if filename in files:
                        found_path = os.path.join(root, filename)
                        logger.info(
                            "TestSourceFetcher: found %s via walk at %s",
                            test_fqn, found_path,
                        )
                        break

            if not found_path:
                logger.warning(
                    "TestSourceFetcher: COULD NOT LOCATE source for %s", test_fqn
                )
                collected.append(
                    f"// ⚠ COULD NOT LOCATE test source for: {test_fqn}\n"
                    f"//   Infer expected behaviour from bug description and error output.\n"
                )
                continue

            try:
                source_text = Path(found_path).read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("TestSourceFetcher: read error for %s: %s", found_path, e)
                collected.append(f"// Error reading {found_path}: {e}\n")
                continue

            snippet = (
                cls._extract_method(source_text, method_name)
                if method_name
                else "\n".join(source_text.splitlines()[:80])
            )
            collected.append(
                f"// === Failing test: {test_fqn} ===\n"
                f"// Source: {os.path.relpath(found_path, project_path)}\n"
                f"{snippet}\n"
            )

        result = "\n".join(collected)
        return result[:max_chars] if len(result) > max_chars else result

    @staticmethod
    def _extract_method(
        source: str, method_name: str, context_lines: int = 10
    ) -> str:
        lines     = source.splitlines()
        start_idx: Optional[int] = None
        for i, line in enumerate(lines):
            if re.search(rf"\b{re.escape(method_name)}\s*\(", line):
                start_idx = max(0, i - 3)
                break
        if start_idx is None:
            return "\n".join(lines[:60])

        depth, end_idx, in_method = 0, start_idx, False
        for i in range(start_idx, min(len(lines), start_idx + 200)):
            for ch in lines[i]:
                if ch == "{":
                    depth += 1; in_method = True
                elif ch == "}":
                    depth -= 1
            if in_method and depth == 0:
                end_idx = i
                break

        lo = max(0, start_idx - context_lines)
        hi = min(len(lines), end_idx + context_lines + 1)
        return "\n".join(lines[lo:hi])


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI BASE AGENT
# ─────────────────────────────────────────────────────────────────────────────

class GeminiAgent:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.logger     = logging.getLogger(self.__class__.__name__)

    def _call(
        self,
        prompt:            str,
        expect_json:       bool            = False,
        max_retries:       int             = 6,
        max_output_tokens: Optional[int]   = None,
        temperature:       Optional[float] = None,
    ) -> Tuple[str, Dict]:
        effective_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else GENERATION_CONFIG["max_output_tokens"]
        )
        effective_temp = (
            temperature
            if temperature is not None
            else GENERATION_CONFIG["temperature"]
        )
        usage: Dict[str, int] = {}
        for attempt in range(max_retries):
            try:
                cfg = types.GenerateContentConfig(
                    temperature        = effective_temp,
                    top_p              = GENERATION_CONFIG["top_p"],
                    top_k              = GENERATION_CONFIG["top_k"],
                    max_output_tokens  = effective_tokens,
                    response_mime_type = (
                        "application/json" if expect_json else "text/plain"
                    ),
                )
                response = client.models.generate_content(
                    model=self.model_name, contents=prompt, config=cfg
                )
                if not response.candidates or not response.candidates[0].content.parts:
                    finish = (
                        response.candidates[0].finish_reason
                        if response.candidates else "unknown"
                    )
                    self.logger.error("No content. finish_reason=%s", finish)
                    return "", {}

                candidate = response.candidates[0]
                text      = candidate.content.parts[0].text
                try:
                    um = response.usage_metadata
                    usage = {
                        "prompt_tokens":    getattr(um, "prompt_token_count", 0),
                        "candidate_tokens": getattr(um, "candidates_token_count", 0),
                        "total_tokens":     getattr(um, "total_token_count", 0),
                    }
                except Exception:
                    usage = {"total_tokens": len(prompt) // 4 + len(text) // 4}

                if expect_json:
                    text = extract_json_block(text)
                return text.strip(), usage

            except QuotaExhausted:
                raise
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "too many requests" in err or "quota" in err:
                    # Gemini returns RESOURCE_EXHAUSTED for BOTH the per-minute
                    # rate limit and the per-day quota. Only the latter means
                    # the run cannot continue. The quotaId in the error
                    # distinguishes them, e.g.
                    #   ...RequestsPerMinutePerProjectPerModel-FreeTier
                    #   ...RequestsPerDayPerProjectPerModel-FreeTier
                    is_daily = any(k in err for k in (
                        "perday", "per day", "requests per day", "rpd",
                        "requestsperdayper", "daily limit", "per-day",
                        "per_day", "_per_day", "perdayper",
                    ))
                    is_minute = any(k in err for k in (
                        "perminute", "per minute", "requests per minute", "rpm",
                        "requestsperminuteper", "per-minute",
                    ))
                    if is_daily and not is_minute:
                        raise QuotaExhausted(
                            "daily API quota exhausted; resume with --resume"
                        )

                    # Ambiguous or per-minute: back off and retry.
                    wait = min(120, (2 ** attempt) * 10 + random.uniform(1, 5))
                    self.logger.warning(
                        "Rate limited (%s) — waiting %.1f s (attempt %d/%d)",
                        "per-minute" if is_minute else "unclassified",
                        wait, attempt + 1, max_retries,
                    )
                    time.sleep(wait)
                else:
                    self.logger.error("API error: %s", e)
                    return "", {}
        self.logger.error("Max retries reached")
        return "", {}


# ─────────────────────────────────────────────────────────────────────────────
# REPAIR AGENT
# ─────────────────────────────────────────────────────────────────────────────

class RepairAgent(GeminiAgent):

    def generate_fix(
        self,
        full_buggy_code:   str,
        error_info:        Optional[str]   = None,
        feedback:          Optional[Dict]  = None,
        project_name:      str             = "",
        test_source:       str             = "",
        conversation_log:  List[Dict]      = None,
        file_label:        str             = "",
        repeat_warning:    str             = "",
        noop_warning:      str             = "",
        temperature:       Optional[float] = None,
    ) -> Tuple[str, Dict]:

        file_ctx = f" (file: {file_label})" if file_label else ""

        test_block = (
            f"\n**Failing test source{file_ctx} — read carefully:**\n"
            f"```java\n{test_source}\n```\n"
            if test_source else ""
        )

        focus_block = ""
        if feedback and feedback.get("focus_snippet"):
            focus_block = (
                "\n═══════════════════════════════════════\n"
                "FOCUS ON THESE LINES (likely location of the bug)\n"
                "═══════════════════════════════════════\n"
                f"```java\n{feedback['focus_snippet']}\n```\n\n"
            )

        history_block = ""
        if ABL_NO_SEMANTIC_FB:
            conversation_log = [
                e for e in (conversation_log or []) if e.get("role") != "judge"
            ]
        if conversation_log:
            lines = ["**Previous iteration attempts and judge feedback:**"]
            for entry in conversation_log:
                if entry["role"] == "repair":
                    lines.append(
                        f"\n--- Iteration {entry['iteration']} repair{file_ctx} ---\n"
                        "[patch shown in context above]\n"
                    )
                elif entry["role"] == "judge":
                    lines.append(
                        f"--- Iteration {entry['iteration']} judge: "
                        f"{entry['verdict']} ---\n"
                        f"Reason: {entry['reason']}\n"
                        f"Issues: {entry.get('issues', [])}\n"
                        f"Suggestions: {entry.get('suggestions', [])}\n"
                        f"Diff:\n```diff\n{entry.get('diff', '(not available)')}\n```\n"
                    )
            history_block = "\n".join(lines)

        if feedback:
            prev_patch    = feedback.get("previous_patch", "")
            judge_reason  = feedback.get("judge_reason", "")
            suggestions   = feedback.get("suggestions", [])
            judge_verdict = feedback.get("judge_feedback", "needs_revision")

            test_output   = feedback.get("test_output", "")[:6000]
            diff_text     = feedback.get("diff", "")

            # [ABLATION no_semantic] The Judge still gates acceptance, but its
            # reasoning is withheld: the repair agent learns only that the
            # patch was rejected, not why.
            if ABL_NO_SEMANTIC_FB:
                judge_reason = "(withheld: no_semantic ablation)"
                suggestions  = []
            if ABL_BINARY_ONLY:
                # The degenerate feedback the paper argues against: the model
                # learns only that the suite still fails, with no detail.
                test_output = "TEST RESULT: FAIL"
                diff_text   = ""
            # [ABLATION no_test_fb] Test output withheld. The suite still
            # decides acceptance; the repair agent just cannot see it.
            if ABL_NO_TEST_FB:
                test_output = "(withheld: no_test_fb ablation)"

            prompt = (
                "You are an expert Java engineer performing automated program repair.\n"
                f"{repeat_warning}"
                f"{noop_warning}"
                f"Your PREVIOUS patch{file_ctx} failed. Study the information below "
                "and produce a NEW, CORRECT patch.\n\n"
                "═══════════════════════════════════════\n"
                f"ORIGINAL BUGGY FILE{file_ctx.upper()}\n"
                "═══════════════════════════════════════\n"
                f"```java\n{full_buggy_code}\n```\n\n"
                f"{focus_block}"
                "═══════════════════════════════════════\n"
                "YOUR PREVIOUS PATCH\n"
                "═══════════════════════════════════════\n"
                f"```java\n{prev_patch}\n```\n\n"
                "═══════════════════════════════════════\n"
                "DIFF: original → your previous patch\n"
                "═══════════════════════════════════════\n"
                f"```diff\n{diff_text}\n```\n\n"
                "═══════════════════════════════════════\n"
                "JUDGE FEEDBACK\n"
                "═══════════════════════════════════════\n"
                f"Verdict:     {judge_verdict}\n"
                f"Reason:      {judge_reason}\n"
                f"Issues:      {suggestions}\n\n"
                "═══════════════════════════════════════\n"
                "TEST / COMPILE OUTPUT\n"
                "═══════════════════════════════════════\n"
                f"{test_output}\n\n"
                f"{test_block}"
                f"{history_block}\n\n"
                "═══════════════════════════════════════\n"
                "YOUR TASK\n"
                "═══════════════════════════════════════\n"
                "1. Read the diff — understand exactly what you changed.\n"
                "2. Read the judge's reason and test output — understand WHY it failed.\n"
                "3. Read the failing test source — understand what the test EXPECTS.\n"
                "4. Fix the bug in the ORIGINAL file (not in your previous patch).\n\n"
                + (
                    build_search_replace_instructions()
                    if EDIT_MODE == "search_replace" else
                    "5. Produce ONE COMPLETE corrected Java file that fixes the bug.\n"
                    "6. Output ONLY the raw Java source. No markdown, no explanations.\n"
                    "7. NEVER append another file's contents at the end.\n\n"
                    "CORRECTED JAVA FILE:\n"
                )
            )
        else:
            prompt = (
                "You are an expert Java engineer performing automated program repair.\n\n"
                "═══════════════════════════════════════\n"
                f"BUGGY FILE{file_ctx.upper()}\n"
                "═══════════════════════════════════════\n"
                f"```java\n{full_buggy_code}\n```\n\n"
                f"{focus_block}"
                "═══════════════════════════════════════\n"
                "BUG DESCRIPTION\n"
                "═══════════════════════════════════════\n"
                f"{error_info or 'The code fails one or more test cases.'}\n\n"
                f"{test_block}"
                "═══════════════════════════════════════\n"
                "YOUR TASK\n"
                "═══════════════════════════════════════\n"
                "1. Identify the exact bug.\n\n"
                + (
                    build_search_replace_instructions()
                    if EDIT_MODE == "search_replace" else
                    "2. Produce ONE COMPLETE corrected Java file.\n"
                    "3. Output ONLY raw Java source. No markdown, no explanations.\n"
                    "4. NEVER append another file's contents at the end.\n\n"
                    "CORRECTED JAVA FILE:\n"
                )
            )

        t0 = time.time()

        line_count = full_buggy_code.count("\n")

        # [FIX-A] In search_replace mode the model emits a handful of edit
        # lines, so the large-file token escalation is unnecessary.
        if EDIT_MODE == "search_replace":
            out_tokens = None
        else:
            out_tokens = (
                LARGE_FILE_MAX_TOKENS
                if line_count > LARGE_FILE_LINE_THRESHOLD
                else None
            )
            if out_tokens:
                logger.info(
                    "Large file (%d lines) — raising max_output_tokens to %d",
                    line_count, out_tokens,
                )

        effective_temp = (
            temperature if temperature is not None
            else GENERATION_CONFIG["temperature"]
        )

        def _strip_fences(text: str) -> str:
            out = extract_code_block(text, "java")
            if out.startswith("```"):
                lines_out = out.splitlines()
                if lines_out and lines_out[0].strip().startswith("```"):
                    lines_out = lines_out[1:]
                if lines_out and lines_out[-1].strip() == "```":
                    lines_out = lines_out[:-1]
                out = "\n".join(lines_out)
                logger.warning(
                    "Fence-leak guard activated for %s", file_label or "file"
                )
            return out

        usage_total: Dict[str, Any] = {}
        cleaned                     = ""
        corrective                  = ""
        attempts                    = 0
        blocks_applied              = 0
        reject_reason               = ""
        noop_detected               = False

        while attempts <= MAX_GENERATION_RETRIES:
            attempts += 1
            raw, usage = self._call(
                prompt + corrective, expect_json=False,
                max_output_tokens=out_tokens,
                temperature=min(effective_temp + 0.1 * (attempts - 1), 0.9),
            )
            usage_total = {
                k: usage_total.get(k, 0) + usage.get(k, 0)
                for k in set(usage_total) | set(usage)
            }

            if EDIT_MODE == "search_replace":
                blocks = parse_search_replace(raw)
                candidate, err = apply_search_replace(full_buggy_code, blocks)
                if candidate is None:
                    reject_reason = err
                    logger.warning(
                        "Edit rejected (attempt %d/%d): %s",
                        attempts, MAX_GENERATION_RETRIES + 1, err,
                    )
                    corrective = (
                        f"\n\n⚠ Your previous response was rejected: {err}.\n"
                        "Re-read the ORIGINAL file above and copy the SEARCH "
                        "section from it exactly, character for character. "
                        "Emit only SEARCH/REPLACE blocks."
                    )
                    continue
                blocks_applied = len(blocks)
                cleaned        = candidate
            else:
                cleaned = _strip_fences(raw)
                output_line_count = cleaned.count("\n")
                if line_count > 50 and output_line_count < line_count * 0.70:
                    logger.warning(
                        "Truncation detected: output %d lines vs original %d "
                        "(%.0f%%) — retrying with max token budget",
                        output_line_count, line_count,
                        100 * output_line_count / max(line_count, 1),
                    )
                    raw2, usage2 = self._call(
                        prompt + (
                            "\n\n⚠ CRITICAL: Your previous response was "
                            "truncated. You MUST output the COMPLETE Java file "
                            "from the first line to the last closing brace. "
                            "Do NOT stop early."
                        ),
                        expect_json=False,
                        max_output_tokens=LARGE_FILE_MAX_TOKENS,
                        temperature=min(effective_temp + 0.1, 0.7),
                    )
                    usage_total = {
                        k: usage_total.get(k, 0) + usage2.get(k, 0)
                        for k in set(usage_total) | set(usage2)
                    }
                    cleaned2 = _strip_fences(raw2)
                    if cleaned2.count("\n") > output_line_count:
                        cleaned = cleaned2
                        logger.info(
                            "Truncation retry succeeded: %d lines",
                            cleaned.count("\n"),
                        )

            
            if is_noop_patch(full_buggy_code, cleaned):
                noop_detected = True
                reject_reason = "model returned the original file unchanged"
                logger.warning(
                    "No-op generation (attempt %d/%d) for %s — retrying, "
                    "iteration NOT consumed",
                    attempts, MAX_GENERATION_RETRIES + 1, file_label or "file",
                )
                corrective = (
                    "\n\n⚠ Your previous response made NO change to the file. "
                    "You must modify the buggy logic. Identify the specific "
                    "incorrect statement and change it."
                )
                continue

            reject_reason = ""
            break

        # Never return an unusable generation as if it were a patch.
        if not cleaned or is_noop_patch(full_buggy_code, cleaned):
            cleaned = full_buggy_code

        changed_lines = count_changed_lines(full_buggy_code, cleaned)
        if changed_lines > DRIFT_LINE_THRESHOLD:
            logger.warning(
                "Large diff for %s: %d changed lines — possible drift",
                file_label or "file", changed_lines,
            )

        metadata = {
            "ablation":            ABLATION,
            "model":               self.model_name,
            "time_seconds":        time.time() - t0,
            "line_count":          line_count,
            "token_budget":        out_tokens or GENERATION_CONFIG["max_output_tokens"],
            "temperature_used":    effective_temp,
            "edit_mode":           EDIT_MODE,
            "generation_attempts": attempts,
            "blocks_applied":      blocks_applied,
            "changed_lines":       changed_lines,
            "drift_suspected":     changed_lines > DRIFT_LINE_THRESHOLD,
            "noop_detected":       noop_detected,
            "generation_rejected": reject_reason,
            **usage_total,
        }
        return cleaned, metadata


# ─────────────────────────────────────────────────────────────────────────────
# JUDGE AGENT
# ─────────────────────────────────────────────────────────────────────────────

class JudgeAgent(GeminiAgent):

    def evaluate_patch(
        self,
        original_code: str,
        patched_code:  str,
        test_results:  Optional[TestResult] = None,
        diff_text:     str = "",
    ) -> Tuple[Verdict, str, Dict]:

        if test_results is None:
            test_status = "NOT_RUN"
            test_output = "No test results provided."
        else:
            test_status = "PASS" if test_results.passed else "FAIL"

            test_output = test_results.output[:6000]

        # Concrete judge suggestions — ban vague "investigate X" format
        prompt = (
            "You are a Principal Software Engineer reviewing an automated patch.\n\n"
            "══════════════════════════\nORIGINAL FILE\n══════════════════════════\n"
            f"```java\n{original_code}\n```\n\n"
            "══════════════════════════\nPATCHED FILE\n══════════════════════════\n"
            f"```java\n{patched_code}\n```\n\n"
            "══════════════════════════\nUNIFIED DIFF (original → patch)\n══════════════════════════\n"
            f"```diff\n{diff_text or '(diff not available)'}\n```\n\n"
            f"══════════════════════════\nTEST STATUS: {test_status}\n══════════════════════════\n"
            f"{test_output}\n\n"
            "DECISION RULES\n"
            "1. PASS → verdict MUST be 'correct' (unless compilation failed).\n"
            "2. FAIL → 'incorrect' (wrong direction) or 'needs_revision' "
            "(right direction, structural problem).\n"
            "3. NOT_RUN → evaluate structural integrity only.\n\n"
            # Concrete suggestion format — bans vague language
            "CRITICAL: Each 'suggestions' entry MUST follow EXACTLY this format:\n"
            "  'In [MethodName](): change [exact original code fragment] to "
            "[exact replacement code] because [specific reason]'\n"
            "  GOOD example: 'In getLine(): change \"if (idx >= lines.length) return null;\" "
            "to \"if (idx > lines.length) return null;\" because the test expects the last "
            "line to be returned even without a trailing newline.'\n"
            "  BAD (forbidden): 'Investigate the getLine() method' or 'Look at the logic'.\n"
            "  If the fix requires understanding the test expectation, read the test output "
            "and state what value the test expects vs what the code currently produces.\n"
            "  Do NOT suggest reverting to the original if the original also fails the tests.\n\n"
            "Return ONLY a JSON object (no markdown):\n"
            "{\n"
            '  "verdict": "correct" | "incorrect" | "needs_revision",\n'
            '  "reason": "one paragraph",\n'
            '  "issues": ["specific issue 1"],\n'
            '  "suggestions": ["In X(): change Y to Z because ..."],\n'
            '  "problematic_lines": [123, 456]\n'
            "}"
        )

        t0         = time.time()
        raw, usage = self._call(prompt, expect_json=True)

        if not raw:
            return Verdict.ERROR, "Empty model response", {}

        try:
            result      = json.loads(raw)
            verdict_str = str(result.get("verdict", "error")).lower()
            verdict     = {
                "correct":        Verdict.CORRECT,
                "incorrect":      Verdict.INCORRECT,
                "needs_revision": Verdict.NEEDS_REVISION,
            }.get(verdict_str, Verdict.ERROR)

            reason      = result.get("reason", "")
            issues      = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            problematic = result.get("problematic_lines", [])
            metadata    = {
                "model":                self.model_name,
                "time_seconds":         time.time() - t0,
                "issues":               issues,
                "suggestions":          suggestions,
                "problematic_lines":    problematic,
                "test_status_observed": test_status,
                **usage,
            }
            return verdict, reason, metadata

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error("Judge JSON parse error: %s  raw=%s", e, raw[:200])
            return Verdict.ERROR, f"JSON parse error: {e}", {}


# ─────────────────────────────────────────────────────────────────────────────
# OSCILLATION DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

class OscillationDetector:
    def __init__(self):
        self._fingerprints: List[str] = []
        self._patches:      List[str] = []

    def record(self, patch: str) -> bool:
        fp = patch_fingerprint(patch)
        self._fingerprints.append(fp)
        self._patches.append(patch)

        if len(self._fingerprints) >= 2:
            recent = self._fingerprints[-OSCILLATION_WINDOW:]
            if len(set(recent)) == 1:
                logger.warning(
                    "Oscillation: exact duplicate for %d consecutive iterations",
                    len(recent),
                )
                return True

        if len(self._patches) >= 2:
            for prev in self._patches[-OSCILLATION_WINDOW:-1]:
                if patch_similarity(prev, patch) >= OSCILLATION_SIMILARITY:
                    logger.warning(
                        "Oscillation: similarity ≥ %.2f threshold",
                        OSCILLATION_SIMILARITY,
                    )
                    return True

        return False

    def reset(self):
        self._fingerprints.clear()
        self._patches.clear()


# ─────────────────────────────────────────────────────────────────────────────
# OSCILLATION DETECTORS (global)
# ─────────────────────────────────────────────────────────────────────────────

_oscillation_detectors: Dict[str, OscillationDetector] = {}
_single_oscillation_detectors: Dict[str, OscillationDetector] = {}

def _get_detector(thread_id: str) -> OscillationDetector:
    if thread_id not in _oscillation_detectors:
        _oscillation_detectors[thread_id] = OscillationDetector()
    return _oscillation_detectors[thread_id]

def _get_single_detector(thread_id: str) -> OscillationDetector:
    key = thread_id + "_single"
    if key not in _single_oscillation_detectors:
        _single_oscillation_detectors[key] = OscillationDetector()
    return _single_oscillation_detectors[key]


# ─────────────────────────────────────────────────────────────────────────────
# LANGGRAPH STATE
# ─────────────────────────────────────────────────────────────────────────────

class RepairState(TypedDict):
    buggy_code:       str
    full_buggy_code:  str
    buggy_file_path:  str
    buggy_file_paths: List[str]
    per_file_sources: Dict[str, str]
    per_file_patches: Dict[str, str]
    project_name:     str
    error_info:       Optional[str]
    language:         str
    test_code:        Optional[str]
    project_path:     Optional[str]
    trigger_tests:    List[str]
    test_source:      str
    current_patch:    Optional[str]
    iteration:        int
    judge_verdict:    Optional[str]
    judge_reason:     Optional[str]
    feedback:         Optional[Dict]
    test_result:      Optional[TestResult]
    history:          List[Dict]
    conversation_log: List[Dict]
    oscillation_abort: bool
    _thread_id:        str
    _repetition_count: Optional[int]
    _single_oscillation_near: Optional[bool]
    _problematic_lines: Optional[List[int]]
    # Track consecutive no-op streak
    _noop_streak:      int
    # [FIX-D] First patch that passed the suite, kept even if the Judge vetoes it
    plausible_patch:     Optional[str]
    plausible_per_file:  Optional[Dict[str, str]]
    plausible_iteration: Optional[int]
    # [FIX-F] tests failing before any patch was applied
    baseline_failing:      Optional[List[str]]
    # [FIX-E] Failure breakdown
    _regressions:          Optional[List[str]]
    _failing_target_tests: Optional[List[str]]
    _preexisting_failures: Optional[List[str]]
    baseline_relative_pass: Optional[bool]


# ─────────────────────────────────────────────────────────────────────────────
# SHARED INSTANCES
# ─────────────────────────────────────────────────────────────────────────────

repair_agent = RepairAgent(model_name=REPAIR_MODEL)
judge_agent  = JudgeAgent(model_name=JUDGE_MODEL)
test_runner  = TestRunner()


# ─────────────────────────────────────────────────────────────────────────────
# NODE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def repair_node(state: RepairState) -> RepairState:
    logger.info("▶ REPAIR  iteration=%d", state["iteration"])

    per_file_sources: Dict[str, str] = state.get("per_file_sources") or {}
    is_multi_file = len(per_file_sources) > 1
    conv_log      = state.get("conversation_log", [])
    feedback      = state.get("feedback")

    if is_multi_file:
        # ── V6 multi-file path ───────────────────────────────────────────────
        logger.info("  Multi-file path (%d files)", len(per_file_sources))
        per_file_patches: Dict[str, str] = {}
        all_metadata: List[Dict]         = []

        for fp, source in per_file_sources.items():
            file_label = os.path.basename(fp)
            logger.info("  Repairing file: %s", file_label)

            file_feedback = None
            if feedback:
                prev_patches  = state.get("per_file_patches") or {}
                file_feedback = {**feedback, "previous_patch": prev_patches.get(fp, "")}

            patch, meta = repair_agent.generate_fix(
                full_buggy_code  = source,
                error_info       = state.get("error_info"),
                feedback         = file_feedback,
                project_name     = state.get("project_name", ""),
                test_source      = state.get("test_source", ""),
                conversation_log = conv_log,
                file_label       = file_label,
            )
            per_file_patches[fp] = patch
            all_metadata.append({"file": file_label, **meta})

        combined_meta = {
            "model":         REPAIR_MODEL,
            "time_seconds":  sum(m.get("time_seconds", 0) for m in all_metadata),
            "total_tokens":  sum(m.get("total_tokens", 0) for m in all_metadata),
            "files":         all_metadata,
            "is_multi_file": True,
        }
        primary_fp    = state.get("buggy_file_path", "")
        primary_patch = per_file_patches.get(
            primary_fp, next(iter(per_file_patches.values()), "")
        )
        state.setdefault("history", []).append({
            "iteration":        state["iteration"],
            "action":           "repair",
            "patch":            primary_patch,
            "per_file_patches": per_file_patches,
            "metadata":         combined_meta,
        })
        state.setdefault("conversation_log", []).append({
            "role":      "repair",
            "iteration": state["iteration"],
            "patch":     primary_patch,
        })
        state["per_file_patches"] = per_file_patches
        state["current_patch"]    = primary_patch

    else:
        # ── V5 single-file path ─────────────────────────────────────────────
        logger.info("  Single-file path")

        prev_repairs   = [h for h in state.get("history", []) if h["action"] == "repair"]
        prev_judges    = [h for h in state.get("history", []) if h["action"] == "judge"]
        repeat_warning = ""
        noop_warning   = ""
        temperature    = None

        # Update noop_streak and reset if not applicable
        noop_streak = state.get("_noop_streak", 0)

        if feedback:
            tested_patch = feedback.get("previous_patch", "")
            tested_fp    = patch_fingerprint(tested_patch)

            # ── Compile error specialisation ─────────────────────────────────
            tr = state.get("test_result")
            if _is_compile_error(tr):
                compile_output = (tr.output or "")[:5000]
                compile_warning = (
                    "\n╔══════════════════════════════════════════════╗\n"
                    "║  ⚠  COMPILATION ERROR — READ BEFORE CODING  ║\n"
                    "╚══════════════════════════════════════════════╝\n"
                    "Your patch DID NOT COMPILE. No tests could run.\n\n"
                    f"Full compile output:\n{compile_output}\n\n"
                    "MANDATORY RULES TO AVOID COMPILE ERRORS:\n"
                    "  1. Only use class names, method names, constants, and enum values "
                    "that appear in the file or its import statements. "
                    "Do NOT invent new symbols.\n"
                    "  2. Do NOT change method signatures unless you update every caller.\n"
                    "  3. Do NOT add generic type parameters to classes that are not generic.\n"
                    "  4. The safest fix is a ONE-LINE logic change inside an existing "
                    "method — do not restructure APIs.\n\n"
                )
                noop_warning = compile_warning + noop_warning
                logger.warning("Compile error detected — compile warning injected")

            # ── Regression detection and scoping ──────────────────────────────
            trigger_set = set(state.get("trigger_tests", []))
            if tr and tr.failing_tests and trigger_set:
                non_trigger_failing = [
                    t for t in tr.failing_tests if t not in trigger_set
                ]
                if non_trigger_failing:
                    regression_warning = (
                        f"\n⚠ REGRESSION: Your last patch broke "
                        f"{len(non_trigger_failing)} test(s) that were "
                        "previously PASSING:\n"
                        + "\n".join(
                            f"  - {t}" for t in non_trigger_failing[:8]
                        ) + "\n\n"
                        "You introduced a regression. You MUST:\n"
                        "  1. Make your fix MORE TARGETED — only modify the "
                        "specific method(s) that the trigger test exercises.\n"
                        "  2. Do NOT add any new 'if' guards, 'else' branches, "
                        "or changed method signatures that could affect other "
                        "callers.\n"
                        "  3. If you changed multiple methods, revert ALL changes "
                        "except the single method closest to the failing test.\n\n"
                    )
                    noop_warning = regression_warning + noop_warning
                    logger.warning(
                        "Regression detected: %d non-trigger tests failing — "
                        "regression_warning injected", len(non_trigger_failing)
                    )

            # ── Stuck-patch detection (rules A–E) ─────────────────────────────
            seen_fps = {patch_fingerprint(h["patch"]) for h in prev_repairs[:-1]}

            if tested_fp in seen_fps:
                revisit_count = sum(
                    1 for h in prev_repairs
                    if patch_fingerprint(h["patch"]) == tested_fp
                )
                repeat_warning = (
                    f"\n⚠ WARNING: Your patch is IDENTICAL to one you already "
                    f"tried {revisit_count} iteration(s) ago. "
                    "You are going in circles. You MUST try a completely "
                    "different approach.\n\n"
                )
                temperature = min(
                    GENERATION_CONFIG["temperature"] + 0.15 * (revisit_count + 1),
                    0.7,
                )
                logger.warning(
                    "Cycle detected: fp %s seen %d time(s) before — "
                    "repeat_warning injected, temp=%.2f",
                    tested_fp[:8], revisit_count, temperature,
                )

            elif len(prev_repairs) >= 2 and (
                patch_fingerprint(prev_repairs[-1]["patch"])
                == patch_fingerprint(prev_repairs[-2]["patch"])
            ):
                last_fp = patch_fingerprint(prev_repairs[-1]["patch"])
                streak  = sum(
                    1 for h in reversed(prev_repairs)
                    if patch_fingerprint(h["patch"]) == last_fp
                )
                repeat_warning = (
                    f"\n⚠ WARNING: Your last {streak} consecutive patches were "
                    "IDENTICAL. You are stuck. Try a completely different fix.\n\n"
                )
                temperature = min(
                    GENERATION_CONFIG["temperature"] + 0.15 * streak,
                    0.7,
                )
                logger.warning(
                    "Consecutive duplicate (streak=%d) — repeat_warning injected, "
                    "temp=%.2f", streak, temperature,
                )

            # Rule C: no-op / near-identical patch
            sim_to_original = patch_similarity(tested_patch, state["full_buggy_code"])
            if sim_to_original >= 0.992:
                noop_streak += 1
                noop_warning += (
                    f"\n⚠ WARNING: Your last patch made almost NO changes to the "
                    f"original file (similarity={sim_to_original:.4f}). "
                    "This is a no-op. You MUST identify the exact method and "
                    "line that is wrong and make a meaningful logic change.\n\n"
                )
                if temperature is None:
                    temperature = min(GENERATION_CONFIG["temperature"] + 0.15, 0.7)
                logger.warning(
                    "No-op patch detected (sim_to_original=%.4f) — "
                    "noop_warning injected", sim_to_original,
                )
            else:
                noop_streak = 0  # reset on a real change

            # Rule E: patch shrinkage
            orig_lines   = state["full_buggy_code"].count("\n") + 1
            tested_lines = tested_patch.count("\n") + 1
            if orig_lines > 50 and tested_lines < orig_lines * 0.85:
                shrink_pct = 100 * tested_lines / orig_lines
                noop_warning += (
                    f"\n⚠ WARNING: Your last patch was only {shrink_pct:.0f}% "
                    f"the length of the original ({tested_lines} vs {orig_lines} lines). "
                    "The fix should be TARGETED — do NOT remove entire methods.\n\n"
                )
                if temperature is None:
                    temperature = min(GENERATION_CONFIG["temperature"] + 0.15, 0.7)
                logger.warning(
                    "Patch shrinkage detected (%d/%d lines = %.0f%%) — injected",
                    tested_lines, orig_lines, shrink_pct,
                )

            # Rule D: repetitive judge feedback
            if len(prev_judges) >= 2:
                last_reason = prev_judges[-1].get("reason", "")
                prev_reason = prev_judges[-2].get("reason", "")
                feedback_sim = patch_similarity(last_reason, prev_reason)
                if feedback_sim >= 0.70 and not repeat_warning:
                    repeat_warning = (
                        "\n⚠ WARNING: The judge has given you nearly identical "
                        f"feedback multiple times (similarity={feedback_sim:.2f}). "
                        "You understand the issue but your implementation is not "
                        "working. You MUST try a fundamentally different strategy.\n\n"
                    )
                    if temperature is None:
                        temperature = min(
                            GENERATION_CONFIG["temperature"] + 0.20, 0.7
                        )
                    logger.warning(
                        "Repetitive judge feedback (sim=%.2f) — injected, temp=%.2f",
                        feedback_sim, temperature,
                    )

            # Near-identical patch + test failed
            if sim_to_original > 0.995 and not state.get(
                "test_result", TestResult(False, "", "", [])
            ).passed:
                noop_warning += (
                    "\n⚠ Your last patch was almost identical to the original "
                    f"(similarity {sim_to_original:.4f}). You MUST make a "
                    "meaningful change.\n"
                )
                if temperature is None:
                    temperature = min(GENERATION_CONFIG["temperature"] + 0.2, 0.8)
                else:
                    temperature = min(temperature + 0.2, 0.8)

            # Single-file oscillation near
            if state.get("_single_oscillation_near", False):
                repeat_warning += (
                    "\n⚠ WARNING: You have submitted the same patch multiple times "
                    "and tests still fail. You MUST significantly change your approach.\n"
                )
                if temperature is None:
                    temperature = min(GENERATION_CONFIG["temperature"] + 0.3, 0.8)
                else:
                    temperature = min(temperature + 0.3, 0.8)

            # Focus snippet injection
            problematic = state.get("_problematic_lines", [])
            if problematic:
                snippet = extract_focused_snippet(
                    state["full_buggy_code"], problematic, context=6
                )
                feedback["focus_snippet"] = snippet

            # ── Surgical mode after 3+ consecutive no-ops ─────────────────────
            if noop_streak >= 3:
                all_judge_suggestions: List[str] = []
                for j in prev_judges:
                    all_judge_suggestions.extend(
                        j.get("metadata", {}).get("suggestions", [])
                    )
                # Deduplicate while preserving order
                seen_sugg: set = set()
                unique_suggestions: List[str] = []
                for s in all_judge_suggestions:
                    if s not in seen_sugg:
                        seen_sugg.add(s)
                        unique_suggestions.append(s)

                surgical_block = (
                    "\n╔══════════════════════════════════════════════════╗\n"
                    "║  🔬 SURGICAL MODE — TARGETED FIX REQUIRED        ║\n"
                    "╚══════════════════════════════════════════════════╝\n"
                    f"You have produced {noop_streak} consecutive near-identical "
                    "patches. You are not making progress.\n\n"
                    "MANDATORY PROCEDURE:\n"
                    "  STEP 1: Identify the ONE method the failing test exercises "
                    "(read the test source above).\n"
                    "  STEP 2: Change ONLY that method — do not touch anything else "
                    "in the file.\n"
                    "  STEP 3: The change must be a LOGIC change (condition, return "
                    "value, algorithm) — NOT whitespace, comments, or formatting.\n"
                    "  STEP 4: The change should be 1–5 lines maximum.\n\n"
                    "All judge suggestions accumulated across iterations:\n"
                )
                for s in unique_suggestions[:10]:
                    surgical_block += f"  • {s}\n"
                surgical_block += (
                    "\nIf suggestions seem contradictory, make the SMALLEST possible "
                    "targeted logic change that could cause the test to pass.\n\n"
                )
                noop_warning = surgical_block + noop_warning
                # Force high temperature in surgical mode
                temperature = 0.85
                logger.warning(
                    "Surgical mode activated (noop_streak=%d, temp=0.85)", noop_streak
                )

        # Persist updated streak
        state["_noop_streak"] = noop_streak

        patch, metadata = repair_agent.generate_fix(
            full_buggy_code  = state["full_buggy_code"],
            error_info       = state.get("error_info"),
            feedback         = feedback,
            project_name     = state.get("project_name", ""),
            test_source      = state.get("test_source", ""),
            conversation_log = conv_log,
            repeat_warning   = repeat_warning,
            noop_warning     = noop_warning,
            temperature      = temperature,
        )
        metadata["is_multi_file"] = False
        state.setdefault("history", []).append({
            "iteration": state["iteration"],
            "action":    "repair",
            "patch":     patch,
            "metadata":  metadata,
        })
        state.setdefault("conversation_log", []).append({
            "role":      "repair",
            "iteration": state["iteration"],
            "patch":     patch,
        })
        state["current_patch"] = patch

    return state


def test_node(state: RepairState) -> RepairState:
    logger.info("▶ TEST    iteration=%d", state["iteration"])

    lang             = state.get("language", "python")
    project_name     = state.get("project_name", "")
    trigger_tests    = state.get("trigger_tests") or []
    per_file_sources = state.get("per_file_sources") or {}
    is_multi_file    = len(per_file_sources) > 1

    try:
        if lang == "python":
            patch     = state.get("current_patch")
            test_code = state.get("test_code")
            tr = (
                test_runner.run_python_tests(patch, test_code)
                if patch and test_code
                else TestResult(False, "No patch or test code", "", [])
            )

        elif lang == "java":
            project_path     = state.get("project_path")
            per_file_patches = state.get("per_file_patches") or {}
            file_paths       = state.get("buggy_file_paths") or []
            if state.get("buggy_file_path"):
                file_paths = file_paths or [state["buggy_file_path"]]

            if not project_path or not file_paths:
                tr = TestResult(False, "Missing Java context", "", [])
            else:
                if is_multi_file and per_file_patches:
                    for fp, patch_text in per_file_patches.items():
                        if fp and patch_text and os.path.isdir(os.path.dirname(fp)):
                            Path(fp).write_text(patch_text, encoding="utf-8")
                            logger.info("Wrote per-file patch → %s", fp)
                else:
                    patch = state.get("current_patch", "")
                    for fp in file_paths:
                        if fp and patch and os.path.isdir(os.path.dirname(fp)):
                            Path(fp).write_text(patch, encoding="utf-8")
                            logger.info("Wrote patch → %s", fp)

                tr = test_runner.run_defects4j_tests(
                    project_path, project_name,
                    trigger_tests=trigger_tests or None,
                )
        else:
            tr = TestResult(False, f"Unknown language: {lang}", "", [])

    except Exception as e:
        logger.exception("Exception in test_node")
        tr = TestResult(False, f"Error: {e}", "", [])

    state["test_result"] = tr

    if tr.passed and not state.get("plausible_patch"):
        state["plausible_patch"]     = state.get("current_patch")
        state["plausible_per_file"]  = dict(state.get("per_file_patches") or {})
        state["plausible_iteration"] = state.get("iteration", 0)
        logger.info(
            "✔ Plausible patch retained at iteration %d",
            state.get("iteration", 0),
        )


    triggers  = {t.strip() for t in (trigger_tests or []) if t.strip()}

    baseline  = set() if ABL_NO_BASELINE_SUB else {
        t.strip() for t in (state.get("baseline_failing") or []) if t.strip()
    }
    failing   = [t for t in (tr.failing_tests or []) if t]

    still_failing_targets = [
        t for t in failing
        if any(t.startswith(x) or x.startswith(t) for x in triggers)
    ]

    regressions = [
        t for t in failing
        if t not in still_failing_targets and t not in baseline
    ]
    preexisting = [
        t for t in failing
        if t not in still_failing_targets and t in baseline
    ]
    state["_preexisting_failures"] = preexisting

    baseline_relative_pass = (not still_failing_targets) and (not regressions)
    state["baseline_relative_pass"] = baseline_relative_pass
    if baseline_relative_pass and not tr.passed:
        logger.info(
            "Baseline-relative PASS: all %d trigger test(s) fixed, 0 regressions, "
            "%d pre-existing failure(s) ignored", len(triggers), len(preexisting),
        )
        tr.passed = True
    state["_regressions"]           = regressions
    state["_failing_target_tests"]  = still_failing_targets

    if failing:
        summary = (
            "\n══════════════════════════\n"
            "TEST BREAKDOWN\n"
            "══════════════════════════\n"
            f"TARGET TESTS STILL FAILING ({len(still_failing_targets)}): "
            f"{still_failing_targets[:8]}\n"
            f"REGRESSIONS INTRODUCED BY YOUR PATCH ({len(regressions)}): "
            f"{regressions[:8]}\n"
            f"(ignored: {len(preexisting)} test(s) already failing before any "
            f"patch — not your fault, do not try to fix them)\n"
            + (
                "NOTE: the target test(s) now pass. The failures above are "
                "regressions your patch caused. They are NOT environment "
                "noise — fix them.\n"
                if regressions and not still_failing_targets else ""
            )
        )
        tr.output = summary + (tr.output or "")

    logger.info(
        "Test passed=%s  targets_failing=%s  regressions=%s  preexisting=%d",
        tr.passed, still_failing_targets[:3], regressions[:3], len(preexisting),
    )
    return state


def judge_node(state: RepairState) -> RepairState:
    # [ABLATION no_judge] Skip the LLM judge; the test suite alone decides.
    # This is the classic test-only APR configuration.
    if ABL_SKIP_JUDGE:
        tr = state.get("test_result")
        ok = bool(tr is not None and tr.passed)
        state["judge_verdict"] = "correct" if ok else "needs_revision"
        state["judge_reason"]  = (
            "[no_judge ablation] verdict taken from the test suite only"
        )
        state.setdefault("history", []).append({
            "iteration": state["iteration"],
            "action":    "judge",
            "verdict":   state["judge_verdict"],
            "reason":    state["judge_reason"],
            "metadata":  {
                "ablation":             "no_judge",
                "test_status_observed": "PASS" if ok else "FAIL",
                "model":                None,
            },
        })
        logger.info("▶ JUDGE   iteration=%d  [no_judge: tests=%s]",
                    state["iteration"], "PASS" if ok else "FAIL")
        if not ok:
            # The full judge_node sets `feedback` and advances the iteration
            # counter before returning; this early exit must do the same or the
            # loop never terminates (decide_next reads state["iteration"]).
            patched   = state.get("current_patch") or ""
            diff_text = ""
            try:
                diff_text = unified_diff(state.get("buggy_code", ""), patched)
            except Exception:
                pass
            state["feedback"] = {
                "previous_patch":   patched,
                "judge_feedback":   "needs_revision",
                "judge_reason":     "[no_judge ablation] tests still failing",
                "suggestions":      [],
                "test_output":      tr.output if tr else "",
                "diff":             diff_text,
                "is_compile_error": _is_compile_error(tr),
            }
            state["iteration"] += 1
        return state

    logger.info("▶ JUDGE   iteration=%d", state["iteration"])

    original = state.get("full_buggy_code", "")
    patched  = state.get("current_patch", "")
    tr       = state.get("test_result")

    per_file_sources = state.get("per_file_sources") or {}
    is_multi_file    = len(per_file_sources) > 1
    thread_id        = state.get("_thread_id", state.get("project_name", "default"))

    if not original:
        state["judge_verdict"] = "error"
        state["judge_reason"]  = "Original code missing"
        state["iteration"] += 1
        return state
    if not patched:
        state["judge_verdict"] = "error"
        state["judge_reason"]  = "No patch to evaluate"
        state["iteration"] += 1
        return state

    if tr is None:
        tr = TestResult(False, "No test result", "No test result", [])

    diff_text   = unified_diff(original, patched)
    test_passed = tr.passed

    # ── Oscillation check: MULTI-FILE only ────────────────────────────────
    if is_multi_file:
        per_file_patches_now: Dict[str, str] = state.get("per_file_patches") or {}
        osc_key = (
            combined_fingerprint(per_file_patches_now)
            if per_file_patches_now
            else patched
        )
        detector          = _get_detector(thread_id)
        oscillation_fired = detector.record(osc_key)

        if oscillation_fired and not test_passed:
            state["oscillation_abort"] = True
            state["judge_verdict"]     = "incorrect"
            state["judge_reason"]      = (
                "Oscillation detected: the agent produced the same patch as a "
                "previous iteration and the tests still fail. Aborting."
            )
            logger.warning(
                "Oscillation abort (multi-file) at iteration %d (thread=%s)",
                state["iteration"], thread_id,
            )
            state.setdefault("history", []).append({
                "iteration": state["iteration"],
                "action":    "judge",
                "verdict":   "incorrect",
                "reason":    state["judge_reason"],
                "metadata":  {"oscillation": True, "is_multi_file": True},
            })
            return state

        if oscillation_fired and test_passed:
            logger.info(
                "Oscillation triggered but test PASSED — accepting (iteration %d)",
                state["iteration"]
            )
    else:
        logger.debug(
            "Single-file: oscillation check skipped (iteration %d)",
            state["iteration"]
        )

    try:
        verdict, reason, metadata = judge_agent.evaluate_patch(
            original_code = original,
            patched_code  = patched,
            test_results  = tr,
            diff_text     = diff_text,
        )
    except Exception as e:
        logger.exception("judge_agent.evaluate_patch raised")
        state["judge_verdict"] = "needs_revision"
        state["judge_reason"]  = f"Judge call failed ({e}) — retrying"
        state.setdefault("history", []).append({
            "iteration": state["iteration"],
            "action":    "judge",
            "verdict":   "needs_revision",
            "reason":    state["judge_reason"],
            "metadata":  {"judge_error": str(e)},
        })
        state["feedback"] = {
            "previous_patch":   patched,
            "judge_feedback":   "needs_revision",
            "judge_reason":     state["judge_reason"],
            "suggestions":      [],
            "test_output":      tr.output if tr else "",
            "diff":             diff_text,
            "is_compile_error": _is_compile_error(tr),
        }
        state["iteration"] += 1
        return state

    metadata["is_multi_file"] = is_multi_file

    # Single-file oscillation tracking
    if not is_multi_file:
        detector_single = _get_single_detector(thread_id)
        detector_single.record(patch_fingerprint(patched))

        recent_fps = detector_single._fingerprints[-OSCILLATION_WINDOW:]
        if len(recent_fps) >= 2 and len(set(recent_fps)) == 1:
            state["_repetition_count"] = state.get("_repetition_count", 0) + 1
        else:
            state["_repetition_count"] = 0

        if state.get("_repetition_count", 0) >= 2:
            state["_single_oscillation_near"] = True
            logger.warning(
                "Single-file oscillation near: same patch %d times in window",
                state["_repetition_count"],
            )
        else:
            state["_single_oscillation_near"] = False

        state["_problematic_lines"] = metadata.get("problematic_lines", [])

    state.setdefault("history", []).append({
        "iteration": state["iteration"],
        "action":    "judge",
        "verdict":   verdict.value,
        "reason":    reason,
        "metadata":  metadata,
    })
    state.setdefault("conversation_log", []).append({
        "role":        "judge",
        "iteration":   state["iteration"],
        "verdict":     verdict.value,
        "reason":      reason,
        "issues":      metadata.get("issues", []),
        "suggestions": metadata.get("suggestions", []),
        "diff":        diff_text,
    })

    state["judge_verdict"] = verdict.value
    state["judge_reason"]  = reason

    if (verdict == Verdict.CORRECT and REQUIRE_TESTS_PASS_TO_ACCEPT
            and not test_passed):
        logger.warning(
            "Judge returned 'correct' but the suite is FAILING (%s) — "
            "downgrading. Failing: %s",
            state.get("project_name", ""),
            (tr.failing_tests[:3] if tr else []),
        )
        verdict = Verdict.NEEDS_REVISION
        reason  = ("Overridden by acceptance gate: the Judge returned "
                   "'correct' but the test suite is still failing. " + reason)
        state["judge_verdict"] = verdict.value
        state["judge_reason"]  = reason
        
    if verdict != Verdict.CORRECT:
        state["feedback"] = {
            "previous_patch":   patched,
            "judge_feedback":   verdict.value,
            "judge_reason":     reason,
            "suggestions":      metadata.get("suggestions", []),
            "test_output":      tr.output if tr else "",
            "diff":             diff_text,
            "is_compile_error": _is_compile_error(tr),
        }
        state["iteration"] += 1

    return state


def decide_next(
    state: RepairState,
) -> Literal["accept", "reject", "continue", "error"]:
    if state.get("oscillation_abort"):
        return "reject"
    verdict   = state.get("judge_verdict", "error")
    iteration = state.get("iteration", 0)

    if verdict == "correct":
        tr = state.get("test_result")
        if tr is not None and tr.passed:
            return "accept"
        logger.error("Gate reached decide_next — judge_node should have "
                     "downgraded this; rejecting to avoid a loop")
        return "reject"
        
        tests_ok = bool(tr is not None and tr.passed)
        if tests_ok or not REQUIRE_TESTS_PASS_TO_ACCEPT:
            return "accept"
        logger.warning(
            "Judge returned 'correct' but the suite is FAILING (%s) — "
            "not accepting. Failing: %s",
            state.get("project_name", ""),
            (tr.failing_tests[:3] if tr else []),
        )
        # Downgrade and keep going: the Judge's own stated rule is that a
        # failing suite cannot yield "correct".
        state["judge_verdict"] = "needs_revision"
        state["judge_reason"]  = (
            "Overridden by acceptance gate: the Judge returned 'correct' but "
            "the test suite is still failing. "
            + (state.get("judge_reason") or "")
        )
        state["iteration"] = state.get("iteration", 0) + 1
        verdict = "needs_revision"

    project_name = state.get("project_name", "")
    max_iter     = MAX_ITERATIONS_BY_PROJECT.get(project_name, MAX_ITERATIONS)
    if state.get("iteration", 0) >= max_iter:
        logger.info(
            "Max iterations reached for %s (%d/%d)",
            project_name, iteration, max_iter,
        )
        return "reject"
    return "continue"


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

workflow = StateGraph(RepairState)
workflow.add_node("repair", repair_node)
workflow.add_node("test",   test_node)
workflow.add_node("judge",  judge_node)
workflow.add_node("accept", lambda s: s)
workflow.add_node("reject", lambda s: s)
workflow.add_node("error",  lambda s: s)

workflow.set_entry_point("repair")
workflow.add_edge("repair", "test")
workflow.add_edge("test",   "judge")
workflow.add_conditional_edges(
    "judge", decide_next,
    {"accept": "accept", "reject": "reject",
     "continue": "repair", "error": "error"},
)
workflow.add_edge("accept", END)
workflow.add_edge("reject", END)
workflow.add_edge("error",  END)

_memory = InMemorySaver()
_app    = workflow.compile(checkpointer=_memory)


# ─────────────────────────────────────────────────────────────────────────────
# FAULT LOCALISATION
# ─────────────────────────────────────────────────────────────────────────────

def get_localized_context(
    full_code:     str,
    failing_tests: List[str],
    project_name:  str = "",
) -> str:
    lines = full_code.splitlines()
    if len(lines) < 150:
        return full_code

    terms: List[str] = []
    for test in failing_tests:
        method = test.split("::")[-1] if "::" in test else test
        terms.append(method)
        no_prefix = re.sub(r"^test", "", method)
        if no_prefix:
            terms.append(no_prefix)
            terms.append(no_prefix[0].lower() + no_prefix[1:])

    if project_name in ("Chart",):
        terms.extend(["getLegendItem", "getItemPaint", "drawItem"])

    found: List[str] = []
    seen:  set        = set()
    for i, line in enumerate(lines):
        if any(t.lower() in line.lower() for t in terms if t):
            lo = max(0, i - 30)
            hi = min(len(lines), i + 70)
            if lo not in seen:
                found.append(
                    f"// --- Context around line {i + 1} ---\n"
                    + "\n".join(lines[lo:hi])
                )
                seen.add(lo)

    if not found:
        return "// [Localisation failed — first 300 lines]\n" + "\n".join(lines[:300])

    return "\n\n/* ... */\n\n".join(found[:3])


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

class AgenticRepairSystem:
    def __init__(self):
        self.app = _app

    def repair_bug(
        self,
        buggy_code:        str,
        full_buggy_code:   Optional[str]           = None,
        buggy_file_path:   Optional[str]            = None,
        buggy_file_paths:  Optional[List[str]]      = None,
        per_file_sources:  Optional[Dict[str, str]] = None,
        project_name:      str                      = "",
        error_info:        Optional[str]             = None,
        language:          str                       = "python",
        test_code:         Optional[str]             = None,
        project_path:      Optional[str]             = None,
        failing_tests:     Optional[List[str]]       = None,
        trigger_tests:     Optional[List[str]]       = None,
        baseline_failing:  Optional[List[str]]       = None,
        thread_id:         str                       = "default",
    ) -> RepairResult:

        t0 = time.time()
        if full_buggy_code is None:
            full_buggy_code = buggy_code

        all_paths: List[str] = []
        if buggy_file_paths:
            all_paths = [p for p in buggy_file_paths if p]
        elif buggy_file_path:
            all_paths = [buggy_file_path]

        effective_triggers = trigger_tests or failing_tests or []

        test_source = ""
        if language == "java" and project_path and failing_tests:
            test_source = TestSourceFetcher.fetch(
                project_path  = project_path,
                project_name  = project_name,
                failing_tests = failing_tests,
            )
            logger.info(
                "Test source: %d chars fetched for %d tests",
                len(test_source), len(failing_tests),
            )

        if thread_id in _oscillation_detectors:
            _oscillation_detectors[thread_id].reset()
        key = thread_id + "_single"
        if key in _single_oscillation_detectors:
            _single_oscillation_detectors[key].reset()

        is_multi_file = bool(per_file_sources) and len(per_file_sources) > 1
        logger.info(
            "repair_bug: %s  thread=%s  files=%d  strategy=%s",
            project_name, thread_id,
            len(per_file_sources) if per_file_sources else 1,
            "multi-file" if is_multi_file else "single-file",
        )

        initial: RepairState = {
            "buggy_code":               buggy_code,
            "full_buggy_code":          full_buggy_code,
            "buggy_file_path":          all_paths[0] if all_paths else "",
            "buggy_file_paths":         all_paths,
            "per_file_sources":         per_file_sources or {},
            "per_file_patches":         {},
            "project_name":             project_name,
            "error_info":               error_info,
            "language":                 language,
            "test_code":                test_code,
            "project_path":             project_path,
            "trigger_tests":            effective_triggers,
            "test_source":              test_source,
            "current_patch":            None,
            "iteration":                0,
            "judge_verdict":            None,
            "judge_reason":             None,
            "feedback":                 None,
            "test_result":              None,
            "history":                  [],
            "conversation_log":         [],
            "oscillation_abort":        False,
            "_thread_id":               thread_id,
            "_repetition_count":        0,
            "_single_oscillation_near": False,
            "_problematic_lines":       [],
            "_noop_streak":             0,
            "baseline_failing":         list(baseline_failing or []),
            "plausible_patch":          None,   # [FIX-D]
            "plausible_per_file":       None,
            "plausible_iteration":      None,
            "_regressions":             [],     # [FIX-E]
            "_preexisting_failures":    [],
            "baseline_relative_pass":   False,
            "_failing_target_tests":    [],
        }

        config      = {"configurable": {"thread_id": thread_id}}
        final_state = self.app.invoke(initial, config)

        final_patch    = final_state.get("current_patch")
        final_per_file = final_state.get("per_file_patches") or {}
        verdict_str    = final_state.get("judge_verdict", "error")
        judge_reason   = final_state.get("judge_reason", "")
        history        = final_state.get("history", [])
        iterations     = len([h for h in history if h["action"] == "repair"])

        test_res = final_state.get("test_result")
        retained_patch     = final_state.get("plausible_patch")
        retained_iteration = final_state.get("plausible_iteration")
        plausible = bool(
            (test_res is not None and test_res.passed) or retained_patch
        )
        
        verdict_map = {
            "correct":        Verdict.CORRECT,
            "incorrect":      Verdict.INCORRECT,
            "needs_revision": Verdict.NEEDS_REVISION,
            "error":          Verdict.ERROR,
        }
        judge_verdict = verdict_map.get(verdict_str, Verdict.ERROR)

        total_tokens = sum(
            h.get("metadata", {}).get("total_tokens", 0) for h in history
        )

        return RepairResult(
            buggy_code      = buggy_code,
            final_patches   = final_per_file,
            final_patch     = final_patch,
            iteration_count = iterations,
            judge_verdict   = judge_verdict,
            judge_reason    = judge_reason,
            plausible       = plausible,
            history         = history,
            cost_estimate   = {
                "total_tokens":  total_tokens,
                "estimated_usd": round(total_tokens * 0.00000035, 4),
            },
            execution_time  = time.time() - t0,
            plausible_patch     = retained_patch,      # [FIX-D]
            plausible_iteration = retained_iteration,  # [FIX-D]
        )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def print_result(result: RepairResult):
    print("\n" + "=" * 60)
    print("REPAIR RESULT")
    print("=" * 60)
    print(f"Verdict:    {result.judge_verdict.value}")
    print(f"Reason:     {result.judge_reason}")
    print(f"Iterations: {result.iteration_count}")
    print(f"Time:       {result.execution_time:.1f} s")
    print(f"Tokens:     {result.cost_estimate.get('total_tokens', 0):,}")
    if result.final_patches:
        print(f"Files patched: {list(result.final_patches.keys())}")
    if result.final_patch:
        print("\nFinal patch (first 40 lines):")
        print("-" * 40)
        lines = result.final_patch.splitlines()
        print("\n".join(lines[:40]))
        if len(lines) > 40:
            print(f"… ({len(lines) - 40} more lines)")


def test_simple_bug():
    system    = AgenticRepairSystem()
    buggy     = "def add(a, b):\n    return a * b\n"
    test_code = (
        "import pytest\nfrom program import add\n"
        "def test_add():\n    assert add(2,3)==5\n    assert add(0,5)==5\n"
    )
    result = system.repair_bug(
        buggy_code = buggy,
        error_info = "Returns product instead of sum",
        test_code  = test_code,
        thread_id  = "simple_test",
    )
    print_result(result)


if __name__ == "__main__":
    test_simple_bug()
