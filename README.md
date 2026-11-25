# SV-ARP: Self-Verifying Agentic Repair Pipeline

> **Paper**: *SV-ARP: A Self-Verifying Agentic Framework for Intelligent
> Automated Program Repair through Collaborative LLM-Based Code Review*

SV-ARP is a two-agent framework for automated program repair. A **Repair
Agent** proposes localized `SEARCH/REPLACE` edits; a **Judge Agent** reviews
every candidate against the diff and the test result and returns a verdict and
line-level suggestions in a mandatory "change X to Y because Z" format. A patch
is accepted when the relevant tests pass and the Judge's verdict is `correct`.

This repository contains the framework, the benchmark runner, the supervisor
script, the analysis script that regenerates every number in the paper, the
result files of every execution, and the correctness labels of every plausible
patch.

---

## Results

Defects4J v1.2 project set, 388 active bugs, all evaluable in every
configuration, `gemini-3.5-flash-lite`, at most four tested candidates per bug.

| Configuration | Plausible | Verified correct | Precision | McNemar p vs Full (Holm) |
|---|---|---|---|---|
| Full | 202 | 175 | 86.6% | |
| No-Semantic (Judge reasoning withheld) | 202 | 168 | 83.2% | 0.45 (0.90) |
| Binary-Only (test output replaced by FAIL) | 182 | 153 | 84.1% | 0.003 (0.008) |
| No-Judge | 192 | 168 | 87.5% | 0.46 (0.90) |
| Resample-4 (four independent single attempts) | 186 | 160 | 86.0% | 0.086 |

Per project, Full configuration (correct / plausible):

| Chart | Closure | Lang | Math | Mockito | Time | Total |
|---|---|---|---|---|---|---|
| 18/19 | 39/46 | 32/37 | 54/63 | 21/24 | 11/13 | **175/202** |

What the measurements say:

- 73% of plausible patches are found at the first attempt.
- One difference survives correction for multiple comparisons: when the Repair
  Agent receives the Judge's review but not the test output (Binary-Only), the
  loop loses 22 correct fixes.
- Removing the Judge costs 7 correct fixes, which cannot be told from
  run-to-run variation (the identical first attempts of the four
  configurations differ by up to 13), at half the cost. Its acceptance gate is
  nominal: it declined one test-passing candidate in 202.
- Four independent single attempts at the temperatures 0.1, 0.45, 0.45, 0.85
  come within 8 correct fixes of the loop without the Judge and within 15 of
  the full system, with half the tokens of the latter.
- Without the developer fix, two offline LLM reviewers (DeepSeek V4 Flash,
  Gemini 3.5 Flash Lite) perform at chance level at detecting overfitting
  patches; Claude Sonnet 5.5 catches 13 of 26 while vetoing 9 of 168 correct
  ones (kappa 0.48). The review covers 194 of the 202 plausible patches.

Cost of the Full configuration: 46.4M tokens, an estimated $0.042 per bug.

---

## Repository structure

```
SV-ARP/
├── src/
│   ├── agentic_apr.py        # agents, adaptive mechanisms, LangGraph loop
│   └── run_benchmark.py      # Defects4J benchmark driver
├── run_all.sh                # supervisor for long unattended runs
├── tests/                    # checks of the correction of the two reduced configurations (tests/README.md)
├── benchmark/
│   ├── versions.txt                  # the 388 active Defects4J v1.2 bugs
│   ├── mockito_gradle_15.txt         # the 15 Mockito bugs that are built with Gradle
│   ├── full_concurrent_52.txt        # the 52 bugs two Full sessions executed concurrently
│   ├── rerun_full_50.txt             # the 50 of them that were executed again on 10 November 2026
│   └── mapping.csv                   # bug -> modified-class source path
├── scripts/
│   ├── check_env.sh          # environment check; run this first
│   ├── judge_swap.py         # offline review of plausible patches by a second model
│   └── topup_mockito15.sh    # executes the bugs of a list that have no completed execution yet
├── analysis/
│   ├── make_figures.py       # regenerates every table and statistic
│   ├── report.md             # its output for the paper
│   ├── justified_check.py    # which labels rest on a written reason; counts of the labels given last
│   └── check_paper_numbers.py  # compares the manuscript source with report.md
├── data/
│   ├── verification/         # labels: 4 configurations + 4 resampling passes
│   ├── second_verification/  # second verification of the 4 configurations
│   ├── overrides_all.csv     # label overrides and later labels, with their reasons
│   ├── harness_false_negatives.csv   # candidates logged as failing that pass (sensitivity only)
│   ├── time_limit_events.csv # test runs and baseline builds cut by their time limit, from the run logs
│   ├── lost_requests.csv     # requests to the model that failed after all retries, from the run logs
│   ├── discarded/            # one session discarded in full, with the reason (not used)
│   ├── offline_review/       # verdicts of the offline reviewers
│   ├── canonical/            # one row per bug and configuration
│   └── results/              # raw result files, zipped (8 archives)
├── replication/replication_guide.txt
├── .env.example
└── requirements.txt
```

The raw result files (one record per bug and execution, with every candidate
patch, verdict, temperature and token count; about 540 MB unpacked) are in
`data/results/`, one zip per configuration and per resampling pass. Each zip
holds every session of its configuration.

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
touch STOP                  # the supervisor exits when the current pass over the bug list ends
# to stop at once (the bug in progress leaves no record and is run again by --resume):
pkill -9 -f run_all.sh; pkill -f run_benchmark.py

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
    --judge-swap data/offline_review/judge_swap_claude_sonnet_5_5_semantic.csv \
    --false-negatives data/harness_false_negatives.csv \
    --concurrent full=20261010_140443+20261010_143326 \
    --rerun full=20261110_104737 \
    --discard-session full=20261110_032346 \
    --reexecuted binary_only=20261120_091831+20261121_115528+20261123_171006 \
    --reexecuted no_judge=20261121_173559+20261123_173421 \
    --without-bugs benchmark/mockito_gradle_15.txt \
    --second-verification data/second_verification \
    > report.md
```

The output should match `analysis/report.md` (the script is deterministic), and
the per-bug tables it writes to `figures_out/` should match `data/canonical/`.
`--concurrent` names the two sessions that shared a working directory,
`--rerun` the session that executed their bugs again after the labels had been
given, `--discard-session` a session that was discarded in full, `--reexecuted`
the sessions that executed Binary-Only and No-Judge with the corrected code,
which are the only canonical ones for these two configurations, and
`--without-bugs` a list of bugs for one more sensitivity analysis (see "Known
limitations" below).

Two further scripts read the same files:

```bash
# labels of Binary-Only and No-Judge that rest on a written reason, and the
# counts of the records labelled last (Section 4.5 of the paper)
python analysis/justified_check.py data figures_out benchmark/mockito_gradle_15.txt

# every table row and figure of the manuscript that comes from the report
python analysis/check_paper_numbers.py analysis/report.md <manuscript>.tex
```

---


## License

MIT. See `LICENSE`.
