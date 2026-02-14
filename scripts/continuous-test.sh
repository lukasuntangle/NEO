#!/usr/bin/env bash
# continuous-test.sh -- Continuous test watcher for Neo Orchestrator
# Watches blackboard for FILE_CHANGED events during jacking-in phase
# and runs affected tests immediately so agents see failures early.
# Usage: bash continuous-test.sh [project-dir] [--matrix-dir .matrix] [--full-interval 60]
set -euo pipefail

PROJECT_DIR="."; MATRIX_DIR_REL=".matrix"; FULL_INTERVAL=60
while [[ $# -gt 0 ]]; do
    case "$1" in
        --matrix-dir) MATRIX_DIR_REL="$2"; shift 2 ;;
        --full-interval) FULL_INTERVAL="$2"; shift 2 ;;
        -*) echo "Unknown flag: $1" >&2; exit 1 ;;
        *)  PROJECT_DIR="$1"; shift ;;
    esac
done

MATRIX_DIR="${PROJECT_DIR}/${MATRIX_DIR_REL}"
BLACKBOARD="${MATRIX_DIR}/blackboard.jsonl"
SESSION_FILE="${MATRIX_DIR}/session.json"
LOG_FILE="${MATRIX_DIR}/logs/continuous-test.log"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[CONTINUOUS-TEST]${NC} $1" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[CONTINUOUS-TEST]${NC} $1" | tee -a "$LOG_FILE" >&2; }
warn() { echo -e "${YELLOW}[CONTINUOUS-TEST]${NC} $1" | tee -a "$LOG_FILE"; }
info() { echo -e "${CYAN}[CONTINUOUS-TEST]${NC} $1" | tee -a "$LOG_FILE"; }

[ ! -d "$MATRIX_DIR" ] && { err "No ${MATRIX_DIR}/ found. Run init-matrix.sh first."; exit 1; }
mkdir -p "${MATRIX_DIR}/logs"; touch "$LOG_FILE" "$BLACKBOARD"

# --- Test runner detection ---
detect_runner() {
    if [ -f "${PROJECT_DIR}/package.json" ]; then
        local ts; ts=$(python3 -c "import json;print(json.load(open('${PROJECT_DIR}/package.json')).get('scripts',{}).get('test',''))" 2>/dev/null)
        [[ -n "$ts" && "$ts" != *"no test specified"* ]] && { echo "npm test --"; return; }
    fi
    for p in vitest.config jest.config; do
        for e in ts js mjs mts cjs; do [ -f "${PROJECT_DIR}/${p}.${e}" ] && { echo "npx ${p%%.*} run"; return; }; done
    done
    for e in ts js; do [ -f "${PROJECT_DIR}/playwright.config.${e}" ] && { echo "npx playwright test"; return; }; done
    echo "npx vitest run"
}
TEST_RUNNER=$(detect_runner); log "Test runner: ${TEST_RUNNER}"

# --- Test file discovery: find tests covering a source file ---
find_test_files() {
    local f="$1" base dir name
    base="${f##*/}"; name="${base%.*}"; dir="$(dirname "$f")"
    for ext in test spec; do for fext in ts tsx js jsx; do
        for candidate in "${dir}/${name}.${ext}.${fext}" "${dir}/__tests__/${name}.${ext}.${fext}"; do
            [ -f "${PROJECT_DIR}/${candidate}" ] && echo "$candidate"
        done
        # Mirror: src/x/foo.ts -> tests/x/foo.test.ts or test/x/foo.test.ts
        local rel="${f#src/}"
        if [ "$rel" != "$f" ]; then
            local mdir; mdir="$(dirname "$rel")"
            for pre in tests test; do
                [ -f "${PROJECT_DIR}/${pre}/${mdir}/${name}.${ext}.${fext}" ] && echo "${pre}/${mdir}/${name}.${ext}.${fext}"
            done
        fi
    done; done | sort -u
}

# --- Helpers ---
should_continue() {
    local phase; phase=$(python3 -c "import json;print(json.load(open('${SESSION_FILE}')).get('phase','unknown'))" 2>/dev/null || echo "unknown")
    case "$phase" in sentinels|zion|escalated|completed) return 1 ;; *) return 0 ;; esac
}
is_source_file() {
    case "$1" in *.test.*|*.spec.*|*__tests__/*) return 1 ;; esac
    case "$1" in *.ts|*.tsx|*.js|*.jsx|*.mts|*.mjs|*.py|*.go|*.rs|*.java) return 0 ;; *) return 1 ;; esac
}

# Parse pass/fail counts from test runner output
parse_counts() {
    local output="$1" exit_code="$2"
    python3 -c "
import sys, re
c = '''${output}'''
p, f = 0, 0
for pat in [r'(\d+)\s+pass', r'Tests:\s+(\d+)\s+passed', r'(\d+)\s+passing']:
    m = re.search(pat, c, re.I)
    if m: p = int(m.group(1)); break
else:
    p = 1 if ${exit_code} == 0 else 0
for pat in [r'(\d+)\s+fail', r'Tests:\s+\d+[^,]*,\s*(\d+)\s+failed', r'(\d+)\s+failing']:
    m = re.search(pat, c, re.I)
    if m: f = int(m.group(1)); break
print(f'{p} {f}')
" 2>/dev/null || echo "0 0"
}

post_result() {
    python3 "${SCRIPTS_DIR}/blackboard.py" post mouse TEST_RESULT \
        "{\"passed\":$1,\"failed\":$2,\"files_tested\":$3,\"trigger\":\"$4\"}" \
        --matrix-dir "$MATRIX_DIR" >> "$LOG_FILE" 2>&1 || true
}

# --- Run tests and post results ---
run_tests() {
    local trigger="$1"; shift; local files=("$@")
    local files_arg="${files[*]}"
    info "Running ${trigger} tests: ${files_arg:-all}"

    local output exit_code=0
    output=$(cd "$PROJECT_DIR" && $TEST_RUNNER $files_arg 2>&1) || exit_code=$?
    local counts; counts=$(parse_counts "$output" "$exit_code")
    local passed="${counts%% *}" failed="${counts##* }"

    if [ "$exit_code" -eq 0 ]; then
        log "PASS (${passed} passed, ${failed} failed): ${files_arg:-full suite}"
    else
        err "FAIL (${passed} passed, ${failed} failed): ${files_arg:-full suite}"
        echo "$output" | tail -20 >> "$LOG_FILE"
    fi

    # Build JSON array of tested files
    local fj="["; local first=true
    for tf in "${files[@]}"; do
        $first && fj="${fj}\"${tf}\"" || fj="${fj},\"${tf}\""; first=false
    done
    post_result "$passed" "$failed" "${fj}]" "$trigger"
}

# --- Main loop ---
log "Watching ${PROJECT_DIR} (interval=${FULL_INTERVAL}s, PID=$$)"
CHANGE_COUNT=0; LAST_FULL=$(date +%s); QUEUED=()
LAST_LINES=$(wc -l < "$BLACKBOARD" | tr -d ' ')

while should_continue; do
    CUR_LINES=$(wc -l < "$BLACKBOARD" | tr -d ' ')
    if [ "$CUR_LINES" -gt "$LAST_LINES" ]; then
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            read -r evt file_path <<< "$(echo "$line" | python3 -c "
import sys,json
try:
    e=json.loads(sys.stdin.read().strip());d=e.get('data',{})
    print(e.get('event_type',''),d.get('file',d.get('path',d.get('filename',''))))
except: print('' '')
" 2>/dev/null)"
            [ "$evt" != "FILE_CHANGED" ] || [ -z "$file_path" ] && continue
            is_source_file "$file_path" || continue
            tests=$(find_test_files "$file_path")
            [ -z "$tests" ] && { info "No tests for ${file_path}"; continue; }
            while IFS= read -r tf; do
                local dup=false; for q in "${QUEUED[@]+"${QUEUED[@]}"}"; do [ "$q" = "$tf" ] && dup=true; done
                $dup || QUEUED+=("$tf")
            done <<< "$tests"
            CHANGE_COUNT=$((CHANGE_COUNT + 1))
        done <<< "$(tail -n +"$((LAST_LINES + 1))" "$BLACKBOARD")"
        LAST_LINES="$CUR_LINES"
    fi

    # Debounce: wait 2s then run queued tests
    if [ ${#QUEUED[@]} -gt 0 ]; then
        sleep 2
        run_tests "continuous" "${QUEUED[@]}"; QUEUED=()
    fi

    # Full suite every FULL_INTERVAL seconds or 5 changes
    NOW=$(date +%s)
    if (( CHANGE_COUNT >= 5 || NOW - LAST_FULL >= FULL_INTERVAL )) && [ "$CHANGE_COUNT" -gt 0 ]; then
        run_tests "full-suite" "*"; CHANGE_COUNT=0; LAST_FULL=$(date +%s)
    elif (( NOW - LAST_FULL >= FULL_INTERVAL )); then
        LAST_FULL=$(date +%s)
    fi

    sleep 1
done
log "Session phase changed. Continuous test watcher stopped."
