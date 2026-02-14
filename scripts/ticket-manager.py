#!/usr/bin/env python3
"""ticket-manager.py — Ticket CRUD + file reservations for Neo Orchestrator.

Usage:
    python3 ticket-manager.py create <title> <description> <agent> [--priority high] [--deps TICKET-001,TICKET-002] [--files src/a.ts,src/b.ts]
    python3 ticket-manager.py create-from-graph <task-graph.json>
    python3 ticket-manager.py update <ticket-id> --status <status> [--agent <agent>]
    python3 ticket-manager.py get <ticket-id>
    python3 ticket-manager.py list [--status pending] [--agent dozer]
    python3 ticket-manager.py next [--agent dozer]
    python3 ticket-manager.py reserve <ticket-id> <agent>
    python3 ticket-manager.py release <ticket-id>
    python3 ticket-manager.py check-reservation <file-path>
    python3 ticket-manager.py graph
    python3 ticket-manager.py stats
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_matrix_dir():
    """Find .matrix/ directory from current or specified path."""
    matrix_dir = os.environ.get("MATRIX_DIR", ".matrix")
    if not os.path.isdir(matrix_dir):
        print(f"Error: {matrix_dir} not found. Run init-matrix.sh first.", file=sys.stderr)
        sys.exit(1)
    return Path(matrix_dir)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


# --- Index operations ---

def load_index(matrix_dir):
    return load_json(matrix_dir / "tickets" / "index.json")


def save_index(matrix_dir, index):
    index["last_updated"] = now_iso()
    return save_json(matrix_dir / "tickets" / "index.json", index)


def recount_statuses(matrix_dir, index):
    """Recount ticket statuses from actual ticket files."""
    counts = {"pending": 0, "in_progress": 0, "review": 0, "completed": 0, "failed": 0, "blocked": 0}
    for ticket_id in index["tickets"]:
        ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
        if ticket_path.exists():
            ticket = load_json(ticket_path)
            status = ticket.get("status", "pending")
            counts[status] = counts.get(status, 0) + 1
    index["by_status"] = counts
    return index


# --- Ticket operations ---

def create_ticket(matrix_dir, title, description, agent, priority="medium",
                  dependencies=None, files=None, acceptance_criteria=None, model=None):
    """Create a new ticket."""
    index = load_index(matrix_dir)
    ticket_num = index["next_id"]
    ticket_id = f"TICKET-{ticket_num:03d}"

    # Determine model from config if not specified
    if model is None:
        config = load_json(matrix_dir / "config.json")
        model = config.get("models", {}).get(agent, "sonnet")

    # Calculate blocked_by from dependencies
    blocked_by = []
    if dependencies:
        for dep_id in dependencies:
            dep_path = matrix_dir / "tickets" / f"{dep_id}.json"
            if dep_path.exists():
                dep = load_json(dep_path)
                if dep["status"] != "completed":
                    blocked_by.append(dep_id)

    ticket = {
        "id": ticket_id,
        "title": title,
        "description": description,
        "status": "blocked" if blocked_by else "pending",
        "priority": priority,
        "agent": agent,
        "model": model,
        "dependencies": dependencies or [],
        "blocked_by": blocked_by,
        "blocks": [],
        "files": files or [],
        "acceptance_criteria": acceptance_criteria or [],
        "rarv": {
            "research": None,
            "analyze": None,
            "reflect": None,
            "verify": None,
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "completed_at": None,
        "git_checkpoint": None,
    }

    # Save ticket
    save_json(matrix_dir / "tickets" / f"{ticket_id}.json", ticket)

    # Update blocks on dependencies
    if dependencies:
        for dep_id in dependencies:
            dep_path = matrix_dir / "tickets" / f"{dep_id}.json"
            if dep_path.exists():
                dep = load_json(dep_path)
                if ticket_id not in dep.get("blocks", []):
                    dep["blocks"] = [*dep.get("blocks", []), ticket_id]
                    save_json(dep_path, dep)

    # Update index
    index["next_id"] = ticket_num + 1
    index["total"] = index.get("total", 0) + 1
    index["tickets"] = [*index.get("tickets", []), ticket_id]
    index = recount_statuses(matrix_dir, index)
    save_index(matrix_dir, index)

    print(json.dumps(ticket, indent=2))
    return ticket


def create_from_graph(matrix_dir, graph_path):
    """Create tickets from a task graph JSON file."""
    graph = load_json(graph_path)
    tasks = graph.get("tasks", [])
    created = []

    for task in tasks:
        ticket = create_ticket(
            matrix_dir,
            title=task["title"],
            description=task.get("description", ""),
            agent=task.get("agent", "dozer"),
            priority=task.get("priority", "medium"),
            dependencies=task.get("dependencies", []),
            files=task.get("files", []),
            acceptance_criteria=task.get("acceptance_criteria", []),
            model=task.get("model"),
        )
        created.append(ticket["id"])

    print(f"\nCreated {len(created)} tickets: {', '.join(created)}", file=sys.stderr)
    return created


def update_ticket(matrix_dir, ticket_id, **kwargs):
    """Update a ticket's fields."""
    ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
    if not ticket_path.exists():
        print(f"Error: {ticket_id} not found.", file=sys.stderr)
        sys.exit(1)

    ticket = load_json(ticket_path)
    old_status = ticket["status"]

    for key, value in kwargs.items():
        if value is not None:
            ticket[key] = value

    ticket["updated_at"] = now_iso()

    # Handle status transitions
    new_status = ticket["status"]
    if new_status == "completed" and old_status != "completed":
        ticket["completed_at"] = now_iso()
        # Unblock dependent tickets
        for blocked_id in ticket.get("blocks", []):
            blocked_path = matrix_dir / "tickets" / f"{blocked_id}.json"
            if blocked_path.exists():
                blocked = load_json(blocked_path)
                blocked["blocked_by"] = [b for b in blocked.get("blocked_by", []) if b != ticket_id]
                if not blocked["blocked_by"] and blocked["status"] == "blocked":
                    blocked["status"] = "pending"
                blocked["updated_at"] = now_iso()
                save_json(blocked_path, blocked)

    save_json(ticket_path, ticket)

    # Recount statuses
    index = load_index(matrix_dir)
    index = recount_statuses(matrix_dir, index)
    save_index(matrix_dir, index)

    print(json.dumps(ticket, indent=2))
    return ticket


def get_ticket(matrix_dir, ticket_id):
    """Get a single ticket."""
    ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
    if not ticket_path.exists():
        print(f"Error: {ticket_id} not found.", file=sys.stderr)
        sys.exit(1)
    ticket = load_json(ticket_path)
    print(json.dumps(ticket, indent=2))
    return ticket


def list_tickets(matrix_dir, status=None, agent=None):
    """List tickets with optional filters."""
    index = load_index(matrix_dir)
    results = []
    for ticket_id in index["tickets"]:
        ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
        if not ticket_path.exists():
            continue
        ticket = load_json(ticket_path)
        if status and ticket["status"] != status:
            continue
        if agent and ticket["agent"] != agent:
            continue
        results.append({
            "id": ticket["id"],
            "title": ticket["title"],
            "status": ticket["status"],
            "agent": ticket["agent"],
            "priority": ticket["priority"],
            "blocked_by": ticket.get("blocked_by", []),
        })
    print(json.dumps(results, indent=2))
    return results


def next_ticket(matrix_dir, agent=None):
    """Get the next available ticket (pending, not blocked, highest priority)."""
    index = load_index(matrix_dir)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    candidates = []

    for ticket_id in index["tickets"]:
        ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
        if not ticket_path.exists():
            continue
        ticket = load_json(ticket_path)
        if ticket["status"] != "pending":
            continue
        if ticket.get("blocked_by"):
            continue
        if agent and ticket["agent"] != agent:
            continue
        candidates.append(ticket)

    if not candidates:
        print(json.dumps(None))
        return None

    candidates.sort(key=lambda t: priority_order.get(t["priority"], 2))
    best = candidates[0]
    print(json.dumps(best, indent=2))
    return best


# --- Reservation operations ---

def load_reservations(matrix_dir):
    return load_json(matrix_dir / "tickets" / "reservations.json")


def save_reservations(matrix_dir, reservations):
    return save_json(matrix_dir / "tickets" / "reservations.json", reservations)


def reserve_files(matrix_dir, ticket_id, agent):
    """Reserve files for a ticket. Fails if any file is already reserved."""
    ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
    if not ticket_path.exists():
        print(f"Error: {ticket_id} not found.", file=sys.stderr)
        sys.exit(1)

    ticket = load_json(ticket_path)
    files = ticket.get("files", [])
    if not files:
        print(json.dumps({"status": "ok", "message": "No files to reserve"}))
        return True

    reservations = load_reservations(matrix_dir)
    conflicts = []

    for f in files:
        existing = reservations["reservations"].get(f)
        if existing and existing["ticket"] != ticket_id:
            conflicts.append({
                "file": f,
                "held_by": existing["ticket"],
                "agent": existing["agent"],
            })

    if conflicts:
        print(json.dumps({"status": "conflict", "conflicts": conflicts}, indent=2))
        return False

    # Reserve all files
    for f in files:
        reservations["reservations"][f] = {
            "ticket": ticket_id,
            "agent": agent,
            "reserved_at": now_iso(),
        }

    save_reservations(matrix_dir, reservations)
    print(json.dumps({"status": "ok", "reserved": files}))
    return True


def release_files(matrix_dir, ticket_id):
    """Release all file reservations held by a ticket."""
    reservations = load_reservations(matrix_dir)
    released = []

    new_reservations = {}
    for f, info in reservations["reservations"].items():
        if info["ticket"] == ticket_id:
            released.append(f)
        else:
            new_reservations[f] = info

    reservations["reservations"] = new_reservations
    save_reservations(matrix_dir, reservations)
    print(json.dumps({"status": "ok", "released": released}))
    return released


def check_reservation(matrix_dir, file_path):
    """Check if a file is reserved."""
    reservations = load_reservations(matrix_dir)
    info = reservations["reservations"].get(file_path)
    if info:
        print(json.dumps({"reserved": True, **info}))
    else:
        print(json.dumps({"reserved": False}))
    return info


# --- Visualization ---

def show_graph(matrix_dir):
    """Display dependency graph as text."""
    index = load_index(matrix_dir)
    print("\n=== Task Dependency Graph ===\n")

    status_icons = {
        "pending": "[ ]",
        "in_progress": "[~]",
        "review": "[?]",
        "completed": "[x]",
        "failed": "[!]",
        "blocked": "[#]",
    }

    for ticket_id in index["tickets"]:
        ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
        if not ticket_path.exists():
            continue
        ticket = load_json(ticket_path)
        icon = status_icons.get(ticket["status"], "[ ]")
        deps = ""
        if ticket.get("dependencies"):
            deps = f" <- {', '.join(ticket['dependencies'])}"
        blocks = ""
        if ticket.get("blocks"):
            blocks = f" -> {', '.join(ticket['blocks'])}"
        print(f"  {icon} {ticket['id']}: {ticket['title']} ({ticket['agent']}){deps}{blocks}")

    print()


def show_stats(matrix_dir):
    """Show ticket statistics."""
    index = load_index(matrix_dir)
    index = recount_statuses(matrix_dir, index)
    save_index(matrix_dir, index)

    stats = {
        "total": index["total"],
        "by_status": index["by_status"],
        "completion": f"{index['by_status'].get('completed', 0)}/{index['total']}"
            if index["total"] > 0 else "0/0",
    }

    # Count by agent
    by_agent = {}
    for ticket_id in index["tickets"]:
        ticket_path = matrix_dir / "tickets" / f"{ticket_id}.json"
        if ticket_path.exists():
            ticket = load_json(ticket_path)
            agent = ticket.get("agent", "unknown")
            by_agent[agent] = by_agent.get(agent, 0) + 1

    stats["by_agent"] = by_agent

    # Reservations count
    reservations = load_reservations(matrix_dir)
    stats["active_reservations"] = len(reservations["reservations"])

    print(json.dumps(stats, indent=2))
    return stats


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Neo Orchestrator Ticket Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create a ticket")
    p_create.add_argument("title")
    p_create.add_argument("description")
    p_create.add_argument("agent")
    p_create.add_argument("--priority", default="medium", choices=["critical", "high", "medium", "low"])
    p_create.add_argument("--deps", default="", help="Comma-separated dependency ticket IDs")
    p_create.add_argument("--files", default="", help="Comma-separated file paths")
    p_create.add_argument("--criteria", default="", help="Comma-separated acceptance criteria")

    # create-from-graph
    p_graph_create = subparsers.add_parser("create-from-graph", help="Create tickets from task graph")
    p_graph_create.add_argument("graph_path")

    # update
    p_update = subparsers.add_parser("update", help="Update a ticket")
    p_update.add_argument("ticket_id")
    p_update.add_argument("--status", choices=["pending", "in_progress", "review", "completed", "failed", "blocked"])
    p_update.add_argument("--agent")
    p_update.add_argument("--git-checkpoint")

    # get
    p_get = subparsers.add_parser("get", help="Get a ticket")
    p_get.add_argument("ticket_id")

    # list
    p_list = subparsers.add_parser("list", help="List tickets")
    p_list.add_argument("--status")
    p_list.add_argument("--agent")

    # next
    p_next = subparsers.add_parser("next", help="Get next available ticket")
    p_next.add_argument("--agent")

    # reserve
    p_reserve = subparsers.add_parser("reserve", help="Reserve files for a ticket")
    p_reserve.add_argument("ticket_id")
    p_reserve.add_argument("agent")

    # release
    p_release = subparsers.add_parser("release", help="Release file reservations")
    p_release.add_argument("ticket_id")

    # check-reservation
    p_check = subparsers.add_parser("check-reservation", help="Check if a file is reserved")
    p_check.add_argument("file_path")

    # graph
    subparsers.add_parser("graph", help="Display dependency graph")

    # stats
    subparsers.add_parser("stats", help="Show ticket statistics")

    args = parser.parse_args()
    matrix_dir = get_matrix_dir()

    if args.command == "create":
        deps = [d.strip() for d in args.deps.split(",") if d.strip()] if args.deps else []
        files = [f.strip() for f in args.files.split(",") if f.strip()] if args.files else []
        criteria = [c.strip() for c in args.criteria.split(",") if c.strip()] if args.criteria else []
        create_ticket(matrix_dir, args.title, args.description, args.agent,
                      priority=args.priority, dependencies=deps, files=files,
                      acceptance_criteria=criteria)

    elif args.command == "create-from-graph":
        create_from_graph(matrix_dir, args.graph_path)

    elif args.command == "update":
        updates = {}
        if args.status:
            updates["status"] = args.status
        if args.agent:
            updates["agent"] = args.agent
        if args.git_checkpoint:
            updates["git_checkpoint"] = args.git_checkpoint
        update_ticket(matrix_dir, args.ticket_id, **updates)

    elif args.command == "get":
        get_ticket(matrix_dir, args.ticket_id)

    elif args.command == "list":
        list_tickets(matrix_dir, status=args.status, agent=args.agent)

    elif args.command == "next":
        next_ticket(matrix_dir, agent=args.agent)

    elif args.command == "reserve":
        reserve_files(matrix_dir, args.ticket_id, args.agent)

    elif args.command == "release":
        release_files(matrix_dir, args.ticket_id)

    elif args.command == "check-reservation":
        check_reservation(matrix_dir, args.file_path)

    elif args.command == "graph":
        show_graph(matrix_dir)

    elif args.command == "stats":
        show_stats(matrix_dir)


if __name__ == "__main__":
    main()
