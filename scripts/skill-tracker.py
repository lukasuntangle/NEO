#!/usr/bin/env python3
"""skill-tracker.py — Agent specialization tracking for Neo Orchestrator.

Tracks per-agent success rates by domain across sessions so Morpheus can
make smarter assignment decisions.

Usage:
    python3 skill-tracker.py record <agent> <ticket-id> <success|failure> [--domain auto] [--matrix-dir .matrix]
    python3 skill-tracker.py recommend <domain> [--matrix-dir .matrix]
    python3 skill-tracker.py profile <agent> [--matrix-dir .matrix]
    python3 skill-tracker.py leaderboard [--matrix-dir .matrix]
    python3 skill-tracker.py promotions [--matrix-dir .matrix]
"""
import argparse, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

DOMAIN_KEYWORDS = {
    "rest-api": ["route", "endpoint", "controller", "rest", "crud", "middleware"],
    "websocket": ["socket", "realtime", "websocket", "sse", "event stream"],
    "database": ["schema", "migration", "query", "sql", "orm", "prisma", "drizzle"],
    "auth": ["login", "signup", "jwt", "oauth", "session", "password", "token"],
    "frontend": ["component", "react", "page", "layout", "css", "tailwind", "ui"],
    "testing": ["test", "coverage", "assert", "mock", "fixture", "spec"],
    "devops": ["docker", "ci", "pipeline", "deploy", "environment", "nginx"],
    "security": ["vulnerability", "injection", "xss", "csrf", "audit", "owasp"],
    "documentation": ["readme", "changelog", "jsdoc", "api doc"],
    "integration": ["webhook", "third-party", "api client", "sdk"],
}

now_iso = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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

def _out(data):
    print(json.dumps(data, indent=2))
    return data

def get_skills_path(matrix_dir):
    return Path(matrix_dir) / "memory" / "procedural" / "agent-skills.json"

def load_skills(matrix_dir):
    data = load_json(get_skills_path(matrix_dir))
    if data is None:
        data = {"updated_at": now_iso(), "agents": {}}
        save_json(get_skills_path(matrix_dir), data)
    return data

def save_skills(matrix_dir, data):
    return save_json(get_skills_path(matrix_dir), {**data, "updated_at": now_iso()})

def detect_domain(matrix_dir, ticket_id):
    """Read ticket file, detect domain from content."""
    ticket = load_json(Path(matrix_dir) / "tickets" / f"{ticket_id}.json")
    if not ticket:
        return None
    text = " ".join([ticket.get("title", ""), ticket.get("description", ""),
                     " ".join(ticket.get("acceptance_criteria", [])),
                     " ".join(ticket.get("files", []))]).lower()
    scores = {}
    for domain, kws in DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in kws if re.search(r'\b' + re.escape(kw) + r'\b', text))
        if count > 0:
            scores[domain] = count
    return max(scores, key=scores.get) if scores else None

def compute_confidence(total):
    """Confidence starts at 0.5, grows by 0.05 per attempt, caps at 1.0."""
    return min(1.0, 0.5 + (total * 0.05))

def compute_rate(s, f):
    return round(s / (s + f), 2) if (s + f) > 0 else 0.0

def evaluate_tier(overall, domains):
    """Determine promotion/demotion candidacy."""
    promotion = any(d["confidence"] > 0.7 and d["rate"] < 0.6 for d in domains.values())
    total = overall["success"] + overall["failure"]
    confident = [d for d in domains.values() if d["confidence"] > 0.7]
    demotion = (total >= 10 and len(confident) > 0
                and all(d["rate"] > 0.95 for d in confident))
    return promotion, demotion

def record_outcome(matrix_dir, agent, ticket_id, success, domain=None):
    """Record a task outcome for an agent, updating domain-level stats."""
    skills = load_skills(matrix_dir)
    if domain is None or domain == "auto":
        domain = detect_domain(matrix_dir, ticket_id)
    agents = skills.get("agents", {})
    ad = agents.get(agent, {"overall": {"success": 0, "failure": 0, "rate": 0.0},
                            "domains": {}, "model_tier": "sonnet",
                            "promotion_candidate": False, "demotion_candidate": False})
    ns = ad["overall"]["success"] + (1 if success else 0)
    nf = ad["overall"]["failure"] + (0 if success else 1)
    overall = {"success": ns, "failure": nf, "rate": compute_rate(ns, nf)}
    domains = {**ad.get("domains", {})}
    if domain:
        od = domains.get(domain, {"success": 0, "failure": 0, "rate": 0.0, "confidence": 0.5})
        ds, df = od["success"] + (1 if success else 0), od["failure"] + (0 if success else 1)
        domains[domain] = {"success": ds, "failure": df, "rate": compute_rate(ds, df),
                           "confidence": round(compute_confidence(ds + df), 2)}
    promo, demo = evaluate_tier(overall, domains)
    updated = {**ad, "overall": overall, "domains": domains,
               "promotion_candidate": promo, "demotion_candidate": demo}
    save_skills(matrix_dir, {**skills, "agents": {**agents, agent: updated}})
    return _out({"agent": agent, "ticket": ticket_id,
                 "outcome": "success" if success else "failure",
                 "domain": domain, "overall_rate": overall["rate"]})

def recommend_agent(matrix_dir, domain, available_agents=None):
    """Best agent for domain. Score = rate * confidence, fallback to overall."""
    skills = load_skills(matrix_dir)
    agents = skills.get("agents", {})
    if available_agents is None:
        available_agents = list(agents.keys())
    scored = []
    for name in available_agents:
        ad = agents.get(name)
        if not ad:
            scored.append({"agent": name, "score": 0.0, "basis": "no-data"})
            continue
        ds = ad.get("domains", {}).get(domain)
        if ds:
            score = round(ds["rate"] * ds["confidence"], 3)
            scored.append({"agent": name, "score": score, "basis": "domain",
                           "rate": ds["rate"], "confidence": ds["confidence"]})
        else:
            ov = ad.get("overall", {})
            rate = ov.get("rate", 0.0)
            total = ov.get("success", 0) + ov.get("failure", 0)
            conf = round(min(0.5, total * 0.03), 2)
            scored.append({"agent": name, "score": round(rate * conf, 3),
                           "basis": "overall-fallback", "rate": rate, "confidence": conf})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return _out(scored)

def get_profile(matrix_dir, agent):
    """Agent's full skill profile."""
    skills = load_skills(matrix_dir)
    ad = skills.get("agents", {}).get(agent)
    return _out({"agent": agent, **ad} if ad else {"agent": agent, "status": "no data"})

def get_promotions(matrix_dir):
    """List of promotion/demotion suggestions."""
    skills, suggestions = load_skills(matrix_dir), []
    for name, ad in skills.get("agents", {}).items():
        if ad.get("promotion_candidate"):
            weak = [{"domain": d, "rate": s["rate"], "confidence": s["confidence"]}
                    for d, s in ad.get("domains", {}).items()
                    if s["confidence"] > 0.7 and s["rate"] < 0.6]
            suggestions.append({"agent": name, "action": "promote",
                                "current_tier": ad.get("model_tier", "unknown"),
                                "reason": "Low success rate in confident domains",
                                "weak_domains": weak})
        if ad.get("demotion_candidate"):
            suggestions.append({"agent": name, "action": "demote",
                                "current_tier": ad.get("model_tier", "unknown"),
                                "reason": "Consistently high success across all confident domains",
                                "overall_rate": ad["overall"]["rate"]})
    return _out(suggestions)

def show_leaderboard(matrix_dir):
    """All agents ranked by overall success rate."""
    skills, board = load_skills(matrix_dir), []
    for name, ad in skills.get("agents", {}).items():
        ov = ad.get("overall", {})
        total = ov.get("success", 0) + ov.get("failure", 0)
        top = sorted(ad.get("domains", {}).items(),
                     key=lambda kv: kv[1]["rate"] * kv[1]["confidence"], reverse=True)[:3]
        board.append({"agent": name, "total_tasks": total,
                      "success_rate": ov.get("rate", 0.0),
                      "model_tier": ad.get("model_tier", "unknown"),
                      "top_domains": [{"domain": d, "score": round(s["rate"] * s["confidence"], 3)}
                                      for d, s in top],
                      "promotion": ad.get("promotion_candidate", False),
                      "demotion": ad.get("demotion_candidate", False)})
    board.sort(key=lambda x: (-x["success_rate"], -x["total_tasks"]))
    return _out(board)

# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Neo Orchestrator Skill Tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("record", help="Record a task outcome")
    p.add_argument("agent"); p.add_argument("ticket_id")
    p.add_argument("outcome", choices=["success", "failure"])
    p.add_argument("--domain", default="auto"); p.add_argument("--matrix-dir")

    p = sub.add_parser("recommend", help="Recommend best agent for domain")
    p.add_argument("domain")
    p.add_argument("--agents", default=""); p.add_argument("--matrix-dir")

    p = sub.add_parser("profile", help="Show agent skill profile")
    p.add_argument("agent"); p.add_argument("--matrix-dir")

    p = sub.add_parser("leaderboard", help="Show all agents ranked")
    p.add_argument("--matrix-dir")

    p = sub.add_parser("promotions", help="Show promotion/demotion suggestions")
    p.add_argument("--matrix-dir")

    args = parser.parse_args()
    md = args.matrix_dir or os.environ.get("MATRIX_DIR", ".matrix")
    if not os.path.isdir(md):
        print(f"Error: {md} not found. Run init-matrix.sh first.", file=sys.stderr)
        sys.exit(1)

    if args.command == "record":
        domain = args.domain if args.domain != "auto" else None
        record_outcome(md, args.agent, args.ticket_id, args.outcome == "success", domain=domain)
    elif args.command == "recommend":
        avail = [a.strip() for a in args.agents.split(",") if a.strip()] or None
        recommend_agent(md, args.domain, available_agents=avail)
    elif args.command == "profile":
        get_profile(md, args.agent)
    elif args.command == "leaderboard":
        show_leaderboard(md)
    elif args.command == "promotions":
        get_promotions(md)

if __name__ == "__main__":
    main()
