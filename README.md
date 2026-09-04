# SV-ARP: Self-Verifying Agentic Repair Pipeline

> **Paper**: *SV-ARP: A Self-Verifying Agentic Framework for Intelligent
> Automated Program Repair through Collaborative LLM-Based Code Review*

SV-ARP is an agentic framework for automated program repair that integrates
structured LLM-based code review directly into the repair loop. Two specialised
agents ( a **Repair Agent** and a **Judge Agent** ) collaborate iteratively: the
Repair Agent generates candidate patches; the Judge Agent evaluates every
candidate against test execution outcomes and returns line-level,
action-oriented feedback. A patch is accepted only when it **both** passes the
test suite **and** receives a `correct` verdict from the Judge.

---

## Read this before running

**The JVM takes its default locale from operating-system settings, not from
`LANG`.** On a non-English system, Defects4J tests that assert on formatted
compiler diagnostics fail on *pristine, unpatched* checkouts. We measured this
on 25 Closure bugs: 18 (72%) showed spurious baseline failures, median 11,
maximum 28. Under a zero-failure plausibility criterion those bugs are
unrepairable regardless of patch quality.

```bash
export _JAVA_OPTIONS="-Duser.language=en -Duser.country=US"
```

Verify with `./scripts/check_env.sh`: a clean Closure 2b checkout must report
exactly **one** failing test. Fourteen means the flag is not in effect.

---

## Key results

Defects4J V1.2, all 388 active bugs, Gemini 3.1 Flash Lite, ≤4 iterations.

| Measure | Count | % of 388 |
|---|---|---|
| Plausible (passes `defects4j test -r`) | 214 | 55.2% |
| Accepted (plausible **and** Judge verdict `correct`) | 187 | 48.2% |
| **Verified correct** (manual comparison with developer patch) | **139** | **35.8%** |

Per project:

| | Chart | Closure | Lang | Math | Mockito | Time | Total |
|---|---|---|---|---|---|---|---|
| Plausible | 19 | 50 | 37 | 63 | 32 | 13 | **214** |
| Verified correct | 10 | 35 | 28 | 47 | 12 | 7 | **139** |

For comparison, ReinFix (GPT-4o) reports 146 correct from 207 plausible patches
using a search space of 45 candidates per bug; SV-ARP explores at most 4, and
71% of its accepted fixes are obtained at the first attempt. The difference in
correct fixes is not statistically significant (*p* = 0.661).

### Component ablation (all 388 bugs, McNemar exact test)

| Configuration | Plausible | Accepted | Vetoed | *p* vs full |
|---|---|---|---|---|
| Full system | 214 | 187 | 27 | — |
| − semantic feedback (Judge still gates) | 211 | 177 | 34 | 0.78 |
| Binary pass/fail feedback only | 211 | 184 | 27 | 0.78 |
| − Judge Agent entirely | 202 | 202 | 0 | 0.18 |

No configuration differs significantly from the full system. The Judge Agent's
measurable contribution is precision, not recall: it raises the proportion of
semantically correct patches from 65.0% to 73.8% while discarding one correct
fix out of 139 (99.3% recall).

---

## Architecture

```
buggy file
    │
    ▼
┌─────────────┐     full file + judge feedback
│ Repair Agent│ ◄──────────────────────────────┐
└──────┬──────┘                                 │
       │ candidate patch                        │
       ▼                                        │
┌──────────────┐                                │
│  Test Runner │  (defects4j test -r)           │
└──────┬───────┘                                │
       │ pass / fail + output                   │
       ▼                                        │
┌─────────────┐   verdict ∈ {correct,           │
│ Judge Agent │     incorrect, needs_revision}  │
└──────┬──────┘   + line-level suggestions      │
       │                                        │
       ├── pass AND correct ──► ACCEPT          │
       ├── max iterations ────► REJECT          │
       └── otherwise ─────────────────────────►─┘
```

The Judge Agent runs on **every** candidate, including patches whose test suite
passes. This is what allows it to reject plausible-but-incorrect patches: 27 of
214 in our evaluation, of which 26 are confirmed semantically incorrect.

Five adaptive warning mechanisms handle distinct failure modes:

| # | Mechanism | Trigger |
|---|---|---|
| 1 | Compile-error specialisation | Patch does not compile |
| 2 | Concrete judge suggestions | Judge must output `In X(): change Y to Z because …` |
| 3 | Regression scoping | Non-trigger tests break after a patch |
| 4 | No-op / surgical mode | Patch similarity to original ≥ 0.992; escalates after 3 consecutive no-ops |
| 5 | Oscillation / repetition guard | Same patch fingerprint within a 3-iteration window |

---

## Repository structure

```
SV-ARP/
├── src/
│   ├── sv_apr.py               # Core system (agents, LangGraph orchestration)
│   └── benchmark_runner.py     # Defects4J benchmark driver
│
├── benchmark/
│   ├── versions.txt            # 388 active Defects4J V1.2 bugs
│   └── mapping.csv             # bug -> modified-class source path
│
├── verification/
│   ├── verification.csv        # per-patch manual correctness classifications
│   └── check_verification.py   # validates the CSV against the paper's figures
│
├── scripts/
│   ├── check_env.sh            # environment verification (run this first)
│   └── make_bug_list.sh        # regenerate versions.txt from your Defects4J
│
├── replication/
│   └── replication_guide.txt   # step-by-step replication instructions
├── .env.example
└── requirements.txt
```

---

## Installation

Requires **Python ≥ 3.10**, **Java 11**, and
[Defects4J](https://github.com/rjust/defects4j).

```bash
git clone https://github.com/SV-ARP/SV-ARP
cd SV-ARP

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env           # then edit
```

### Environment variables

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 11)   # macOS; adjust on Linux
export PATH="$JAVA_HOME/bin:$PATH"                 # JAVA_HOME alone is not enough
export TZ="America/Los_Angeles"
export _JAVA_OPTIONS="-Duser.language=en -Duser.country=US"

export D4J_HOME=/path/to/defects4j
export PATH="$D4J_HOME/framework/bin:$PATH"

export GEMINI_API_KEY=<your-key>
# or, for full runs, several keys rotated automatically:
export APR_API_KEYS=key1,key2,key3
export APR_DAILY_QUOTA=200

./scripts/check_env.sh          # must print: Failing tests: 1
```

Optional overrides: `APR_RESULTS_DIR`, `APR_WORK_DIR`, `APR_BUG_LIST`,
`APR_EDIT_MODE`, `APR_ABLATION`.

---

## Running

### Single bug (quick check)

```bash
cd src
python benchmark_runner.py --bug Lang_1
```

### Full benchmark

```bash
cd src
python benchmark_runner.py --bug-list ../benchmark/versions.txt
```

A full run is roughly 2,300 API requests and 1–2 days of wall clock; test
execution, not the API, is the bottleneck.

### Resume an interrupted run

```bash
python benchmark_runner.py --bug-list ../benchmark/versions.txt --resume
```

### Ablation configurations

| `APR_ABLATION` | Judge gates? | Judge reasoning in prompt? | Test output in prompt? |
|---|---|---|---|
| `full` (default) | yes | yes | yes |
| `no_semantic` | yes | **no** | yes |
| `binary_only` | yes | **no** | **no** (`TEST RESULT: FAIL` only) |
| `no_judge` | **no** | n/a | yes |

```bash
APR_ABLATION=no_semantic APR_RESULTS_DIR=../results/no_semantic \
  python benchmark_runner.py --bug-list ../benchmark/versions.txt
```

Use a separate `APR_RESULTS_DIR` per arm — `--resume` matches on bug ID alone,
so a shared directory makes the second arm skip everything the first completed.

---

## Output

Results are written as timestamped CSVs, one row per bug:

| Column | Meaning |
|---|---|
| `plausible` | the patch passed `defects4j test -r` |
| `accepted` | plausible **and** Judge verdict `correct` |
| `verdict` | `correct`, `needs_revision`, `incorrect` |
| `iterations` | iterations consumed (budget 4) |
| `history` | per-iteration JSON: patches, verdicts, metadata |
| `total_tokens`, `estimated_usd`, `time_seconds` | cost accounting |

`plausible` and `accepted` are distinct, and neither equals *correct*. The
per-patch correctness classifications behind the 139 figure are in
`verification/verification.csv`; run `verification/check_verification.py` to
confirm they reproduce every figure in the paper.

---

## Key parameters

| Parameter | Value | Basis |
|---|---|---|
| Iteration budget | 4 | 100% of accepted fixes occur within 4 |
| Initial temperature | 0.1 | deterministic default |
| Cycle escalation | +0.15, cap 0.70 | a priori |
| Surgical mode temperature | 0.85 | a priori |
| Cycle similarity threshold | > 0.99 | a priori |
| No-op similarity threshold | ≥ 0.992 | a priori |
| Shrinkage / truncation thresholds | < 85% / < 70% lines | a priori |
| Surgical trigger | no-op streak ≥ 3 | a priori |
| Oscillation window | 3 iterations | a priori |

None were tuned on held-out data.

---

## Reproducibility notes

**Run-to-run variance.** LLM sampling is stochastic; across bugs executed more
than once, roughly 15% change outcome between runs. Ablation comparisons are
paired on identical bug sets and tested with McNemar's exact test.

**Deprecated bugs.** Seven V1.2 bugs no longer reproduce under current Java
(Lang 2, 18, 25, 48; Time 21; Closure 63, 93), giving 388 active bugs of 395.

**Closure range.** Defects4J V1.2 Closure spans bugs 1–133.

See [`replication/replication_guide.txt`](replication/replication_guide.txt) for
a complete walkthrough.
