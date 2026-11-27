# SV-ARP figures — regenerated from raw files

rule for repeated executions: **first session**

- `full`: 8 session(s), 403 rows, 388 bugs; verification: `data/verification_full.csv` (373 rows)
- `binary_only`: executed again in full in session(s) 20261120_091831, 20261121_115528, 20261123_171006; the earlier session(s) 20261017_013332, 20261018_045332 are kept for labels and comparison only
- `binary_only`: 3 session(s), 399 rows, 388 bugs; verification of the earlier sessions: `data/verification_binary_only.csv` (373 rows)
- `no_judge`: executed again in full in session(s) 20261121_173559, 20261123_173421; the earlier session(s) 20261013_100040, 20261014_083544 are kept for labels and comparison only
- `no_judge`: 2 session(s), 403 rows, 388 bugs; verification of the earlier sessions: `data/verification_no_judge.csv` (373 rows)

benchmark: 388 bugs

## 1. Evaluable bugs and exclusions

- excluded per arm: full=0, binary_only=0, no_judge=0  (identical set in every arm)
- evaluable in all three arms (the paired set): **388**

## 2. Bugs executed more than once (appendix table)

- `full`: none
- `binary_only`: none
- `no_judge`: none
Records that are never canonical:

- `full`: aborted (build_broken: Baseline does not compile): 15 (Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8, Mockito_9, Mockito_10, Mockito_11, Mockito_18, Mockito_19, Mockito_20, Mockito_21)
- `binary_only`: aborted (failed: all API keys exhausted for today: #1:498): 9 (Math_106, Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8)
- `binary_only`: aborted (build_broken: Baseline does not compile): 2 (Mockito_9, Mockito_10)
- `no_judge`: aborted (build_broken: Baseline does not compile): 15 (Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8, Mockito_9, Mockito_10, Mockito_11, Mockito_18, Mockito_19, Mockito_20, Mockito_21)

## 2b. Executions made after the verification

- `full`: session(s) 20261110_104737 executed after the verification; canonical record of 50 bugs

  | bug | record when the labels were given | re-execution | label | source of the label |
  |---|---|---|---|---|
  | Chart_16 | none in the data | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Chart_17 | none in the data | plausible at attempt 1 | Correct (identical) | verification (identical patch) |
  | Chart_19 | none in the data | plausible at attempt 1 | Correct (identical) | verification (identical patch) |
  | Chart_20 | none in the data | plausible at attempt 1 | Correct (identical) | verification (identical patch) |
  | Chart_23 | none in the data | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t010) |
  | Chart_24 | none in the data | plausible at attempt 1 | Correct (identical) | verification (identical patch) |
  | Chart_26 | none in the data | plausible at attempt 1 | Correct (identical) | verification (identical patch) |
  | Closure_5 | none in the data | plausible at attempt 1 | Correct (identical) | identical labelled patch (control pass sample_t010) |
  | Closure_6 | none in the data | plausible at attempt 1 | Correct (identical) | verification (identical patch) |
  | Closure_7 | none in the data | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261013_100040) |
  | Closure_8 | none in the data | plausible at attempt 4 | Correct (alternative) | labelled after the re-execution |
  | Closure_9 | none in the data | plausible at attempt 1 | Overfitting | override (identical patch) |
  | Closure_11 | none in the data | plausible at attempt 1 | Correct (identical) | identical labelled patch (binary_only, session 20261017_013332; kind from control pass sample_t010) |
  | Closure_12 | none in the data | plausible at attempt 3 | Correct (equivalent) | labelled after the re-execution |
  | Closure_18 | none in the data | plausible at attempt 1 | Correct (identical) | verification (identical patch) |
  | Closure_33 | none in the data | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Closure_36 | none in the data | plausible at attempt 3 | Correct (identical) | verification (identical patch) |

  none in the data -> correct: 15; none in the data -> not correct: 2; none in the data -> not plausible: 33

- `binary_only`: executed again in full with corrected code (session(s) 20261120_091831, 20261121_115528, 20261123_171006); 388 completed records, listed below when either execution is plausible

  | bug | record when the labels were given | re-execution | label | source of the label |
  |---|---|---|---|---|
  | Chart_1 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_3 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t010) |
  | Chart_4 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_6 | not plausible | plausible at attempt 1 | Correct (alternative) | identical labelled patch (control pass sample_t045a) |
  | Chart_7 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_8 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_9 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Chart_10 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Chart_11 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_12 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_14 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Chart_16 | not plausible | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Chart_17 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Chart_19 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Chart_20 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Chart_21 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (control pass sample_t045a) |
  | Chart_23 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (labelled on a record not in the data; --text-labels) |
  | Chart_24 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Chart_25 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Chart_26 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Closure_1 | not plausible | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Closure_3 | plausible at attempt 2, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Closure_5 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t045a) |
  | Closure_6 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Closure_7 | plausible at attempt 1, Correct | plausible at attempt 1 | Overfitting | identical labelled patch (control pass sample_t010) |
  | Closure_8 | plausible at attempt 3, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Closure_9 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | override (identical patch) |
  | Closure_10 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_11 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (binary_only, session 20261017_013332; kind from control pass sample_t010) |
  | Closure_18 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Closure_20 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_36 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Closure_38 | plausible at attempt 3, Correct | plausible at attempt 3 | Correct (identical) | labelled after the re-execution |
  | Closure_42 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (binary_only, session 20261017_013332; kind from full, session 20261011_005033) |
  | Closure_44 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_51 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Closure_52 | plausible at attempt 3, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (full, session 20261011_005033) |
  | Closure_53 | plausible at attempt 1, Correct | plausible at attempt 3 | Correct (alternative) | labelled after the re-execution |
  | Closure_56 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Closure_57 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_58 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t045a) |
  | Closure_61 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_62 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (control pass sample_t010) |
  | Closure_64 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_65 | not plausible | plausible at attempt 1 | Correct (identical) | identical labelled patch (full, session 20261011_005033) |
  | Closure_70 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_73 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_75 | plausible at attempt 4, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Closure_77 | plausible at attempt 2, Correct | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Closure_78 | plausible at attempt 3, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_80 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_86 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_88 | plausible at attempt 2, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Closure_91 | plausible at attempt 2, Overfitting | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_92 | plausible at attempt 2, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Closure_94 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261013_100040) |
  | Closure_95 | plausible at attempt 2, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Closure_96 | not plausible | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t010) |
  | Closure_97 | plausible at attempt 2, Correct | plausible at attempt 4 | Correct (equivalent) | labelled after the re-execution |
  | Closure_101 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_102 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_107 | not plausible | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_109 | not plausible | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_111 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_113 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_118 | not plausible | plausible at attempt 1 | Correct (identical) | labelled after the re-execution |
  | Closure_119 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Closure_120 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_122 | plausible at attempt 2, Overfitting | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_123 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Closure_126 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | labelled after the re-execution |
  | Closure_127 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Closure_128 | plausible at attempt 4, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_129 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261014_083544) |
  | Closure_130 | plausible at attempt 1, Correct | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261014_083544) |
  | Closure_131 | plausible at attempt 1, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Lang_4 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261014_083544) |
  | Lang_5 | not plausible | plausible at attempt 3 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_8 | not plausible | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Lang_11 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_12 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Lang_13 | plausible at attempt 4, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_14 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_16 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | override (identical patch) |
  | Lang_17 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261017_013332; kind from full, session 20261011_005033) |
  | Lang_21 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Lang_23 | plausible at attempt 1, Overfitting | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Lang_24 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_27 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_28 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_31 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Lang_32 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_33 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_37 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Lang_40 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_41 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_42 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Lang_43 | plausible at attempt 3, Overfitting | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (full, session 20261011_005033) |
  | Lang_44 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_45 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Lang_46 | plausible at attempt 2, Correct | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Lang_47 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_49 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_50 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Lang_51 | not plausible | plausible at attempt 4 | Correct (alternative) | labelled after the re-execution |
  | Lang_54 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (binary_only, session 20261017_013332) |
  | Lang_55 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_56 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_57 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261017_013332; kind from full, session 20261011_005033) |
  | Lang_58 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Lang_59 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_60 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_61 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_62 | plausible at attempt 3, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Lang_63 | not plausible | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Lang_64 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Math_3 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Math_4 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_5 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_9 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_10 | plausible at attempt 1, Correct | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Math_11 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_12 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_13 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_14 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_19 | plausible at attempt 2, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_20 | not plausible | plausible at attempt 1 | Overfitting | identical labelled patch (labelled on a record not in the data; --text-labels) |
  | Math_23 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Math_24 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261014_083544) |
  | Math_25 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (control pass sample_t045a) |
  | Math_26 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_27 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_28 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Math_30 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_31 | not plausible | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Math_32 | not plausible | plausible at attempt 4 | Correct (identical) | identical labelled patch (control pass sample_t045b) |
  | Math_33 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_34 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_35 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_41 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_42 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_43 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_45 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_46 | plausible at attempt 1, Correct | plausible at attempt 4 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_48 | plausible at attempt 1, Correct | plausible at attempt 4 | Correct (identical) | identical labelled patch (binary_only, session 20261017_013332; kind from full, session 20261011_005033) |
  | Math_49 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_50 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (full, session 20261011_005033) |
  | Math_53 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_56 | plausible at attempt 3, Correct | plausible at attempt 2 | Correct (identical) | labelled after the re-execution |
  | Math_57 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_59 | not plausible | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Math_60 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_61 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_63 | plausible at attempt 1, Correct | plausible at attempt 1 | Overfitting | identical labelled patch (full, session 20261011_005033, accepted patch) |
  | Math_69 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_70 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_71 | plausible at attempt 2, Overfitting | plausible at attempt 4 | Overfitting | labelled after the re-execution |
  | Math_75 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_77 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_78 | not plausible | plausible at attempt 3 | Overfitting | labelled after the re-execution |
  | Math_79 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_82 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (identical) | identical labelled patch (binary_only, session 20261017_013332; kind from full, session 20261011_005033) |
  | Math_83 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_84 | plausible at attempt 2, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Math_85 | plausible at attempt 2, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (control pass sample_t045b) |
  | Math_86 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_87 | plausible at attempt 2, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (control pass sample_t085) |
  | Math_90 | plausible at attempt 3, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Math_91 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_94 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | override (identical patch) |
  | Math_95 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_96 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_97 | not plausible | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Math_98 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_100 | plausible at attempt 3, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Math_101 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t085) |
  | Math_102 | plausible at attempt 3, Correct | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Math_103 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_105 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_106 | plausible at attempt 1, Correct | plausible at attempt 3 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_1 | none in the data | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Mockito_2 | none in the data | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_5 | none in the data | plausible at attempt 1 | Correct (identical) | labelled after the re-execution |
  | Mockito_9 | none in the data | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Mockito_11 | none in the data | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Mockito_12 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Mockito_13 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_15 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_17 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_18 | none in the data | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_21 | none in the data | plausible at attempt 4 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_22 | not plausible | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Mockito_24 | not plausible | plausible at attempt 2 | Correct (equivalent) | identical labelled patch (full, session 20261011_005033) |
  | Mockito_27 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_29 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_30 | not plausible | plausible at attempt 3 | Correct (alternative) | labelled after the re-execution |
  | Mockito_31 | plausible at attempt 2, Overfitting | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (control pass sample_t045a) |
  | Mockito_32 | plausible at attempt 4, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_33 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_34 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (binary_only, session 20261018_045332; kind from full, session 20261011_005033) |
  | Mockito_36 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_38 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (binary_only, session 20261018_045332; kind from full, session 20261012_084950) |
  | Time_1 | plausible at attempt 3, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Time_3 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Time_4 | plausible at attempt 1, Correct | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Time_5 | plausible at attempt 2, Overfitting | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Time_9 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (binary_only, session 20261018_045332) |
  | Time_10 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Time_11 | not plausible | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Time_12 | plausible at attempt 3, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Time_13 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (binary_only, session 20261018_045332) |
  | Time_14 | plausible at attempt 2, Overfitting | plausible at attempt 3 | Overfitting | labelled after the re-execution |
  | Time_15 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261012_084950) |
  | Time_17 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Time_18 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Time_19 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Time_20 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261018_045332; kind from control pass sample_t010) |
  | Time_23 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t045a) |

  correct -> correct: 123; correct -> not correct: 8; correct -> not plausible: 28; none in the data -> correct: 6; none in the data -> not correct: 1; none in the data -> not plausible: 8; not correct -> correct: 6; not correct -> not correct: 16; not correct -> not plausible: 8; not plausible -> correct: 16; not plausible -> not correct: 6; not plausible -> not plausible: 162

- `no_judge`: executed again in full with corrected code (session(s) 20261121_173559, 20261123_173421); 388 completed records, listed below when either execution is plausible

  | bug | record when the labels were given | re-execution | label | source of the label |
  |---|---|---|---|---|
  | Chart_1 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_3 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t010) |
  | Chart_4 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_6 | plausible at attempt 2, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (control pass sample_t045a) |
  | Chart_7 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_8 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_9 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Chart_10 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Chart_11 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_12 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261010_140443) |
  | Chart_13 | not plausible | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Chart_14 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (binary_only, session 20261120_091831) |
  | Chart_17 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Chart_19 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Chart_20 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Chart_21 | plausible at attempt 3, Correct | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Chart_23 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t010) |
  | Chart_24 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Chart_26 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Closure_1 | plausible at attempt 4, Overfitting | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Closure_5 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t045a) |
  | Closure_6 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Closure_7 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Closure_8 | plausible at attempt 3, Correct | plausible at attempt 4 | Correct (alternative) | labelled after the re-execution |
  | Closure_9 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | override (identical patch) |
  | Closure_10 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t045a) |
  | Closure_12 | plausible at attempt 4, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_13 | plausible at attempt 2, Overfitting | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_16 | not plausible | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_17 | not plausible | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Closure_18 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Closure_20 | plausible at attempt 2, Correct | plausible at attempt 3 | Correct (equivalent) | labelled after the re-execution |
  | Closure_25 | not plausible | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Closure_33 | not plausible | plausible at attempt 3 | Correct (identical) | labelled after the re-execution |
  | Closure_36 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261110_104737) |
  | Closure_38 | plausible at attempt 4, Correct | plausible at attempt 2 | Correct (identical) | labelled after the re-execution |
  | Closure_42 | plausible at attempt 2, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (binary_only, session 20261017_013332; kind from full, session 20261011_005033) |
  | Closure_44 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_51 | not plausible | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261120_091831) |
  | Closure_52 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (full, session 20261011_005033) |
  | Closure_56 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Closure_57 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_58 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t045a) |
  | Closure_61 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_62 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (control pass sample_t010) |
  | Closure_64 | not plausible | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_70 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_73 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_75 | plausible at attempt 3, Correct | plausible at attempt 3 | Correct (equivalent) | labelled after the re-execution |
  | Closure_77 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_78 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_86 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_88 | plausible at attempt 2, Overfitting | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_91 | plausible at attempt 3, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Closure_92 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | labelled after the re-execution |
  | Closure_94 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261013_100040) |
  | Closure_95 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_96 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from control pass sample_t010) |
  | Closure_97 | plausible at attempt 2, Correct | plausible at attempt 4 | Correct (equivalent) | labelled after the re-execution |
  | Closure_101 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_102 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_103 | not plausible | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Closure_109 | plausible at attempt 1, Correct | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_111 | plausible at attempt 4, Correct | not plausible | N/A (not plausible) | n/a |
  | Closure_113 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (identical) | identical labelled patch (no_judge, session 20261013_100040; kind from full, session 20261011_005033) |
  | Closure_122 | plausible at attempt 1, Correct | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_123 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Closure_126 | not plausible | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Closure_127 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Closure_129 | plausible at attempt 1, Overfitting | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Closure_130 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Closure_131 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | labelled after the re-execution |
  | Closure_133 | not plausible | plausible at attempt 1 | Correct (alternative) | identical labelled patch (full, session 20261011_005033) |
  | Lang_4 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261014_083544) |
  | Lang_5 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_11 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_12 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Lang_13 | plausible at attempt 4, Correct | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Lang_14 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_16 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | override (identical patch) |
  | Lang_17 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261017_013332; kind from full, session 20261011_005033) |
  | Lang_19 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_21 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from binary_only, session 20261120_091831) |
  | Lang_22 | not plausible | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Lang_23 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Lang_24 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_26 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_27 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_28 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_31 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Lang_32 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_33 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_37 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Lang_39 | plausible at attempt 2, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Lang_40 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_41 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Lang_42 | plausible at attempt 3, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Lang_43 | plausible at attempt 4, Correct | plausible at attempt 4 | Correct (equivalent) | labelled after the re-execution |
  | Lang_44 | not plausible | plausible at attempt 3 | Correct (alternative) | labelled after the re-execution |
  | Lang_45 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Lang_46 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Lang_47 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_49 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_50 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (alternative) | identical labelled patch (binary_only, session 20261017_013332; kind from control pass sample_t045a) |
  | Lang_51 | plausible at attempt 4, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_52 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Lang_55 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_57 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (control pass sample_t045b) |
  | Lang_58 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Lang_59 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_60 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_61 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Lang_62 | not plausible | plausible at attempt 3 | Correct (equivalent) | labelled after the re-execution |
  | Lang_64 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_2 | plausible at attempt 4, Overfitting | plausible at attempt 3 | Overfitting | labelled after the re-execution |
  | Math_3 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (binary_only, session 20261120_091831) |
  | Math_4 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_5 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_8 | plausible at attempt 4, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Math_9 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (control pass sample_t045b) |
  | Math_10 | plausible at attempt 1, Correct | plausible at attempt 3 | Correct (identical) | labelled after the re-execution |
  | Math_11 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from binary_only, session 20261120_091831) |
  | Math_12 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (equivalent) | identical labelled patch (full, session 20261011_005033) |
  | Math_13 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_14 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_19 | plausible at attempt 4, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_20 | not plausible | plausible at attempt 1 | Overfitting | identical labelled patch (labelled on a record not in the data; --text-labels) |
  | Math_22 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_23 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_24 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261014_083544) |
  | Math_26 | not plausible | plausible at attempt 3 | Correct (alternative) | labelled after the re-execution |
  | Math_27 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_28 | plausible at attempt 3, Correct | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Math_29 | not plausible | plausible at attempt 3 | Correct (equivalent) | labelled after the re-execution |
  | Math_30 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_33 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_34 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_35 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_37 | not plausible | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Math_41 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_43 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_45 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_46 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_48 | plausible at attempt 4, Correct | plausible at attempt 2 | Correct (identical) | identical labelled patch (binary_only, session 20261017_013332; kind from full, session 20261011_005033) |
  | Math_50 | not plausible | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_53 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_56 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Math_57 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_59 | plausible at attempt 4, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Math_60 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_61 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_63 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_69 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261120_091831) |
  | Math_70 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_71 | not plausible | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Math_72 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_75 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_77 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_78 | plausible at attempt 1, Overfitting | plausible at attempt 4 | Overfitting | labelled after the re-execution |
  | Math_79 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_82 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | identical labelled patch (no_judge, session 20261014_083544) |
  | Math_84 | plausible at attempt 2, Correct | plausible at attempt 4 | Correct (alternative) | labelled after the re-execution |
  | Math_85 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_86 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (alternative) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t085) |
  | Math_87 | plausible at attempt 1, Correct | plausible at attempt 3 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_88 | not plausible | plausible at attempt 3 | Correct (equivalent) | labelled after the re-execution |
  | Math_89 | not plausible | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Math_90 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | override (identical patch) |
  | Math_91 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_92 | plausible at attempt 3, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Math_94 | plausible at attempt 1, Overfitting | plausible at attempt 1 | Overfitting | override (identical patch) |
  | Math_95 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Math_97 | not plausible | plausible at attempt 4 | Correct (alternative) | labelled after the re-execution |
  | Math_98 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_100 | plausible at attempt 4, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Math_101 | plausible at attempt 3, Correct | plausible at attempt 2 | Correct (equivalent) | identical labelled patch (binary_only, session 20261018_045332; kind from control pass sample_t010) |
  | Math_102 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Math_103 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Math_105 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (control pass sample_t045b) |
  | Math_106 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (full, session 20261011_005033) |
  | Mockito_1 | none in the data | plausible at attempt 1 | Correct (alternative) | identical labelled patch (full, session 20261123_064025) |
  | Mockito_2 | none in the data | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (full, session 20261123_064025) |
  | Mockito_3 | none in the data | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Mockito_5 | none in the data | plausible at attempt 1 | Correct (identical) | identical labelled patch (full, session 20261123_064025) |
  | Mockito_9 | none in the data | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Mockito_11 | none in the data | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Mockito_12 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Mockito_13 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_15 | plausible at attempt 3, Correct | plausible at attempt 4 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_17 | not plausible | plausible at attempt 2 | Overfitting | labelled after the re-execution |
  | Mockito_18 | none in the data | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (full, session 20261123_100046) |
  | Mockito_22 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_24 | plausible at attempt 3, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_26 | plausible at attempt 1, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_27 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261121_115528) |
  | Mockito_28 | plausible at attempt 2, Correct | not plausible | N/A (not plausible) | n/a |
  | Mockito_29 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261011_005033) |
  | Mockito_31 | not plausible | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (control pass sample_t045a) |
  | Mockito_32 | plausible at attempt 4, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_33 | plausible at attempt 4, Overfitting | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_34 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_36 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_37 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (equivalent) | labelled after the re-execution |
  | Mockito_38 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (binary_only, session 20261018_045332; kind from full, session 20261012_084950) |
  | Time_3 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from control pass sample_t010) |
  | Time_4 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | labelled after the re-execution |
  | Time_5 | plausible at attempt 2, Correct | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Time_7 | not plausible | plausible at attempt 1 | Overfitting | identical labelled patch (labelled on a record not in the data; --text-labels) |
  | Time_9 | plausible at attempt 1, Overfitting | not plausible | N/A (not plausible) | n/a |
  | Time_12 | not plausible | plausible at attempt 1 | Correct (alternative) | labelled after the re-execution |
  | Time_13 | not plausible | plausible at attempt 1 | Overfitting | identical labelled patch (binary_only, session 20261018_045332) |
  | Time_14 | not plausible | plausible at attempt 2 | Correct (alternative) | labelled after the re-execution |
  | Time_15 | plausible at attempt 1, Correct | plausible at attempt 2 | Correct (identical) | identical labelled patch (no_judge, session 20261014_083544; kind from full, session 20261012_084950) |
  | Time_16 | not plausible | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (full, session 20261012_084950) |
  | Time_17 | not plausible | plausible at attempt 4 | Correct (equivalent) | labelled after the re-execution |
  | Time_18 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (alternative) | identical labelled patch (control pass sample_t010) |
  | Time_20 | plausible at attempt 2, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261018_045332; kind from control pass sample_t010) |
  | Time_23 | plausible at attempt 1, Correct | plausible at attempt 1 | Correct (equivalent) | identical labelled patch (binary_only, session 20261018_045332; kind from full, session 20261012_084950) |
  | Time_25 | not plausible | plausible at attempt 1 | Correct (identical) | labelled after the re-execution |

  correct -> correct: 132; correct -> not correct: 2; correct -> not plausible: 21; none in the data -> correct: 6; none in the data -> not correct: 1; none in the data -> not plausible: 8; not correct -> correct: 5; not correct -> not correct: 15; not correct -> not plausible: 6; not plausible -> correct: 24; not plausible -> not correct: 7; not plausible -> not plausible: 161

labelled texts with conflicting labels: none

re-executed records that still need a label or the kind of a correct patch: 0 (none); see `figures_out/rerun_labels_todo.csv`

patch texts labelled on records that are not in the data (--text-labels): 3; records that take such a label: 4 (binary_only Chart_23, binary_only Math_20, no_judge Math_20, no_judge Time_7)

## 2c. Repair attempts that received no model output

An attempt received no model output when every generation came back without output tokens (requests refused by the model API or not reaching it), so the unchanged file was tested and the attempt spent. These executions are kept as recorded.

| configuration | bug | session | attempts without output, before / after the first plausible candidate | canonical |
|---|---|---|---|---|
| full | Mockito_6 | 20261123_064025 | [2] / - | yes |
| binary_only | Lang_20 | 20261120_091831 | [2, 3, 4] / - | yes |
| binary_only | Lang_30 | 20261120_091831 | [2, 3, 4] / - | yes |
| binary_only | Lang_31 | 20261120_091831 | - / [2, 3, 4] | yes |
| binary_only | Lang_39 | 20261120_091831 | [2, 3, 4] / - | yes |
| no_judge | Lang_20 | 20261121_173559 | [2, 3, 4] / - | yes |
| no_judge | Lang_30 | 20261121_173559 | [2, 3, 4] / - | yes |
| no_judge | Lang_39 | 20261121_173559 | [2, 3, 4] / - | yes |
| sample_t045a | Closure_4 | 20261106_001716 | [1] / - | yes |

executions with an attempt that received no model output: 9

Sensitivity: the paired comparisons on the 383 evaluable bugs without the bugs whose canonical execution in some configuration has such an attempt (Lang_20, Lang_30, Lang_31, Lang_39, Mockito_6):

- full vs binary_only: correct 35 vs 14 (p = 0.0038); plausible 38 vs 19 (p = 0.0163)
- full vs no_judge: correct 35 vs 29 (p = 0.5323); plausible 38 vs 29 (p = 0.3284)

## 3. Headline, paired set

plausible = a test-passing candidate was found; accepted = the loop ended with an accepted patch; correct = the first plausible candidate is labelled correct; delivered correct = the accepted patch is labelled correct.

| arm | plausible | accepted | correct | delivered correct | pending | precision (correct/plausible) | overfitting |
|---|---|---|---|---|---|---|---|
| full | 202 | 202 | 173 | 173 | 0 | 85.6% | 29 |
| binary_only | 182 | 180 | 151 | 151 | 0 | 83.0% | 31 |
| no_judge | 192 | 192 | 167 | 167 | 0 | 87.0% | 25 |

- `full`: Judge withheld the first plausible candidate and the loop delivered a different patch: Math_63, Mockito_5; plausible candidate found but no patch accepted: none
- `binary_only`: Judge withheld the first plausible candidate and the loop delivered a different patch: Closure_126, Lang_14, Lang_63, Time_20; plausible candidate found but no patch accepted: Closure_107, Lang_31

full arm label split: {'Correct (alternative)': 38, 'Correct (equivalent)': 65, 'Correct (identical)': 70, 'Overfitting': 29}

## 3b. Identical patch texts across configurations (same Java token sequence; complete multi-file patches)

- plausible records: 576; distinct patch texts: 375; texts recurring in two or more configurations: 129 (330 records); texts produced by all three: 72
- recurring texts whose final labels differ between configurations: none

## 4. Statistical comparison (paired on bug identity)

McNemar exact test against `full`; p two-sided, p1 one-sided (full > arm), Holm over the two correct-fix comparisons:

| arm | correct: full-only | arm-only | discordant | p | p1 | Holm p | plausible: full-only | arm-only | discordant | p | delivered correct: full-only | arm-only | p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| binary_only | 36 | 14 | 50 | 0.0026 | 0.0013 | 0.0052 | 39 | 19 | 58 | 0.0119 | 36 | 14 | 0.0026 |
| no_judge | 36 | 30 | 66 | 0.5386 | 0.2693 | 0.5386 | 39 | 29 | 68 | 0.2750 | 36 | 30 | 0.5386 |

Pairwise among ablations (correct):

- binary_only vs no_judge: binary_only-only=20, no_judge-only=36, p=0.0440

Cochran's Q across the three arms (correct): Q=9.02, df=2, p=0.0110

Power of the exact McNemar test (two-sided, alpha 0.05), conditional on the 66 discordant pairs of full vs no_judge: 0.65 for a true difference of 20 correct fixes, 0.09 for a difference of 6, the one observed

Bugs fixed by k of 3 arms: k=0: 178, k=1: 53, k=2: 33, k=3: 124 → outcome depends on the arm for 86 bugs

## 4b. First attempts are three replications of the same procedure

The first-attempt prompt is identical in every arm (feedback exists only after a failure), so iteration-1 outcomes replicate one stochastic procedure three times.

| arm | iter-1 plausible | iter-1 correct | gained at iterations 2-4: plausible | correct | bugs without a first-attempt plausible | later plausible among them |
|---|---|---|---|---|---|---|
| full | 148 | 130 | 54 | 43 | 240 | 54 (22.5%) |
| binary_only | 142 | 120 | 40 | 31 | 246 | 40 (16.3%) |
| no_judge | 132 | 119 | 60 | 48 | 256 | 60 (23.4%) |

Pairwise discordance at iteration 1 (bugs correct in exactly one of the two arms):

- full vs binary_only: correct 27/17 (11.3% of bugs), plausible 28/22 (12.9%)
- full vs no_judge: correct 29/18 (12.1% of bugs), plausible 35/19 (13.9%)
- binary_only vs no_judge: correct 20/19 (10.1% of bugs), plausible 29/19 (12.4%)

Three first attempts combined (proxy for best-of-3 resampling at the first-attempt temperature): union plausible=179, union correct=158; first-plausible-wins plausible=179, correct=154

| arm (full loop) | vs first-plausible-wins proxy: plausible full-only/proxy-only, p | correct, p | vs union correct, p |
|---|---|---|---|
| full | 42/19, p=0.0044 | 34/15, p=0.0094 | 34/19, p=0.0534 |
| binary_only | 25/22, p=0.7709 | 18/21, p=0.7493 | 18/25, p=0.3604 |
| no_judge | 39/26, p=0.1360 | 36/23, p=0.1175 | 32/23, p=0.2806 |

Attempts 2 to 4, on the bugs whose first attempt is plausible in neither of the two configurations compared (both loops start their feedback from a failed first attempt):

| pair | bugs | plausible later: first / second | only first / only second, p | correct later: first / second | only first / only second, p |
|---|---|---|---|---|---|
| full vs binary_only | 218 | 45 / 27 | 24/6, p=0.0014 | 35 / 19 | 19/3, p=0.0009 |
| full vs no_judge | 221 | 48 / 44 | 20/16, p=0.6177 | 39 / 34 | 19/14, p=0.4869 |
| binary_only vs no_judge | 227 | 31 / 48 | 10/27, p=0.0076 | 23 / 38 | 8/23, p=0.0107 |

## 4c. Equal-budget control: independent single attempts (best-of-k resampling)

- `sample_t010`: verification file `data/verification_sample_t010.csv`; textually identical to an independently labelled arm patch for 99 bugs, label agreement 98/99; disagreements: Math_94 (Correct (alternative) vs arm Overfitting); plausible patches with a recorded execution-based re-verification: 33
- `sample_t045a`: verification file `data/verification_sample_t045a.csv`; textually identical to an independently labelled arm patch for 101 bugs, label agreement 99/101; disagreements: Closure_9 (Correct (equivalent) vs arm Overfitting), Math_94 (Correct (alternative) vs arm Overfitting); plausible patches with a recorded execution-based re-verification: 33
- `sample_t045b`: verification file `data/verification_sample_t045b.csv`; textually identical to an independently labelled arm patch for 97 bugs, label agreement 96/97; disagreements: Closure_9 (Correct (equivalent) vs arm Overfitting); plausible patches with a recorded execution-based re-verification: 33
- `sample_t085`: verification file `data/verification_sample_t085.csv`; textually identical to an independently labelled arm patch for 91 bugs, label agreement 89/91; disagreements: Closure_9 (Correct (equivalent) vs arm Overfitting), Math_90 (Correct (equivalent) vs arm Overfitting); plausible patches with a recorded execution-based re-verification: 27
  (arm patches whose only label was taken from an identical control patch, left out of this check: Chart_6, Chart_21, Closure_5, Closure_7, Closure_62, Lang_57, Math_9, Math_25, Math_32, Math_85, Math_87, Math_105, Mockito_31, Time_18)

| sample | temperature | evaluable bugs run | plausible | correct | pending labels | label sources |
|---|---|---|---|---|---|---|
| sample_t010 | 0.1 | 388 | 140 | 121 | 0 | {'verification': 133, 'override': 2, 'identical patch in an arm': 5} |
| sample_t045a | 0.45 | 388 | 145 | 125 | 0 | {'verification': 138, 'override': 3, 'identical patch in an arm': 4} |
| sample_t045b | 0.45 | 388 | 144 | 123 | 0 | {'verification': 137, 'override': 2, 'identical patch in an arm': 5} |
| sample_t085 | 0.85 | 388 | 140 | 125 | 0 | {'verification': 133, 'override': 3, 'identical patch in an arm': 4} |

Best-of-k in temperature order (first plausible sample wins):

| k | samples | plausible | correct | pending | vs full: plausible full-only/ctrl-only, p | correct, p | vs no_judge: plausible, p | correct, p |
|---|---|---|---|---|---|---|---|---|
| 1 | sample_t010 | 140 | 121 | 0 | 74/12, p=0.0000 | 63/11, p=0.0000 | 67/15, p=0.0000 | 58/12, p=0.0000 |
| 2 | sample_t010, sample_t045a | 165 | 141 | 0 | 55/18, p=0.0000 | 50/18, p=0.0001 | 50/23, p=0.0021 | 44/18, p=0.0013 |
| 3 | sample_t010, sample_t045a, sample_t045b | 173 | 148 | 0 | 52/23, p=0.0011 | 47/22, p=0.0035 | 47/28, p=0.0370 | 41/22, p=0.0226 |
| 4 | sample_t010, sample_t045a, sample_t045b, sample_t085 | 186 | 159 | 0 | 45/29, p=0.0805 | 40/26, p=0.1089 | 39/33, p=0.5560 | 34/26, p=0.3663 |

Best-of-4 control vs every configuration (McNemar exact, two-sided):

| configuration | plausible: conf-only/ctrl-only, p | correct: conf-only/ctrl-only, p |
|---|---|---|
| full | 45/29, p=0.0805 | 40/26, p=0.1089 |
| binary_only | 31/35, p=0.7122 | 23/31, p=0.3409 |
| no_judge | 39/33, p=0.5560 | 34/26, p=0.3663 |

control cost over the 4 samples: 1552 tested candidates, 2028 repair calls, 22,235,176 tokens, $7.78 ($0.0201 per bug, $0.0489 per correct fix), 20.0 h, 185 s per bug
  per sample: sample_t010: 521 calls, 5.81M tokens, 4.60 h; sample_t045a: 520 calls, 5.59M tokens, 5.34 h; sample_t045b: 502 calls, 5.61M tokens, 5.09 h; sample_t085: 485 calls, 5.22M tokens, 4.95 h
control stopping each bug at its first plausible sample: 1074 tested candidates, 1476 repair calls, 16,260,898 tokens, $5.69 ($0.0147 per bug, $0.0358 per correct fix), 14.0 h, 130 s per bug
control precision: 85.5%
first-plausible-wins correct over all 24 sample orderings: min 155, max 159, mean 156.9; union (a correct patch in at least one sample): 164

## 4d. Candidates with the same text: are the recorded test outcomes the same?

Every tested candidate of every completed execution (all sessions of the three configurations and the control passes, the sessions made before the correction of binary_only and no_judge included), compared by its complete text (Java token sequence).

- tested candidates in valid executions: 6752; distinct texts: 3886; texts tested more than once: 973 (3839 candidates)
- texts recorded both as passing and as failing: 4, of which 4 within valid executions (Mockito_5, Mockito_22, Mockito_24, Mockito_26)

| bug | where it passed | where it failed |
|---|---|---|
| Mockito_5 | sample_t085 attempt 1 | sample_t045a attempt 1 |
| Mockito_22 | full (005033) attempt 1; binary_only (115528) attempt 1; no_judge, before the correction (083544) attempt 1; sample_t010 attempt 1; sample_t045a attempt 1; sample_t045b attempt 1; sample_t085 attempt 1 | no_judge (173559) attempt 1; binary_only, before the correction (045332) attempt 1 |
| Mockito_24 | full (005033) attempt 2; binary_only (115528) attempt 2 | binary_only, before the correction (045332) attempt 2; binary_only, before the correction (045332) attempt 3; binary_only, before the correction (045332) attempt 4 |
| Mockito_26 | full (005033) attempt 1; no_judge, before the correction (083544) attempt 1 | binary_only (115528) attempt 1; binary_only (115528) attempt 2; binary_only (115528) attempt 3; no_judge (173559) attempt 1; no_judge (173559) attempt 2; no_judge (173559) attempt 4; binary_only, before the correction (045332) attempt 1; binary_only, before the correction (045332) attempt 3; binary_only, before the correction (045332) attempt 4; sample_t010 attempt 1; sample_t045a attempt 1; sample_t045b attempt 1; sample_t085 attempt 1 |


## 4e. The re-execution against the other executions of the same bugs

`full`: 50 bugs whose canonical record is a re-execution (session 20261110_104737).

- re-execution: valid executions 50, plausible 17, tested candidates 156

First candidate with the same text (same Java token sequence), on these bugs:

- re-execution against each other execution: binary_only 22/50; no_judge 18/50; sample_t010 19/50 (range 18 to 22)
- between two of the other executions: range 16 to 23 of 50 to 50 bugs (binary_only vs no_judge 23/50; binary_only vs sample_t010 21/50; no_judge vs sample_t010 16/50)
- first candidates that pass: re-execution 12; binary_only 15; no_judge 16; sample_t010 15 (others: 15 to 16)

Recorded size of the first Repair Agent prompt (single-file bugs whose first generation was usable in both executions), re-execution against each other execution, equal/compared; and of the first Judge prompt where the first candidate has the same text and passes:

- binary_only 32/32, Judge 6/6; no_judge 31/31; sample_t010 22/22; sample_t045a 30/30; sample_t045b 30/30; sample_t085 30/30
- bugs compared per execution: 22 to 32; first Repair Agent prompt of equal size in every comparison: yes; first Judge prompt of equal size: 6/6

## 4f. Configurations executed again in full with corrected code

`binary_only`, corrected code in session(s) 20261120_091831, 20261121_115528, 20261123_171006. Bugs with a valid execution under both the earlier and the corrected code: 373; only under the corrected code: 15 (Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8, Mockito_9, Mockito_10, Mockito_11, Mockito_18, Mockito_19, Mockito_20, Mockito_21); only under the earlier code: 0 (none)

| on the bugs valid under both | earlier code | corrected code | both | only earlier | only corrected |
|---|---|---|---|---|---|
| plausible | 189 | 175 | 153 | 36 | 22 |
| correct (first plausible candidate) | 159 | 145 | 123 | 36 | 22 |

- plausible only under the earlier code: Chart_10, Chart_25, Closure_3, Closure_10, Closure_20, Closure_64, Closure_80, Closure_88, Closure_111, Closure_113, Closure_120, Closure_128, Closure_131, Lang_13, Lang_32, Lang_44, Lang_56, Math_12, Math_26, Math_42, Math_49, Math_83, Math_84, Math_86, Math_90, Math_96, Math_100, Mockito_13, Mockito_15, Mockito_17, Mockito_32, Time_1, Time_10, Time_12, Time_17, Time_19
- plausible only under the corrected code: Chart_6, Chart_16, Closure_1, Closure_65, Closure_96, Closure_107, Closure_109, Closure_118, Lang_5, Lang_8, Lang_51, Lang_63, Math_20, Math_31, Math_32, Math_59, Math_78, Math_97, Mockito_22, Mockito_24, Mockito_30, Time_11

`full` against `binary_only` on these 373 bugs (full: 194 plausible, 166 correct), full-only/other-only: correct, earlier code 34/27 (p=0.4426), corrected code 35/14 (p=0.0038); plausible, earlier code 34/29 (p=0.6147), corrected code 38/19 (p=0.0163)

corrected against earlier code of `binary_only`, corrected-only/earlier-only: correct 22/36 (p=0.0869); plausible 22/36 (p=0.0869)

First attempt, whose prompt the correction does not touch: first candidate with the same text 137/373; first candidate passes under the earlier code 134, under the corrected code 137, under both 113; first Repair Agent prompt of equal recorded size 258/259 (single-file bugs whose first generation was usable in both); differs: Math_105

Second attempt after the same failed first candidate (single-file, first generation usable): 39 bugs; recorded prompt size, corrected minus earlier: median +129 tokens, larger in 29, equal in 0, smaller in 10

| on the bugs valid under both | earlier code | corrected code |
|---|---|---|
| attempts | 1004 | 1028 |
| attempts after a failed one | 631 | 655 |
| stagnation aborts | 5 | 8 |
| Repair Agent calls | 1292 | 1431 |
| tokens (M) | 44.4 | 43.8 |
| estimated cost (USD) | 15.54 | 15.34 |
| attempts after a failed one at temperature 0.10 | 214 | 222 |
| attempts after a failed one at temperature 0.25 | 49 | 42 |
| attempts after a failed one at temperature 0.45 | 247 | 258 |
| attempts after a failed one at temperature 0.55 | 7 | 10 |
| attempts after a failed one at temperature 0.75 | 19 | 16 |
| attempts after a failed one at temperature 0.80 | 0 | 1 |
| attempts after a failed one at temperature 0.85 | 95 | 106 |

`no_judge`, corrected code in session(s) 20261121_173559, 20261123_173421. Bugs with a valid execution under both the earlier and the corrected code: 373; only under the corrected code: 15 (Mockito_1, Mockito_2, Mockito_3, Mockito_4, Mockito_5, Mockito_6, Mockito_7, Mockito_8, Mockito_9, Mockito_10, Mockito_11, Mockito_18, Mockito_19, Mockito_20, Mockito_21); only under the earlier code: 0 (none)

| on the bugs valid under both | earlier code | corrected code | both | only earlier | only corrected |
|---|---|---|---|---|---|
| plausible | 181 | 185 | 154 | 27 | 31 |
| correct (first plausible candidate) | 155 | 161 | 132 | 23 | 29 |

- plausible only under the earlier code: Chart_10, Closure_12, Closure_77, Closure_91, Closure_95, Closure_111, Lang_5, Lang_19, Lang_26, Lang_32, Lang_39, Lang_51, Lang_52, Math_8, Math_22, Math_30, Math_63, Math_72, Math_92, Math_100, Math_102, Mockito_13, Mockito_22, Mockito_24, Mockito_26, Mockito_28, Time_9
- plausible only under the corrected code: Chart_13, Closure_16, Closure_17, Closure_25, Closure_33, Closure_51, Closure_64, Closure_103, Closure_126, Closure_133, Lang_22, Lang_44, Lang_62, Math_20, Math_26, Math_29, Math_37, Math_50, Math_71, Math_88, Math_89, Math_97, Mockito_17, Mockito_31, Time_7, Time_12, Time_13, Time_14, Time_16, Time_17, Time_25

`full` against `no_judge` on these 373 bugs (full: 194 plausible, 166 correct), full-only/other-only: correct, earlier code 32/21 (p=0.1690), corrected code 34/29 (p=0.6147); plausible, earlier code 35/22 (p=0.1112), corrected code 37/28 (p=0.3211)

corrected against earlier code of `no_judge`, corrected-only/earlier-only: correct 29/23 (p=0.4885); plausible 31/27 (p=0.6940)

First attempt, whose prompt the correction does not touch: first candidate with the same text 135/373; first candidate passes under the earlier code 134, under the corrected code 127, under both 107; first Repair Agent prompt of equal recorded size 255/255 (single-file bugs whose first generation was usable in both)

Second attempt after the same failed first candidate (single-file, first generation usable): 41 bugs; recorded prompt size, corrected minus earlier: median -1998 tokens, larger in 1, equal in 2, smaller in 38

| on the bugs valid under both | earlier code | corrected code |
|---|---|---|
| attempts | 1040 | 1011 |
| attempts after a failed one | 667 | 638 |
| stagnation aborts | 0 | 8 |
| Repair Agent calls | 1324 | 1386 |
| tokens (M) | 24.9 | 22.6 |
| estimated cost (USD) | 8.72 | 7.93 |
| attempts after a failed one at temperature 0.10 | 125 | 212 |
| attempts after a failed one at temperature 0.25 | 39 | 44 |
| attempts after a failed one at temperature 0.30 | 80 | 0 |
| attempts after a failed one at temperature 0.45 | 219 | 245 |
| attempts after a failed one at temperature 0.55 | 26 | 17 |
| attempts after a failed one at temperature 0.70 | 6 | 0 |
| attempts after a failed one at temperature 0.75 | 57 | 18 |
| attempts after a failed one at temperature 0.80 | 0 | 1 |
| attempts after a failed one at temperature 0.85 | 115 | 101 |

First candidate with the same text, between complete executions, on the 373 bugs valid before and after the correction (the first attempt has the same prompt in every configuration; executions of configurations with re-executed or set-aside sessions are left out):

- binary_only, earlier code vs binary_only, corrected code: 137/373 (36.7%)
- binary_only, earlier code vs no_judge, earlier code: 152/373 (40.8%)
- binary_only, earlier code vs no_judge, corrected code: 129/373 (34.6%)
- binary_only, corrected code vs no_judge, earlier code: 144/373 (38.6%)
- binary_only, corrected code vs no_judge, corrected code: 141/373 (37.8%)
- no_judge, earlier code vs no_judge, corrected code: 135/373 (36.2%)

## 5. Per project (plausible / correct)

| project | n | full | binary_only | no_judge |
|---|---|---|---|---|
| Chart | 26 | 19 / 18 | 18 / 18 | 18 / 18 |
| Closure | 131 | 46 / 39 | 45 / 35 | 49 / 38 |
| Lang | 61 | 37 / 32 | 36 / 29 | 34 / 32 |
| Math | 106 | 63 / 52 | 54 / 45 | 58 / 50 |
| Mockito | 38 | 24 / 21 | 18 / 17 | 19 / 17 |
| Time | 26 | 13 / 11 | 11 / 7 | 14 / 12 |

## 6. Iteration at which the first plausible candidate was produced

| arm | plausible by attempt 1/2/3/4 | correct by attempt 1/2/3/4 |
|---|---|---|
| full | 148 / 29 / 14 / 11 | 130 / 22 / 13 / 8 |
| binary_only | 142 / 26 / 7 / 7 | 120 / 20 / 5 / 6 |
| no_judge | 132 / 41 / 11 / 8 | 119 / 31 / 10 / 7 |

full arm:

| attempt | plausible | share | cumulative | correct | precision |
|---|---|---|---|---|---|
| 1 | 148 | 73.3% | 73.3% | 130 | 87.8% |
| 2 | 29 | 14.4% | 87.6% | 22 | 75.9% |
| 3 | 14 | 6.9% | 94.6% | 13 | 92.9% |
| 4 | 11 | 5.4% | 100.0% | 8 | 72.7% |

full arm, found after the first attempt: plausible 54 (26.7%), correct 43 (24.9%)
full arm, share of each project's plausible patches found at the first attempt: Chart 14/19 = 73.7%, Closure 32/46 = 69.6%, Lang 27/37 = 73.0%, Math 51/63 = 81.0%, Mockito 13/24 = 54.2%, Time 11/13 = 84.6%
mean iterations, full arm, all evaluable bugs: 2.67
full arm, bugs without a plausible patch: 186; iterations used: {2: 1, 3: 3, 4: 182}; stagnation aborts: Closure_30 (after 3 iterations, plausible=False), Closure_37 (after 3 iterations, plausible=False), Closure_72 (after 2 iterations, plausible=False), Closure_103 (after 3 iterations, plausible=False), Closure_110 (after 4 iterations, plausible=False), Math_22 (after 4 iterations, plausible=False)
full arm, multi-file bugs: 31, plausible 7, correct 7 (22.6%); single-file bugs: 357, correct 166 (46.5%)
full arm, correct per project as a share of evaluable bugs: Chart 18/26 = 69.2%, Closure 39/131 = 29.8%, Lang 32/61 = 52.5%, Math 52/106 = 49.1%, Mockito 21/38 = 55.3%, Time 11/26 = 42.3%
full arm, overfitting per project: Chart 1, Closure 7, Lang 5, Math 11, Mockito 3, Time 2

## 6b. Adaptive-mechanism activity (repair attempts made after a failed attempt)

Multi-file bugs take no part in the mechanisms (their attempts run at the base temperature); they are counted in the attempts.

| arm | attempts after a failure | of which multi-file | temperature > 0.1 | at 0.45 | at 0.85 (surgical mode) | other levels | bugs reaching surgical mode | at exactly 0.30 |
|---|---|---|---|---|---|---|---|---|
| full | 648 | 71 | 430 (66%) | 268 | 106 | 56 | 106 | 0 |
| binary_only | 683 | 69 | 450 (66%) | 266 | 110 | 74 | 110 | 0 |
| no_judge | 664 | 58 | 444 (67%) | 253 | 106 | 85 | 106 | 0 |

(0.45 is the no-op rule plus the near-identical-and-failed rule firing together; 0.85 is surgical mode, reachable only at the fourth attempt; 0.30 is the repeated-rationale rule firing alone; in the no_judge sessions executed before the correction it fired on the constant placeholder rationale, see section 4f)

Temperature of single-file attempts, by attempt number:

- `full`: attempt 1: 0.1: 357; attempt 2: 0.1: 57, 0.25: 21, 0.45: 138; attempt 3: 0.1: 48, 0.25: 10, 0.45: 117, 0.55: 3, 0.75: 9; attempt 4: 0.1: 42, 0.25: 3, 0.45: 13, 0.55: 9, 0.75: 1, 0.85: 106
- `binary_only`: attempt 1: 0.1: 357; attempt 2: 0.1: 56, 0.25: 27, 0.45: 143; attempt 3: 0.1: 52, 0.25: 10, 0.45: 113, 0.55: 7, 0.75: 15; attempt 4: 0.1: 56, 0.25: 6, 0.45: 10, 0.55: 5, 0.75: 3, 0.8: 1, 0.85: 110
- `no_judge`: attempt 1: 0.1: 357; attempt 2: 0.1: 64, 0.25: 24, 0.45: 143; attempt 3: 0.1: 55, 0.25: 14, 0.45: 97, 0.55: 8, 0.75: 19; attempt 4: 0.1: 43, 0.25: 8, 0.45: 13, 0.55: 10, 0.75: 1, 0.8: 1, 0.85: 106

## 6c. Candidates, Repair Agent calls and regenerations (all attempts)

| arm | tested candidates | of which multi-file | file generations | repair calls | regeneration calls | single-file attempts left without a usable edit | multi-file attempts with a file left unchanged |
|---|---|---|---|---|---|---|---|
| full | 1036 | 102 | 1174 | 1425 | 251 (17.6%) | 25 of 934 ({'SEARCH text matches N times (ambiguous)': 4, 'SEARCH text not found in source': 7, 'model returned the original file unchanged': 6, 'no SEARCH/REPLACE block found in response': 8}) | 25 |
| binary_only | 1071 | 100 | 1207 | 1503 | 296 (19.7%) | 30 of 971 ({'SEARCH text matches N times (ambiguous)': 2, 'SEARCH text not found in source': 8, 'model returned the original file unchanged': 4, 'no SEARCH/REPLACE block found in response': 16}) | 22 |
| no_judge | 1052 | 89 | 1177 | 1446 | 269 (18.6%) | 21 of 963 ({'SEARCH text matches N times (ambiguous)': 3, 'SEARCH text not found in source': 4, 'model returned the original file unchanged': 2, 'no SEARCH/REPLACE block found in response': 12}) | 9 |
| sample_t010 | 388 | 31 | 428 | 521 | 93 (17.9%) | 5 of 357 ({'SEARCH text not found in source': 2, 'model returned the original file unchanged': 1, 'no SEARCH/REPLACE block found in response': 2}) | 2 |
| sample_t045a | 388 | 31 | 428 | 520 | 92 (17.7%) | 9 of 357 ({'SEARCH text matches N times (ambiguous)': 1, 'SEARCH text not found in source': 3, 'model returned the original file unchanged': 3, 'no SEARCH/REPLACE block found in response': 2}) | 3 |
| sample_t045b | 388 | 31 | 428 | 502 | 74 (14.7%) | 4 of 357 ({'SEARCH text matches N times (ambiguous)': 1, 'SEARCH text not found in source': 2, 'model returned the original file unchanged': 1}) | 3 |
| sample_t085 | 388 | 31 | 428 | 485 | 57 (11.8%) | 6 of 357 ({'SEARCH text matches N times (ambiguous)': 1, 'SEARCH text not found in source': 2, 'model returned the original file unchanged': 1, 'no SEARCH/REPLACE block found in response': 2}) | 4 |

## 6d. Judge reviews lost, and test-passing candidates not accepted

| arm | Judge invocations | parsed reviews | unparseable responses | empty responses | skipped (stagnation abort) |
|---|---|---|---|---|---|
| full | 1030 | 1014 | 9 | 7 | 6 |
| binary_only | 1063 | 1048 | 2 | 13 | 8 |

Test-passing candidates that were not accepted on the spot:

| arm | bug | attempt | Judge outcome | label of that candidate | what followed | label of the accepted patch |
|---|---|---|---|---|---|---|
| full | Math_63 | 1 | verdict incorrect | Overfitting | a different patch accepted later | Overfitting |
| full | Math_79 | 1 | unparseable response | Correct (identical) | the same text accepted later | Correct (identical) |
| full | Mockito_5 | 1 | empty response | Correct (identical) | a different patch accepted later | Correct (equivalent) |
| binary_only | Closure_107 | 2 | verdict incorrect | Overfitting | no patch accepted |  |
| binary_only | Closure_126 | 1 | verdict incorrect | Correct (identical) | a different patch accepted later | Correct (identical) |
| binary_only | Lang_14 | 1 | empty response | Correct (identical) | a different patch accepted later | Correct (equivalent) |
| binary_only | Lang_31 | 1 | empty response | Overfitting | no patch accepted |  |
| binary_only | Lang_60 | 1 | unparseable response | Correct (equivalent) | the same text accepted later | Correct (equivalent) |
| binary_only | Lang_63 | 1 | verdict incorrect | Overfitting | a different patch accepted later | Overfitting |
| binary_only | Time_20 | 1 | verdict needs_revision | Correct (equivalent) | a different patch accepted later | Correct (equivalent) |

genuine vetoes (a parsed verdict other than correct on a passing candidate): 5 (2 labelled correct, 3 overfitting; 4 followed by an accepted patch, 1 not); reviews lost on a passing candidate: 5

## 7. Cost and time (canonical executions, evaluable set)

| arm | tested candidates | repair calls | total tokens | total USD | mean USD/bug | median USD/bug | max USD/bug | USD per correct fix | mean s/bug | hours | mean s (accepted) | mean s (not plausible) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 1036 | 1425 | 46,395,468 | $16.24 | $0.0419 | $0.0222 | $0.4553 | $0.0939 | 240 | 25.9 | 131 | 359 |
| binary_only | 1071 | 1503 | 44,675,418 | $15.64 | $0.0403 | $0.0239 | $0.2878 | $0.1036 | 200 | 21.6 | 75 | 280 |
| no_judge | 1052 | 1446 | 23,071,977 | $8.08 | $0.0208 | $0.0123 | $0.1884 | $0.0484 | 206 | 22.2 | 93 | 317 |

three configurations together: $39.95, 69.6 machine-hours
full arm, plausible patches found at the first attempt: n=148, median tokens 18,948, median seconds 32.8, median USD 0.0066
full arm, plausible patches found after iteration: n=54, median tokens 53,086, median seconds 101.1, median USD 0.0186

## 7b. Token split per arm (canonical executions, evaluable set)

| arm | repair calls | repair prompt tokens | repair output tokens | judge calls | judge prompt tokens | judge output tokens | judge share of all tokens |
|---|---|---|---|---|---|---|---|
| full | 1036 | 25,085,077 | 746,480 | 1014 | 20,326,954 | 236,957 | 44.3% |
| binary_only | 1071 | 24,016,988 | 664,772 | 1048 | 19,746,880 | 246,778 | 44.8% |
| no_judge | 1052 | 22,349,863 | 722,114 | 0 | 0 | 0 | 0.0% |

## 8. Baseline failing-test counts (full arm)

1 tests: 246 bugs, 2 tests: 70 bugs, 3 tests: 23 bugs, 4 tests: 11 bugs, 5 tests: 7 bugs, 6 tests: 4 bugs, 7 tests: 7 bugs, 8 tests: 8 bugs, 9 tests: 2 bugs, 10+ tests: 10 bugs

## 8b. Pre-existing failures beyond the trigger tests (B \ Tg)

| arm | bugs with extra baseline failures | extra failing tests in total | per project (bugs) | bugs |
|---|---|---|---|---|
| full | 2 | 2 | Chart 0, Closure 0, Lang 0, Math 0, Mockito 2, Time 0 | Mockito_25 (+1, plausible=False), Mockito_26 (+1, plausible=True) |
| binary_only | 2 | 2 | Chart 0, Closure 0, Lang 0, Math 0, Mockito 2, Time 0 | Mockito_25 (+1, plausible=False), Mockito_26 (+1, plausible=False) |
| no_judge | 5 | 5 | Chart 0, Closure 0, Lang 0, Math 0, Mockito 5, Time 0 | Mockito_22 (+1, plausible=False), Mockito_23 (+1, plausible=False), Mockito_24 (+1, plausible=False), Mockito_25 (+1, plausible=False), Mockito_26 (+1, plausible=False) |

canonical records whose trigger-test list is empty (repaired without trigger-test information): none
- `sample_t010` (baseline set logged): every trigger test fails at baseline for 388/388 bugs; baseline failures outside the trigger tests: Mockito_19: VerificationWithTimeoutTest::canIgnoreInvocationsWithJunit, Mockito_25: ConcurrentModificationExceptionOnMultiThreadedVerificationTest::testInvocationConcurrently, Mockito_26: ConcurrentModificationExceptionOnMultiThreadedVerificationTest::testInvocationConcurrently
- `sample_t045a` (baseline set logged): every trigger test fails at baseline for 388/388 bugs; baseline failures outside the trigger tests: Mockito_25: ConcurrentModificationExceptionOnMultiThreadedVerificationTest::testInvocationConcurrently, Mockito_26: ConcurrentModificationExceptionOnMultiThreadedVerificationTest::testInvocationConcurrently
- `sample_t045b` (baseline set logged): every trigger test fails at baseline for 388/388 bugs; baseline failures outside the trigger tests: Mockito_26: ConcurrentModificationExceptionOnMultiThreadedVerificationTest::testInvocationConcurrently
- `sample_t085` (baseline set logged): every trigger test fails at baseline for 388/388 bugs; baseline failures outside the trigger tests: Mockito_25: ConcurrentModificationExceptionOnMultiThreadedVerificationTest::testInvocationConcurrently

## 9. Inter-rater agreement on the full arm's plausible patches

Bugs whose blind passes reviewed the patch of another execution, excluded here: 16 (Chart_16, Chart_23, Closure_5, Closure_7, Closure_8, Closure_11, Closure_12, Closure_33, Mockito_1, Mockito_2, Mockito_4, Mockito_5, Mockito_9, Mockito_11, Mockito_18, Mockito_21)

- final label vs Independent review 2 (blind): n=123, agreement=92.7%, κ=0.757 [95% bootstrap CI 0.60, 0.89], disagreements=9: Closure_9 (final Overfitting; pass Correct (alternative)); Lang_16 (final Overfitting; pass Correct (alternative)); Lang_23 (final Overfitting; pass Correct (alternative)); Lang_31 (final Overfitting; pass Correct (alternative)); Math_36 (final Overfitting; pass Correct (alternative)); Math_44 (final Overfitting; pass Correct (alternative)); Math_90 (final Overfitting; pass Correct (alternative)); Math_94 (final Overfitting; pass Correct (alternative)); Time_13 (final Overfitting; pass Correct (alternative))
- final label vs Independent review 3 (blind): n=186, agreement=96.8%, κ=0.857 [95% bootstrap CI 0.73, 0.95], disagreements=6: Closure_9 (final Overfitting; pass Correct (alternative)); Lang_16 (final Overfitting; pass Correct (alternative)); Math_36 (final Overfitting; pass Correct (alternative)); Math_44 (final Overfitting; pass Correct (alternative)); Math_90 (final Overfitting; pass Correct (alternative)); Math_94 (final Overfitting; pass Correct (alternative))

## 9b. Second verification (labels given again, with execution where the project could be rebuilt)

- `full`: 198 patches logged plausible in the file; canonical plausible patches whose text it reviewed: 186 of 202
  - label differs from the first verification file: 3 (Closure_9: Correct (alternative) -> Overfitting, Lang_16: Correct (alternative) -> Overfitting, Math_44: Correct (alternative) -> Overfitting)
  - label differs from the final label: 3 (Math_36: Correct (alternative), final Overfitting, Math_90: Correct (alternative), final Overfitting, Math_94: Correct (alternative), final Overfitting)
  - 'Verified plausible' of the logged-plausible patches: {'Not verifiable': 1, 'Yes': 197}
  - execution of the logged-plausible patches: {'JDK 8 re-run of the relevant tests': 120, 'not re-run (project could not be rebuilt)': 14, 'token-identical to the developer fix, not re-executed': 64}
- `binary_only`: 189 patches logged plausible in the file (the sessions executed before the correction); canonical plausible patches whose text it reviewed: 90 of 182
  - label differs from the first verification file: 1 (Math_49: Overfitting -> Correct)
  - label differs from the final label: 1 (Math_94: Correct, final Overfitting)
  - 'Verified plausible' of the logged-plausible patches: {'No': 1, 'Yes': 170, 'Yes (logs only)': 18}
  - logged as failing, passing when re-executed: Lang_29, Mockito_22, Mockito_24, Mockito_26
- `no_judge`: 181 patches logged plausible in the file (the sessions executed before the correction); canonical plausible patches whose text it reviewed: 96 of 192
  - label differs from the first verification file: 1 (Math_94: Correct -> Overfitting)
  - label differs from the final label: 1 (Math_90: Correct, final Overfitting)
  - 'Verified plausible' of the logged-plausible patches: {'Yes': 181}
  - logged as failing, passing when re-executed: Lang_29

canonical plausible patches of the three configurations whose text the second verification reviewed: 372 of 576

## 10. Offline judge pilot vs human labels (full arm, plausible set)

Scored only on patches whose judged text is the canonical, labelled text; bugs judged on the text of another execution are listed and excluded.

| model | judged on canonical text | vetoed | overfitting caught | correct wrongly vetoed | veto precision | κ vs labels [95% bootstrap CI] | excluded: other execution's text | not judged |
|---|---|---|---|---|---|---|---|---|
| gemini_3_5_flash_lite_semantic | 202 | 9 | 4/29 | 5/173 | 4/9 | 0.153 [-0.004, 0.333] | 0 () | 0 () |
  - vetoed, overfitting: Lang_16, Lang_31, Math_63, Math_90
  - vetoed, correct: Closure_6 [Correct (identical)], Closure_62 [Correct (alternative)], Lang_49 [Correct (identical)], Math_19 [Correct (equivalent)], Mockito_13 [Correct (equivalent)]
| claude_sonnet_5_5_semantic | 194 | 22 | 14/28 | 8/166 | 14/22 | 0.496 [0.301, 0.671] | 0 () | 8 (Mockito_1, Mockito_2, Mockito_4, Mockito_5, Mockito_9, Mockito_11, Mockito_18, Mockito_21) |
  - vetoed, overfitting: Chart_13, Closure_7, Closure_59, Closure_131, Lang_12, Lang_16, Lang_31, Math_8, Math_10, Math_24, Math_29, Math_36, Math_44, Mockito_35
  - vetoed, correct: Closure_62 [Correct (alternative)], Closure_64 [Correct (equivalent)], Math_50 [Correct (alternative)], Math_84 [Correct (alternative)], Math_103 [Correct (equivalent)], Time_4 [Correct (alternative)], Time_16 [Correct (equivalent)], Time_17 [Correct (alternative)]

vetoed by every reviewer: Closure_62, Lang_16, Lang_31; overfitting caught by every reviewer: Lang_16, Lang_31

Each reviewer as a filter on the patches it was scored on (a veto removes the patch):

| model | patches | precision before | overfitting removed | correct removed | patches kept | overfitting among them | precision after |
|---|---|---|---|---|---|---|---|
| gemini_3_5_flash_lite_semantic | 202 | 85.6% | 4/29 | 5/173 | 193 | 25 (13.0%) | 87.0% |
| claude_sonnet_5_5_semantic | 194 | 85.6% | 14/28 | 8/166 | 172 | 14 (8.1%) | 91.9% |

Matched set, the patches scored for every reviewer: 194 patches (28 overfitting, 166 correct)

| model | overfitting caught | correct wrongly vetoed | κ vs labels | precision before | precision after |
|---|---|---|---|---|---|
| gemini_3_5_flash_lite_semantic | 4/28 | 5/166 | 0.157 | 85.6% | 87.0% |
| claude_sonnet_5_5_semantic | 14/28 | 8/166 | 0.496 | 85.6% | 91.9% |

Matched set, the same without the multi-file patches: 187 patches (28 overfitting, 159 correct)

| model | overfitting caught | correct wrongly vetoed | κ vs labels | precision before | precision after |
|---|---|---|---|---|---|
| gemini_3_5_flash_lite_semantic | 4/28 | 5/159 | 0.155 | 85.0% | 86.5% |
| claude_sonnet_5_5_semantic | 14/28 | 8/159 | 0.493 | 85.0% | 91.5% |

Confusion matrix of each reviewer against the labels, on the patches it was scored on (a veto is a positive), with sensitivity, specificity and veto precision and their 95% Wilson intervals:

| model | patches | overfitting vetoed | correct vetoed | overfitting kept | correct kept | sensitivity | specificity | veto precision |
|---|---|---|---|---|---|---|---|---|
| gemini_3_5_flash_lite_semantic | 202 | 4 | 5 | 25 | 168 | 4/29, 13.8% [5.5, 30.6] | 168/173, 97.1% [93.4, 98.8] | 4/9, 44.4% [18.9, 73.3] |
| claude_sonnet_5_5_semantic | 194 | 14 | 8 | 14 | 158 | 14/28, 50.0% [32.6, 67.4] | 158/166, 95.2% [90.8, 97.5] | 14/22, 63.6% [43.0, 80.3] |

Confusion matrix of each reviewer against the labels, on the matched set (a veto is a positive), with sensitivity, specificity and veto precision and their 95% Wilson intervals:

| model | patches | overfitting vetoed | correct vetoed | overfitting kept | correct kept | sensitivity | specificity | veto precision |
|---|---|---|---|---|---|---|---|---|
| gemini_3_5_flash_lite_semantic | 194 | 4 | 5 | 24 | 161 | 4/28, 14.3% [5.7, 31.5] | 161/166, 97.0% [93.1, 98.7] | 4/9, 44.4% [18.9, 73.3] |
| claude_sonnet_5_5_semantic | 194 | 14 | 8 | 14 | 158 | 14/28, 50.0% [32.6, 67.4] | 158/166, 95.2% [90.8, 97.5] | 14/22, 63.6% [43.0, 80.3] |

Pairs of reviewers on the matched set (McNemar exact, two-sided, unadjusted; first-only/second-only): overfitting patches that only one of the two vetoes, correct patches that only one of the two vetoes, and patches on which only one of the two agrees with the label:

- gemini_3_5_flash_lite_semantic vs claude_sonnet_5_5_semantic: overfitting vetoed 2/12, p=0.0129; correct vetoed 4/7, p=0.5488; agrees with the label 9/16, p=0.2295

κ against the labels on the matched set, with its 95% bootstrap interval (2,000 resamples, fixed seed):

- gemini_3_5_flash_lite_semantic: 194 patches, κ 0.157 [-0.005, 0.334]
- claude_sonnet_5_5_semantic: 194 patches, κ 0.496 [0.301, 0.671]

Tokens of each offline review, as its file records them (every row of the file, one per patch text judged):

- gemini_3_5_flash_lite_semantic: 208 rows; 3,792,776 input and 31,404 output tokens
- claude_sonnet_5_5_semantic: 194 rows; 5,244,143 input and 187,177 output tokens

## 12. Size of the modified files, and the diff section of the no_judge prompt

- single-file bugs: 357; lines in the modified file: median 666, quartiles 296 / 1370; 323 (90.5%) have 150 lines or more, 133 (37.3%) have 1,000 or more
- median lines per project (single-file bugs): Chart 690, Closure 938, Lang 1018, Math 456, Mockito 110, Time 1182
- no_judge, sessions executed before the correction: bugs that received feedback (first attempt not plausible): 239; of these, bugs with a modified file of 150 lines or more, for which the diff section was computed against the localized excerpt instead of the original file: 224 (94%). The corrected code computes it against the original file (section 4f).

## 13. Candidates that did not compile, by the Judge's rationale (full arm, proxy)

A failed candidate is counted when the Judge's rationale mentions compilation; the test result itself is not stored per iteration.

| project | failed candidates reviewed | rationale mentions compilation | share | bugs with at least one |
|---|---|---|---|---|
| Chart | 37 | 2 | 5% | 1 |
| Closure | 349 | 79 | 23% | 49 |
| Lang | 110 | 8 | 7% | 7 |
| Math | 195 | 23 | 12% | 14 |
| Mockito | 66 | 28 | 42% | 17 |
| Time | 54 | 7 | 13% | 3 |
| all | 811 | 147 | 18% | |

## 14. Sensitivity: candidates logged as failing that pass when re-executed

Counted as plausible and correct (their patches are identical or equivalent to the developer fix); the reported figures do not include them.

| arm | added | plausible | correct | vs full, correct: full-only/arm-only, p |
|---|---|---|---|---|
| full | Lang_29 | 203 | 174 |  |
| binary_only | Lang_29, Mockito_22, Mockito_24, Mockito_26 (ALREADY PLAUSIBLE: Mockito_22, Mockito_24) | 184 | 153 | 35/14, p=0.0038 |
| no_judge | Lang_29, Mockito_22, Mockito_26 | 195 | 170 | 34/30, p=0.7080 |
| control (best of 4) | Lang_29, Mockito_26 | 188 | 161 | 39/26, p=0.1360 (vs no_judge 34/25, p=0.2976) |

## 14c. Sensitivity: without the 15 bugs of `mockito_gradle_15.txt`

Paired set restricted to the other 373 bugs; McNemar exact against `full`, Holm over the two correct-fix comparisons.

| arm | plausible | correct | correct: full-only/arm-only | p | Holm p | plausible: full-only/arm-only | p |
|---|---|---|---|---|---|---|---|
| full | 194 | 166 | | | | | |
| binary_only | 175 | 145 | 35/14 | 0.0038 | 0.0076 | 38/19 | 0.0163 |
| no_judge | 185 | 161 | 34/29 | 0.6147 | 0.6147 | 37/28 | 0.3211 |

on the 15 bugs themselves (plausible / correct): full 8 / 7; binary_only 7 / 6; no_judge 7 / 6
control (best of 4) on the 373 bugs: plausible 180, correct 153; full vs control correct 39/26, p=0.1360; no_judge vs control correct 33/25, p=0.3581; on the 15 bugs: plausible 6, correct 6

## 11. Sensitivity to the choice among repeated executions (full arm)

- rule `first`: plausible=202, correct=173, pending=0; on the 50 re-executed bugs: plausible=17, correct=15; correct fixes against the reduced configurations (full-only/other-only, McNemar): binary_only 36/14 p=0.003; no_judge 36/30 p=0.539; smallest Holm-adjusted value 0.005
- rule `last`: plausible=202, correct=173, pending=0; on the 50 re-executed bugs: plausible=17, correct=15; correct fixes against the reduced configurations (full-only/other-only, McNemar): binary_only 36/14 p=0.003; no_judge 36/30 p=0.539; smallest Holm-adjusted value 0.005
- strict (plausible in every execution): plausible=202

## 15. Paired differences, with 95% confidence intervals

Difference between two configurations on the same bugs (first minus second). The interval is the normal approximation for a difference of paired proportions, its variance taken from the discordant pairs; it is not adjusted.

| comparison | metric | first-only | second-only | difference (bugs) | 95% interval (bugs) | difference (points) | 95% interval (points) |
|---|---|---|---|---|---|---|---|
| full minus binary_only | correct | 36 | 14 | +22 | +8.3 to +35.7 | +5.67 | +2.14 to +9.20 |
| full minus binary_only | plausible | 39 | 19 | +20 | +5.2 to +34.8 | +5.15 | +1.34 to +8.97 |
| full minus no_judge | correct | 36 | 30 | +6 | -9.9 to +21.9 | +1.55 | -2.55 to +5.65 |
| full minus no_judge | plausible | 39 | 29 | +10 | -6.1 to +26.1 | +2.58 | -1.58 to +6.73 |
| full minus control | correct | 40 | 26 | +14 | -1.9 to +29.9 | +3.61 | -0.48 to +7.70 |
| full minus control | plausible | 45 | 29 | +16 | -0.8 to +32.8 | +4.12 | -0.20 to +8.45 |
| binary_only minus control | correct | 23 | 31 | -8 | -22.4 to +6.4 | -2.06 | -5.77 to +1.64 |
| binary_only minus control | plausible | 31 | 35 | -4 | -19.9 to +11.9 | -1.03 | -5.13 to +3.07 |
| no_judge minus control | correct | 34 | 26 | +8 | -7.2 to +23.2 | +2.06 | -1.85 to +5.97 |
| no_judge minus control | plausible | 39 | 33 | +6 | -10.6 to +22.6 | +1.55 | -2.74 to +5.83 |

## 16. First attempts and the temperature requested

The first-attempt prompt is the same in every configuration and in every pass of the control; the runs differ in the temperature that the harness requested. If the setting took effect, two runs that both requested a low temperature would produce the same candidate more often than two runs of which one requested a high temperature.

| run | temperature requested at the first attempt | bugs with a first attempt | of which at that request | plausible at the first attempt | correct |
|---|---|---|---|---|---|
| full | 0.1 | 388 | 388 | 148 | 130 |
| binary_only | 0.1 | 388 | 388 | 142 | 120 |
| no_judge | 0.1 | 388 | 388 | 132 | 119 |
| sample_t010 | 0.1 | 388 | 388 | 140 | 121 |
| sample_t045a | 0.45 | 388 | 388 | 145 | 125 |
| sample_t045b | 0.45 | 388 | 388 | 144 | 123 |
| sample_t085 | 0.85 | 388 | 388 | 140 | 125 |

over the 7 runs: plausible at the first attempt 132 to 148, correct 119 to 130

Share of bugs whose first-attempt candidates have the same text in two runs (same Java token sequence; bugs on which both runs made their usual request):

| temperatures requested by the two runs | pairs of runs | comparisons | same text | share | lowest pair | highest pair |
|---|---|---|---|---|---|---|
| 0.1 and 0.1 | 6 | 2328 | 860 | 36.9% | 33.5% | 40.7% |
| 0.1 and 0.45 | 8 | 3104 | 1254 | 40.4% | 38.1% | 43.6% |
| 0.1 and 0.85 | 4 | 1552 | 602 | 38.8% | 35.6% | 41.8% |
| 0.45 and 0.45 | 1 | 388 | 169 | 43.6% | 43.6% | 43.6% |
| 0.45 and 0.85 | 2 | 776 | 330 | 42.5% | 41.8% | 43.3% |

all 21 pairs of runs: 3215 of 8148 comparisons (39.5%), from 33.5% to 43.6% per pair
per pair: full / binary_only 147/388; full / no_judge 130/388; full / sample_t010 142/388; binary_only / no_judge 150/388; binary_only / sample_t010 158/388; no_judge / sample_t010 133/388; full / sample_t045a 154/388; full / sample_t045b 154/388; binary_only / sample_t045a 166/388; binary_only / sample_t045b 153/388; no_judge / sample_t045a 151/388; no_judge / sample_t045b 148/388; sample_t010 / sample_t045a 159/388; sample_t010 / sample_t045b 169/388; full / sample_t085 149/388; binary_only / sample_t085 153/388; no_judge / sample_t085 138/388; sample_t010 / sample_t085 162/388; sample_t045a / sample_t045b 169/388; sample_t045a / sample_t085 162/388; sample_t045b / sample_t085 168/388

## 17. Correct fixes by kind of label, and the comparisons without alternative fixes

| configuration | plausible | identical | equivalent | alternative | correct, kind not recorded | overfitting | identical or equivalent |
|---|---|---|---|---|---|---|---|
| full | 202 | 70 | 65 | 38 | 0 | 29 | 135 |
| binary_only | 182 | 66 | 59 | 26 | 0 | 31 | 125 |
| no_judge | 192 | 64 | 69 | 34 | 0 | 25 | 133 |
| control | 186 | 69 | 62 | 28 | 0 | 27 | 131 |

patch texts that carry two kinds of correct label (across the configurations and the control passes): 1 (Math_50: alternative in full, binary_only and equivalent in control)

Identical or equivalent patches only (alternative fixes not counted as correct), McNemar exact against `full`; configurations whose correct patches all carry a kind:

| comparison | full | other | full-only | other-only | p | p, texts with two kinds counted | p, not counted |
|---|---|---|---|---|---|---|---|
| full vs binary_only | 135 | 125 | 27 | 17 | 0.1742 | 0.1742 | 0.1742 |
| full vs no_judge | 135 | 133 | 30 | 28 | 0.8957 | 0.7914 | 0.8957 |
| full vs control | 135 | 131 | 29 | 25 | 0.6835 | 0.5831 | 0.5831 |

full minus binary_only, by kind: identical +4, equivalent +6, alternative +12, all correct +22

full minus no_judge, by kind: identical +6, equivalent -4, alternative +4, all correct +6

Attempts 2 to 4 on the bugs whose first attempt is plausible in neither of the two configurations, identical or equivalent only:

- full vs binary_only: 218 bugs, 23 / 16, only first 12, only second 5, p=0.1435
- full vs no_judge: 221 bugs, 24 / 22, only first 12, only second 10, p=0.8318
- binary_only vs no_judge: 227 bugs, 18 / 28, only first 6, only second 16, p=0.0525

Plausible patches, which involve no label: McNemar exact against `full`, Holm over the two: binary_only 39/19, p=0.0119, Holm 0.0239; no_judge 39/29, p=0.2750, Holm 0.2750

## 18. Cost at the provider's list prices

Input and output tokens are priced separately, at USD 0.30 per million input tokens and USD 2.50 per million output tokens (`--price-in`, `--price-out`; the defaults are the list prices of `gemini-3.5-flash-lite`, standard paid tier, as published on 25 November 2026). Section 7 gives the estimate that the harness logged at a flat rate; here the cost is computed from the logged token counts.

| configuration | input tokens | output tokens | output share | USD | repair USD | Judge USD | Judge share of USD | USD per bug | USD per plausible patch | USD per correct fix | USD logged at the flat rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 45,412,031 | 983,437 | 2.1% | $16.08 | $9.39 | $6.69 | 41.6% | $0.0414 | $0.0796 | $0.0930 | $16.24 |
| binary_only | 43,763,868 | 911,550 | 2.0% | $15.41 | $8.87 | $6.54 | 42.5% | $0.0397 | $0.0847 | $0.1020 | $15.64 |
| no_judge | 22,349,863 | 722,114 | 3.1% | $8.51 | $8.51 | $0.00 | 0.0% | $0.0219 | $0.0443 | $0.0510 | $8.08 |
| control, as run | 21,082,897 | 1,152,279 | 5.2% | $9.21 | $9.21 | $0.00 | 0.0% | $0.0237 | $0.0495 | $0.0579 | $7.78 |
| control, early stop | 15,353,076 | 907,822 | 5.6% | $6.88 | $6.88 | $0.00 | 0.0% | $0.0177 | $0.0370 | $0.0432 | $5.69 |

steps with a token record (the three configurations and the control passes): 7,309; steps whose logged total is not the sum of prompt and output tokens: 0
three configurations together: $40.00
- full: per bug, mean $0.0414, median $0.0247, maximum $0.3948
- binary_only: per bug, mean $0.0397, median $0.0260, maximum $0.2520
- no_judge: per bug, mean $0.0219, median $0.0145, maximum $0.1956
full arm, plausible patches found at the first attempt: n=148, median USD at list prices 0.0068
full arm, plausible patches found after iteration: n=54, median USD at list prices 0.0223
example trajectory (Closure_51, full): 18,651 input and 912 output tokens, 19,563 in all, $0.0079

Prompt sizes in `full`, in tokens as the API counted them (one request per file; requests that were regenerated are left out):

- Repair Agent prompt, first attempt: 378 requests, median 6,888, 90th percentile 20,241, maximum 76,129
- Repair Agent prompt, later attempts: 609 requests, median 16,338, 90th percentile 41,745, maximum 158,176
- Judge prompt: 1014 requests, median 13,667, 90th percentile 39,295, maximum 152,526

Incremental cost per additional correct fix (difference in USD over difference in correct fixes; the differences in correct fixes are those of section 15, with their intervals):

- full against binary_only: +0.67 USD for +22 correct fixes, $0.03 per additional correct fix
- full against no_judge: +7.57 USD for +6 correct fixes, $1.26 per additional correct fix
- full against control, as run: +6.88 USD for +14 correct fixes, $0.49 per additional correct fix
- full against control, early stop: +9.21 USD for +14 correct fixes, $0.66 per additional correct fix
- no_judge against control, as run: -0.70 USD for +8 correct fixes
- no_judge against control, early stop: +1.63 USD for +8 correct fixes, $0.20 per additional correct fix

Budget of k iterations (the first k iterations of every execution; a loop stopped after k iterations would have produced them) and of k control passes: fixes and cost at list prices.

| configuration | k | plausible | correct | input tokens | output tokens | USD | USD per correct fix |
|---|---|---|---|---|---|---|---|
| full | 1 | 148 | 130 | 12,667,043 | 368,270 | $4.72 | $0.0363 |
| full | 2 | 177 | 152 | 24,325,552 | 632,273 | $8.88 | $0.0584 |
| full | 3 | 191 | 165 | 35,287,055 | 848,266 | $12.71 | $0.0770 |
| full | 4 | 202 | 173 | 45,412,031 | 983,437 | $16.08 | $0.0930 |
| binary_only | 1 | 142 | 120 | 12,546,263 | 364,020 | $4.67 | $0.0389 |
| binary_only | 2 | 168 | 140 | 23,986,343 | 602,721 | $8.70 | $0.0622 |
| binary_only | 3 | 175 | 145 | 33,999,415 | 778,173 | $12.15 | $0.0838 |
| binary_only | 4 | 182 | 151 | 43,763,868 | 911,550 | $15.41 | $0.1020 |
| no_judge | 1 | 132 | 119 | 5,414,042 | 253,401 | $2.26 | $0.0190 |
| no_judge | 2 | 173 | 150 | 11,830,503 | 443,669 | $4.66 | $0.0311 |
| no_judge | 3 | 184 | 160 | 17,478,813 | 613,372 | $6.78 | $0.0424 |
| no_judge | 4 | 192 | 167 | 22,349,863 | 722,114 | $8.51 | $0.0510 |
| control, as run | 1 | 140 | 121 | 5,545,432 | 268,888 | $2.34 | $0.0193 |
| control, early stop | 1 | 140 | 121 | 5,545,432 | 268,888 | $2.34 | $0.0193 |
| control, as run | 2 | 165 | 141 | 10,834,168 | 570,339 | $4.68 | $0.0332 |
| control, early stop | 2 | 165 | 141 | 9,156,015 | 508,760 | $4.02 | $0.0285 |
| control, as run | 3 | 173 | 148 | 16,106,547 | 904,231 | $7.09 | $0.0479 |
| control, early stop | 3 | 173 | 148 | 12,442,176 | 752,106 | $5.61 | $0.0379 |
| control, as run | 4 | 186 | 159 | 21,082,897 | 1,152,279 | $9.21 | $0.0579 |
| control, early stop | 4 | 186 | 159 | 15,353,076 | 907,822 | $6.88 | $0.0432 |

The loop after k iterations against k control passes (the same number of tested candidates; McNemar exact on correct fixes, two-sided, unadjusted; loop-only/control-only):

| k | configuration | correct | USD | control correct | control USD, as run | discordant | p |
|---|---|---|---|---|---|---|---|
| 1 | full | 130 | $4.72 | 121 | $2.34 | 24/15 | 0.1996 |
| 1 | no_judge | 119 | $2.26 | 121 | $2.34 | 19/21 | 0.8746 |
| 2 | full | 152 | $8.88 | 141 | $4.68 | 34/23 | 0.1849 |
| 2 | no_judge | 150 | $4.66 | 141 | $4.68 | 31/22 | 0.2717 |
| 3 | full | 165 | $12.71 | 148 | $7.09 | 42/25 | 0.0498 |
| 3 | no_judge | 160 | $6.78 | 148 | $7.09 | 35/23 | 0.1480 |
| 4 | full | 173 | $16.08 | 159 | $9.21 | 40/26 | 0.1089 |
| 4 | no_judge | 167 | $8.51 | 159 | $9.21 | 34/26 | 0.3663 |

At about the cost of `no_judge` with 4 iterations ($8.51, 167 correct), paired on bug identity:

- binary_only, k=2: $8.70, 140 correct; no_judge-only 41, other-only 14, p=0.0004
- full, k=2: $8.88, 152 correct; no_judge-only 43, other-only 28, p=0.0959
- control, as run, k=4: $9.21, 159 correct; no_judge-only 34, other-only 26, p=0.3663
- control, as run, k=3: $7.09, 148 correct; no_judge-only 41, other-only 22, p=0.0226

## 19. Later attempts on the bugs whose first candidate is the same in two configurations

The first-attempt prompt is the same in every configuration, and two configurations often produce the same first candidate (same Java token sequence, all files). On the bugs where they do and that candidate fails, the two loops start their feedback from one and the same failed candidate; what differs afterwards is the feedback. The subset is selected by what the model generated, not at random, and the analysis is post hoc.

| pair | bugs with the same first candidate | recorded outcome differs | it fails in both | plausible later: first / second | only first / only second, p | correct later: first / second | only first / only second, p |
|---|---|---|---|---|---|---|---|
| full vs binary_only | 147 | 1 (Mockito_26) | 62 | 12 / 10 | 2/0, p=0.5000 | 10 / 7 | 3/0, p=0.2500 |
| full vs no_judge | 130 | 2 (Mockito_22, Mockito_26) | 51 | 15 / 15 | 4/4, p=1.0000 | 14 / 11 | 6/3, p=0.5078 |
| binary_only vs no_judge | 150 | 1 (Mockito_22) | 61 | 13 / 14 | 4/5, p=1.0000 | 10 / 12 | 3/5, p=0.7266 |

The same comparison on the bugs whose first candidates differ and both fail:

| pair | bugs | plausible later: first / second | only first / only second, p | correct later: first / second | only first / only second, p |
|---|---|---|---|---|---|
| full vs binary_only | 156 | 33 / 17 | 22/6, p=0.0037 | 25 / 12 | 16/3, p=0.0044 |
| full vs no_judge | 170 | 33 / 29 | 16/12, p=0.5716 | 25 / 23 | 13/11, p=0.8388 |
| binary_only vs no_judge | 166 | 18 / 34 | 6/22, p=0.0037 | 13 / 26 | 5/18, p=0.0106 |

## 20. Three endpoints: test-passing, identical or equivalent, all correct

A correct patch whose kind was not recorded takes the kind of the same patch text where one was recorded (in another configuration or in a control pass). Where no occurrence of the text carries a kind, the patch is counted at the upper end of the range only; a text that carries two kinds, one of them alternative, likewise.

| configuration | plausible | identical or equivalent | all correct | kind recorded | kind from the same text elsewhere | no kind anywhere |
|---|---|---|---|---|---|---|
| full | 202 | 135 to 136 | 173 | 173 | 0 | 0 |
| binary_only | 182 | 125 to 126 | 151 | 151 | 0 | 0 |
| no_judge | 192 | 133 | 167 | 167 | 0 | 0 |
| control | 186 | 130 to 131 | 159 | 159 | 0 | 0 |

Identical or equivalent patches, McNemar exact against `full`, at the lower end of both ranges and at the upper end of both (a text is counted in the same way wherever it occurs):

- full vs binary_only: 135 against 125, 27/17, p=0.1742; 136 against 126, 27/17, p=0.1742
- full vs no_judge: 135 against 133, 30/28, p=0.8957; 136 against 133, 30/27, p=0.7914
- full vs control: 135 against 130, 29/24, p=0.5831; 136 against 131, 29/24, p=0.5831

## 21. Label sensitivity of the comparisons with `full` (tipping point)

How many correct-label changes would alter the outcome of a comparison on the primary metric? A change moves one bug: a correct patch relabelled overfitting in the configuration ahead removes one of its discordant bugs, and an overfitting patch relabelled correct in the other configuration adds one of its own. Against the leader, the changes are placed to raise the p-value as fast as possible; Holm adjusts over the two comparisons with `full`, the other kept as it is.

- full vs binary_only (36/14, significant after adjustment): Holm-adjusted p reaches 0.05 after 5 changes placed against `full` (7 if only correct labels of `full` change); unadjusted p reaches 0.05 after 7 changes placed against `full` (9 if only correct labels of `full` change)
- full vs no_judge (36/30, not significant): the Holm-adjusted p falls below 0.05 after 10 changes placed in favour of `full`
- kinds of the correct patches on the discordant bugs, full vs binary_only: full-only 36 (identical 6, equivalent 18, alternative 12, no kind 0); binary_only-only 14 (identical 5, equivalent 6, alternative 3, no kind 0)
- kinds of the correct patches on the discordant bugs, full vs no_judge: full-only 36 (identical 8, equivalent 18, alternative 10, no kind 0); no_judge-only 30 (identical 6, equivalent 14, alternative 10, no kind 0)

canonical per-bug tables written to `figures_out/canonical_<arm>.csv`
