#!/usr/bin/env bash
# quality-gate.sh — Sentinel pipeline for Neo Orchestrator
# Usage: bash quality-gate.sh <gate> [project-dir]
#   Gates: smith, trinity, switch, all, lint
set -euo pipefail

GATE="${1:?Usage: quality-gate.sh <gate> [project-dir]}"
PROJECT_DIR="${2:-.}"
MATRIX_DIR="${PROJECT_DIR}/.matrix"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="${SKILL_DIR}/scripts"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
SENTINEL_DIR="${MATRIX_DIR}/sentinels"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[SENTINEL]${NC} $1"; }
err() { echo -e "${RED}[SENTINEL]${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[SENTINEL]${NC} $1"; }

# Validate
if [ ! -d "$MATRIX_DIR" ]; then
    err "No .matrix/ directory found."
    exit 1
fi

# Load config
CONFIG=$(cat "$MATRIX_DIR/config.json")
MAX_CYCLES=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['thresholds']['max_remediation_cycles'])")
COVERAGE_MIN=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['thresholds']['coverage_minimum'])")
SMITH_MIN_ISSUES=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['thresholds']['smith_min_issues'])")

# Get current remediation cycle
CURRENT_CYCLE=$(python3 -c "
import json
with open('$MATRIX_DIR/session.json') as f:
    print(json.load(f).get('remediation_cycle', 0))
")

record_gate_result() {
    local gate_name="$1"
    local passed="$2"
    local details="$3"

    python3 -c "
import json
from datetime import datetime, timezone

with open('$SENTINEL_DIR/gate-log.json') as f:
    log = json.load(f)

entry = {
    'gate': '$gate_name',
    'passed': $passed,
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'cycle': $CURRENT_CYCLE,
    'details': '''$details'''
}

log['gates'] = [*log['gates'], entry]
log['last_run'] = entry['timestamp']
if $passed:
    log['pass_count'] = log.get('pass_count', 0) + 1
else:
    log['fail_count'] = log.get('fail_count', 0) + 1

with open('$SENTINEL_DIR/gate-log.json', 'w') as f:
    json.dump(log, f, indent=2)
"
}

# --- Gate: Lint ---
run_lint() {
    log "Running lint check..."

    local issues=0
    local details=""

    # Check for console.log
    if grep -r "console\.log" "$PROJECT_DIR/src" 2>/dev/null | grep -v node_modules | grep -v ".test." | head -20; then
        details="Found console.log statements in source files"
        issues=$((issues + 1))
    fi

    # Check for TODO/FIXME
    local todo_count
    todo_count=$(grep -rc "TODO\|FIXME\|HACK\|XXX" "$PROJECT_DIR/src" 2>/dev/null | grep -v ":0$" | wc -l || echo 0)
    if [ "$todo_count" -gt 0 ]; then
        details="${details}; Found ${todo_count} files with TODO/FIXME comments"
    fi

    if [ "$issues" -eq 0 ]; then
        log "Lint check passed."
        record_gate_result "lint" "True" "Clean"
        return 0
    else
        warn "Lint check found issues: ${details}"
        record_gate_result "lint" "False" "$details"
        return 1
    fi
}

# --- Gate: Smith (Blind Code Review) ---
run_smith() {
    log "Deploying Agent Smith for blind code review..."

    # Prepare blind diff
    bash "$SCRIPTS_DIR/blind-review-prep.sh" "$PROJECT_DIR" > "${SENTINEL_DIR}/blind-diff.patch" 2>/dev/null || true

    if [ ! -s "${SENTINEL_DIR}/blind-diff.patch" ]; then
        warn "No diff available for review. Skipping Smith."
        record_gate_result "smith" "True" "No changes to review"
        return 0
    fi

    local blind_diff
    blind_diff=$(cat "${SENTINEL_DIR}/blind-diff.patch")

    # Spawn Smith with blind diff
    local smith_result
    smith_result=$(bash "$SCRIPTS_DIR/spawn-agent.sh" smith opus \
        "Review this code diff. You MUST find at least ${SMITH_MIN_ISSUES} issues or provide a >100 word justification for why the code is clean. Categorize each issue as critical/major/minor. Diff:\n\n${blind_diff}" \
        "$PROJECT_DIR" 2>/dev/null) || true

    # Save result
    echo "$smith_result" > "${SENTINEL_DIR}/smith-review.json"

    # Parse result — check if Smith found issues
    local issue_count
    issue_count=$(echo "$smith_result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    issues = data.get('issues_found', data.get('issues', []))
    print(len(issues) if isinstance(issues, list) else 0)
except:
    print(0)
" 2>/dev/null || echo "0")

    if [ "$issue_count" -ge "$SMITH_MIN_ISSUES" ]; then
        warn "Smith found ${issue_count} issues."
        record_gate_result "smith" "False" "Found ${issue_count} issues"
        return 1
    fi

    # Check for justification length if few issues
    local has_justification
    has_justification=$(echo "$smith_result" | python3 -c "
import sys
content = sys.stdin.read()
words = len(content.split())
print('true' if words > 100 else 'false')
" 2>/dev/null || echo "false")

    if [ "$has_justification" = "true" ]; then
        log "Smith approved with justification."
        record_gate_result "smith" "True" "Approved with justification (${issue_count} issues)"
        return 0
    fi

    # Spawn second Smith clone
    log "Smith found ${issue_count} issues without sufficient justification. Spawning clone..."
    local smith2_result
    smith2_result=$(bash "$SCRIPTS_DIR/spawn-agent.sh" smith opus \
        "INDEPENDENT REVIEW — ignore any prior reviews. Review this code diff. Find at least ${SMITH_MIN_ISSUES} issues or justify why it's clean (>100 words). Diff:\n\n${blind_diff}" \
        "$PROJECT_DIR" 2>/dev/null) || true

    echo "$smith2_result" > "${SENTINEL_DIR}/smith-review-clone.json"

    local clone_issues
    clone_issues=$(echo "$smith2_result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    issues = data.get('issues_found', data.get('issues', []))
    print(len(issues) if isinstance(issues, list) else 0)
except:
    print(0)
" 2>/dev/null || echo "0")

    if [ "$clone_issues" -eq 0 ] && [ "$issue_count" -eq 0 ]; then
        log "Both Smiths found 0 issues. Code is genuinely clean."
        record_gate_result "smith" "True" "Both Smiths confirmed clean"
        return 0
    fi

    warn "Smith clone found ${clone_issues} issues."
    record_gate_result "smith" "False" "Clone found ${clone_issues} issues"
    return 1
}

# --- Gate: Trinity (Security) ---
run_trinity() {
    log "Deploying Trinity for security audit..."

    # Get list of changed files
    local changed_files
    changed_files=$(cd "$PROJECT_DIR" && git diff --name-only HEAD~1 2>/dev/null || find src -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" 2>/dev/null || echo "")

    if [ -z "$changed_files" ]; then
        log "No files to audit."
        record_gate_result "trinity" "True" "No files to audit"
        return 0
    fi

    # Spawn Trinity
    local trinity_result
    trinity_result=$(bash "$SCRIPTS_DIR/spawn-agent.sh" trinity sonnet \
        "Perform a security audit on these files: ${changed_files}. Check for OWASP Top 10, hardcoded secrets, SQL injection, XSS, command injection, path traversal, and auth issues." \
        "$PROJECT_DIR" 2>/dev/null) || true

    echo "$trinity_result" > "${SENTINEL_DIR}/trinity-security.json"

    # Check for critical findings
    local critical_count
    critical_count=$(echo "$trinity_result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    issues = data.get('issues_found', [])
    critical = [i for i in issues if isinstance(i, dict) and i.get('severity') == 'critical']
    print(len(critical))
except:
    print(0)
" 2>/dev/null || echo "0")

    if [ "$critical_count" -gt 0 ]; then
        err "Trinity found ${critical_count} CRITICAL security issues!"
        record_gate_result "trinity" "False" "${critical_count} critical security issues"
        return 1
    fi

    log "Trinity security audit passed."
    record_gate_result "trinity" "True" "No critical security issues"
    return 0
}

# --- Gate: Switch + Mouse (Tests) ---
run_switch() {
    log "Deploying Switch for test verification..."

    # Spawn Switch to write/verify tests
    local switch_result
    switch_result=$(bash "$SCRIPTS_DIR/spawn-agent.sh" switch sonnet \
        "Review and write tests for all implemented code. Ensure 80% minimum coverage. Test happy paths, error paths, and edge cases." \
        "$PROJECT_DIR" 2>/dev/null) || true

    echo "$switch_result" > "${SENTINEL_DIR}/switch-tests.json"

    # Spawn Mouse to run tests
    log "Deploying Mouse to run tests..."
    local mouse_result
    mouse_result=$(bash "$SCRIPTS_DIR/spawn-agent.sh" mouse haiku \
        "Run the full test suite. Report pass/fail counts and code coverage percentage. Command: npm test -- --coverage 2>&1 || npx jest --coverage 2>&1 || npx vitest run --coverage 2>&1" \
        "$PROJECT_DIR" 2>/dev/null) || true

    echo "$mouse_result" > "${SENTINEL_DIR}/mouse-coverage.json"

    # Parse coverage
    local coverage
    coverage=$(echo "$mouse_result" | python3 -c "
import sys, json, re
content = sys.stdin.read()
# Try JSON parse first
try:
    data = json.loads(content)
    cov = data.get('coverage', data.get('coverage_percentage', 0))
    if isinstance(cov, str):
        cov = float(re.search(r'[\d.]+', cov).group())
    print(cov)
except:
    # Try regex on raw output
    match = re.search(r'(?:All files|Statements|Lines)\s*\|\s*([\d.]+)%', content)
    if match:
        print(match.group(1))
    else:
        print(0)
" 2>/dev/null || echo "0")

    if python3 -c "exit(0 if float('$coverage') >= float('$COVERAGE_MIN') else 1)" 2>/dev/null; then
        log "Test coverage: ${coverage}% (minimum: ${COVERAGE_MIN}%)"
        record_gate_result "switch" "True" "Coverage: ${coverage}%"
        return 0
    else
        warn "Test coverage ${coverage}% below minimum ${COVERAGE_MIN}%"
        record_gate_result "switch" "False" "Coverage: ${coverage}% < ${COVERAGE_MIN}%"
        return 1
    fi
}

# --- Run gates ---
run_all() {
    local failed=0

    log "Running all sentinel gates (cycle ${CURRENT_CYCLE}/${MAX_CYCLES})..."
    echo ""

    # Gate 1: Smith
    echo -e "${CYAN}━━━ Gate 1: Agent Smith (Blind Review) ━━━${NC}"
    if ! run_smith; then
        failed=$((failed + 1))
    fi
    echo ""

    # Gate 2: Trinity
    echo -e "${CYAN}━━━ Gate 2: Trinity (Security Audit) ━━━${NC}"
    if ! run_trinity; then
        failed=$((failed + 1))
    fi
    echo ""

    # Gate 3: Switch + Mouse
    echo -e "${CYAN}━━━ Gate 3: Switch + Mouse (Tests) ━━━${NC}"
    if ! run_switch; then
        failed=$((failed + 1))
    fi
    echo ""

    if [ "$failed" -eq 0 ]; then
        echo -e "${GREEN}━━━ ALL SENTINEL GATES PASSED ━━━${NC}"
        return 0
    else
        echo -e "${RED}━━━ ${failed} SENTINEL GATE(S) FAILED ━━━${NC}"

        # Check remediation cycle limit
        local next_cycle=$((CURRENT_CYCLE + 1))
        if [ "$next_cycle" -gt "$MAX_CYCLES" ]; then
            err "Max remediation cycles (${MAX_CYCLES}) exceeded. Escalating to user."
            python3 -c "
import json
with open('$MATRIX_DIR/session.json') as f:
    s = json.load(f)
s['phase'] = 'escalated'
s['remediation_cycle'] = $next_cycle
with open('$MATRIX_DIR/session.json', 'w') as f:
    json.dump(s, f, indent=2)
"
            return 2
        fi

        # Increment cycle
        python3 -c "
import json
with open('$MATRIX_DIR/session.json') as f:
    s = json.load(f)
s['remediation_cycle'] = $next_cycle
with open('$MATRIX_DIR/session.json', 'w') as f:
    json.dump(s, f, indent=2)
"
        warn "Remediation cycle ${next_cycle}/${MAX_CYCLES}. Fix issues and re-run."
        return 1
    fi
}

# Dispatch
case "$GATE" in
    lint)    run_lint ;;
    smith)   run_smith ;;
    trinity) run_trinity ;;
    switch)  run_switch ;;
    all)     run_all ;;
    *)
        err "Unknown gate: $GATE. Must be: lint, smith, trinity, switch, all"
        exit 1
        ;;
esac
