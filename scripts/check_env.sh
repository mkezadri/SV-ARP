#!/usr/bin/env bash
# Verify the environment reproduces Defects4J correctly.
# A clean Closure 2b checkout must report exactly ONE failing test.
set -uo pipefail

fail=0
check() { printf '  %-22s %s\n' "$1" "$2"; }

echo "Environment:"
check "java"          "$(java -version 2>&1 | grep -o 'version "[^"]*"' || echo MISSING)"
check "JAVA_HOME"     "${JAVA_HOME:-UNSET}"
check "TZ"            "${TZ:-UNSET}"
check "_JAVA_OPTIONS" "${_JAVA_OPTIONS:-UNSET}"
check "D4J_HOME"      "${D4J_HOME:-UNSET}"

java -version 2>&1 | grep -q 'version "11' || { echo "  ! Java 11 required"; fail=1; }
[ "${TZ:-}" = "America/Los_Angeles" ] || { echo "  ! TZ must be America/Los_Angeles"; fail=1; }
echo "${_JAVA_OPTIONS:-}" | grep -q 'user.language=en' || {
    echo "  ! _JAVA_OPTIONS must include -Duser.language=en -Duser.country=US"; fail=1; }
[ -x "${D4J_HOME:-}/framework/bin/defects4j" ] || { echo "  ! defects4j not found"; fail=1; }
[ $fail -eq 0 ] || { echo; echo "Fix the above before running the benchmark."; exit 1; }

echo
echo "Smoke test: Closure 2b baseline (expect exactly 1 failing test)"
w=$(mktemp -d)
"$D4J_HOME/framework/bin/defects4j" checkout -p Closure -v 2b -w "$w" >/dev/null 2>&1
( cd "$w" && "$D4J_HOME/framework/bin/defects4j" compile >/dev/null 2>&1 \
  && "$D4J_HOME/framework/bin/defects4j" test -r 2>&1 | grep -E "^Failing tests" )
rm -rf "$w"
echo
echo "  1 failing test   -> environment correct"
echo "  14 failing tests -> locale not applied; see README"
