#!/usr/bin/env bash
# status-report.sh — Display session status for Neo Orchestrator
# Usage: bash status-report.sh [project-dir]
set -euo pipefail

PROJECT_DIR="${1:-.}"
MATRIX_DIR="${PROJECT_DIR}/.matrix"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

if [ ! -d "$MATRIX_DIR" ]; then
    echo -e "${RED}No .matrix/ directory found. No active session.${NC}"
    exit 1
fi

# Load session
SESSION=$(cat "$MATRIX_DIR/session.json")

SESSION_ID=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
STATUS=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
PHASE=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['phase'])")
STARTED=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['started_at'])")
AGENTS=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agents_spawned', 0))")
REM_CYCLE=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin).get('remediation_cycle', 0))")
CHECKPOINTS=$(echo "$SESSION" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('checkpoints', [])))")

# Phase display names
declare -A PHASE_NAMES
PHASE_NAMES=(
    ["red-pill"]="Phase 1: RED PILL"
    ["construct"]="Phase 2: THE CONSTRUCT"
    ["jacking-in"]="Phase 3: JACKING IN"
    ["bullet-time"]="Phase 4: BULLET TIME"
    ["sentinels"]="Phase 5: SENTINELS"
    ["zion"]="Phase 6: ZION"
    ["escalated"]="ESCALATED TO USER"
)

PHASE_DISPLAY="${PHASE_NAMES[$PHASE]:-$PHASE}"

# Header
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}NEO ORCHESTRATOR — SESSION STATUS${NC}                   ${CYAN}║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  Session:  ${SESSION_ID:0:40}     ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Status:   ${STATUS}                                      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Phase:    ${PHASE_DISPLAY}                     ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Started:  ${STARTED}                    ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# Ticket stats
if [ -f "$MATRIX_DIR/tickets/index.json" ]; then
    echo -e "${BOLD}Tickets:${NC}"
    python3 -c "
import json
with open('$MATRIX_DIR/tickets/index.json') as f:
    idx = json.load(f)
total = idx.get('total', 0)
by_status = idx.get('by_status', {})
completed = by_status.get('completed', 0)
in_progress = by_status.get('in_progress', 0)
pending = by_status.get('pending', 0)
failed = by_status.get('failed', 0)
blocked = by_status.get('blocked', 0)

if total > 0:
    pct = int(completed / total * 100)
    bar_len = 30
    filled = int(bar_len * completed / total)
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f'  Progress: [{bar}] {pct}% ({completed}/{total})')
    print(f'  Pending: {pending}  In Progress: {in_progress}  Completed: {completed}  Failed: {failed}  Blocked: {blocked}')
else:
    print('  No tickets created yet.')
"
    echo ""
fi

# Reservations
if [ -f "$MATRIX_DIR/tickets/reservations.json" ]; then
    RES_COUNT=$(python3 -c "
import json
with open('$MATRIX_DIR/tickets/reservations.json') as f:
    print(len(json.load(f).get('reservations', {})))
")
    if [ "$RES_COUNT" -gt 0 ]; then
        echo -e "${BOLD}Active File Reservations:${NC} ${RES_COUNT}"
        python3 -c "
import json
with open('$MATRIX_DIR/tickets/reservations.json') as f:
    res = json.load(f)['reservations']
for f, info in res.items():
    print(f\"  {f} -> {info['agent']} ({info['ticket']})\")
"
        echo ""
    fi
fi

# Quality gates
if [ -f "$MATRIX_DIR/sentinels/gate-log.json" ]; then
    echo -e "${BOLD}Sentinel Gates:${NC}"
    python3 -c "
import json
with open('$MATRIX_DIR/sentinels/gate-log.json') as f:
    log = json.load(f)
gates = log.get('gates', [])
if gates:
    for g in gates[-6:]:
        icon = '✓' if g['passed'] else '✗'
        color = '' if g['passed'] else ''
        print(f\"  {icon} {g['gate']}: {g.get('details', 'N/A')} (cycle {g.get('cycle', 0)})\")
    print(f\"  Total: {log.get('pass_count', 0)} passed, {log.get('fail_count', 0)} failed\")
else:
    print('  No gates run yet.')
"
    echo ""
fi

# Summary stats
echo -e "${BOLD}Summary:${NC}"
echo "  Agents spawned:      ${AGENTS}"
echo "  Git checkpoints:     ${CHECKPOINTS}"
echo "  Remediation cycles:  ${REM_CYCLE}"

# Memory stats
if [ -d "$MATRIX_DIR/memory" ]; then
    STRAT_COUNT=$(python3 -c "
import json
from pathlib import Path
p = Path('$MATRIX_DIR/memory/procedural/strategies.json')
if p.exists():
    with open(p) as f:
        print(len(json.load(f).get('strategies', [])))
else:
    print(0)
" 2>/dev/null || echo 0)
    echo "  Learned strategies:  ${STRAT_COUNT}"
fi

echo ""
