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

## Key results

Defects4J V1.2, all 388 active bugs, Gemini 3.1 Flash Lite, ≤4 iterations.

| Measure | Count | % of 388 |
|---|---|---|
| Logged plausible (reported by the test harness) | 215 | — |
| **Verified plausible** (manual inspection of every patch) | **195** | 50.3% |
| Accepted (verified plausible **and** Judge verdict `correct`) | 182 | 46.9% |
| **Verified correct** (manual comparison with developer patch) | **138** | **35.6%** |

Per project:

| | Chart | Closure | Lang | Math | Mockito | Time | Total |
|---|---|---|---|---|---|---|---|
| Verified plausible | 19 | 40 | 37 | 60 | 29 | 10 | **195** |
| Verified correct | 17 | 29 | 30 | 42 | 12 | 8 | **138** |

For comparison, ReinFix (GPT-4o) reports 146 correct fixes using a search space
of 45 candidates per bug; SV-ARP explores at most 4, and 71.1% of its accepted
fixes are obtained at the first attempt (133/187). The difference in correct
fixes is not statistically significant (*z* = −0.51, *p* = 0.607).

### Component ablation (all 388 bugs, McNemar exact test)

| Configuration | Logged plausible | **Verified plausible** | 
|---|---|---|
| Full system | 215 | **195** | 
| − semantic feedback (Judge still gates) | 211 | 160 |
| Binary pass/fail feedback only | 211 | 154 | 
| − Judge Agent entirely | 203 | 158 |

Verified plausible per project:

| Configuration | Chart | Closure | Lang | Math | Mockito | Time |
|---|---|---|---|---|---|---|
| Full system | 19 | 40 | 37 | 60 | 29 | 10 |
| − semantic feedback | 18 | 40 | 33 | 50 | 9 | 10 |
| Binary pass/fail only | 16 | 42 | 35 | 46 | 8 | 7 |
| − Judge Agent | 18 | 36 | 29 | 46 | 24 | 5 |

Every ablated configuration is significantly worse than the full system. The
three ablations differ little among themselves, so the data establish that
feedback content affects repair outcomes without separating the contribution of
semantic gating from that of structured feedback.

As a gate, the Judge Agent accepts 182 of the 195 verified plausible patches, of
which 137 are correct (75.3% acceptance precision), and rejects 13, of which 12
are incorrect (92.3% rejection precision), discarding one correct fix out of 138
(99.3% recall).

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
passes. This is what allows it to reject plausible-but-incorrect patches: 13 of
195 in our evaluation, of which 12 are confirmed semantically incorrect.

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
├── results/               # per-patch manual verification, all four arms
│   ├── verification_full_388.csv
│   └── logs
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
git clone https://github.com/mkezadri/SV-ARP
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

./scripts/check_env.sh          # must print: Failing tests: 1
```

Optional overrides: `APR_RESULTS_DIR`, `APR_WORK_DIR`, `APR_BUG_LIST`,
`APR_EDIT_MODE`, `APR_ABLATION`.

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

**Plausibility must be verified, not trusted.** An earlier version of this
pipeline recorded non-compiling patches as passing: when compilation fails,
`defects4j test -r` emits no `Failing tests` line, an empty failing-test list
was read as zero failures, and a baseline-relative comparison then promoted the
result to a pass. This is fixed in `TestRunner.run_tests`, but every figure in
the paper is based on manually verified plausibility rather than the harness
alone. The per-patch records are in `verification/`.

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


---

## Output

Results are written as timestamped CSVs, one row per bug:

| Column | Meaning |
|---|---|
| `plausible` | the harness reported a passing suite |
| `accepted` | plausible **and** Judge verdict `correct` |
| `verdict` | `correct`, `needs_revision`, `incorrect` |
| `iterations` | iterations consumed (budget 4) |
| `history` | per-iteration JSON: patches, verdicts, metadata |
| `total_tokens`, `estimated_usd`, `time_seconds` | cost accounting |

`plausible` and `accepted` are distinct, and neither equals *correct*. The
`plausible` column is the harness's judgement, not ground truth; the paper
reports verified plausibility, which is lower.


---

## Reproducibility notes

**Run-to-run variance.** LLM sampling is stochastic; across bugs executed more
than once, roughly 15% change outcome between runs. Ablation comparisons are
paired on identical bug sets and tested with McNemar's exact test.

**Deprecated bugs.** Seven V1.2 bugs no longer reproduce under current Java
(Lang 2, 18, 25, 48; Time 21; Closure 63, 93), giving 388 active bugs of 395.
Closure 111, 113 and 115 do not compile on a clean checkout.

**Closure range.** Defects4J V1.2 Closure spans bugs 1–133.

See [`replication/replication_guide.txt`](replication/replication_guide.txt) for
a complete walkthrough.
