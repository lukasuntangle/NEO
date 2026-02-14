#!/usr/bin/env bash
# status-report.sh — Rich visual dashboard for Neo Orchestrator sessions
# Usage: bash status-report.sh [project-dir]
set -euo pipefail

PROJECT_DIR="${1:-.}"
MATRIX_DIR="${PROJECT_DIR}/.matrix"

# Colors
GREEN='\033[0;32m'
BRIGHT_GREEN='\033[1;32m'
RED='\033[0;31m'
BRIGHT_RED='\033[1;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BRIGHT_CYAN='\033[1;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# Box-drawing characters
H_LINE='═'
V_LINE='║'
TL='╔'
TR='╗'
BL='╚'
BR='╝'
T_LEFT='╠'
T_RIGHT='╣'
T_DOWN='╦'
T_UP='╩'
CROSS='╬'

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

# Phase display names (compatible with bash 3.x on macOS)
PHASE_DISPLAY=$(python3 -c "
phases = {
    'red-pill': 'Phase 1: RED PILL',
    'construct': 'Phase 2: THE CONSTRUCT',
    'jacking-in': 'Phase 3: JACKING IN',
    'bullet-time': 'Phase 4: BULLET TIME',
    'sentinels': 'Phase 5: SENTINELS',
    'zion': 'Phase 6: ZION',
    'escalated': 'ESCALATED TO USER',
}
print(phases.get('$PHASE', '$PHASE'))
")

# ============================================================================
# MATRIX-STYLE HEADER with digital rain effect
# ============================================================================
echo ""
echo -e "${BRIGHT_GREEN}"
python3 -c "
import random
cols = 60
rain_chars = list('01.:+*#@%&=~^')
line1 = ''.join(random.choice(rain_chars) for _ in range(cols))
line2 = ''.join(random.choice(rain_chars) for _ in range(cols))
print(f'  {line1}')
print(f'  {line2}')
"
echo -e "${NC}"

echo -e "  ${BRIGHT_GREEN}${BOLD}    ___  __  ____  ____     __  __  ____  ____  ____  _  _${NC}"
echo -e "  ${BRIGHT_GREEN}${BOLD}   / __)(  )(  _ \\( ___)   (  \\/  )( ___)(_  _)(  _ \\(_)( )${NC}"
echo -e "  ${BRIGHT_GREEN}${BOLD}  ( (__  )(  )   / )__)     )    (  )__)   )(   )   / _)( X${NC}"
echo -e "  ${BRIGHT_GREEN}${BOLD}   \\___)(__)(__)\\)(____)   (_/\\/\\_)(____) (__) (_)\\_(___)(_)${NC}"
echo -e "  ${GREEN}${DIM}          N E O   O R C H E S T R A T O R${NC}"
echo ""

echo -e "${BRIGHT_GREEN}"
python3 -c "
import random
cols = 60
rain_chars = list('01.:+*#@%&=~^')
line = ''.join(random.choice(rain_chars) for _ in range(cols))
print(f'  {line}')
"
echo -e "${NC}"

# ============================================================================
# SESSION INFO BOX
# ============================================================================

# Status color
STATUS_COLOR="${GREEN}"
if [ "$STATUS" = "escalated" ] || [ "$STATUS" = "failed" ]; then
    STATUS_COLOR="${RED}"
elif [ "$STATUS" = "active" ]; then
    STATUS_COLOR="${BRIGHT_GREEN}"
fi

# Phase color
PHASE_COLOR="${CYAN}"
if [ "$PHASE" = "escalated" ]; then
    PHASE_COLOR="${RED}"
elif [ "$PHASE" = "zion" ]; then
    PHASE_COLOR="${GREEN}"
elif [ "$PHASE" = "bullet-time" ]; then
    PHASE_COLOR="${YELLOW}"
elif [ "$PHASE" = "sentinels" ]; then
    PHASE_COLOR="${MAGENTA}"
fi

# Calculate elapsed time
ELAPSED=$(python3 -c "
from datetime import datetime, timezone
try:
    started = datetime.fromisoformat('${STARTED}'.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    delta = now - started
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        print(f'{hours}h {minutes}m {seconds}s')
    elif minutes > 0:
        print(f'{minutes}m {seconds}s')
    else:
        print(f'{seconds}s')
except:
    print('N/A')
")

printf "  ${CYAN}${TL}"
printf "${H_LINE}%.0s" {1..58}
printf "${TR}${NC}\n"

printf "  ${CYAN}${V_LINE}${NC}  ${BRIGHT_GREEN}${BOLD}%-20s${NC} %-35s ${CYAN}${V_LINE}${NC}\n" "SESSION" "${SESSION_ID:0:35}"
printf "  ${CYAN}${T_LEFT}"
printf "${H_LINE}%.0s" {1..58}
printf "${T_RIGHT}${NC}\n"

printf "  ${CYAN}${V_LINE}${NC}  ${DIM}Status:${NC}    ${STATUS_COLOR}%-10s${NC}  ${DIM}Phase:${NC}  ${PHASE_COLOR}%-22s${NC} ${CYAN}${V_LINE}${NC}\n" "$STATUS" "$PHASE_DISPLAY"
printf "  ${CYAN}${V_LINE}${NC}  ${DIM}Started:${NC}   %-10s  ${DIM}Elapsed:${NC} %-22s ${CYAN}${V_LINE}${NC}\n" "${STARTED:0:10}" "$ELAPSED"
printf "  ${CYAN}${V_LINE}${NC}  ${DIM}Agents:${NC}    %-10s  ${DIM}Cycle:${NC}  %-22s ${CYAN}${V_LINE}${NC}\n" "$AGENTS" "${REM_CYCLE}/3"

printf "  ${CYAN}${BL}"
printf "${H_LINE}%.0s" {1..58}
printf "${BR}${NC}\n"
echo ""

# ============================================================================
# PROGRESS BAR
# ============================================================================
if [ -f "$MATRIX_DIR/tickets/index.json" ]; then
    python3 -c "
import json, sys

with open('$MATRIX_DIR/tickets/index.json') as f:
    idx = json.load(f)

total = idx.get('total', 0)
by_status = idx.get('by_status', {})
completed = by_status.get('completed', 0)
in_progress = by_status.get('in_progress', 0)
review = by_status.get('review', 0)
pending = by_status.get('pending', 0)
failed = by_status.get('failed', 0)
blocked = by_status.get('blocked', 0)

if total > 0:
    pct = int(completed / total * 100)
    bar_len = 40
    done_len = int(bar_len * completed / total)
    review_len = int(bar_len * review / total)
    progress_len = int(bar_len * in_progress / total)
    remaining = bar_len - done_len - review_len - progress_len

    # Build colored progress bar
    bar = ''
    bar += '\033[1;32m' + '\u2588' * done_len      # green = completed
    bar += '\033[1;35m' + '\u2588' * review_len     # magenta = review
    bar += '\033[1;33m' + '\u2588' * progress_len   # yellow = in progress
    bar += '\033[2m' + '\u2591' * remaining          # dim = remaining
    bar += '\033[0m'

    print(f'  \033[1mProgress\033[0m  [{bar}] {pct}%  ({completed}/{total} tickets)')
    print()
    # Status breakdown with colored indicators
    print(f'  \033[2m\u25cf\033[0m Pending: {pending}   '
          f'\033[1;33m\u25cf\033[0m Working: {in_progress}   '
          f'\033[1;35m\u25cf\033[0m Review: {review}   '
          f'\033[1;32m\u25cf\033[0m Done: {completed}   '
          f'\033[1;31m\u25cf\033[0m Failed: {failed}   '
          f'\033[0;31m\u25cf\033[0m Blocked: {blocked}')
else:
    print('  \033[2mNo tickets created yet.\033[0m')
"
    echo ""
fi

# ============================================================================
# ASCII KANBAN BOARD
# ============================================================================
if [ -f "$MATRIX_DIR/tickets/index.json" ]; then
    python3 -c "
import json, os
from pathlib import Path

matrix = Path('$MATRIX_DIR')
with open(matrix / 'tickets' / 'index.json') as f:
    idx = json.load(f)

total = idx.get('total', 0)
if total == 0:
    exit(0)

# Collect tickets by column
columns = {
    'PENDING': [],
    'WORKING': [],
    'REVIEW': [],
    'COMPLETE': [],
    'FAILED': [],
    'BLOCKED': [],
}

status_to_col = {
    'pending': 'PENDING',
    'in_progress': 'WORKING',
    'review': 'REVIEW',
    'completed': 'COMPLETE',
    'failed': 'FAILED',
    'blocked': 'BLOCKED',
}

for ticket_id in idx.get('tickets', []):
    ticket_path = matrix / 'tickets' / f'{ticket_id}.json'
    if not ticket_path.exists():
        continue
    with open(ticket_path) as f:
        ticket = json.load(f)
    col = status_to_col.get(ticket['status'], 'PENDING')
    short_id = ticket['id'].replace('TICKET-', 'T-')
    priority = ticket.get('priority', 'medium')
    agent = ticket.get('agent', '?')[:6]
    columns[col].append({
        'id': short_id,
        'priority': priority,
        'agent': agent,
        'title': ticket.get('title', '')[:14],
    })

# Determine which columns to show (skip empty FAILED/BLOCKED if nothing there)
visible = ['PENDING', 'WORKING', 'REVIEW', 'COMPLETE']
if columns['FAILED']:
    visible.append('FAILED')
if columns['BLOCKED']:
    visible.append('BLOCKED')

# Column width
COL_W = 16
GAP = '  '

# Colors for columns
col_colors = {
    'PENDING':  '\033[2m',        # dim
    'WORKING':  '\033[1;33m',     # yellow
    'REVIEW':   '\033[1;35m',     # magenta
    'COMPLETE': '\033[1;32m',     # green
    'FAILED':   '\033[1;31m',     # red
    'BLOCKED':  '\033[0;31m',     # dark red
}

# Priority symbols
pri_sym = {
    'critical': '\033[1;31m!\033[0m',
    'high':     '\033[1;33m\u25b2\033[0m',
    'medium':   '\033[0;36m\u25cf\033[0m',
    'low':      '\033[2m\u25bd\033[0m',
}

NC = '\033[0m'

print(f'  \033[1mKanban Board\033[0m')
print()

# Header row
header = '  '
for col in visible:
    cc = col_colors[col]
    label = col.center(COL_W - 2)
    header += f'\u250c\u2500{cc}{label}{NC}\u2500\u2510{GAP}'
print(header)

# Separator
sep = '  '
for col in visible:
    sep += f'\u251c' + '\u2500' * (COL_W - 2 + 2) + f'\u2524{GAP}'
print(sep)

# Calculate max rows
max_rows = max(len(columns[c]) for c in visible) if visible else 0
max_rows = max(max_rows, 1)  # at least 1 row

for row in range(max_rows):
    line = '  '
    for col in visible:
        items = columns[col]
        if row < len(items):
            item = items[row]
            p = pri_sym.get(item['priority'], ' ')
            # Ticket ID + agent
            cell = f\"{p} {item['id']} {item['agent']}\"
            # We need to account for ANSI codes in padding
            # Visible length of priority symbol is 1 char
            visible_len = 1 + 1 + len(item['id']) + 1 + len(item['agent'])
            pad = COL_W - visible_len
            if pad < 0:
                pad = 0
            line += f'\u2502 {cell}' + ' ' * pad + f'\u2502{GAP}'
        else:
            line += f'\u2502' + ' ' * COL_W + f'\u2502{GAP}'
    print(line)

# Bottom row
bottom = '  '
for col in visible:
    count = len(columns[col])
    cc = col_colors[col]
    count_str = f'({count})'
    pad_total = COL_W - len(count_str)
    left_pad = pad_total // 2
    right_pad = pad_total - left_pad
    bottom += f'\u2514' + '\u2500' * left_pad + f'{cc}{count_str}{NC}' + '\u2500' * right_pad + f'\u2518{GAP}'
print(bottom)
print()
"
fi

# ============================================================================
# DEPENDENCY GRAPH (ASCII)
# ============================================================================
if [ -f "$MATRIX_DIR/tickets/index.json" ]; then
    python3 -c "
import json, os
from pathlib import Path

matrix = Path('$MATRIX_DIR')
with open(matrix / 'tickets' / 'index.json') as f:
    idx = json.load(f)

total = idx.get('total', 0)
if total == 0:
    exit(0)

# Load all tickets
tickets = {}
for ticket_id in idx.get('tickets', []):
    ticket_path = matrix / 'tickets' / f'{ticket_id}.json'
    if not ticket_path.exists():
        continue
    with open(ticket_path) as f:
        tickets[ticket_id] = json.load(f)

# Only show graph if there are dependencies
has_deps = any(t.get('dependencies') or t.get('blocks') for t in tickets.values())
if not has_deps:
    exit(0)

# Color codes
status_colors = {
    'completed':   '\033[1;32m',  # bright green
    'in_progress': '\033[1;33m',  # yellow
    'review':      '\033[1;35m',  # magenta
    'pending':     '\033[0;37m',  # white
    'failed':      '\033[1;31m',  # red
    'blocked':     '\033[0;31m',  # dark red
}
NC = '\033[0m'
DIM = '\033[2m'
BOLD = '\033[1m'

# Status icons
status_icons = {
    'completed':   '\u2714',  # check
    'in_progress': '\u25b6',  # play
    'review':      '\u25c9',  # circle dot
    'pending':     '\u25cb',  # empty circle
    'failed':      '\u2718',  # cross
    'blocked':     '\u26d4',  # no entry
}

print(f'  {BOLD}Dependency Graph{NC}')
print()

# Build execution groups from index
exec_order = idx.get('execution_order', [])

if exec_order:
    # Render by execution groups
    for group_info in exec_order:
        group_num = group_info.get('group', '?')
        group_tickets = group_info.get('tickets', [])

        print(f'  {DIM}Group {group_num}:{NC}')
        for tid in group_tickets:
            if tid not in tickets:
                continue
            t = tickets[tid]
            sc = status_colors.get(t['status'], NC)
            icon = status_icons.get(t['status'], '?')
            short = tid.replace('TICKET-', 'T-')
            agent = t.get('agent', '?')[:8]

            # Build arrow line
            deps_str = ''
            if t.get('dependencies'):
                dep_shorts = [d.replace('TICKET-', 'T-') for d in t['dependencies']]
                deps_str = f' {DIM}<-- {', '.join(dep_shorts)}{NC}'

            blocks_str = ''
            if t.get('blocks'):
                blk_shorts = [b.replace('TICKET-', 'T-') for b in t['blocks']]
                blocks_str = f' {DIM}--> {', '.join(blk_shorts)}{NC}'

            title = t.get('title', '')[:30]
            print(f'    {sc}{icon} {short}{NC} [{agent}] {title}{deps_str}{blocks_str}')

        # Draw connector between groups
        if group_info != exec_order[-1]:
            print(f'    {DIM}\u2502{NC}')
            print(f'    {DIM}\u25bc{NC}')
        print()
else:
    # Fallback: show flat list with dependencies
    for tid in sorted(tickets.keys()):
        t = tickets[tid]
        sc = status_colors.get(t['status'], NC)
        icon = status_icons.get(t['status'], '?')
        short = tid.replace('TICKET-', 'T-')
        agent = t.get('agent', '?')[:8]

        deps_str = ''
        if t.get('dependencies'):
            dep_shorts = [d.replace('TICKET-', 'T-') for d in t['dependencies']]
            deps_str = f' {DIM}<-- {', '.join(dep_shorts)}{NC}'

        blocks_str = ''
        if t.get('blocks'):
            blk_shorts = [b.replace('TICKET-', 'T-') for b in t['blocks']]
            blocks_str = f' {DIM}--> {', '.join(blk_shorts)}{NC}'

        title = t.get('title', '')[:30]
        print(f'    {sc}{icon} {short}{NC} [{agent}] {title}{deps_str}{blocks_str}')
    print()

# Legend
print(f'  {DIM}Legend: {status_colors[\"completed\"]}\u2714 complete{NC}  '
      f'{status_colors[\"in_progress\"]}\u25b6 working{NC}  '
      f'{status_colors[\"review\"]}\u25c9 review{NC}  '
      f'{status_colors[\"pending\"]}\u25cb pending{NC}  '
      f'{status_colors[\"failed\"]}\u2718 failed{NC}  '
      f'{status_colors[\"blocked\"]}\u26d4 blocked{NC}')
print()
"
fi

# ============================================================================
# AGENT ACTIVITY SUMMARY
# ============================================================================
if [ -f "$MATRIX_DIR/tickets/index.json" ]; then
    python3 -c "
import json, os
from pathlib import Path

matrix = Path('$MATRIX_DIR')
with open(matrix / 'tickets' / 'index.json') as f:
    idx = json.load(f)

total = idx.get('total', 0)
if total == 0:
    exit(0)

# Collect per-agent stats
agent_stats = {}
for ticket_id in idx.get('tickets', []):
    ticket_path = matrix / 'tickets' / f'{ticket_id}.json'
    if not ticket_path.exists():
        continue
    with open(ticket_path) as f:
        ticket = json.load(f)
    agent = ticket.get('agent', 'unknown')
    if agent not in agent_stats:
        agent_stats[agent] = {'total': 0, 'completed': 0, 'in_progress': 0, 'failed': 0, 'pending': 0, 'review': 0, 'blocked': 0}
    agent_stats[agent]['total'] += 1
    status = ticket.get('status', 'pending')
    agent_stats[agent][status] = agent_stats[agent].get(status, 0) + 1

if not agent_stats:
    exit(0)

NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
RED = '\033[1;31m'
CYAN = '\033[0;36m'

# Agent role descriptions
agent_roles = {
    'neo': 'Orchestrator',
    'morpheus': 'Dispatcher',
    'oracle': 'Analyzer',
    'trinity': 'Security',
    'smith': 'Reviewer',
    'dozer': 'Builder',
    'tank': 'Builder',
    'niobe': 'Builder',
    'switch': 'Tester',
    'mouse': 'Runner',
    'keymaker': 'Utility',
    'trainman': 'Utility',
    'sati': 'Utility',
    'architect': 'Architect',
    'shannon': 'Analyst',
}

print(f'  {BOLD}Agent Activity{NC}')
print()
print(f'  {DIM}{\"Agent\":<12} {\"Role\":<12} {\"Total\":>5} {\"Done\":>5} {\"Work\":>5} {\"Fail\":>5} {\"Bar\":<20}{NC}')
print(f'  {DIM}' + '\u2500' * 65 + f'{NC}')

for agent in sorted(agent_stats.keys()):
    stats = agent_stats[agent]
    role = agent_roles.get(agent, 'Agent')
    t = stats['total']
    done = stats['completed']
    work = stats['in_progress'] + stats['review']
    fail = stats['failed']

    # Mini bar
    bar_len = 15
    if t > 0:
        done_part = int(bar_len * done / t)
        work_part = int(bar_len * work / t)
        fail_part = int(bar_len * fail / t)
        rest = bar_len - done_part - work_part - fail_part
        bar = f'{GREEN}' + '\u2588' * done_part + f'{YELLOW}' + '\u2588' * work_part + f'{RED}' + '\u2588' * fail_part + f'{DIM}' + '\u2591' * rest + f'{NC}'
    else:
        bar = f'{DIM}' + '\u2591' * bar_len + f'{NC}'

    # Color the agent name based on their completion
    agent_color = NC
    if t > 0:
        if done == t:
            agent_color = GREEN
        elif fail > 0:
            agent_color = RED
        elif work > 0:
            agent_color = YELLOW

    print(f'  {agent_color}{agent:<12}{NC} {DIM}{role:<12}{NC} {t:>5} {GREEN}{done:>5}{NC} {YELLOW}{work:>5}{NC} {RED}{fail:>5}{NC}  {bar}')

print()
"
fi

# ============================================================================
# SPRINT VELOCITY (across sessions)
# ============================================================================
python3 -c "
import json, os
from pathlib import Path

matrix = Path('$MATRIX_DIR')
project = Path('$PROJECT_DIR')

# Look for archived sessions
archives = sorted(project.glob('.matrix_archive_*'))
sessions_data = []

# Load archived session data
for archive in archives:
    session_file = archive / 'session.json'
    index_file = archive / 'tickets' / 'index.json'
    if session_file.exists() and index_file.exists():
        try:
            with open(session_file) as f:
                sess = json.load(f)
            with open(index_file) as f:
                idx = json.load(f)
            completed = idx.get('by_status', {}).get('completed', 0)
            total = idx.get('total', 0)
            sessions_data.append({
                'id': sess.get('session_id', '?')[:15],
                'started': sess.get('started_at', '?')[:10],
                'completed': completed,
                'total': total,
                'agents': sess.get('agents_spawned', 0),
                'status': sess.get('status', '?'),
            })
        except (json.JSONDecodeError, KeyError):
            pass

# Add current session
session_file = matrix / 'session.json'
index_file = matrix / 'tickets' / 'index.json'
if session_file.exists() and index_file.exists():
    try:
        with open(session_file) as f:
            sess = json.load(f)
        with open(index_file) as f:
            idx = json.load(f)
        completed = idx.get('by_status', {}).get('completed', 0)
        total = idx.get('total', 0)
        sessions_data.append({
            'id': sess.get('session_id', '?')[:15],
            'started': sess.get('started_at', '?')[:10],
            'completed': completed,
            'total': total,
            'agents': sess.get('agents_spawned', 0),
            'status': 'current',
        })
    except (json.JSONDecodeError, KeyError):
        pass

if len(sessions_data) < 2:
    exit(0)

NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
BRIGHT_GREEN = '\033[1;32m'

print(f'  {BOLD}Sprint Velocity{NC}  ({len(sessions_data)} sessions)')
print()

max_completed = max(s['completed'] for s in sessions_data) if sessions_data else 1
if max_completed == 0:
    max_completed = 1
bar_max = 30

for i, s in enumerate(sessions_data):
    is_current = s['status'] == 'current'
    label = f\"{s['started']}\"
    bar_len = int(bar_max * s['completed'] / max_completed)

    marker = f'{BRIGHT_GREEN}\u25b8 ' if is_current else '  '
    bar_color = BRIGHT_GREEN if is_current else GREEN
    bar = f'{bar_color}' + '\u2588' * bar_len + f'{DIM}' + '\u2591' * (bar_max - bar_len) + f'{NC}'

    print(f'  {marker}{DIM}{label}{NC} {bar} {s[\"completed\"]}/{s[\"total\"]} tickets  ({s[\"agents\"]} agents)')

# Average velocity
avg = sum(s['completed'] for s in sessions_data) / len(sessions_data)
print()
print(f'  {DIM}Average velocity: {avg:.1f} tickets/session{NC}')
print()
" 2>/dev/null || true

# ============================================================================
# FILE RESERVATIONS
# ============================================================================
if [ -f "$MATRIX_DIR/tickets/reservations.json" ]; then
    RES_COUNT=$(python3 -c "
import json
with open('$MATRIX_DIR/tickets/reservations.json') as f:
    print(len(json.load(f).get('reservations', {})))
")
    if [ "$RES_COUNT" -gt 0 ]; then
        echo -e "  ${BOLD}File Reservations${NC}  (${RES_COUNT} active)"
        echo ""
        python3 -c "
import json

NC = '\033[0m'
DIM = '\033[2m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'

with open('$MATRIX_DIR/tickets/reservations.json') as f:
    res = json.load(f)['reservations']
for filepath, info in res.items():
    agent = info.get('agent', '?')
    ticket = info.get('ticket', '?').replace('TICKET-', 'T-')
    print(f'    {YELLOW}\U0001f512{NC} {filepath}  {DIM}\u2192 {agent} ({ticket}){NC}')
"
        echo ""
    fi
fi

# ============================================================================
# QUALITY GATES
# ============================================================================
if [ -f "$MATRIX_DIR/sentinels/gate-log.json" ]; then
    python3 -c "
import json

NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
GREEN = '\033[1;32m'
RED = '\033[1;31m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'

with open('$MATRIX_DIR/sentinels/gate-log.json') as f:
    log = json.load(f)

gates = log.get('gates', [])
pass_count = log.get('pass_count', 0)
fail_count = log.get('fail_count', 0)

if not gates:
    print(f'  {BOLD}Sentinel Gates{NC}  {DIM}No gates run yet.{NC}')
    print()
    exit(0)

total_gates = pass_count + fail_count
pass_pct = int(pass_count / total_gates * 100) if total_gates > 0 else 0

print(f'  {BOLD}Sentinel Gates{NC}  {GREEN}{pass_count} passed{NC}  {RED}{fail_count} failed{NC}  ({pass_pct}% pass rate)')
print()

# Show last 8 gates
for g in gates[-8:]:
    passed = g.get('passed', False)
    icon = f'{GREEN}\u2714{NC}' if passed else f'{RED}\u2718{NC}'
    gate_name = g.get('gate', '?')
    details = g.get('details', 'N/A')[:40]
    cycle = g.get('cycle', 0)

    # Gate type color
    gate_colors = {
        'smith': YELLOW,
        'trinity': CYAN,
        'switch': '\033[1;35m',
        'lint': DIM,
    }
    gc = gate_colors.get(gate_name, NC)

    print(f'    {icon}  {gc}{gate_name:<10}{NC} {details}  {DIM}(cycle {cycle}){NC}')

print()
"
fi

# ============================================================================
# SUMMARY STATS TABLE
# ============================================================================
echo -e "  ${BOLD}Summary${NC}"
echo ""

# Calculate memory stats
STRAT_COUNT=0
EPISODIC_COUNT=0
SEMANTIC_KEYS=0
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

    EPISODIC_COUNT=$(python3 -c "
import json
from pathlib import Path
ep_dir = Path('$MATRIX_DIR/memory/episodic')
total = 0
if ep_dir.exists():
    for f in ep_dir.glob('session_*.json'):
        with open(f) as fh:
            data = json.load(fh)
            total += len(data.get('entries', []))
print(total)
" 2>/dev/null || echo 0)

    SEMANTIC_KEYS=$(python3 -c "
import json
from pathlib import Path
p = Path('$MATRIX_DIR/memory/semantic/project-knowledge.json')
if p.exists():
    with open(p) as f:
        data = json.load(f)
        count = 0
        for k, v in data.items():
            if v and k != 'last_updated':
                if isinstance(v, list):
                    count += len(v)
                elif isinstance(v, dict):
                    count += len(v)
                else:
                    count += 1
        print(count)
else:
    print(0)
" 2>/dev/null || echo 0)
fi

# Log file count
LOG_COUNT=0
if [ -d "$MATRIX_DIR/logs" ]; then
    LOG_COUNT=$(ls "$MATRIX_DIR/logs/" 2>/dev/null | wc -l | tr -d ' ')
fi

printf "    ${DIM}%-24s${NC} %-8s     ${DIM}%-24s${NC} %-8s\n" \
    "Agents spawned:" "$AGENTS" \
    "Git checkpoints:" "$CHECKPOINTS"
printf "    ${DIM}%-24s${NC} %-8s     ${DIM}%-24s${NC} %-8s\n" \
    "Remediation cycles:" "$REM_CYCLE" \
    "Log files:" "$LOG_COUNT"
printf "    ${DIM}%-24s${NC} %-8s     ${DIM}%-24s${NC} %-8s\n" \
    "Learned strategies:" "$STRAT_COUNT" \
    "Episodic entries:" "$EPISODIC_COUNT"
printf "    ${DIM}%-24s${NC} %-8s\n" \
    "Semantic facts:" "$SEMANTIC_KEYS"
echo ""

# ============================================================================
# EXECUTION ORDER TIMELINE
# ============================================================================
if [ -f "$MATRIX_DIR/tickets/index.json" ]; then
    python3 -c "
import json
from pathlib import Path

matrix = Path('$MATRIX_DIR')
with open(matrix / 'tickets' / 'index.json') as f:
    idx = json.load(f)

exec_order = idx.get('execution_order', [])
if not exec_order:
    exit(0)

NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
RED = '\033[1;31m'
MAGENTA = '\033[1;35m'

status_colors = {
    'completed':   GREEN,
    'in_progress': YELLOW,
    'review':      MAGENTA,
    'pending':     DIM,
    'failed':      RED,
    'blocked':     RED,
}

print(f'  {BOLD}Execution Timeline{NC}')
print()

for i, group in enumerate(exec_order):
    group_num = group.get('group', i + 1)
    group_tickets = group.get('tickets', [])

    # Check group completion
    all_done = True
    any_active = False
    for tid in group_tickets:
        tp = matrix / 'tickets' / f'{tid}.json'
        if tp.exists():
            with open(tp) as f:
                t = json.load(f)
            if t['status'] != 'completed':
                all_done = False
            if t['status'] in ('in_progress', 'review'):
                any_active = True

    # Group indicator
    if all_done:
        indicator = f'{GREEN}\u25c9{NC}'
        group_label = f'{GREEN}Group {group_num}{NC}'
    elif any_active:
        indicator = f'{YELLOW}\u25c9{NC}'
        group_label = f'{YELLOW}Group {group_num}{NC}'
    else:
        indicator = f'{DIM}\u25cb{NC}'
        group_label = f'{DIM}Group {group_num}{NC}'

    # Ticket badges
    badges = []
    for tid in group_tickets:
        short = tid.replace('TICKET-', 'T-')
        tp = matrix / 'tickets' / f'{tid}.json'
        if tp.exists():
            with open(tp) as f:
                t = json.load(f)
            sc = status_colors.get(t['status'], DIM)
            badges.append(f'{sc}[{short}]{NC}')
        else:
            badges.append(f'{DIM}[{short}]{NC}')

    connector = f'  {DIM}\u2502{NC}' if i < len(exec_order) - 1 else '   '
    print(f'    {indicator} {group_label}: {\" \".join(badges)}')
    if i < len(exec_order) - 1:
        print(f'    {DIM}\u2502{NC}')

print()
" 2>/dev/null || true
fi

# ============================================================================
# FOOTER
# ============================================================================
echo -e "${BRIGHT_GREEN}"
python3 -c "
import random
cols = 60
rain_chars = list('01.:+*#@%&=~^')
line = ''.join(random.choice(rain_chars) for _ in range(cols))
print(f'  {line}')
"
echo -e "${NC}"
echo -e "  ${DIM}Generated at $(date -u +%Y-%m-%dT%H:%M:%SZ) | Neo Orchestrator v1.0${NC}"
echo ""
