# SV-ARP figures — regenerated from raw files

rule for repeated executions: **first session**

- `full`: 6 session(s), 442 rows, 388 bugs; verification: `./verification_full.csv` (373 rows)
- `no_semantic`: 2 session(s), 409 rows, 388 bugs; verification: `./verification_no_semantic.csv` (373 rows)
- `binary_only`: 2 session(s), 389 rows, 388 bugs; verification: `./verification_binary_only.csv` (373 rows)
- `no_judge`: 2 session(s), 388 rows, 388 bugs; verification: `./verification_no_judge.csv` (373 rows)

benchmark: 388 bugs

canonical plausible patches exported to `figures_out/canonical_patches_<arm>.csv`

## 1. Evaluable bugs and exclusions

- excluded per arm: full=15, no_semantic=15, binary_only=15, no_judge=15  (identical set in every arm)
- evaluable in all four arms (the paired set): **373**
  - `full` build_broken: Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8, Mockito_9, Mockito_10, Mockito_11, Mockito_18, Mockito_19, Mockito_20, Mockito_21
  - `no_semantic` build_broken: Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8, Mockito_9, Mockito_10, Mockito_11, Mockito_18, Mockito_19, Mockito_20, Mockito_21
  - `binary_only` build_broken: Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8, Mockito_9, Mockito_10, Mockito_11, Mockito_18, Mockito_19, Mockito_20, Mockito_21
  - `no_judge` build_broken: Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8, Mockito_9, Mockito_10, Mockito_11, Mockito_18, Mockito_19, Mockito_20, Mockito_21

## 2. Bugs executed more than once (appendix table)

- `full`: 44 bug(s) with >1 valid execution; plausibility differs in 4

  | bug | exec 1 | exec 2 | canonical | reviewed | label applies |
  |---|---|---|---|---|---|
  | Chart_16 | 140443: P/it1/2 | 143326: P/it1/2 | 140443 | 143326 | override |
  | Chart_17 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | verification (identical patch) |
  | Chart_18 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Chart_19 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | verification (identical patch) |
  | Chart_20 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | verification (identical patch) |
  | Chart_21 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | override |
  | Chart_22 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Chart_23 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | verification (identical patch) |
  | Chart_24 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | verification (identical patch) |
  | Chart_25 | 140443: P/it1/2 | 143326: P/it0/1 | 140443 | 143326 | override |
  | Chart_26 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | verification (identical patch) |
  | Closure_1 | 140443: np/it-1/4 | 143326: P/it0/1 | 140443 | 143326 | n/a |
  | Closure_5 | 140443: P/it0/1 | 143326: P/it2/3 | 140443 | 143326 | override |
  | Closure_6 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | verification (identical patch) |
  | Closure_7 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | override |
  | Closure_8 | 140443: P/it1/2 | 143326: P/it2/3 | 140443 | 143326 | override |
  | Closure_9 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | override |
  | Closure_10 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_11 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_12 | 140443: np/it-1/4 | 143326: P/it1/2 | 140443 | 143326 | n/a |
  | Closure_13 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | verification (identical patch) |
  | Closure_14 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_15 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_16 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_17 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_18 | 140443: P/it0/1 | 143326: P/it0/1 | 140443 | 143326 | verification (identical patch) |
  | Closure_19 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_20 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_21 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_22 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_23 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_24 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_25 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_26 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_27 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_28 | 140443: P/it2/3 | 143326: np/it-1/4 | 140443 | 143326 | override |
  | Closure_29 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_30 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_31 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_32 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_33 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_34 | 140443: np/it-1/4 | 143326: np/it-1/4 | 140443 | 143326 | n/a |
  | Closure_35 | 140443: np/it-1/4 | 143326: P/it3/4 | 140443 | 143326 | n/a |
  | Closure_36 | 140443: P/it1/2 | 143326: P/it1/2 | 140443 | 143326 | verification (identical patch) |

- `no_semantic`: none
- `binary_only`: none
- `no_judge`: none
## 3. Headline, paired set

plausible = a test-passing candidate was found; accepted = the loop ended with an accepted patch; correct = the first plausible candidate is labelled correct; delivered correct = the accepted patch is labelled correct.

| arm | plausible | accepted | correct | delivered correct | pending | precision (correct/plausible) | overfitting |
|---|---|---|---|---|---|---|---|
| full | 196 | 196 | 170 | 170 | 0 | 86.7% | 26 |
| no_semantic | 194 | 191 | 161 | 160 | 0 | 83.0% | 33 |
| binary_only | 189 | 188 | 160 | 159 | 0 | 84.7% | 29 |
| no_judge | 181 | 181 | 156 | 156 | 0 | 86.2% | 25 |

- `full`: Judge withheld the first plausible candidate and the loop delivered a different patch: Math_63; plausible candidate found but no patch accepted: none
- `no_semantic`: Judge withheld the first plausible candidate and the loop delivered a different patch: Lang_47; plausible candidate found but no patch accepted: Math_49, Math_63, Math_92
- `binary_only`: Judge withheld the first plausible candidate and the loop delivered a different patch: Time_20; plausible candidate found but no patch accepted: Math_49

full arm label split: {'Correct (identical)': 66, 'Correct (equivalent)': 65, 'Correct (alternative)': 39, 'Overfitting': 26}; strict correct (identical + equivalent) = 131, lenient (plus alternative) = 170; strict precision = 66.8%

## 4. Statistical comparison (paired on bug identity)

McNemar exact test against `full`; p two-sided, p1 one-sided (full > arm), Holm over the three correct-fix comparisons:

| arm | correct: full-only | arm-only | discordant | p | p1 | Holm p | plausible: full-only | arm-only | discordant | p | delivered correct: full-only | arm-only | p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no_semantic | 34 | 25 | 59 | 0.2976 | 0.1488 | 0.4741 | 30 | 28 | 58 | 0.8957 | 34 | 24 | 0.2370 |
| binary_only | 34 | 24 | 58 | 0.2370 | 0.1185 | 0.4741 | 33 | 26 | 59 | 0.4350 | 34 | 23 | 0.1849 |
| no_judge | 33 | 19 | 52 | 0.0704 | 0.0352 | 0.2112 | 35 | 20 | 55 | 0.0581 | 33 | 19 | 0.0704 |

Pairwise among ablations (correct):

- no_semantic vs binary_only: no_semantic-only=29, binary_only-only=28, p=1.0000
- binary_only vs no_judge: binary_only-only=28, no_judge-only=24, p=0.6778
- no_semantic vs no_judge: no_semantic-only=31, no_judge-only=26, p=0.5966

Cochran's Q across the four arms (correct): Q=3.75, df=3, p=0.2895
(no ordered-trend test: with three nested arms the Page statistic reduces to the one-sided full-vs-no_judge comparison, and the four-arm orderings are not implied by prompt-content inclusion)

Bugs fixed by k of 4 arms: k=0: 157, k=1: 42, k=2: 32, k=3: 27, k=4: 115 → outcome depends on the arm for 101 bugs

## 4b. First attempts are four replications of the same procedure

The first-attempt prompt is identical in every arm (feedback exists only after a failure), so iteration-1 outcomes replicate one stochastic procedure four times.

| arm | iter-1 plausible | iter-1 correct | gained at iterations 2-4: plausible | correct | bugs without a first-attempt plausible | later plausible among them |
|---|---|---|---|---|---|---|
| full | 143 | 126 | 53 | 44 | 230 | 53 (23.0%) |
| no_semantic | 146 | 128 | 48 | 33 | 227 | 48 (21.1%) |
| binary_only | 134 | 118 | 55 | 42 | 239 | 55 (23.0%) |
| no_judge | 134 | 119 | 47 | 37 | 239 | 47 (19.7%) |

Pairwise discordance at iteration 1 (bugs correct in exactly one of the two arms):

- full vs no_semantic: correct 19/21 (10.7% of bugs), plausible 20/23 (11.5%)
- full vs binary_only: correct 29/21 (13.4% of bugs), plausible 29/20 (13.1%)
- full vs no_judge: correct 26/19 (12.1% of bugs), plausible 27/18 (12.1%)
- no_semantic vs binary_only: correct 22/12 (9.1% of bugs), plausible 22/10 (8.6%)
- no_semantic vs no_judge: correct 28/19 (12.6% of bugs), plausible 29/17 (12.3%)
- binary_only vs no_judge: correct 22/23 (12.1% of bugs), plausible 21/21 (11.3%)

Four first attempts combined (proxy for best-of-4 resampling at the first-attempt temperature): union plausible=180, union correct=164; first-plausible-wins plausible=180, correct=156

| arm (full loop) | vs first-plausible-wins proxy: plausible full-only/proxy-only, p | correct, p | vs union correct, p |
|---|---|---|---|
| full | 36/20, p=0.0440 | 31/17, p=0.0595 | 31/25, p=0.5044 |
| no_semantic | 28/14, p=0.0436 | 24/19, p=0.5424 | 20/23, p=0.7608 |
| binary_only | 35/26, p=0.3057 | 28/24, p=0.6778 | 24/28, p=0.6778 |
| no_judge | 31/30, p=1.0000 | 27/27, p=1.0000 | 23/31, p=0.3409 |

## 4c. Equal-budget control: independent single attempts (best-of-k resampling)

- `sample_t010`: verification file `./verification_sample_t010.csv`; textually identical to a labelled arm patch for 107 bugs, label agreement 106/107; disagreements: Math_94 (Correct (alternative) vs arm Overfitting)
- `sample_t045a`: verification file `./verification_sample_t045a.csv`; textually identical to a labelled arm patch for 110 bugs, label agreement 108/110; disagreements: Closure_9 (Correct (equivalent) vs arm Overfitting), Math_94 (Correct (alternative) vs arm Overfitting)
- `sample_t045b`: verification file `./verification_sample_t045b.csv`; textually identical to a labelled arm patch for 107 bugs, label agreement 106/107; disagreements: Closure_9 (Correct (equivalent) vs arm Overfitting)
- `sample_t085`: verification file `./verification_sample_t085.csv`; textually identical to a labelled arm patch for 103 bugs, label agreement 102/103; disagreements: Closure_9 (Correct (equivalent) vs arm Overfitting)

| sample | temperature | evaluable bugs run | plausible | correct | strict correct (identical+equivalent) | pending labels | label sources |
|---|---|---|---|---|---|---|---|
| sample_t010 | 0.1 | 373 | 134 | 115 | 98 | 0 | {'verification': 133, 'override': 1} |
| sample_t045a | 0.45 | 373 | 141 | 122 | 104 | 0 | {'verification': 139, 'override': 2} |
| sample_t045b | 0.45 | 373 | 139 | 119 | 101 | 0 | {'verification': 138, 'override': 1} |
| sample_t085 | 0.85 | 373 | 135 | 121 | 106 | 0 | {'verification': 134, 'override': 1} |

Best-of-k in temperature order (first plausible sample wins):

| k | samples | plausible | correct | strict correct | pending | vs full: plausible full-only/ctrl-only, p | correct, p | vs no_judge: plausible, p | correct, p |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sample_t010 | 134 | 115 | 98 | 0 | 73/11, p=0.0000 | 65/10, p=0.0000 | 61/14, p=0.0000 | 53/12, p=0.0000 |
| 2 | sample_t010, sample_t045a | 159 | 136 | 115 | 0 | 54/17, p=0.0000 | 51/17, p=0.0000 | 48/26, p=0.0141 | 40/20, p=0.0135 |
| 3 | sample_t010, sample_t045a, sample_t045b | 167 | 143 | 120 | 0 | 51/22, p=0.0009 | 48/21, p=0.0016 | 45/31, p=0.1354 | 37/24, p=0.1237 |
| 4 | sample_t010, sample_t045a, sample_t045b, sample_t085 | 180 | 154 | 129 | 0 | 44/28, p=0.0764 | 41/25, p=0.0640 | 40/39, p=1.0000 | 33/31, p=0.9007 |

Best-of-4 control vs every configuration (McNemar exact, two-sided):

| configuration | plausible: conf-only/ctrl-only, p | correct: conf-only/ctrl-only, p |
|---|---|---|
| full | 44/28, p=0.0764 | 41/25, p=0.0640 |
| no_semantic | 38/24, p=0.0980 | 31/24, p=0.4188 |
| binary_only | 39/30, p=0.3356 | 35/29, p=0.5323 |
| no_judge | 40/39, p=1.0000 | 33/31, p=0.9007 |

control cost over the 4 samples: 21,909,319 tokens, $7.67 ($0.0206 per bug)
first-plausible-wins correct over all 24 sample orderings: min 150, max 154, mean 151.9; union (a correct patch in at least one sample): 159

## 5. Per project (plausible / correct)

| project | n | full | no_semantic | binary_only | no_judge |
|---|---|---|---|---|---|
| Chart | 26 | 22 / 21 | 20 / 20 | 18 / 18 | 18 / 18 |
| Closure | 131 | 45 / 38 | 47 / 36 | 50 / 42 | 45 / 35 |
| Lang | 61 | 37 / 32 | 37 / 31 | 36 / 29 | 38 / 34 |
| Math | 106 | 63 / 54 | 64 / 53 | 58 / 51 | 57 / 48 |
| Mockito | 23 | 16 / 14 | 13 / 12 | 12 / 11 | 15 / 14 |
| Time | 26 | 13 / 11 | 13 / 9 | 15 / 9 | 8 / 7 |

## 6. Iteration at which the accepted patch was produced (full arm)

| attempt | accepted patches | share | cumulative |
|---|---|---|---|
| 1 | 143 | 73.0% | 73.0% |
| 2 | 31 | 15.8% | 88.8% |
| 3 | 13 | 6.6% | 95.4% |
| 4 | 9 | 4.6% | 100.0% |

mean iterations, full arm, all evaluable bugs: 2.65

## 6b. Adaptive-mechanism activity (repair steps after a failed attempt)

| arm | later repair steps | temperature > 0.1 | at 0.45 | at 0.85 (surgical mode) | other levels | bugs reaching surgical mode | regenerations after unusable output | no-op echoes |
|---|---|---|---|---|---|---|---|---|
| full | 616 | 412 (67%) | 255 | 101 | 56 | 101 | 15 | 20 |
| no_semantic | 613 | 414 (68%) | 248 | 96 | 70 | 96 | 9 | 15 |
| binary_only | 631 | 417 (66%) | 247 | 95 | 75 | 95 | 10 | 18 |
| no_judge | 667 | 542 (81%) | 219 | 115 | 208 | 115 | 14 | 12 |

(the 0.45 level is the no-op rule plus the near-identical-and-failed rule firing together on a localized edit; 0.85 is surgical mode, reachable only at the fourth attempt)

## 7. Cost and time (canonical executions, evaluable set)

| arm | total tokens | total USD | mean USD/bug | mean s/bug | mean s (accepted) | mean s (not plausible) |
|---|---|---|---|---|---|---|
| full | 44,757,776 | $15.67 | $0.0420 | 222 | 109 | 348 |
| no_semantic | 40,732,583 | $14.26 | $0.0382 | 171 | 82 | 237 |
| binary_only | 44,405,261 | $15.54 | $0.0417 | 184 | 90 | 281 |
| no_judge | 24,909,660 | $8.72 | $0.0234 | 130 | 63 | 193 |

## 7b. Token split per arm (canonical executions, evaluable set)

| arm | repair calls | repair prompt tokens | repair output tokens | judge calls | judge prompt tokens | judge output tokens | judge share of all tokens |
|---|---|---|---|---|---|---|---|
| full | 989 | 23,646,244 | 721,840 | 978 | 20,161,345 | 228,347 | 45.6% |
| no_semantic | 986 | 20,494,527 | 575,646 | 970 | 19,435,722 | 226,688 | 48.3% |
| binary_only | 1004 | 22,785,197 | 739,273 | 993 | 20,649,657 | 231,134 | 47.0% |
| no_judge | 1040 | 24,242,986 | 666,674 | 0 | 0 | 0 | 0.0% |

## 8. Baseline failing-test counts (full arm)

1 tests: 239 bugs, 2 tests: 69 bugs, 3 tests: 21 bugs, 4 tests: 10 bugs, 5 tests: 7 bugs, 6 tests: 4 bugs, 7 tests: 6 bugs, 8 tests: 7 bugs, 9 tests: 1 bugs, 10+ tests: 9 bugs

## 8b. Pre-existing failures beyond the trigger tests (B \ Tg)

| arm | bugs with extra baseline failures | extra failing tests in total | per project (bugs) |
|---|---|---|---|
| full | 2 | 2 | Chart 0, Closure 0, Lang 0, Math 0, Mockito 2, Time 0 |
| no_semantic | 2 | 2 | Chart 0, Closure 0, Lang 0, Math 0, Mockito 2, Time 0 |
| binary_only | 6 | 7 | Chart 0, Closure 0, Lang 0, Math 1, Mockito 5, Time 0 |
| no_judge | 1 | 1 | Chart 0, Closure 0, Lang 0, Math 0, Mockito 1, Time 0 |

## 9. Inter-rater agreement on the full arm's plausible patches

- final label vs Independent review 2 (blind): n=131, agreement=93.1%, κ=0.760 [95% bootstrap CI 0.59, 0.89], disagreements=9: Math_44 (final Overfitting; pass Correct (alternative)); Closure_7 (final Overfitting; pass Correct (alternative)); Chart_14 (final Correct (alternative); pass Incorrect); Lang_16 (final Overfitting; pass Correct (alternative)); Time_13 (final Overfitting; pass Correct (alternative)); Lang_23 (final Overfitting; pass Correct (alternative)); Math_94 (final Overfitting; pass Correct (alternative)); Closure_9 (final Overfitting; pass Correct (alternative)); Lang_31 (final Overfitting; pass Correct (alternative))
- final label vs Independent review 3 (blind): n=195, agreement=96.9%, κ=0.858 [95% bootstrap CI 0.73, 0.96], disagreements=6: Math_44 (final Overfitting; pass Correct (alternative)); Closure_7 (final Overfitting; pass Correct (alternative)); Chart_14 (final Correct (alternative); pass Incorrect); Lang_16 (final Overfitting; pass Correct (alternative)); Math_94 (final Overfitting; pass Correct (alternative)); Closure_9 (final Overfitting; pass Correct (alternative))

## 10. Offline judge pilot vs human labels (full arm, plausible set)

| model | judged | vetoed | bad caught | correct wrongly vetoed | veto precision | κ vs human [95% bootstrap CI] | not canonical |
|---|---|---|---|---|---|---|---|
| deepseek_v4_flash_semantic | 192 | 20 | 4/26 | 16/166 | 4/20 | 0.064 [-0.09, 0.23] | 7 (Chart_14, Chart_16, Chart_21, Chart_25, Closure_5, Closure_7, Closure_8) |
  - not judged: Closure_28, Closure_38, Lang_45, Mockito_17
  - re-judge on the canonical patches: Chart_14, Chart_16, Chart_21, Chart_25, Closure_28, Closure_38, Closure_5, Closure_7, Closure_8, Lang_45, Mockito_17
| gemini_3_5_flash_lite_semantic | 194 | 10 | 3/26 | 7/168 | 3/10 | 0.100 [-0.06, 0.28] | 7 (Chart_14, Chart_16, Chart_21, Chart_25, Closure_5, Closure_7, Closure_8) |
  - not judged: Closure_28, Closure_38
  - re-judge on the canonical patches: Chart_14, Chart_16, Chart_21, Chart_25, Closure_28, Closure_38, Closure_5, Closure_7, Closure_8

## 11. Sensitivity to the repeated-execution rule (full arm)

- rule `first`: plausible=196, correct=170, pending=0
- rule `last`: plausible=198, correct=172, pending=0
- strict (plausible in every execution): plausible=195

canonical per-bug tables written to `figures_out/canonical_<arm>.csv`
