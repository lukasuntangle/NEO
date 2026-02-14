#!/usr/bin/env python3
"""matrix-dashboard.py -- Full-screen live terminal dashboard for Neo Orchestrator.

A Matrix-style curses TUI that displays real-time agent activity, ticket progress,
blackboard events, costs, test results, and dependency graphs.  Think htop for a
multi-agent build system with green-on-black aesthetics.

Usage:
    python3 matrix-dashboard.py [--matrix-dir .matrix] [--refresh-rate 2]
"""
import argparse
import curses
import json
import os
import random
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RAIN_CHARS = list("01.:+*#@%&=~^ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘ")

AGENT_ROLES = {
    "neo": "orchestrate",
    "morpheus": "dispatch",
    "oracle": "analyze",
    "trinity": "security",
    "smith": "review",
    "dozer": "build",
    "tank": "build",
    "niobe": "build",
    "switch": "test",
    "mouse": "run",
    "keymaker": "utility",
    "trainman": "utility",
    "sati": "utility",
    "architect": "architect",
    "shannon": "analyst",
}

ALL_AGENTS = [
    "neo", "morpheus", "oracle", "dozer", "niobe", "tank",
    "trinity", "smith", "switch", "mouse", "shannon",
    "keymaker", "trainman", "sati", "architect",
]

PHASE_DISPLAY = {
    "red-pill": "RED PILL",
    "construct": "CONSTRUCT",
    "jacking-in": "JACKING IN",
    "bullet-time": "BULLET TIME",
    "sentinels": "SENTINELS",
    "zion": "ZION",
    "escalated": "ESCALATED",
    "unplugged": "UNPLUGGED",
    "reloaded": "RELOADED",
}

STATUS_ICON = {
    "completed": "✓",
    "in_progress": "●",
    "review": "◎",
    "pending": "○",
    "failed": "✗",
    "blocked": "#",
}

# ---------------------------------------------------------------------------
# Color pair IDs
# ---------------------------------------------------------------------------

C_GREEN = 1
C_DIM_GREEN = 2
C_BRIGHT_GREEN = 3
C_RED = 4
C_YELLOW = 5
C_CYAN = 6
C_WHITE = 7
C_GREEN_ON_GREEN = 8
C_MAGENTA = 9
C_RAIN = 10

# ---------------------------------------------------------------------------
# Data loading helpers -- all tolerant of missing files
# ---------------------------------------------------------------------------


def _load_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _tail_jsonl(path, n=15):
    """Return the last *n* JSON objects from a JSONL file."""
    try:
        with open(path) as fh:
            lines = fh.readlines()
    except OSError:
        return []
    entries = []
    for line in lines[-n:]:
        stripped = line.strip()
        if stripped:
            try:
                entries.append(json.loads(stripped))
            except json.JSONDecodeError:
                pass
    return entries


class DashboardState:
    """Container for all data consumed by the dashboard."""

    def __init__(self, matrix_dir):
        self.matrix_dir = Path(matrix_dir)
        self.session = {}
        self.ticket_index = {}
        self.tickets = {}
        self.costs = {}
        self.events = []
        self.gate_log = {}
        self.pipeline = {}
        self.last_load = 0.0

    def reload(self):
        md = self.matrix_dir
        self.session = _load_json(md / "session.json") or {}
        self.ticket_index = _load_json(md / "tickets" / "index.json") or {}
        self.costs = _load_json(md / "costs.json") or {}
        self.gate_log = _load_json(md / "sentinels" / "gate-log.json") or {}
        self.pipeline = _load_json(md / "construct" / "pipeline.json") or {}
        self.events = _tail_jsonl(md / "blackboard.jsonl", 15)

        # Load individual tickets
        self.tickets = {}
        for tid in self.ticket_index.get("tickets", []):
            t = _load_json(md / "tickets" / f"{tid}.json")
            if t:
                self.tickets[tid] = t

        self.last_load = time.time()

    # Derived helpers --------------------------------------------------------

    @property
    def phase(self):
        return self.session.get("phase", "unknown")

    @property
    def session_id(self):
        return self.session.get("session_id", "???")

    @property
    def status(self):
        return self.session.get("status", "unknown")

    @property
    def agents_spawned(self):
        return self.session.get("agents_spawned", 0)

    @property
    def total_tickets(self):
        return self.ticket_index.get("total", 0)

    @property
    def by_status(self):
        return self.ticket_index.get("by_status", {})

    @property
    def completed_tickets(self):
        return self.by_status.get("completed", 0)

    @property
    def total_cost(self):
        return self.costs.get("session_total", {}).get("cost_usd", 0.0)

    @property
    def budget(self):
        return self.costs.get("budget", None)

    @property
    def cost_by_model(self):
        return self.costs.get("by_model", {})

    def agent_ticket(self, agent_name):
        """Return the ticket ID an agent is currently working on, or None."""
        for tid, t in self.tickets.items():
            if t.get("agent") == agent_name and t.get("status") == "in_progress":
                return tid
        return None

    def agent_status(self, agent_name):
        """Return a display string for what the agent is doing."""
        tid = self.agent_ticket(agent_name)
        if tid:
            return tid.replace("TICKET-", "T-")
        role = AGENT_ROLES.get(agent_name, "idle")
        # Check if any ticket is assigned to this agent at all
        has_work = any(
            t.get("agent") == agent_name and t.get("status") in ("in_progress", "review")
            for t in self.tickets.values()
        )
        if has_work:
            return role
        return "idle"

    def latest_test_result(self):
        """Return the most recent TEST_RESULT event, or None."""
        for ev in reversed(self.events):
            if ev.get("event_type") == "TEST_RESULT":
                return ev
        return None


# ---------------------------------------------------------------------------
# Drawing utilities
# ---------------------------------------------------------------------------


def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    try:
        curses.init_pair(C_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(C_DIM_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(C_BRIGHT_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(C_RED, curses.COLOR_RED, -1)
        curses.init_pair(C_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(C_CYAN, curses.COLOR_CYAN, -1)
        curses.init_pair(C_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(C_GREEN_ON_GREEN, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(C_MAGENTA, curses.COLOR_MAGENTA, -1)
        curses.init_pair(C_RAIN, curses.COLOR_GREEN, -1)
    except curses.error:
        pass


def _cp(pair_id, bold=False):
    attr = curses.color_pair(pair_id)
    if bold:
        attr |= curses.A_BOLD
    return attr


def _dim(pair_id):
    return curses.color_pair(pair_id) | curses.A_DIM


def _safe_addstr(win, y, x, text, attr=0):
    """Write text clipped to window bounds -- never raises."""
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    available = max_x - x - 1
    if available <= 0:
        return
    try:
        win.addnstr(y, x, text, available, attr)
    except curses.error:
        pass


def _hline(win, y, x, ch, length, attr=0):
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y:
        return
    available = max_x - x - 1
    length = min(length, available)
    if length <= 0:
        return
    try:
        win.hline(y, x, ch, length, attr)
    except curses.error:
        pass


def _draw_box(win, y, x, h, w, attr):
    """Draw a box with single-line Unicode box drawing chars."""
    max_y, max_x = win.getmaxyx()
    if y >= max_y or x >= max_x:
        return
    _safe_addstr(win, y, x, "┌" + "─" * (w - 2) + "┐", attr)
    for row in range(1, h - 1):
        _safe_addstr(win, y + row, x, "│", attr)
        _safe_addstr(win, y + row, x + w - 1, "│", attr)
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", attr)


def _draw_double_box(win, y, x, h, w, attr):
    """Draw a box with double-line box drawing chars."""
    _safe_addstr(win, y, x, "╔" + "═" * (w - 2) + "╗", attr)
    for row in range(1, h - 1):
        _safe_addstr(win, y + row, x, "║", attr)
        _safe_addstr(win, y + row, x + w - 1, "║", attr)
    _safe_addstr(win, y + h - 1, x, "╚" + "═" * (w - 2) + "╝", attr)


def _progress_bar(filled, total, width):
    """Return a string like '████████░░░░░░░░░░░░'."""
    if total <= 0:
        return "░" * width
    ratio = min(filled / total, 1.0)
    done = int(width * ratio)
    return "█" * done + "░" * (width - done)


def _rain_line(length):
    return "".join(random.choice(RAIN_CHARS) for _ in range(length))


# ---------------------------------------------------------------------------
# Panel renderers
# ---------------------------------------------------------------------------


def _draw_header(win, state, frame_counter):
    """Matrix-style banner with digital rain and phase indicator."""
    max_y, max_x = win.getmaxyx()
    w = max_x - 2  # usable inner width
    if w < 20 or max_y < 5:
        return 0

    _draw_double_box(win, 0, 0, 4, max_x, _dim(C_GREEN))

    # Digital rain line (changes every frame)
    rain = _rain_line(min(w - 4, 40))
    _safe_addstr(win, 1, 2, " ▓▒░ ", _cp(C_GREEN, bold=True))
    _safe_addstr(win, 1, 7, "N E O   O R C H E S T R A T O R", _cp(C_GREEN, bold=True))
    _safe_addstr(win, 1, 40, " ░▒▓", _cp(C_GREEN, bold=True))

    phase_label = PHASE_DISPLAY.get(state.phase, state.phase.upper())
    phase_str = f"[Phase: {phase_label}]"
    right_x = max(max_x - len(phase_str) - 3, 50)
    _safe_addstr(win, 1, right_x, phase_str, _cp(C_CYAN, bold=True))

    # Second line: rain and session
    _safe_addstr(win, 2, 2, " ░▒▓█▓▒░ ", _dim(C_GREEN))
    _safe_addstr(win, 2, 12, "THE MATRIX DASHBOARD", _dim(C_GREEN))
    _safe_addstr(win, 2, 33, " ░▒▓█▓▒░", _dim(C_GREEN))

    sess_str = f"Session: {state.session_id[:16]}..."
    _safe_addstr(win, 2, right_x, sess_str, _dim(C_WHITE))

    # Separator
    _safe_addstr(win, 3, 0, "╠" + "═" * (max_x - 2) + "╣", _dim(C_GREEN))

    return 4  # rows consumed


def _draw_agents_panel(win, y, x, h, w, state):
    """Agents panel with activity indicators."""
    _safe_addstr(win, y, x, "┌─ AGENTS ", _dim(C_GREEN))
    _safe_addstr(win, y, x + 10, "─" * (w - 11) + "┐", _dim(C_GREEN))
    for row in range(1, h - 1):
        _safe_addstr(win, y + row, x, "│", _dim(C_GREEN))
        _safe_addstr(win, y + row, x + w - 1, "│", _dim(C_GREEN))
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", _dim(C_GREEN))

    row = y + 1
    visible_agents = ALL_AGENTS[:h - 2]  # fit inside box
    for agent in visible_agents:
        if row >= y + h - 1:
            break
        agent_st = state.agent_status(agent)
        active = agent_st != "idle"
        icon = "●" if active else "○"
        icon_color = _cp(C_GREEN, bold=True) if active else _dim(C_GREEN)
        name_color = _cp(C_WHITE, bold=True) if active else _dim(C_WHITE)

        _safe_addstr(win, row, x + 2, icon, icon_color)
        _safe_addstr(win, row, x + 4, f"{agent:<11}", name_color)
        status_text = f"[{agent_st}]"
        st_color = _cp(C_CYAN) if active else _dim(C_GREEN)
        _safe_addstr(win, row, x + 16, status_text[:w - 18], st_color)
        row += 1


def _draw_tickets_panel(win, y, x, h, w, state):
    """Tickets panel with progress bar and status counts."""
    _safe_addstr(win, y, x, "┌─ TICKETS ", _dim(C_GREEN))
    _safe_addstr(win, y, x + 11, "─" * (w - 12) + "┐", _dim(C_GREEN))
    for row in range(1, h - 1):
        _safe_addstr(win, y + row, x, "│", _dim(C_GREEN))
        _safe_addstr(win, y + row, x + w - 1, "│", _dim(C_GREEN))
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", _dim(C_GREEN))

    total = state.total_tickets
    done = state.completed_tickets
    pct = int(done / total * 100) if total > 0 else 0

    bar_w = min(w - 20, 20)
    bar = _progress_bar(done, total, bar_w)
    _safe_addstr(win, y + 1, x + 2, bar, _cp(C_GREEN, bold=True))
    _safe_addstr(win, y + 1, x + 2 + bar_w + 1, f"{done}/{total}  ({pct}%)", _cp(C_WHITE))

    # Status row
    by = state.by_status
    if h >= 5:
        _safe_addstr(win, y + 3, x + 2, "PEND", _dim(C_WHITE))
        _safe_addstr(win, y + 3, x + 8, "WORK", _cp(C_YELLOW))
        _safe_addstr(win, y + 3, x + 14, "REVW", _cp(C_MAGENTA))
        _safe_addstr(win, y + 3, x + 20, "DONE", _cp(C_GREEN))
        _safe_addstr(win, y + 3, x + 26, "FAIL", _cp(C_RED))

        _safe_addstr(win, y + 4, x + 3, str(by.get("pending", 0)), _cp(C_WHITE))
        _safe_addstr(win, y + 4, x + 9, str(by.get("in_progress", 0)), _cp(C_YELLOW, bold=True))
        _safe_addstr(win, y + 4, x + 15, str(by.get("review", 0)), _cp(C_MAGENTA, bold=True))
        _safe_addstr(win, y + 4, x + 21, str(by.get("completed", 0)), _cp(C_GREEN, bold=True))
        _safe_addstr(win, y + 4, x + 27, str(by.get("failed", 0)), _cp(C_RED, bold=True))


def _draw_cost_panel(win, y, x, h, w, state):
    """Cost panel with budget bar and per-model breakdown."""
    _safe_addstr(win, y, x, "┌─ COST ", _dim(C_GREEN))
    _safe_addstr(win, y, x + 8, "─" * (w - 9) + "┐", _dim(C_GREEN))
    for row in range(1, h - 1):
        _safe_addstr(win, y + row, x, "│", _dim(C_GREEN))
        _safe_addstr(win, y + row, x + w - 1, "│", _dim(C_GREEN))
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", _dim(C_GREEN))

    total = state.total_cost
    budget = state.budget

    if budget is not None and budget > 0:
        _safe_addstr(win, y + 1, x + 2, f"Total: ${total:.2f} / ${budget:.2f} budget", _cp(C_WHITE))
        bar_w = min(w - 10, 20)
        bar = _progress_bar(total, budget, bar_w)
        pct = min(total / budget * 100, 100)
        bar_color = _cp(C_GREEN) if pct < 60 else (_cp(C_YELLOW) if pct < 85 else _cp(C_RED, bold=True))
        _safe_addstr(win, y + 2, x + 2, bar, bar_color)
        _safe_addstr(win, y + 2, x + 2 + bar_w + 1, f"{pct:.1f}%", _cp(C_WHITE))
    else:
        _safe_addstr(win, y + 1, x + 2, f"Total: ${total:.2f}  (no budget set)", _cp(C_WHITE))
        _safe_addstr(win, y + 2, x + 2, "─" * (w - 6), _dim(C_GREEN))

    # Per-model breakdown
    if h >= 5:
        models = state.cost_by_model
        parts = []
        for m in ("opus", "sonnet", "haiku"):
            mc = models.get(m, {}).get("cost_usd", 0.0)
            parts.append(f"{m}: ${mc:.2f}")
        _safe_addstr(win, y + 3, x + 2, "  ".join(parts), _dim(C_WHITE))


def _draw_live_feed(win, y, x, h, w, state, scroll_offset):
    """Scrolling blackboard events."""
    _safe_addstr(win, y, x, "┌─ LIVE FEED ", _dim(C_GREEN))
    _safe_addstr(win, y, x + 13, "─" * (w - 14) + "┐", _dim(C_GREEN))
    for row in range(1, h - 1):
        _safe_addstr(win, y + row, x, "│", _dim(C_GREEN))
        _safe_addstr(win, y + row, x + w - 1, "│", _dim(C_GREEN))
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", _dim(C_GREEN))

    events = state.events
    if not events:
        _safe_addstr(win, y + 1, x + 2, "waiting for data...", _dim(C_GREEN))
        return

    avail_rows = h - 2
    start_idx = max(0, len(events) - avail_rows - scroll_offset)
    end_idx = start_idx + avail_rows
    visible = events[start_idx:end_idx]

    row = y + 1
    for ev in visible:
        if row >= y + h - 1:
            break
        ts = ev.get("timestamp", "??:??:??")
        # Show just the time portion
        if "T" in ts:
            ts = ts.split("T")[1][:8]
        agent = ev.get("agent", "???")[:8]
        etype = ev.get("event_type", "???")

        _safe_addstr(win, row, x + 2, ts, _dim(C_WHITE))
        _safe_addstr(win, row, x + 11, agent, _cp(C_CYAN))
        etype_color = _cp(C_GREEN)
        if etype in ("ISSUE_FOUND", "BLOCKER"):
            etype_color = _cp(C_RED, bold=True)
        elif etype == "TEST_RESULT":
            etype_color = _cp(C_YELLOW)
        elif etype == "GATE_RESULT":
            etype_color = _cp(C_MAGENTA)
        _safe_addstr(win, row, x + 20, etype, etype_color)
        row += 1

        # Second line: summary of data
        data = ev.get("data", {})
        summary = ""
        if isinstance(data, dict):
            if "message" in data:
                summary = str(data["message"])[:w - 8]
            elif "file" in data:
                summary = str(data["file"])[:w - 8]
            elif "passed" in data:
                p = data.get("passed", 0)
                f = data.get("failed", 0)
                summary = f"✓ {p} passed, ✗ {f} failed"
            elif "decision" in data:
                summary = str(data["decision"])[:w - 8]
            else:
                # Grab first key-value
                for k, v in data.items():
                    summary = f"{k}: {v}"
                    break
                summary = summary[:w - 8]
        elif isinstance(data, str):
            summary = data[:w - 8]

        if summary and row < y + h - 1:
            _safe_addstr(win, row, x + 4, summary, _dim(C_WHITE))
            row += 1


def _draw_tests_panel(win, y, x, h, w, state):
    """Tests panel with latest results and coverage."""
    _safe_addstr(win, y, x, "┌─ TESTS ", _dim(C_GREEN))
    _safe_addstr(win, y, x + 9, "─" * (w - 10) + "┐", _dim(C_GREEN))
    for row in range(1, h - 1):
        _safe_addstr(win, y + row, x, "│", _dim(C_GREEN))
        _safe_addstr(win, y + row, x + w - 1, "│", _dim(C_GREEN))
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", _dim(C_GREEN))

    test_ev = state.latest_test_result()
    gate_log = state.gate_log

    if not test_ev and not gate_log.get("gates"):
        _safe_addstr(win, y + 1, x + 2, "waiting for data...", _dim(C_GREEN))
        return

    row = y + 1

    if test_ev:
        ts = test_ev.get("timestamp", "")
        if "T" in ts:
            ts = ts.split("T")[1][:8]
        _safe_addstr(win, row, x + 2, f"Last run: {ts}", _dim(C_WHITE))
        row += 1

        data = test_ev.get("data", {})
        passed = data.get("passed", 0)
        failed = data.get("failed", 0)
        p_color = _cp(C_GREEN, bold=True)
        f_color = _cp(C_RED, bold=True) if failed > 0 else _dim(C_WHITE)
        _safe_addstr(win, row, x + 2, f"✓ {passed} passed", p_color)
        _safe_addstr(win, row, x + 16, f"✗ {failed} failed", f_color)
        row += 1

        coverage = data.get("coverage")
        if coverage is not None and row < y + h - 1:
            cov_bar_w = min(w - 24, 10)
            cov_bar = _progress_bar(coverage, 100, cov_bar_w)
            cov_color = _cp(C_GREEN) if coverage >= 80 else (_cp(C_YELLOW) if coverage >= 60 else _cp(C_RED))
            _safe_addstr(win, row, x + 2, f"Coverage: {coverage:.1f}% [", _cp(C_WHITE))
            _safe_addstr(win, row, x + 17, cov_bar, cov_color)
            _safe_addstr(win, row, x + 17 + cov_bar_w, "] 80%", _dim(C_WHITE))
            row += 1
    else:
        # Fall back to gate log info
        gates = gate_log.get("gates", [])
        pc = gate_log.get("pass_count", 0)
        fc = gate_log.get("fail_count", 0)
        _safe_addstr(win, row, x + 2, f"Gates: {pc} passed, {fc} failed", _cp(C_WHITE))
        row += 1
        for g in gates[-3:]:
            if row >= y + h - 1:
                break
            icon = "✓" if g.get("passed") else "✗"
            ic = _cp(C_GREEN) if g.get("passed") else _cp(C_RED)
            _safe_addstr(win, row, x + 2, icon, ic)
            _safe_addstr(win, row, x + 4, g.get("gate", "?")[:w - 8], _dim(C_WHITE))
            row += 1


def _draw_dep_graph(win, y, x, h, w, state):
    """Simplified dependency graph visualization."""
    _safe_addstr(win, y, x, "┌─ DEPENDENCY GRAPH ", _dim(C_GREEN))
    _safe_addstr(win, y, x + 20, "─" * (w - 21) + "┐", _dim(C_GREEN))
    for row in range(1, h - 1):
        _safe_addstr(win, y + row, x, "│", _dim(C_GREEN))
        _safe_addstr(win, y + row, x + w - 1, "│", _dim(C_GREEN))
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", _dim(C_GREEN))

    tickets = state.tickets
    index = state.ticket_index
    if not tickets:
        _safe_addstr(win, y + 1, x + 2, "waiting for data...", _dim(C_GREEN))
        return

    exec_order = index.get("execution_order", [])

    if exec_order:
        # Render by execution groups
        row = y + 1
        for gi, group in enumerate(exec_order):
            if row >= y + h - 1:
                break
            group_tickets = group.get("tickets", [])
            chain_parts = []
            for tid in group_tickets:
                short = tid.replace("TICKET-", "T-")
                t = tickets.get(tid, {})
                st = t.get("status", "pending")
                icon = STATUS_ICON.get(st, "?")
                chain_parts.append(f"[{icon}{short}]")
            chain = "──>".join(chain_parts)
            _safe_addstr(win, row, x + 3, chain[:w - 6], _cp(C_GREEN))
            row += 1
    else:
        # Build chains from dependency info
        # Find root tickets (no dependencies)
        roots = []
        for tid, t in tickets.items():
            deps = t.get("dependencies", [])
            if not deps:
                roots.append(tid)
        roots.sort()

        visited = set()
        row = y + 1

        def render_chain(tid, col):
            nonlocal row
            if tid in visited or row >= y + h - 1:
                return
            visited.add(tid)
            t = tickets.get(tid, {})
            short = tid.replace("TICKET-", "T-")
            st = t.get("status", "pending")
            icon = STATUS_ICON.get(st, "?")

            node = f"[{icon}{short}]"
            _safe_addstr(win, row, x + col, node, _cp(C_GREEN))

            blocks = t.get("blocks", [])
            if blocks:
                arrow_x = x + col + len(node)
                _safe_addstr(win, row, arrow_x, "──>", _dim(C_GREEN))
                next_col = col + len(node) + 3
                first = True
                for b in blocks:
                    if first:
                        render_chain(b, next_col)
                        first = False
                    else:
                        row += 1
                        if row < y + h - 1:
                            _safe_addstr(win, row, x + col + len(node), "└──>", _dim(C_GREEN))
                            render_chain(b, next_col + 1)
            else:
                row += 1

        for root in roots:
            if row >= y + h - 1:
                break
            render_chain(root, 3)


def _draw_footer(win, y, x, w, paused):
    """Keyboard shortcuts bar."""
    _safe_addstr(win, y, x, "╚" + "═" * (w - 2) + "╝", _dim(C_GREEN))
    keys = "[q] Quit  [p] Pause  [r] Refresh  [d] Detail  [c] Cost  [t] Tickets"
    ky = y - 1
    _safe_addstr(win, ky, x + 2, keys, _dim(C_WHITE))
    if paused:
        _safe_addstr(win, ky, x + w - 12, "  PAUSED  ", _cp(C_YELLOW, bold=True))


def _draw_rain_border(win, y, x, w, frame):
    """Draw a single line of matrix rain as a decorative border."""
    random.seed(frame)
    rain = _rain_line(w - 2)
    _safe_addstr(win, y, x + 1, rain, _dim(C_GREEN))


# ---------------------------------------------------------------------------
# Detail modes
# ---------------------------------------------------------------------------


def _draw_detail_tickets(win, y, x, h, w, state):
    """Expanded ticket detail view."""
    _safe_addstr(win, y, x, "┌─ TICKET DETAIL ", _dim(C_GREEN))
    _safe_addstr(win, y, x + 17, "─" * (w - 18) + "┐", _dim(C_GREEN))
    for row_i in range(1, h - 1):
        _safe_addstr(win, y + row_i, x, "│", _dim(C_GREEN))
        _safe_addstr(win, y + row_i, x + w - 1, "│", _dim(C_GREEN))
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", _dim(C_GREEN))

    row = y + 1
    for tid in sorted(state.tickets.keys()):
        if row >= y + h - 1:
            break
        t = state.tickets[tid]
        st = t.get("status", "pending")
        icon = STATUS_ICON.get(st, "?")
        agent = t.get("agent", "?")[:8]
        title = t.get("title", "")[:w - 36]
        short = tid.replace("TICKET-", "T-")

        st_colors = {
            "completed": _cp(C_GREEN, bold=True),
            "in_progress": _cp(C_YELLOW, bold=True),
            "review": _cp(C_MAGENTA, bold=True),
            "pending": _dim(C_WHITE),
            "failed": _cp(C_RED, bold=True),
            "blocked": _cp(C_RED),
        }
        sc = st_colors.get(st, _dim(C_WHITE))

        _safe_addstr(win, row, x + 2, f"{icon} {short}", sc)
        _safe_addstr(win, row, x + 12, f"[{agent}]", _cp(C_CYAN))
        _safe_addstr(win, row, x + 23, title, _cp(C_WHITE))
        _safe_addstr(win, row, x + 23 + len(title) + 1, st, sc)
        row += 1


def _draw_detail_cost(win, y, x, h, w, state):
    """Expanded cost detail view."""
    _safe_addstr(win, y, x, "┌─ COST DETAIL ", _dim(C_GREEN))
    _safe_addstr(win, y, x + 15, "─" * (w - 16) + "┐", _dim(C_GREEN))
    for row_i in range(1, h - 1):
        _safe_addstr(win, y + row_i, x, "│", _dim(C_GREEN))
        _safe_addstr(win, y + row_i, x + w - 1, "│", _dim(C_GREEN))
    _safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", _dim(C_GREEN))

    row = y + 1
    total = state.total_cost
    budget = state.budget

    _safe_addstr(win, row, x + 2, f"Session Total: ${total:.4f}", _cp(C_WHITE, bold=True))
    row += 1
    if budget:
        remaining = budget - total
        _safe_addstr(win, row, x + 2, f"Budget: ${budget:.2f}   Remaining: ${remaining:.4f}", _cp(C_WHITE))
    else:
        _safe_addstr(win, row, x + 2, "Budget: not set", _dim(C_WHITE))
    row += 2

    # By model
    _safe_addstr(win, row, x + 2, "By Model:", _cp(C_GREEN, bold=True))
    row += 1
    for m in ("opus", "sonnet", "haiku"):
        if row >= y + h - 1:
            break
        bucket = state.cost_by_model.get(m, {})
        cost = bucket.get("cost_usd", 0.0)
        spawns = bucket.get("spawns", 0)
        inp = bucket.get("input_tokens", 0)
        out = bucket.get("output_tokens", 0)
        _safe_addstr(win, row, x + 4, f"{m:<8} ${cost:.4f}  ({spawns} spawns, {inp} in / {out} out)", _cp(C_WHITE))
        row += 1

    row += 1
    # By agent (top 8)
    by_agent = state.costs.get("by_agent", {})
    if by_agent and row < y + h - 1:
        _safe_addstr(win, row, x + 2, "Top Agents:", _cp(C_GREEN, bold=True))
        row += 1
        sorted_agents = sorted(by_agent.items(), key=lambda kv: kv[1].get("cost_usd", 0), reverse=True)
        for aname, bucket in sorted_agents[:8]:
            if row >= y + h - 1:
                break
            cost = bucket.get("cost_usd", 0.0)
            spawns = bucket.get("spawns", 0)
            _safe_addstr(win, row, x + 4, f"{aname:<12} ${cost:.4f}  ({spawns} spawns)", _cp(C_WHITE))
            row += 1


# ---------------------------------------------------------------------------
# Main draw loop
# ---------------------------------------------------------------------------


def _draw_all(stdscr, state, frame, paused, scroll_offset, detail_mode, cost_view):
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    if max_y < 10 or max_x < 40:
        _safe_addstr(stdscr, 0, 0, "Terminal too small. Resize to 80x24+", _cp(C_RED, bold=True))
        stdscr.noutrefresh()
        curses.doupdate()
        return

    # --- Header (rows 0-3) ---
    header_h = _draw_header(stdscr, state, frame)
    cur_y = header_h

    # Check for detail mode overlays
    if detail_mode == "tickets":
        avail = max_y - cur_y - 2
        _draw_detail_tickets(stdscr, cur_y, 1, max(avail, 5), max_x - 2, state)
        _draw_footer(stdscr, max_y - 1, 0, max_x, paused)
        stdscr.noutrefresh()
        curses.doupdate()
        return

    if detail_mode == "cost":
        avail = max_y - cur_y - 2
        _draw_detail_cost(stdscr, cur_y, 1, max(avail, 5), max_x - 2, state)
        _draw_footer(stdscr, max_y - 1, 0, max_x, paused)
        stdscr.noutrefresh()
        curses.doupdate()
        return

    # --- Regular layout ---
    # Calculate column widths
    left_w = min(30, max_x // 3)
    right_w = max_x - left_w - 3  # gap
    right_x = left_w + 2

    # --- Left column: Agents panel ---
    agents_h = min(len(ALL_AGENTS) + 2, max_y - cur_y - 8)
    agents_h = max(agents_h, 5)
    if cur_y + agents_h < max_y:
        _draw_agents_panel(stdscr, cur_y, 1, agents_h, left_w, state)

    # --- Right column: Tickets + Cost + Tests ---
    # Tickets panel
    tickets_h = 6
    if cur_y + tickets_h < max_y and right_x + right_w <= max_x:
        _draw_tickets_panel(stdscr, cur_y, right_x, tickets_h, right_w, state)

    # Cost panel
    cost_y = cur_y + tickets_h + 1
    cost_h = 5
    if cost_y + cost_h < max_y and right_x + right_w <= max_x:
        _draw_cost_panel(stdscr, cost_y, right_x, cost_h, right_w, state)

    # Tests panel
    tests_y = cost_y + cost_h + 1
    tests_h = 5
    if tests_y + tests_h < max_y and right_x + right_w <= max_x:
        _draw_tests_panel(stdscr, tests_y, right_x, tests_h, right_w, state)

    # --- Live feed (below agents, spanning width) ---
    feed_y = cur_y + agents_h + 1
    feed_bottom = max_y - 8  # leave room for dep graph + footer
    feed_h = max(feed_bottom - feed_y, 4)
    feed_w = max_x - 2
    if feed_y + feed_h < max_y:
        _draw_live_feed(stdscr, feed_y, 1, feed_h, feed_w, state, scroll_offset)

    # --- Dependency graph (bottom) ---
    dep_y = feed_y + feed_h + 1
    dep_h = max(max_y - dep_y - 2, 4)
    dep_w = max_x - 2
    if dep_y + dep_h < max_y and dep_h >= 3:
        _draw_dep_graph(stdscr, dep_y, 1, dep_h, dep_w, state)

    # --- Footer ---
    _draw_footer(stdscr, max_y - 1, 0, max_x, paused)

    stdscr.noutrefresh()
    curses.doupdate()


# ---------------------------------------------------------------------------
# Curses main
# ---------------------------------------------------------------------------


def dashboard_main(stdscr, matrix_dir, refresh_rate):
    _init_colors()
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(200)  # getch timeout in ms

    state = DashboardState(matrix_dir)
    state.reload()

    frame = 0
    paused = False
    scroll_offset = 0
    detail_mode = None  # None, "tickets", "cost"
    last_refresh = time.time()

    while True:
        # --- Input handling ---
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key == ord("q") or key == ord("Q"):
            break
        elif key == ord("p") or key == ord("P"):
            paused = not paused
        elif key == ord("r") or key == ord("R"):
            state.reload()
            last_refresh = time.time()
        elif key == ord("d") or key == ord("D"):
            if detail_mode == "tickets":
                detail_mode = None
            else:
                detail_mode = "tickets"
        elif key == ord("c") or key == ord("C"):
            if detail_mode == "cost":
                detail_mode = None
            else:
                detail_mode = "cost"
        elif key == ord("t") or key == ord("T"):
            if detail_mode == "tickets":
                detail_mode = None
            else:
                detail_mode = "tickets"
        elif key == curses.KEY_UP:
            scroll_offset = min(scroll_offset + 1, max(len(state.events) - 3, 0))
        elif key == curses.KEY_DOWN:
            scroll_offset = max(scroll_offset - 1, 0)
        elif key == curses.KEY_RESIZE:
            stdscr.clear()
        elif key == 27:  # ESC
            detail_mode = None

        # --- Auto-refresh ---
        now = time.time()
        if not paused and now - last_refresh >= refresh_rate:
            state.reload()
            last_refresh = now

        # --- Draw ---
        try:
            _draw_all(stdscr, state, frame, paused, scroll_offset, detail_mode, 0)
        except curses.error:
            pass

        frame += 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Neo Orchestrator -- The Matrix Dashboard (live curses TUI)"
    )
    parser.add_argument(
        "--matrix-dir",
        default=".matrix",
        help="Path to .matrix directory (default: .matrix)",
    )
    parser.add_argument(
        "--refresh-rate",
        type=float,
        default=2.0,
        help="Auto-refresh interval in seconds (default: 2)",
    )
    args = parser.parse_args()

    matrix_dir = args.matrix_dir
    if not os.path.isdir(matrix_dir):
        print(f"Error: {matrix_dir} not found. Run init-matrix.sh first.")
        print(f"Usage: python3 matrix-dashboard.py [--matrix-dir .matrix]")
        raise SystemExit(1)

    curses.wrapper(lambda stdscr: dashboard_main(stdscr, matrix_dir, args.refresh_rate))


if __name__ == "__main__":
    main()
