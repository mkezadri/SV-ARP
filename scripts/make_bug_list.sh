#!/usr/bin/env bash
# Regenerate benchmark/versions.txt from your local Defects4J install.
#   ./scripts/make_bug_list.sh > benchmark/versions.txt
# V1.2 ranges: Chart 1-26, Closure 1-133, Lang 1-65, Math 1-106,
# Mockito 1-38, Time 1-27. The seven deprecated bugs are excluded
# automatically because they no longer appear in active-bugs.csv.
set -euo pipefail
: "${D4J_HOME:?set D4J_HOME first}"

for entry in Chart:26 Closure:133 Lang:65 Math:106 Mockito:38 Time:27; do
    proj="${entry%%:*}"; max="${entry##*:}"
    awk -F, -v p="$proj" -v m="$max" 'NR>1 && $1+0>=1 && $1+0<=m {print p"_"$1}' \
        "$D4J_HOME/framework/projects/$proj/active-bugs.csv"
done
