#!/usr/bin/env python3
"""cost-tracker.py — Token usage and cost tracking for Neo Orchestrator.

Tracks costs per agent, per ticket, per phase, per model, and per session.
Agents spawned via `claude -p --output-format json` return usage data that
this script aggregates into .matrix/costs.json.

Usage:
    python3 cost-tracker.py record <agent> <model> <input_tokens> <output_tokens> [--ticket TICKET-001] [--phase construct] [--matrix-dir .matrix]
    python3 cost-tracker.py status [--matrix-dir .matrix]
    python3 cost-tracker.py budget <amount_usd> [--matrix-dir .matrix]
    python3 cost-tracker.py remaining [--matrix-dir .matrix]
    python3 cost-tracker.py recommend <complexity> [--matrix-dir .matrix]
    python3 cost-tracker.py report [--matrix-dir .matrix]
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# --- Pricing per 1M tokens (2025) ---

PRICING = {
    "opus":   {"input": 15.00, "output": 75.00},
    "sonnet": {"input":  3.00, "output": 15.00},
    "haiku":  {"input":  0.25, "output":  1.25},
}

VALID_PHASES = ("construct", "jacking-in", "sentinels", "unplugged", "reloaded")
BOX_W = 38


# --- Helpers ---

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_matrix_dir(matrix_dir_arg):
    path = Path(matrix_dir_arg)
    if not path.is_dir():
        print(f"Error: {path} not found. Run init-matrix.sh first.", file=sys.stderr)
        sys.exit(1)
    return path


def costs_path(matrix_dir):
    return matrix_dir / "costs.json"


def load_costs(matrix_dir):
    path = costs_path(matrix_dir)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return _empty_costs()


def save_costs(matrix_dir, data):
    path = costs_path(matrix_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def _empty_costs():
    return {
        "session_total": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
        "budget": None,
        "by_agent": {},
        "by_ticket": {},
        "by_model": {},
        "by_phase": {},
        "history": [],
    }


def _empty_bucket():
    return {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


def compute_cost(model, input_tokens, output_tokens):
    prices = PRICING.get(model, PRICING["sonnet"])
    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    return round(input_cost + output_cost, 6)


def _add_to_bucket(bucket, input_tokens, output_tokens, cost):
    return {
        **bucket,
        "input_tokens": bucket["input_tokens"] + input_tokens,
        "output_tokens": bucket["output_tokens"] + output_tokens,
        "cost_usd": round(bucket["cost_usd"] + cost, 6),
    }


# --- Core functions (importable) ---

def record_usage(matrix_dir, agent, model, input_tokens, output_tokens,
                 ticket=None, phase=None):
    """Record a single agent spawn's token usage."""
    data = load_costs(matrix_dir)
    cost = compute_cost(model, input_tokens, output_tokens)

    # Session total
    data = {
        **data,
        "session_total": _add_to_bucket(
            data["session_total"], input_tokens, output_tokens, cost
        ),
    }

    # By agent (includes spawn count)
    agent_bucket = data["by_agent"].get(agent, {**_empty_bucket(), "spawns": 0})
    agent_bucket = {
        **_add_to_bucket(agent_bucket, input_tokens, output_tokens, cost),
        "spawns": agent_bucket["spawns"] + 1,
    }
    data = {**data, "by_agent": {**data["by_agent"], agent: agent_bucket}}

    # By ticket
    if ticket:
        ticket_bucket = data["by_ticket"].get(ticket, _empty_bucket())
        data = {
            **data,
            "by_ticket": {
                **data["by_ticket"],
                ticket: _add_to_bucket(ticket_bucket, input_tokens, output_tokens, cost),
            },
        }

    # By model (includes spawn count)
    model_bucket = data["by_model"].get(model, {**_empty_bucket(), "spawns": 0})
    model_bucket = {
        **_add_to_bucket(model_bucket, input_tokens, output_tokens, cost),
        "spawns": model_bucket["spawns"] + 1,
    }
    data = {**data, "by_model": {**data["by_model"], model: model_bucket}}

    # By phase
    if phase:
        phase_bucket = data["by_phase"].get(phase, _empty_bucket())
        data = {
            **data,
            "by_phase": {
                **data["by_phase"],
                phase: _add_to_bucket(phase_bucket, input_tokens, output_tokens, cost),
            },
        }

    # History entry
    entry = {
        "timestamp": now_iso(),
        "agent": agent,
        "model": model,
        "ticket": ticket,
        "phase": phase,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }
    data = {**data, "history": [*data["history"], entry]}

    save_costs(matrix_dir, data)
    return entry


def get_session_cost(matrix_dir):
    """Return total session cost in USD."""
    data = load_costs(matrix_dir)
    return data["session_total"]["cost_usd"]


def get_budget_remaining(matrix_dir):
    """Return remaining budget in USD, or None if no budget is set."""
    data = load_costs(matrix_dir)
    if data["budget"] is None:
        return None
    return round(data["budget"] - data["session_total"]["cost_usd"], 6)


def set_budget(matrix_dir, amount_usd):
    """Set the session budget."""
    data = load_costs(matrix_dir)
    data = {**data, "budget": amount_usd}
    save_costs(matrix_dir, data)
    return amount_usd


def recommend_model(matrix_dir, complexity):
    """Recommend a model tier based on remaining budget and task complexity.

    Complexity levels: S (small), M (medium), L (large), XL (extra-large).
    Returns one of: opus, sonnet, haiku, or "STOP".
    """
    remaining = get_budget_remaining(matrix_dir)

    # No budget set -- default to sonnet (safe middle ground)
    if remaining is None:
        return "sonnet"

    data = load_costs(matrix_dir)
    budget = data["budget"]

    if budget <= 0:
        return "STOP"

    pct = (remaining / budget) * 100

    if pct < 5:
        return "STOP"

    complexity = complexity.upper()

    if pct >= 80:
        # Plenty of budget -- use best model for size
        return {"S": "haiku", "M": "sonnet", "L": "sonnet", "XL": "opus"}[complexity]

    if pct >= 40:
        # Moderate budget -- downgrade XL from opus to sonnet
        return {"S": "haiku", "M": "sonnet", "L": "sonnet", "XL": "sonnet"}[complexity]

    if pct >= 20:
        # Low budget -- everything sonnet (security gates keep opus)
        return "sonnet"

    # Very low (< 20%) -- haiku for everything except opus-tier
    return {"S": "haiku", "M": "haiku", "L": "haiku", "XL": "sonnet"}[complexity]


def format_report(matrix_dir):
    """Build a pretty-printed cost breakdown string."""
    data = load_costs(matrix_dir)
    total = data["session_total"]["cost_usd"]
    budget = data["budget"]
    remaining = get_budget_remaining(matrix_dir)

    lines = []
    lines.append(f"{'':>{BOX_W}}".replace(" ", "="))
    lines.append(f"  COST TRACKER -- The Matrix")
    lines.append(f"{'':>{BOX_W}}".replace(" ", "="))

    # Session totals
    lines.append(f"  Session Total:    ${total:.2f}")
    if budget is not None:
        lines.append(f"  Budget:           ${budget:.2f}")
        pct = (remaining / budget * 100) if budget > 0 else 0
        lines.append(f"  Remaining:        ${remaining:.2f} ({pct:.0f}%)")
    else:
        lines.append(f"  Budget:           not set")

    lines.append(f"{'':>{BOX_W}}".replace(" ", "-"))

    # By model
    lines.append(f"  By Model:")
    for model_name in ("opus", "sonnet", "haiku"):
        bucket = data["by_model"].get(model_name)
        if bucket:
            lines.append(
                f"    {model_name:<8} ${bucket['cost_usd']:.2f}  "
                f"({bucket['spawns']} spawns)"
            )
        else:
            lines.append(f"    {model_name:<8} $0.00  (0 spawns)")

    lines.append(f"{'':>{BOX_W}}".replace(" ", "-"))

    # Top agents (sorted by cost descending)
    lines.append(f"  Top Agents:")
    agents_sorted = sorted(
        data["by_agent"].items(),
        key=lambda kv: kv[1]["cost_usd"],
        reverse=True,
    )
    for agent_name, bucket in agents_sorted[:5]:
        lines.append(f"    {agent_name:<10} ${bucket['cost_usd']:.2f}")

    if not agents_sorted:
        lines.append(f"    (none)")

    # By phase (only if any phases recorded)
    if data["by_phase"]:
        lines.append(f"{'':>{BOX_W}}".replace(" ", "-"))
        lines.append(f"  By Phase:")
        for phase_name, bucket in data["by_phase"].items():
            lines.append(f"    {phase_name:<14} ${bucket['cost_usd']:.2f}")

    # By ticket (top 5)
    if data["by_ticket"]:
        lines.append(f"{'':>{BOX_W}}".replace(" ", "-"))
        lines.append(f"  Top Tickets:")
        tickets_sorted = sorted(
            data["by_ticket"].items(),
            key=lambda kv: kv[1]["cost_usd"],
            reverse=True,
        )
        for ticket_id, bucket in tickets_sorted[:5]:
            lines.append(f"    {ticket_id:<14} ${bucket['cost_usd']:.2f}")

    lines.append(f"{'':>{BOX_W}}".replace(" ", "="))

    # Wrap in box drawing
    max_len = max(len(line) for line in lines)
    box_w = max_len + 2
    result = []
    for i, line in enumerate(lines):
        if set(line.strip()) <= {"="}:
            if i == 0:
                result.append(f"\u2554{'=' * box_w}\u2557")
            elif i == len(lines) - 1:
                result.append(f"\u255a{'=' * box_w}\u255d")
            else:
                result.append(f"\u2560{'=' * box_w}\u2563")
        elif set(line.strip()) <= {"-"}:
            result.append(f"\u2560{'-' * box_w}\u2563")
        else:
            result.append(f"\u2551 {line:<{box_w - 1}}\u2551")

    return "\n".join(result)


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Neo Orchestrator Cost Tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # record
    p_record = subparsers.add_parser("record", help="Record token usage from an agent spawn")
    p_record.add_argument("agent", help="Agent name (e.g. dozer, oracle)")
    p_record.add_argument("model", choices=list(PRICING.keys()), help="Model tier")
    p_record.add_argument("input_tokens", type=int, help="Input token count")
    p_record.add_argument("output_tokens", type=int, help="Output token count")
    p_record.add_argument("--ticket", default=None, help="Associated ticket ID")
    p_record.add_argument("--phase", default=None, choices=VALID_PHASES, help="Pipeline phase")
    p_record.add_argument("--matrix-dir", default=".matrix", help="Path to .matrix directory")

    # status
    p_status = subparsers.add_parser("status", help="Show current cost status")
    p_status.add_argument("--matrix-dir", default=".matrix")

    # budget
    p_budget = subparsers.add_parser("budget", help="Set session budget")
    p_budget.add_argument("amount_usd", type=float, help="Budget in USD")
    p_budget.add_argument("--matrix-dir", default=".matrix")

    # remaining
    p_remaining = subparsers.add_parser("remaining", help="Show remaining budget")
    p_remaining.add_argument("--matrix-dir", default=".matrix")

    # recommend
    p_recommend = subparsers.add_parser("recommend", help="Recommend model for task complexity")
    p_recommend.add_argument("complexity", choices=["S", "M", "L", "XL"], help="Task complexity")
    p_recommend.add_argument("--matrix-dir", default=".matrix")

    # report
    p_report = subparsers.add_parser("report", help="Full cost breakdown report")
    p_report.add_argument("--matrix-dir", default=".matrix")

    args = parser.parse_args()
    matrix_dir = resolve_matrix_dir(args.matrix_dir)

    if args.command == "record":
        entry = record_usage(
            matrix_dir, args.agent, args.model,
            args.input_tokens, args.output_tokens,
            ticket=args.ticket, phase=args.phase,
        )
        print(json.dumps(entry, indent=2))

    elif args.command == "status":
        print(format_report(matrix_dir))

    elif args.command == "budget":
        set_budget(matrix_dir, args.amount_usd)
        remaining = get_budget_remaining(matrix_dir)
        print(json.dumps({"budget": args.amount_usd, "remaining": remaining}))

    elif args.command == "remaining":
        remaining = get_budget_remaining(matrix_dir)
        data = load_costs(matrix_dir)
        if remaining is None:
            print(json.dumps({"budget": None, "remaining": None, "message": "No budget set"}))
        else:
            pct = (remaining / data["budget"] * 100) if data["budget"] > 0 else 0
            print(json.dumps({
                "budget": data["budget"],
                "spent": data["session_total"]["cost_usd"],
                "remaining": remaining,
                "percent_remaining": round(pct, 1),
            }))

    elif args.command == "recommend":
        model = recommend_model(matrix_dir, args.complexity)
        remaining = get_budget_remaining(matrix_dir)
        result = {"complexity": args.complexity, "recommended_model": model}
        if remaining is not None:
            data = load_costs(matrix_dir)
            pct = (remaining / data["budget"] * 100) if data["budget"] > 0 else 0
            result["budget_percent_remaining"] = round(pct, 1)
        if model == "STOP":
            result["warning"] = "Budget nearly exhausted. Stop spawning agents."
        print(json.dumps(result, indent=2))

    elif args.command == "report":
        print(format_report(matrix_dir))


if __name__ == "__main__":
    main()
