#!/usr/bin/env bash
# Verify that the environment reproduces Defects4J as in the paper's runs.
#
#   1. Java 11, the time zone and both JVM locale options are set.
#   2. Ant-built project: a clean Closure 2b checkout must report exactly one
#      failing test, TypeCheckTest::testBadInterfaceExtendsNonExistentInterfaces
#      (14 failing tests mean that the JVM locale is not English).
#   3. Gradle-built project: a clean Mockito 1b checkout must build and report
#      26 failing tests, as it did in every run of the paper. A build that stops
#      within seconds means that the Gradle distribution of Defects4J was not
#      unpacked (see the replication guide, Step 1).
#
# Exits with status 1 if any check fails. The two smoke tests take a few minutes.
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
for opt in -Duser.language=en -Duser.country=US; do
    case " ${_JAVA_OPTIONS:-} " in
        *" $opt "*) ;;
        *) echo "  ! _JAVA_OPTIONS must include $opt"; fail=1 ;;
    esac
done
[ -x "${D4J_HOME:-}/framework/bin/defects4j" ] || { echo "  ! defects4j not found"; fail=1; }
[ $fail -eq 0 ] || { echo; echo "Fix the above before running the benchmark."; exit 1; }

D4J="$D4J_HOME/framework/bin/defects4j"

# smoke PROJECT VERSION EXPECTED_COUNT [EXPECTED_TEST]
smoke() {
    local w out n
    echo
    echo "Smoke test: $1 $2 baseline (expect $3 failing test(s)${4:+, among them $4})"
    w=$(mktemp -d)
    out=$("$D4J" checkout -p "$1" -v "$2" -w "$w" >/dev/null 2>&1 \
          && cd "$w" && "$D4J" compile >/dev/null 2>&1 && "$D4J" test -r 2>&1)
    rm -rf "$w"
    n=$(printf '%s\n' "$out" | sed -n 's/^Failing tests: *\([0-9][0-9]*\).*/\1/p' | head -n 1)
    if [ -z "$n" ]; then
        echo "  ! the checkout did not build or the tests did not run (no 'Failing tests:' line)"
        fail=1; return
    fi
    echo "  Failing tests: $n"
    [ "$n" = "$3" ] || { echo "  ! expected $3"; fail=1; }
    if [ -n "${4:-}" ] && ! printf '%s\n' "$out" | grep -q -- "- .*::$4\$"; then
        echo "  ! $4 is not among the failing tests"; fail=1
    fi
}

smoke Closure 2b 1 testBadInterfaceExtendsNonExistentInterfaces
smoke Mockito 1b 26

echo
if [ $fail -eq 0 ]; then
    echo "Environment correct."
else
    echo "Environment NOT correct: see the lines marked '!' above."
    echo "  Closure 2b with 14 failing tests: the JVM locale is not applied (see the README)."
    echo "  Mockito 1b that does not build: the Gradle distribution is missing (replication guide, Step 1)."
    exit 1
fi
