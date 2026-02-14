#!/usr/bin/env python3
"""warm-handoff.py — Structured handoff system between agents in Neo Orchestrator.

When an agent finishes a ticket, it creates a handoff document capturing what
was built and why, so downstream agents get structured context instead of raw diffs.

Usage:
    python3 warm-handoff.py create <ticket-id> '<json-data>' [--matrix-dir .matrix]
    python3 warm-handoff.py get <ticket-id> [--matrix-dir .matrix]
    python3 warm-handoff.py upstream <ticket-id> [--matrix-dir .matrix]
    python3 warm-handoff.py context <ticket-id> [--matrix-dir .matrix]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_matrix_dir(override=None):
    """Find .matrix/ directory from override, env, or default."""
    matrix_dir = override or os.environ.get("MATRIX_DIR", ".matrix")
    if not os.path.isdir(matrix_dir):
        print(f"Error: {matrix_dir} not found. Run init-matrix.sh first.", file=sys.stderr)
        sys.exit(1)
    return Path(matrix_dir)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def handoffs_dir(matrix_dir):
    return matrix_dir / "tickets" / "handoffs"


# --- Core functions (importable) ---

def create_handoff(matrix_dir, ticket_id, handoff_data):
    """Create a handoff document for a completed ticket.

    handoff_data is a dict with: summary, decisions, gotchas, files_modified,
    interfaces_exposed, test_status, context_for_downstream.
    Agent and model are read from the ticket file if not provided.
    """
    matrix_dir = Path(matrix_dir)
    ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
    ticket = load_json(ticket_path)
    if not ticket:
        print(f"Error: {ticket_id} not found.", file=sys.stderr)
        sys.exit(1)

    handoff = {
        "ticket_id": ticket_id,
        "agent": handoff_data.get("agent", ticket.get("agent", "unknown")),
        "model": handoff_data.get("model", ticket.get("model", "sonnet")),
        "completed_at": handoff_data.get("completed_at", now_iso()),
        "summary": handoff_data.get("summary", ""),
        "decisions": handoff_data.get("decisions", []),
        "gotchas": handoff_data.get("gotchas", []),
        "files_modified": handoff_data.get("files_modified", []),
        "interfaces_exposed": handoff_data.get("interfaces_exposed", []),
        "test_status": handoff_data.get("test_status", {
            "tests_written": 0,
            "tests_passing": 0,
            "coverage": "0%",
        }),
        "context_for_downstream": handoff_data.get("context_for_downstream", ""),
    }

    path = handoffs_dir(matrix_dir) / f"{ticket_id}-handoff.json"
    save_json(path, handoff)
    print(json.dumps(handoff, indent=2))
    return handoff


def get_handoff(matrix_dir, ticket_id):
    """Get a handoff document for a ticket. Returns handoff dict or None."""
    matrix_dir = Path(matrix_dir)
    path = handoffs_dir(matrix_dir) / f"{ticket_id}-handoff.json"
    return load_json(path)


def get_upstream_handoffs(matrix_dir, ticket_id):
    """Get handoff documents from all dependency tickets.

    Reads the ticket to find its dependencies, then collects handoffs
    for each dependency that has one. Missing handoffs are skipped.
    """
    matrix_dir = Path(matrix_dir)
    ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
    ticket = load_json(ticket_path)
    if not ticket:
        print(f"Error: {ticket_id} not found.", file=sys.stderr)
        sys.exit(1)

    dependencies = ticket.get("dependencies", [])
    handoffs = []

    for dep_id in dependencies:
        handoff = get_handoff(matrix_dir, dep_id)
        if handoff:
            handoffs.append(handoff)

    return handoffs


def build_downstream_context(matrix_dir, ticket_id):
    """Build a markdown context string from all upstream handoffs.

    For a given ticket, reads its dependencies and compiles their handoff
    documents into a structured markdown string for downstream agent prompts.
    """
    matrix_dir = Path(matrix_dir)
    ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
    ticket = load_json(ticket_path)
    if not ticket:
        print(f"Error: {ticket_id} not found.", file=sys.stderr)
        sys.exit(1)

    handoffs = get_upstream_handoffs(matrix_dir, ticket_id)
    if not handoffs:
        return ""

    # Load dependency ticket titles for richer headings
    dep_titles = {}
    for dep_id in ticket.get("dependencies", []):
        dep_ticket = load_json(matrix_dir / "tickets" / f"{dep_id}.json")
        if dep_ticket:
            dep_titles[dep_id] = dep_ticket.get("title", "")

    sections = ["## Upstream Context\n"]

    for handoff in handoffs:
        tid = handoff["ticket_id"]
        agent = handoff.get("agent", "unknown")
        title = dep_titles.get(tid, "")
        heading = f"### From {tid} ({agent})"
        if title:
            heading += f": {title}"
        sections.append(heading)

        # Summary
        if handoff.get("summary"):
            sections.append(f"**Summary:** {handoff['summary']}")

        # Key decisions
        decisions = handoff.get("decisions", [])
        if decisions:
            decision_strs = [d.get("decision", "") for d in decisions if d.get("decision")]
            if decision_strs:
                sections.append(f"**Key Decisions:** {', '.join(decision_strs)}")

        # Gotchas
        gotchas = handoff.get("gotchas", [])
        if gotchas:
            gotcha_text = "; ".join(gotchas)
            sections.append(f"**Gotchas:** {gotcha_text}")

        # Interfaces
        interfaces = handoff.get("interfaces_exposed", [])
        if interfaces:
            sections.append("**Interfaces Available:**")
            for iface in interfaces:
                name = iface.get("name", "")
                file = iface.get("file", "")
                usage = iface.get("usage", "")
                line = f"- `{name}` from {file}"
                if usage:
                    line += f" — {usage}"
                sections.append(line)

        # Context for downstream
        if handoff.get("context_for_downstream"):
            sections.append(f"**For You:** {handoff['context_for_downstream']}")

        sections.append("")  # blank line between handoffs

    return "\n".join(sections)


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Neo Orchestrator Warm Handoff System")
    parser.add_argument("--matrix-dir", default=None, help="Path to .matrix directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create a handoff document")
    p_create.add_argument("ticket_id", help="Ticket ID (e.g. TICKET-001)")
    p_create.add_argument("json_data", help="JSON string with handoff data")

    # get
    p_get = subparsers.add_parser("get", help="Get a handoff document")
    p_get.add_argument("ticket_id", help="Ticket ID (e.g. TICKET-001)")

    # upstream
    p_upstream = subparsers.add_parser("upstream", help="Get handoffs from dependency tickets")
    p_upstream.add_argument("ticket_id", help="Ticket ID (e.g. TICKET-003)")

    # context
    p_context = subparsers.add_parser("context", help="Build full context string for downstream agent")
    p_context.add_argument("ticket_id", help="Ticket ID (e.g. TICKET-003)")

    args = parser.parse_args()
    matrix_dir = get_matrix_dir(args.matrix_dir)

    if args.command == "create":
        try:
            data = json.loads(args.json_data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON — {e}", file=sys.stderr)
            sys.exit(1)
        create_handoff(matrix_dir, args.ticket_id, data)

    elif args.command == "get":
        handoff = get_handoff(matrix_dir, args.ticket_id)
        if handoff:
            print(json.dumps(handoff, indent=2))
        else:
            print(f"No handoff found for {args.ticket_id}.", file=sys.stderr)
            sys.exit(1)

    elif args.command == "upstream":
        handoffs = get_upstream_handoffs(matrix_dir, args.ticket_id)
        print(json.dumps(handoffs, indent=2))

    elif args.command == "context":
        context = build_downstream_context(matrix_dir, args.ticket_id)
        if context:
            print(context)
        else:
            print("No upstream handoffs found.", file=sys.stderr)


if __name__ == "__main__":
    main()
