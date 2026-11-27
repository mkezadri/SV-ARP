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
raw result files, and the correctness labels of every plausible patch.

---

## Results

Defects4J v1.2 project set, 388 active bugs, all evaluable in every
configuration, `gemini-3.5-flash-lite`, at most four tested candidates per bug.

| Configuration | Plausible | Verified correct | Precision | McNemar p vs Full (Holm) |
|---|---|---|---|---|
| Full | 202 | 173 | 85.6% | |
| Binary-Only (test output replaced by FAIL) | 182 | 151 | 83.0% | 0.003 (0.005) |
| No-Judge | 192 | 167 | 87.0% | 0.54 (0.54) |
| Resample-4 (four independent single attempts) | 186 | 159 | 85.5% | 0.11 |

Per project, Full configuration (correct / plausible):

| Chart | Closure | Lang | Math | Mockito | Time | Total |
|---|---|---|---|---|---|---|
| 18/19 | 39/46 | 32/37 | 52/63 | 21/24 | 11/13 | **173/202** |

What the measurements say:

- 73% of plausible patches are found at the first attempt.
- One difference survives correction for multiple comparisons: when the Repair
  Agent receives the Judge's review but not the test output (Binary-Only), the
  loop loses 22 correct fixes. The 22 include a surplus of 12 alternative fixes
  (38 against 26): counting only patches identical or equivalent to the
  developer fix (135 against 125), the difference is not significant, while
  the plausible count, which involves no label, shows it as well (202 against
  182).
- Removing the Judge costs 6 correct fixes (95% confidence interval -10 to
  +22), a difference the experiment does not establish (the identical first
  attempts of the three configurations differ by up to 11), at 53% of the cost.
  Its acceptance gate is nominal: it declined one test-passing candidate in
  202.
- Four independent single attempts come within 8 correct fixes of the loop
  without the Judge and within 14 of the full system, with half the tokens of
  the latter; neither difference is significant. At two, three and four
  candidates the loop without the Judge is ahead of the same number of
  independent attempts (150, 160 and 167 correct fixes against 141, 148 and
  159) at nearly the same cost.
- `gemini-3.5-flash-lite` ignores the temperature, top-p and top-k of a
  request (provider documentation), and the records agree: two runs give the
  same first candidate for about 40% of the bugs whatever temperatures they
  requested. The temperatures in the code, in the logs and in the names of the
  control passes are requests that had no effect. The model ran at its default
  thinking level, minimal.
- Without the developer fix, on the 194 patches that both judged, agreement
  with the labels beyond chance is not established for Gemini 3.5 Flash Lite
  reviewing offline (kappa 0.16); Claude Sonnet 5.5 catches 14 of 28
  overfitting patches while vetoing 8 of 166 correct ones (kappa 0.50).
  Gemini judged all 202 plausible patches, Claude Sonnet 5.5 194 of them.

Cost, from the logged token counts at the provider's list prices ($0.30 per
million input tokens, $2.50 per million output tokens): $16.08 for the Full
configuration (46.4M tokens, $0.041 per bug, $0.092 per correct fix), $8.51
without the Judge ($0.051 per correct fix), $9.21 for the four resampling
passes, or $6.88 when each bug stops at its first test-passing patch.

---

## Repository structure

```
SV-ARP/
├── src/
│   ├── agentic_apr.py        # agents, adaptive mechanisms, LangGraph loop
│   └── run_benchmark.py      # Defects4J benchmark driver
├── run_all.sh                # supervisor for long unattended runs
├── benchmark/
│   ├── versions.txt          # the 388 active Defects4J v1.2 bugs
│   └── mapping.csv           # bug -> modified-class source path
├── scripts/
│   ├── check_env.sh          # environment check; run this first
│   └── judge_swap.py         # offline review of plausible patches by a second model
├── analysis/
│   ├── make_figures.py       # regenerates every table and statistic
│   ├── report.md             # its output for the paper
│   └── check_paper_numbers.py  # compares the manuscript source with report.md
├── data/
│   ├── verification/         # labels: 3 configurations + 4 resampling passes
│   ├── second_verification/  # second verification of the 3 configurations
│   ├── overrides_all.csv     # label overrides and later labels, with their reasons
│   ├── judged_texts.csv      # records judged but not in the package, by the SHA-256 of their patch text
│   ├── text_labels.csv       # labels of patch texts labelled on records not in the package, by the SHA-256 of the text
│   ├── harness_false_negatives.csv   # candidates logged as failing that pass (sensitivity only)
│   ├── time_limit_events.csv # test runs and baseline builds cut by their time limit, from the run logs
│   ├── lost_requests.csv     # requests to the model that failed after all retries, from the run logs
│   ├── offline_review/       # verdicts of the offline reviewers
│   ├── canonical/            # one row per bug and configuration
│   └── results/              # raw result files, zipped (7 archives)
├── replication/replication_guide.txt
├── .env.example
└── requirements.txt
```

The raw result files (one record per bug and execution, with every candidate
patch, verdict, requested temperature and token count; about 460 MB unpacked)
are in `data/results/`, one zip per configuration and per resampling pass.

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
chmod +x run_all.sh scripts/check_env.sh
```

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 11)   # macOS; adjust on Linux
export PATH="$JAVA_HOME/bin:$PATH"
export TZ="America/Los_Angeles"
export _JAVA_OPTIONS="-Duser.language=en -Duser.country=US"
export D4J_HOME=/path/to/defects4j
export PATH="$D4J_HOME/framework/bin:$PATH"
export GEMINI_API_KEY=<your-key>

./scripts/check_env.sh      # must end with: Environment correct.
```

API keys are read from the environment only. Never commit one.

### Read this before running

The JVM takes its default locale from operating-system settings, not from
`LANG`. On a non-English system, Defects4J tests that assert on formatted
compiler diagnostics fail on pristine, unpatched checkouts (18 of 25 Closure
bugs in our measurement), and a candidate is plausible only if no relevant
test fails, so those bugs become unrepairable. The `_JAVA_OPTIONS` line above
is required; `check_env.sh` verifies it on Closure 2b (one failing test,
named), and checks that a Gradle-built bug (Mockito 1b) builds and reports its
26 failing tests. The two smoke tests take a few minutes.

---

## Running

```bash
# one bug
python src/run_benchmark.py --bug Lang_33

# the benchmark, resumable
python src/run_benchmark.py --bug-list benchmark/versions.txt --resume

# all three configurations, unattended (survives network drops and restarts)
nohup ./run_all.sh > supervisor.log 2>&1 &
./run_all.sh --status
touch STOP                  # the supervisor exits when the current pass over the bug list ends
# to stop at once (the bug in progress leaves no record and is run again by --resume):
pkill -9 -f run_all.sh; pkill -f run_benchmark.py

# one configuration, or one resampling pass (named after the temperature it requests)
./run_all.sh no_judge
./run_all.sh sample_t045a
```

Configuration is by environment variable:

| Variable | Default | Meaning |
|---|---|---|
| `APR_ABLATION` | `full` | `full`, `binary_only`, `no_judge` |
| `APR_REPAIR_MODEL`, `APR_JUDGE_MODEL` | `gemini-3.5-flash-lite` | model identifiers |
| `APR_TEMPERATURE` | `0.1` | initial temperature requested (`gemini-3.5-flash-lite` ignores it) |
| `APR_MAX_ITERATIONS` | `4` | tested candidates per bug |
| `APR_RESULTS_DIR` | `results` | one directory per configuration |
| `APR_WORK_DIR` | `/tmp/d4j_benchmark` | checkout scratch space |
| `APR_MAPPING_FILE` | `mapping.csv` | optional; set to `benchmark/mapping.csv` |
| `APR_USD_PER_TOKEN` | `0.00000035` | flat rate of the estimate that the harness logs; the paper prices input and output tokens separately (`--price-in`, `--price-out` of `analysis/make_figures.py`) |

Use a separate results directory per configuration: `--resume` matches on the
bug id alone.

---

## Regenerating the paper's numbers

Unpack the raw results into `data/`, then run the script:

```bash
for z in data/results/*.zip; do unzip -q -o "$z" -d data; done
cp data/verification/*.csv data/
printf 'Mockito_%s\n' 1 2 3 4 5 6 7 8 9 10 11 18 19 20 21 > data/mockito_gradle_15.txt   # the 15 Gradle-built Mockito bugs
python analysis/make_figures.py --raw data --rule first \
    --bug-list benchmark/versions.txt \
    --overrides data/overrides_all.csv \
    --judge-swap data/offline_review/judge_swap_gemini_3_5_flash_lite_semantic.csv \
    --judge-swap data/offline_review/judge_swap_claude_sonnet_5_5_semantic.csv \
    --false-negatives data/harness_false_negatives.csv \
    --judged-texts data/judged_texts.csv \
    --text-labels data/text_labels.csv \
    --rerun full=20261110_104737 \
    --reexecuted binary_only=20261120_091831+20261121_115528+20261123_171006 \
    --reexecuted no_judge=20261121_173559+20261123_173421 \
    --without-bugs data/mockito_gradle_15.txt \
    --second-verification data/second_verification \
    > report.md
cmp report.md analysis/report.md && echo "report.md matches analysis/report.md"
for f in data/canonical/*.csv; do cmp "$f" "figures_out/$(basename "$f")" && echo "$(basename "$f") matches"; done
```

The last two commands check that the output matches `analysis/report.md` (the
script is deterministic) and that the per-bug tables it writes to `figures_out/`
match `data/canonical/`.
`--judged-texts` lists eleven records of the Full configuration on which labels
and reviews were given and that are not in the package, by the SHA-256 of
their patch text, which is that of the bug's canonical record; `--text-labels`
the labels of three patch texts that were labelled on records that are not in
the package, by the SHA-256 of the text (a record with that text takes the
label, as it takes that of any labelled patch with the same text); `--rerun` names
a Full session executed after the labels of that configuration had been given
(its records take the label of a labelled patch with the same text, or of an
override row that names the session); `--reexecuted` the sessions that executed
Binary-Only and No-Judge with the corrected code, which are the only canonical
ones for these two configurations; and `--without-bugs` a list of bugs for one more sensitivity analysis (section 14c of
the report repeats the comparisons without the 15 Gradle-built Mockito bugs).

A second script compares the manuscript with the report:

```bash
# every table row and figure of the manuscript that comes from the report
python analysis/check_paper_numbers.py analysis/report.md <manuscript>.tex
```

---


## License

MIT. See `LICENSE`.
