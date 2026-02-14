#!/usr/bin/env python3
"""blackboard.py -- Append-only shared state for Neo Orchestrator agents.

A JSONL-based blackboard (`.matrix/blackboard.jsonl`) that all agents read
from and write to.  Decisions, file changes, test results, issues, schema
updates and more are posted here so downstream agents have fresh context.

Usage:
    python3 blackboard.py post <agent> <event_type> '<json-data>' [--matrix-dir .matrix]
    python3 blackboard.py read [--since <ISO-ts>] [--agent <name>] [--type <event_type>] [--last <N>] [--matrix-dir .matrix]
    python3 blackboard.py latest <event_type> [--matrix-dir .matrix]
    python3 blackboard.py summary [--matrix-dir .matrix]
    python3 blackboard.py context <agent> [--matrix-dir .matrix]
    python3 blackboard.py clear [--matrix-dir .matrix]
"""
import argparse
import fcntl
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES = frozenset({
    "FILE_CHANGED",
    "DECISION_MADE",
    "ISSUE_FOUND",
    "TEST_RESULT",
    "SCHEMA_UPDATE",
    "BLOCKER",
    "HANDOFF",
    "COST_UPDATE",
    "GATE_RESULT",
    "AGENT_STATUS",
})

SECURITY_AGENTS = frozenset({"trinity", "shannon"})
IMPL_AGENTS = frozenset({"dozer", "niobe", "tank"})
TEST_AGENTS = frozenset({"switch", "mouse"})

CONTEXT_LIMIT = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bb_path(matrix_dir):
    return Path(matrix_dir) / "blackboard.jsonl"


def _archive_dir(matrix_dir):
    return Path(matrix_dir) / "blackboard_archive"


def _read_all(matrix_dir):
    """Read every entry from the blackboard JSONL file."""
    path = _bb_path(matrix_dir)
    if not path.exists():
        return []
    entries = []
    with open(path, "r") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                entries.append(json.loads(stripped))
    return entries


def _next_seq(matrix_dir):
    """Determine the next monotonically-increasing sequence number."""
    path = _bb_path(matrix_dir)
    if not path.exists() or path.stat().st_size == 0:
        return 1
    # Read last line efficiently
    with open(path, "rb") as fh:
        fh.seek(0, 2)
        pos = fh.tell()
        if pos == 0:
            return 1
        # Walk backwards to find the last newline before EOF
        while pos > 0:
            pos -= 1
            fh.seek(pos)
            if fh.read(1) == b"\n" and pos < fh.seek(0, 2) - 1:
                break
        if pos == 0:
            fh.seek(0)
        last_line = fh.readline().decode().strip()
    if not last_line:
        return 1
    return json.loads(last_line).get("seq", 0) + 1


# ---------------------------------------------------------------------------
# Core functions (importable API)
# ---------------------------------------------------------------------------

def post(matrix_dir, agent, event_type, data):
    """Append an entry to the blackboard. Returns the sequence number."""
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type '{event_type}'. Must be one of: {', '.join(sorted(VALID_EVENT_TYPES))}")

    path = _bb_path(matrix_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            seq = _next_seq(matrix_dir)
            entry = {
                "timestamp": _now_iso(),
                "agent": agent.lower(),
                "event_type": event_type,
                "data": data,
                "seq": seq,
            }
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")
            fh.flush()
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)

    return seq


def read(matrix_dir, since=None, agent=None, event_type=None, last=None):
    """Read entries with optional filters."""
    entries = _read_all(matrix_dir)

    if since is not None:
        entries = [e for e in entries if e["timestamp"] >= since]

    if agent is not None:
        agent_lower = agent.lower()
        entries = [e for e in entries if e["agent"] == agent_lower]

    if event_type is not None:
        entries = [e for e in entries if e["event_type"] == event_type]

    if last is not None:
        entries = entries[-last:]

    return entries


def latest(matrix_dir, event_type):
    """Return the most recent entry of a given event type, or None."""
    entries = _read_all(matrix_dir)
    for entry in reversed(entries):
        if entry["event_type"] == event_type:
            return entry
    return None


def summary(matrix_dir):
    """Return counts by event_type, active agents, and last activity time."""
    entries = _read_all(matrix_dir)
    by_type = {}
    agents = set()
    last_ts = None

    for entry in entries:
        et = entry["event_type"]
        by_type[et] = by_type.get(et, 0) + 1
        agents.add(entry["agent"])
        ts = entry["timestamp"]
        if last_ts is None or ts > last_ts:
            last_ts = ts

    return {
        "total_entries": len(entries),
        "by_event_type": by_type,
        "active_agents": sorted(agents),
        "last_activity": last_ts,
    }


def context_for_agent(matrix_dir, agent):
    """Build smart context for a specific agent.

    All agents see: DECISION_MADE, SCHEMA_UPDATE, BLOCKER
    Security agents additionally see: ISSUE_FOUND
    Implementation agents additionally see: FILE_CHANGED, TEST_RESULT
    Test agents additionally see: FILE_CHANGED, ISSUE_FOUND
    Results are capped at CONTEXT_LIMIT entries.
    """
    agent_lower = agent.lower()

    relevant_types = {"DECISION_MADE", "SCHEMA_UPDATE", "BLOCKER"}

    if agent_lower in SECURITY_AGENTS:
        relevant_types.add("ISSUE_FOUND")
    elif agent_lower in IMPL_AGENTS:
        relevant_types.add("FILE_CHANGED")
        relevant_types.add("TEST_RESULT")
    elif agent_lower in TEST_AGENTS:
        relevant_types.add("FILE_CHANGED")
        relevant_types.add("ISSUE_FOUND")

    entries = _read_all(matrix_dir)
    filtered = [e for e in entries if e["event_type"] in relevant_types]

    return filtered[-CONTEXT_LIMIT:]


def clear(matrix_dir):
    """Archive the current blackboard and start a fresh one."""
    path = _bb_path(matrix_dir)
    if not path.exists() or path.stat().st_size == 0:
        return {"archived": False, "reason": "blackboard is empty or missing"}

    archive = _archive_dir(matrix_dir)
    archive.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = archive / f"blackboard_{stamp}.jsonl"
    shutil.move(str(path), str(dest))

    # Touch a fresh empty file so subsequent reads work
    path.touch()

    return {"archived": True, "archive_path": str(dest)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_json_data(raw):
    """Parse a JSON string from the CLI, exiting on failure."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON data -- {exc}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Neo Orchestrator Blackboard -- append-only shared state",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- post --
    p_post = subparsers.add_parser("post", help="Post an event to the blackboard")
    p_post.add_argument("agent", help="Agent name (e.g. dozer, trinity)")
    p_post.add_argument("event_type", choices=sorted(VALID_EVENT_TYPES), help="Event type")
    p_post.add_argument("data", help="JSON object with event payload")
    p_post.add_argument("--matrix-dir", default=os.environ.get("MATRIX_DIR", ".matrix"))

    # -- read --
    p_read = subparsers.add_parser("read", help="Read entries with optional filters")
    p_read.add_argument("--since", help="ISO-8601 timestamp lower bound")
    p_read.add_argument("--agent", help="Filter by agent name")
    p_read.add_argument("--type", dest="event_type", help="Filter by event type")
    p_read.add_argument("--last", type=int, help="Return only the last N entries")
    p_read.add_argument("--matrix-dir", default=os.environ.get("MATRIX_DIR", ".matrix"))

    # -- latest --
    p_latest = subparsers.add_parser("latest", help="Get most recent entry of a type")
    p_latest.add_argument("event_type", choices=sorted(VALID_EVENT_TYPES), help="Event type")
    p_latest.add_argument("--matrix-dir", default=os.environ.get("MATRIX_DIR", ".matrix"))

    # -- summary --
    p_summary = subparsers.add_parser("summary", help="Show blackboard summary")
    p_summary.add_argument("--matrix-dir", default=os.environ.get("MATRIX_DIR", ".matrix"))

    # -- context --
    p_context = subparsers.add_parser("context", help="Get relevant context for an agent")
    p_context.add_argument("agent", help="Agent name")
    p_context.add_argument("--matrix-dir", default=os.environ.get("MATRIX_DIR", ".matrix"))

    # -- clear --
    p_clear = subparsers.add_parser("clear", help="Archive blackboard and start fresh")
    p_clear.add_argument("--matrix-dir", default=os.environ.get("MATRIX_DIR", ".matrix"))

    args = parser.parse_args()
    matrix_dir = args.matrix_dir

    if not os.path.isdir(matrix_dir):
        print(f"Error: {matrix_dir} not found. Run init-matrix.sh first.", file=sys.stderr)
        sys.exit(1)

    if args.command == "post":
        data = _parse_json_data(args.data)
        seq = post(matrix_dir, args.agent, args.event_type, data)
        print(json.dumps({"status": "ok", "seq": seq}))

    elif args.command == "read":
        entries = read(
            matrix_dir,
            since=args.since,
            agent=args.agent,
            event_type=args.event_type,
            last=args.last,
        )
        print(json.dumps(entries, indent=2))

    elif args.command == "latest":
        entry = latest(matrix_dir, args.event_type)
        print(json.dumps(entry, indent=2) if entry else "null")

    elif args.command == "summary":
        result = summary(matrix_dir)
        print(json.dumps(result, indent=2))

    elif args.command == "context":
        entries = context_for_agent(matrix_dir, args.agent)
        print(json.dumps(entries, indent=2))

    elif args.command == "clear":
        result = clear(matrix_dir)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
