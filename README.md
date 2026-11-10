# SV-ARP: Self-Verifying Agentic Repair Pipeline

> **Paper**: *SV-ARP: A Self-Verifying Agentic Framework for Intelligent
> Automated Program Repair through Collaborative LLM-Based Code Review*

SV-ARP is a two-agent framework for automated program repair. A **Repair
Agent** proposes localized `SEARCH/REPLACE` edits; a **Judge Agent** reviews
every candidate against the diff and the test result and returns a verdict and
line-level suggestions in a mandatory "change X to Y because Z" format. A patch
is accepted when the relevant tests pass and the Judge's verdict is `correct`.

This repository contains the framework, the benchmark runner, the supervisor
script, the analysis script that regenerates every number in the paper, and
the correctness labels of every plausible patch.

---

## Results

Defects4J v1.2 project set, 388 active bugs, 373 evaluable (15 Mockito bugs do
not build under Java 11 and are excluded from every configuration),
`gemini-3.5-flash-lite`, at most four tested candidates per bug.

| Configuration | Plausible | Verified correct | Precision | McNemar p vs Full (Holm) |
|---|---|---|---|---|
| Full | 196 | 170 | 86.7% | |
| No-Semantic (Judge reasoning withheld) | 194 | 161 | 83.0% | 0.30 (0.47) |
| Binary-Only (test output replaced by FAIL) | 189 | 160 | 84.7% | 0.24 (0.47) |
| No-Judge | 181 | 156 | 86.2% | 0.070 (0.21) |
| Resample-4 (four independent single attempts) | 180 | 154 | 85.6% | 0.064 |

Per project, Full configuration (correct / plausible):

| Chart | Closure | Lang | Math | Mockito | Time | Total |
|---|---|---|---|---|---|---|
| 21/22 | 38/45 | 32/37 | 54/63 | 14/16 | 11/13 | **170/196** |

What the measurements say:

- 73% of plausible patches are found at the first attempt.
- No configuration difference survives correction for multiple comparisons.
- The Judge's acceptance gate is nominal: it withheld one test-passing
  candidate in 196.
- Four independent single attempts at the temperatures 0.1, 0.45, 0.45, 0.85
  reproduce the loop without the Judge at half the tokens of the full system.
- Two offline LLM reviewers, asked to detect overfitting patches without the
  developer fix, perform at chance level.

Cost of the Full configuration: 44.8M tokens, an estimated $0.042 per bug.

---

## Repository structure

```
SV-ARP/
├── src/
│   ├── agentic_apr.py        # agents, adaptive mechanisms, LangGraph loop
│   └── run_benchmark.py      # Defects4J benchmark driver
├── benchmark/
│   ├── versions.txt                  # the 388 active Defects4J v1.2 bugs
│   ├── versions_v1.2_and_v2.0.txt    # v1.2 and v2.0 bug ids (not used in the paper)
│   └── mapping.csv                   # bug -> modified-class source path
├── scripts/
│   ├── check_env.sh          # environment check; run this first
│   ├── make_bug_list.sh      # regenerate the bug list from your Defects4J
│   ├── fixed_baseline.py     # relevant tests on the developer-fixed versions
│   └── judge_swap.py         # offline review of plausible patches by a second model
├── run_all.sh                # supervisor for long unattended runs
├── analysis/
│   ├── make_figures.py       # regenerates every table and statistic
│   └── report.md             # its output for the paper
├── data/
│   ├── verification/         # labels: 4 configurations + 4 resampling passes
│   ├── second_verification/  # second, execution-based verification of the 4 configurations
│   ├── overrides_all.csv     # label overrides with their reasons
│   ├── offline_review/       # verdicts of the two offline reviewers
│   ├── canonical/            # one row per bug and configuration
│   └── results/              # raw result files, zipped (8 archives)
├── replication/replication_guide.txt
├── .env.example
└── requirements.txt
```

The raw result files (one record per bug and execution, with every candidate
patch, verdict, temperature and token count; about 400 MB unpacked) are in
`data/results/`, one zip per configuration and per resampling pass.

---

## Installation

Requires Python 3.10 or later, **Java 11**, and
[Defects4J](https://github.com/rjust/defects4j).

```bash
git clone https://github.com/mkezadri/SV-ARP
cd SV-ARP
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit; .env is git-ignored
```

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 11)   # macOS; adjust on Linux
export PATH="$JAVA_HOME/bin:$PATH"
export TZ="America/Los_Angeles"
export _JAVA_OPTIONS="-Duser.language=en -Duser.country=US"
export D4J_HOME=/path/to/defects4j
export PATH="$D4J_HOME/framework/bin:$PATH"
export GEMINI_API_KEY=<your-key>

./scripts/check_env.sh      # must report: Failing tests: 1
```

API keys are read from the environment only. Never commit one.

### Read this before running

The JVM takes its default locale from operating-system settings, not from
`LANG`. On a non-English system, Defects4J tests that assert on formatted
compiler diagnostics fail on pristine, unpatched checkouts (18 of 25 Closure
bugs in our measurement), and a candidate is plausible only if no relevant
test fails, so those bugs become unrepairable. The `_JAVA_OPTIONS` line above
is required; `check_env.sh` verifies it on Closure 2b.

---

## Running

```bash
# one bug
python src/run_benchmark.py --bug Lang_33

# the benchmark, resumable
python src/run_benchmark.py --bug-list benchmark/versions.txt --resume

# all four configurations, unattended (survives network drops and restarts)
nohup ./run_all.sh > supervisor.log 2>&1 &
./run_all.sh --status
touch STOP                  # finishes the current bug, then exits

# one configuration, or one resampling pass at temperature 0.45
./run_all.sh no_judge
./run_all.sh sample_t045a
```

Configuration is by environment variable:

| Variable | Default | Meaning |
|---|---|---|
| `APR_ABLATION` | `full` | `full`, `no_semantic`, `binary_only`, `no_judge` |
| `APR_REPAIR_MODEL`, `APR_JUDGE_MODEL` | `gemini-3.5-flash-lite` | model identifiers |
| `APR_TEMPERATURE` | `0.1` | initial sampling temperature |
| `APR_MAX_ITERATIONS` | `4` | tested candidates per bug |
| `APR_RESULTS_DIR` | `results` | one directory per configuration |
| `APR_WORK_DIR` | `/tmp/d4j_benchmark` | checkout scratch space |
| `APR_MAPPING_FILE` | `mapping.csv` | optional; set to `benchmark/mapping.csv` |
| `APR_USD_PER_TOKEN` | `0.00000035` | flat rate used for the cost estimate |

Use a separate results directory per configuration: `--resume` matches on the
bug id alone.

---

## Regenerating the paper's numbers

Unpack the raw results into `data/`, then run the script:

```bash
for z in data/results/*.zip; do unzip -q -o "$z" -d data; done
cp data/verification/*.csv data/
python analysis/make_figures.py --raw data --rule first \
    --bug-list benchmark/versions.txt \
    --overrides data/overrides_all.csv \
    --judge-swap data/offline_review/judge_swap_deepseek_v4_flash_semantic.csv \
    --judge-swap data/offline_review/judge_swap_gemini_3_5_flash_lite_semantic.csv \
    > report.md
```
---

## License

MIT. See `LICENSE`.

