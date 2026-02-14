#!/usr/bin/env python3
"""memory-manager.py — 3-tier memory operations for Neo Orchestrator.

Usage:
    python3 memory-manager.py init
    python3 memory-manager.py log-episodic <type> <content> [--outcome success|failure]
    python3 memory-manager.py get-episodic [--last N]
    python3 memory-manager.py update-semantic <key> <value>
    python3 memory-manager.py get-semantic [--key <key>]
    python3 memory-manager.py record-strategy <description> <context> --outcome success|failure
    python3 memory-manager.py get-strategies [--min-confidence 0.3]
    python3 memory-manager.py consolidate
    python3 memory-manager.py load-context [--max-tokens 4000]
    python3 memory-manager.py stats
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_matrix_dir():
    matrix_dir = os.environ.get("MATRIX_DIR", ".matrix")
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


# --- Episodic Memory ---

def get_session_id(matrix_dir):
    session = load_json(matrix_dir / "session.json")
    return session["session_id"] if session else "unknown"


def get_episodic_path(matrix_dir):
    session_id = get_session_id(matrix_dir)
    return matrix_dir / "memory" / "episodic" / f"{session_id}.json"


def init_episodic(matrix_dir):
    """Initialize episodic memory for current session."""
    path = get_episodic_path(matrix_dir)
    if path.exists():
        return load_json(path)

    episodic = {
        "session_id": get_session_id(matrix_dir),
        "started_at": now_iso(),
        "entries": [],
        "summary": None,
    }
    save_json(path, episodic)
    return episodic


def log_episodic(matrix_dir, entry_type, content, outcome=None):
    """Add an entry to episodic memory."""
    path = get_episodic_path(matrix_dir)
    episodic = load_json(path)
    if not episodic:
        episodic = init_episodic(matrix_dir)

    entry = {
        "timestamp": now_iso(),
        "type": entry_type,
        "content": content,
        "outcome": outcome,
    }

    episodic = {
        **episodic,
        "entries": [*episodic["entries"], entry],
    }
    save_json(path, episodic)
    print(json.dumps(entry, indent=2))
    return entry


def get_episodic(matrix_dir, last_n=None):
    """Get episodic memory entries."""
    path = get_episodic_path(matrix_dir)
    episodic = load_json(path)
    if not episodic:
        print(json.dumps([]))
        return []

    entries = episodic["entries"]
    if last_n:
        entries = entries[-last_n:]
    print(json.dumps(entries, indent=2))
    return entries


# --- Semantic Memory ---

def get_semantic_path(matrix_dir):
    return matrix_dir / "memory" / "semantic" / "project-knowledge.json"


def init_semantic(matrix_dir):
    """Initialize semantic memory."""
    path = get_semantic_path(matrix_dir)
    if path.exists():
        return load_json(path)

    semantic = {
        "project_name": None,
        "tech_stack": [],
        "conventions": {},
        "structure": {},
        "endpoints": [],
        "known_issues": [],
        "patterns": [],
        "last_updated": now_iso(),
    }
    save_json(path, semantic)
    return semantic


def update_semantic(matrix_dir, key, value):
    """Update a key in semantic memory."""
    path = get_semantic_path(matrix_dir)
    semantic = load_json(path)
    if not semantic:
        semantic = init_semantic(matrix_dir)

    # Parse value as JSON if possible
    try:
        parsed_value = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        parsed_value = value

    # For list fields, append instead of replace
    if key in ("tech_stack", "endpoints", "known_issues", "patterns"):
        existing = semantic.get(key, [])
        if isinstance(parsed_value, list):
            merged = [*existing, *parsed_value]
        else:
            merged = [*existing, parsed_value]
        # Deduplicate if items are strings
        if merged and isinstance(merged[0], str):
            merged = list(dict.fromkeys(merged))
        semantic = {**semantic, key: merged, "last_updated": now_iso()}
    elif key == "conventions" or key == "structure":
        existing = semantic.get(key, {})
        if isinstance(parsed_value, dict):
            semantic = {**semantic, key: {**existing, **parsed_value}, "last_updated": now_iso()}
        else:
            semantic = {**semantic, key: parsed_value, "last_updated": now_iso()}
    else:
        semantic = {**semantic, key: parsed_value, "last_updated": now_iso()}

    save_json(path, semantic)
    print(json.dumps(semantic, indent=2))
    return semantic


def get_semantic(matrix_dir, key=None):
    """Get semantic memory."""
    path = get_semantic_path(matrix_dir)
    semantic = load_json(path)
    if not semantic:
        semantic = init_semantic(matrix_dir)

    if key:
        result = semantic.get(key)
        print(json.dumps(result, indent=2) if result else "null")
        return result

    print(json.dumps(semantic, indent=2))
    return semantic


# --- Procedural Memory ---

def get_procedural_path(matrix_dir):
    return matrix_dir / "memory" / "procedural" / "strategies.json"


def init_procedural(matrix_dir):
    """Initialize procedural memory."""
    path = get_procedural_path(matrix_dir)
    if path.exists():
        return load_json(path)

    procedural = {
        "strategies": [],
        "last_updated": now_iso(),
    }
    save_json(path, procedural)
    return procedural


def record_strategy(matrix_dir, description, context, outcome):
    """Record a strategy outcome. Updates confidence if strategy exists."""
    path = get_procedural_path(matrix_dir)
    procedural = load_json(path)
    if not procedural:
        procedural = init_procedural(matrix_dir)

    # Check if strategy already exists (fuzzy match by description)
    existing_idx = None
    desc_lower = description.lower()
    for i, s in enumerate(procedural["strategies"]):
        if s["description"].lower() == desc_lower:
            existing_idx = i
            break

    if existing_idx is not None:
        # Update existing strategy (immutable pattern)
        old = procedural["strategies"][existing_idx]
        successes = old["successes"] + (1 if outcome == "success" else 0)
        failures = old["failures"] + (1 if outcome == "failure" else 0)
        confidence = max(0.1, min(0.95, successes / (successes + failures)))

        updated = {
            **old,
            "successes": successes,
            "failures": failures,
            "confidence": round(confidence, 3),
            "last_used": now_iso(),
        }

        strategies = [
            updated if i == existing_idx else s
            for i, s in enumerate(procedural["strategies"])
        ]
        procedural = {**procedural, "strategies": strategies, "last_updated": now_iso()}
        save_json(path, procedural)
        print(json.dumps(updated, indent=2))
        return updated
    else:
        # Create new strategy
        strategy = {
            "id": f"STRAT-{len(procedural['strategies']) + 1:03d}",
            "description": description,
            "context": context,
            "confidence": 0.5,
            "successes": 1 if outcome == "success" else 0,
            "failures": 1 if outcome == "failure" else 0,
            "last_used": now_iso(),
            "created_at": now_iso(),
        }

        procedural = {
            **procedural,
            "strategies": [*procedural["strategies"], strategy],
            "last_updated": now_iso(),
        }
        save_json(path, procedural)
        print(json.dumps(strategy, indent=2))
        return strategy


def get_strategies(matrix_dir, min_confidence=0.0):
    """Get strategies above minimum confidence."""
    path = get_procedural_path(matrix_dir)
    procedural = load_json(path)
    if not procedural:
        print(json.dumps([]))
        return []

    filtered = [s for s in procedural["strategies"] if s["confidence"] >= min_confidence]
    filtered.sort(key=lambda s: s["confidence"], reverse=True)
    print(json.dumps(filtered, indent=2))
    return filtered


# --- Consolidation ---

def consolidate(matrix_dir):
    """Consolidate memory: compress old episodic, archive low-confidence strategies."""
    episodic_dir = matrix_dir / "memory" / "episodic"
    results = {"episodic_compressed": 0, "strategies_archived": 0}

    # Compress old episodic sessions (keep last 5 full, compress older)
    if episodic_dir.exists():
        session_files = sorted(episodic_dir.glob("session_*.json"), reverse=True)
        current_session_id = get_session_id(matrix_dir)

        for i, sf in enumerate(session_files):
            if sf.stem == current_session_id:
                continue
            if i >= 5:
                # Compress: keep only summary and key decisions
                episodic = load_json(sf)
                if episodic and not episodic.get("compressed"):
                    key_entries = [
                        e for e in episodic.get("entries", [])
                        if e.get("type") in ("decision", "error", "milestone", "strategy")
                        or e.get("outcome") == "failure"
                    ]
                    compressed = {
                        **episodic,
                        "entries": key_entries,
                        "compressed": True,
                        "original_entry_count": len(episodic.get("entries", [])),
                        "compressed_at": now_iso(),
                    }
                    save_json(sf, compressed)
                    results["episodic_compressed"] += 1

    # Archive low-confidence strategies
    proc_path = get_procedural_path(matrix_dir)
    procedural = load_json(proc_path)
    if procedural:
        active = []
        archived = []
        for s in procedural.get("strategies", []):
            if s["confidence"] < 0.3 and (s["successes"] + s["failures"]) >= 3:
                archived.append(s)
                results["strategies_archived"] += 1
            else:
                active.append(s)

        if archived:
            # Save archived strategies separately
            archive_path = matrix_dir / "memory" / "procedural" / "archived.json"
            existing_archive = load_json(archive_path) or {"archived": []}
            existing_archive = {
                **existing_archive,
                "archived": [*existing_archive["archived"], *archived],
            }
            save_json(archive_path, existing_archive)

            procedural = {**procedural, "strategies": active, "last_updated": now_iso()}
            save_json(proc_path, procedural)

    print(json.dumps(results, indent=2))
    return results


# --- Context Loading ---

def load_context(matrix_dir, max_tokens=4000):
    """Load memory as context string, prioritized by tier.
    Priority: procedural > semantic > episodic (most recent)
    Rough estimate: 1 token ~= 4 chars
    """
    max_chars = max_tokens * 4
    context_parts = []
    chars_used = 0

    # 1. Procedural (most actionable)
    proc_path = get_procedural_path(matrix_dir)
    procedural = load_json(proc_path)
    if procedural and procedural.get("strategies"):
        high_conf = [s for s in procedural["strategies"] if s["confidence"] >= 0.5]
        if high_conf:
            proc_text = "## Learned Strategies\n"
            for s in sorted(high_conf, key=lambda x: x["confidence"], reverse=True)[:10]:
                proc_text += f"- [{s['confidence']:.0%}] {s['description']} (context: {s['context']})\n"
            context_parts.append(proc_text)
            chars_used += len(proc_text)

    # 2. Semantic (project knowledge)
    if chars_used < max_chars:
        sem_path = get_semantic_path(matrix_dir)
        semantic = load_json(sem_path)
        if semantic:
            sem_text = "## Project Knowledge\n"
            if semantic.get("project_name"):
                sem_text += f"Project: {semantic['project_name']}\n"
            if semantic.get("tech_stack"):
                sem_text += f"Stack: {', '.join(semantic['tech_stack'])}\n"
            if semantic.get("conventions"):
                sem_text += f"Conventions: {json.dumps(semantic['conventions'])}\n"
            if semantic.get("known_issues"):
                sem_text += "Known Issues:\n"
                for issue in semantic["known_issues"][:5]:
                    sem_text += f"  - {issue}\n"
            remaining = max_chars - chars_used
            if len(sem_text) > remaining:
                sem_text = sem_text[:remaining]
            context_parts.append(sem_text)
            chars_used += len(sem_text)

    # 3. Episodic (recent history)
    if chars_used < max_chars:
        ep_path = get_episodic_path(matrix_dir)
        episodic = load_json(ep_path)
        if episodic and episodic.get("entries"):
            ep_text = "## Recent Session Activity\n"
            for entry in episodic["entries"][-10:]:
                ep_text += f"- [{entry.get('type', '?')}] {entry.get('content', '')}"
                if entry.get("outcome"):
                    ep_text += f" -> {entry['outcome']}"
                ep_text += "\n"
            remaining = max_chars - chars_used
            if len(ep_text) > remaining:
                ep_text = ep_text[:remaining]
            context_parts.append(ep_text)

    result = "\n".join(context_parts)
    print(result)
    return result


# --- Stats ---

def show_stats(matrix_dir):
    """Show memory statistics."""
    stats = {"episodic": {}, "semantic": {}, "procedural": {}}

    # Episodic
    ep_dir = matrix_dir / "memory" / "episodic"
    if ep_dir.exists():
        session_files = list(ep_dir.glob("session_*.json"))
        total_entries = 0
        for sf in session_files:
            data = load_json(sf)
            if data:
                total_entries += len(data.get("entries", []))
        stats["episodic"] = {
            "sessions": len(session_files),
            "total_entries": total_entries,
        }

    # Semantic
    sem = load_json(get_semantic_path(matrix_dir))
    if sem:
        stats["semantic"] = {
            "tech_stack_items": len(sem.get("tech_stack", [])),
            "endpoints": len(sem.get("endpoints", [])),
            "known_issues": len(sem.get("known_issues", [])),
            "last_updated": sem.get("last_updated"),
        }

    # Procedural
    proc = load_json(get_procedural_path(matrix_dir))
    if proc:
        strategies = proc.get("strategies", [])
        stats["procedural"] = {
            "total_strategies": len(strategies),
            "high_confidence": len([s for s in strategies if s["confidence"] >= 0.7]),
            "medium_confidence": len([s for s in strategies if 0.3 <= s["confidence"] < 0.7]),
            "low_confidence": len([s for s in strategies if s["confidence"] < 0.3]),
        }

    # Archived
    archive = load_json(matrix_dir / "memory" / "procedural" / "archived.json")
    if archive:
        stats["procedural"]["archived"] = len(archive.get("archived", []))

    print(json.dumps(stats, indent=2))
    return stats


# --- Init ---

def init_all(matrix_dir):
    """Initialize all memory tiers."""
    init_episodic(matrix_dir)
    init_semantic(matrix_dir)
    init_procedural(matrix_dir)
    print(json.dumps({"status": "initialized", "tiers": ["episodic", "semantic", "procedural"]}))


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Neo Orchestrator Memory Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    subparsers.add_parser("init", help="Initialize all memory tiers")

    # log-episodic
    p_log = subparsers.add_parser("log-episodic", help="Log an episodic entry")
    p_log.add_argument("type", choices=["decision", "error", "milestone", "strategy", "observation", "task"])
    p_log.add_argument("content")
    p_log.add_argument("--outcome", choices=["success", "failure"])

    # get-episodic
    p_get_ep = subparsers.add_parser("get-episodic", help="Get episodic entries")
    p_get_ep.add_argument("--last", type=int, help="Get last N entries")

    # update-semantic
    p_sem_update = subparsers.add_parser("update-semantic", help="Update semantic memory")
    p_sem_update.add_argument("key")
    p_sem_update.add_argument("value")

    # get-semantic
    p_sem_get = subparsers.add_parser("get-semantic", help="Get semantic memory")
    p_sem_get.add_argument("--key", help="Specific key to retrieve")

    # record-strategy
    p_strat = subparsers.add_parser("record-strategy", help="Record a strategy outcome")
    p_strat.add_argument("description")
    p_strat.add_argument("context")
    p_strat.add_argument("--outcome", required=True, choices=["success", "failure"])

    # get-strategies
    p_get_strat = subparsers.add_parser("get-strategies", help="Get strategies")
    p_get_strat.add_argument("--min-confidence", type=float, default=0.0)

    # consolidate
    subparsers.add_parser("consolidate", help="Consolidate memory")

    # load-context
    p_ctx = subparsers.add_parser("load-context", help="Load memory as context")
    p_ctx.add_argument("--max-tokens", type=int, default=4000)

    # stats
    subparsers.add_parser("stats", help="Show memory statistics")

    args = parser.parse_args()
    matrix_dir = get_matrix_dir()

    if args.command == "init":
        init_all(matrix_dir)
    elif args.command == "log-episodic":
        log_episodic(matrix_dir, args.type, args.content, outcome=args.outcome)
    elif args.command == "get-episodic":
        get_episodic(matrix_dir, last_n=args.last)
    elif args.command == "update-semantic":
        update_semantic(matrix_dir, args.key, args.value)
    elif args.command == "get-semantic":
        get_semantic(matrix_dir, key=args.key)
    elif args.command == "record-strategy":
        record_strategy(matrix_dir, args.description, args.context, args.outcome)
    elif args.command == "get-strategies":
        get_strategies(matrix_dir, min_confidence=args.min_confidence)
    elif args.command == "consolidate":
        consolidate(matrix_dir)
    elif args.command == "load-context":
        load_context(matrix_dir, max_tokens=args.max_tokens)
    elif args.command == "stats":
        show_stats(matrix_dir)


if __name__ == "__main__":
    main()
