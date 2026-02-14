#!/usr/bin/env python3
"""pipeline-generator.py -- Adaptive pipeline DAG generator for Neo Orchestrator.

Generates a custom pipeline based on detected project features rather than
running a fixed 7-phase pipeline. Scans PRD content, codebase structure, and
task graphs to skip irrelevant agents and adjust quality gates.

Usage:
    python3 pipeline-generator.py generate [project-dir] [--prd <path>] [--task-graph <path>] [--matrix-dir .matrix]
    python3 pipeline-generator.py show [--matrix-dir .matrix]
    python3 pipeline-generator.py agents [--matrix-dir .matrix]
    python3 pipeline-generator.py gates [--matrix-dir .matrix]
"""
import argparse, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

FEATURE_KEYWORDS = {
    "has_frontend": ["react", "next", "vue", "angular", "component", "ui", "page", "layout", "css", "tailwind"],
    "has_backend": ["express", "fastify", "hono", "route", "endpoint", "controller", "middleware", "api"],
    "has_database": ["prisma", "drizzle", "sequelize", "sql", "migration", "schema", "postgres", "mongo"],
    "has_auth": ["login", "signup", "jwt", "oauth", "session", "password", "authentication", "authorization"],
    "has_api_endpoints": ["endpoint", "route", "api", "rest", "graphql", "controller", "handler"],
    "has_realtime": ["websocket", "socket.io", "sse", "realtime", "live", "stream", "pubsub"],
    "has_file_uploads": ["upload", "multipart", "formdata", "file upload", "multer", "s3", "storage"],
    "has_payments": ["stripe", "payment", "billing", "subscription", "checkout", "invoice"],
}
CODEBASE_MARKERS = {
    "has_ci_cd": [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci"],
    "has_docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore"],
}
CLI_MARKERS = ["bin", "commander", "yargs", "meow", "cli", "oclif", "inquirer"]

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data

def resolve_matrix_dir(arg):
    path = Path(arg)
    if not path.is_dir():
        print(f"Error: {path} not found. Run init-matrix.sh first.", file=sys.stderr)
        sys.exit(1)
    return path

def pipeline_path(matrix_dir):
    return Path(matrix_dir) / "construct" / "pipeline.json"

# --- Feature detection ---

def _scan_text(text):
    text_lower = text.lower()
    return {feat: any(kw in text_lower for kw in kws) for feat, kws in FEATURE_KEYWORDS.items()}

def _scan_codebase(project_dir):
    project = Path(project_dir)
    detected = {"has_ci_cd": False, "has_docker": False, "is_cli_tool": False, "is_library": False}
    for feat, markers in CODEBASE_MARKERS.items():
        if any((project / m).exists() for m in markers):
            detected[feat] = True
    pkg_path = project / "package.json"
    if pkg_path.exists():
        try:
            pkg = load_json(pkg_path)
            all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            dep_names = " ".join(all_deps.keys()).lower()
            if "bin" in pkg or any(re.search(rf'\b{m}\b', dep_names) for m in CLI_MARKERS):
                detected["is_cli_tool"] = True
            scripts = pkg.get("scripts", {})
            has_lib = any(k in pkg for k in ["main", "module", "types", "exports", "typings"])
            if has_lib and "start" not in scripts and "dev" not in scripts and not detected["is_cli_tool"]:
                detected["is_library"] = True
            for k, v in _scan_text(json.dumps(pkg)).items():
                if v:
                    detected[k] = True
        except (json.JSONDecodeError, OSError):
            pass
    if (project / "src" / "components").exists() or (project / "app").exists():
        detected["has_frontend"] = True
    if (project / "src" / "routes").exists() or (project / "src" / "controllers").exists():
        detected["has_backend"] = True
    if (project / "prisma").exists() or (project / "migrations").exists():
        detected["has_database"] = True
    return detected

def detect_features(project_dir, prd_content=None, task_graph=None):
    """Detect project features from PRD, codebase, and task graph. Any source match wins."""
    features = {k: False for k in [
        "has_frontend", "has_backend", "has_database", "has_auth", "has_api_endpoints",
        "has_realtime", "has_file_uploads", "has_payments", "has_ci_cd", "has_docker",
        "is_cli_tool", "is_library",
    ]}
    sources = []
    if prd_content:
        sources.append(_scan_text(prd_content))
    if project_dir and Path(project_dir).is_dir():
        sources.append(_scan_codebase(project_dir))
    if task_graph:
        tasks = task_graph.get("tasks", [])
        blob = " ".join(f"{t.get('title','')} {t.get('description','')} {' '.join(t.get('files',[]))}" for t in tasks)
        sources.append(_scan_text(blob))
    for src in sources:
        for k, v in src.items():
            if v:
                features[k] = True
    return features

# --- Agent / gate rules ---

def should_skip_agent(agent, features):
    """Check if an agent is needed given detected features."""
    f = features.get
    rules = {
        "niobe": not f("has_frontend") or f("is_cli_tool") or f("is_library"),
        "dozer": not f("has_backend") and not f("has_api_endpoints") and not f("has_database"),
        "tank": (not f("has_ci_cd") and not f("has_docker")) or f("is_library"),
        "shannon": not f("has_api_endpoints") or f("is_cli_tool") or f("is_library"),
    }
    return rules.get(agent, False)

def _skip_reason(agent, features):
    if agent == "niobe":
        return "CLI tool project" if features.get("is_cli_tool") else "library project" if features.get("is_library") else "no frontend detected"
    if agent == "dozer":
        return "no backend or database detected"
    if agent == "tank":
        return "library project" if features.get("is_library") else "no CI/CD or Docker detected"
    if agent == "shannon":
        return "CLI tool project" if features.get("is_cli_tool") else "library project" if features.get("is_library") else "no API endpoints detected"
    return "not needed for this project type"

def _classify_project(features):
    if features.get("is_cli_tool"): return "cli-tool"
    if features.get("is_library"): return "library"
    fe, be = features.get("has_frontend"), features.get("has_backend")
    if fe and be: return "full-stack-web"
    if fe: return "frontend-only"
    if be: return "backend-api"
    return "unknown"

# --- Pipeline generation ---

def _base_phases():
    return [
        {"id": "source",     "name": "THE SOURCE",     "order": 0, "agents": [],                                          "gates": []},
        {"id": "red-pill",   "name": "RED PILL",       "order": 1, "agents": ["neo"],                                     "gates": []},
        {"id": "construct",  "name": "THE CONSTRUCT",  "order": 2, "agents": ["oracle", "architect"],                     "gates": []},
        {"id": "jacking-in", "name": "JACKING IN",     "order": 3, "agents": ["morpheus", "dozer", "niobe", "tank"],      "gates": []},
        {"id": "bullet-time","name": "BULLET TIME",    "order": 4, "agents": ["neo"],                                     "gates": ["integration-check"]},
        {"id": "sentinels",  "name": "SENTINELS",      "order": 5, "agents": ["smith", "trinity", "shannon", "switch", "mouse"], "gates": ["smith-review", "trinity-security", "shannon-pentest", "switch-coverage"]},
        {"id": "zion",       "name": "ZION",           "order": 6, "agents": ["sati", "trainman"],                        "gates": []},
    ]

def _gate_config(features):
    threshold = 90 if features.get("has_payments") else 80
    cfg = {
        "smith-review":    {"enabled": True, "agent": "smith",   "model": "opus"},
        "trinity-security":{"enabled": True, "agent": "trinity", "model": "sonnet"},
        "shannon-pentest": {"enabled": bool(features.get("has_api_endpoints") and not features.get("is_cli_tool")), "agent": "shannon", "model": "sonnet"},
        "switch-coverage": {"enabled": True, "agent": "switch",  "model": "sonnet", "threshold": threshold},
    }
    if features.get("has_realtime"):
        cfg["stress-test"] = {"enabled": True, "agent": "mouse", "model": "sonnet"}
    return cfg

def generate_pipeline(matrix_dir, features, config=None):
    """Generate a full pipeline DAG adapted to detected features. Writes to .matrix/construct/pipeline.json."""
    phases, gate_cfg, opts = _base_phases(), _gate_config(features), []

    # Skip agents
    for agent in ("niobe", "dozer", "tank", "shannon"):
        if should_skip_agent(agent, features):
            opts.append(f"Skipped {agent}: {_skip_reason(agent, features)}")
            for p in phases:
                if agent in p["agents"]:
                    p["agents"] = [a for a in p["agents"] if a != agent]

    # Gate adjustments
    if not features.get("has_api_endpoints") or features.get("is_cli_tool"):
        opts.append("Disabled shannon-pentest: no HTTP endpoints to test")
    if features.get("has_payments"):
        opts.append("Enforced 90% coverage threshold: payment-handling project")
    if features.get("has_realtime"):
        sentinels = next((p for p in phases if p["id"] == "sentinels"), None)
        if sentinels and "stress-test" not in sentinels["gates"]:
            sentinels["gates"] = [*sentinels["gates"], "stress-test"]
        opts.append("Added stress-test gate: realtime features detected")
    if features.get("has_auth"):
        opts.append("Added early trinity pass: auth-heavy project")
        sentinels = next((p for p in phases if p["id"] == "sentinels"), None)
        if sentinels and "trinity" in sentinels["agents"]:
            sentinels["agents"] = ["trinity", *(a for a in sentinels["agents"] if a != "trinity")]

    # Mark empty non-structural phases as skipped
    structural = {"source", "red-pill", "bullet-time", "zion"}
    for p in phases:
        p["skip"] = p["id"] not in structural and not p["agents"]
        p["skip_reason"] = "no agents remaining after adaptation" if p["skip"] else None

    if features.get("has_backend") and not features.get("has_frontend"):
        opts.append("Backend-only: frontend agents removed from implementation wave")

    # Remove disabled gates from phase gate lists
    for p in phases:
        p["gates"] = [g for g in p["gates"] if gate_cfg.get(g, {}).get("enabled", True)]

    pipeline = {
        "generated_at": now_iso(), "project_type": _classify_project(features),
        "features_detected": features, "phases": phases,
        "gate_config": gate_cfg, "optimizations": opts,
    }
    if config and "gate_overrides" in config:
        for gid, ov in config["gate_overrides"].items():
            if gid in pipeline["gate_config"]:
                pipeline["gate_config"][gid] = {**pipeline["gate_config"][gid], **ov}

    save_json(pipeline_path(matrix_dir), pipeline)
    return pipeline

# --- Query functions ---

def get_active_agents(matrix_dir):
    """Returns list of agents needed for this pipeline."""
    path = pipeline_path(matrix_dir)
    if not path.exists():
        return []
    agents = set()
    for p in load_json(path).get("phases", []):
        if not p.get("skip"):
            agents.update(p.get("agents", []))
    return sorted(agents)

def get_active_gates(matrix_dir):
    """Returns list of enabled gates."""
    path = pipeline_path(matrix_dir)
    if not path.exists():
        return []
    return [gid for gid, g in load_json(path).get("gate_config", {}).items() if g.get("enabled")]

# --- Display ---

def _display(pipeline):
    print(f"\n  Pipeline: {pipeline['project_type']}")
    print(f"  Generated: {pipeline['generated_at']}\n  {'=' * 50}")
    for p in pipeline["phases"]:
        tag = " [SKIP]" if p.get("skip") else ""
        print(f"\n  Phase {p['order']}: {p['name']}{tag}")
        print(f"    Agents: {', '.join(p['agents']) or '(none)'}")
        if p["gates"]:
            print(f"    Gates:  {', '.join(p['gates'])}")
        if p.get("skip_reason"):
            print(f"    Reason: {p['skip_reason']}")
    if pipeline.get("optimizations"):
        print(f"\n  {'=' * 50}\n  Optimizations:")
        for o in pipeline["optimizations"]:
            print(f"    - {o}")
    feats = pipeline.get("features_detected", {})
    print(f"\n  Detected: {', '.join(k for k, v in feats.items() if v) or '(none)'}")
    print(f"  Absent:   {', '.join(k for k, v in feats.items() if not v) or '(none)'}\n")

# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Neo Orchestrator Adaptive Pipeline Generator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Generate adaptive pipeline")
    p_gen.add_argument("project_dir", nargs="?", default=".", help="Project root directory")
    p_gen.add_argument("--prd", default=None, help="Path to PRD file")
    p_gen.add_argument("--task-graph", default=None, help="Path to task graph JSON")
    p_gen.add_argument("--matrix-dir", default=".matrix", help="Path to .matrix directory")

    for name in ("show", "agents", "gates"):
        p = sub.add_parser(name, help=f"{'Display current pipeline' if name == 'show' else 'List active ' + name}")
        p.add_argument("--matrix-dir", default=".matrix")

    args = parser.parse_args()

    if args.command == "generate":
        prd_content = None
        if args.prd:
            p = Path(args.prd)
            if p.exists(): prd_content = p.read_text()
            else: print(f"Warning: PRD file {args.prd} not found.", file=sys.stderr)
        task_graph = None
        if args.task_graph:
            p = Path(args.task_graph)
            if p.exists(): task_graph = load_json(p)
            else: print(f"Warning: Task graph {args.task_graph} not found.", file=sys.stderr)
        matrix_dir = Path(args.matrix_dir)
        if not matrix_dir.is_dir():
            print(f"Error: {matrix_dir} not found. Run init-matrix.sh first.", file=sys.stderr)
            sys.exit(1)
        pipeline = generate_pipeline(matrix_dir, detect_features(args.project_dir, prd_content, task_graph))
        _display(pipeline)
        print(json.dumps(pipeline, indent=2))

    elif args.command == "show":
        md = resolve_matrix_dir(args.matrix_dir)
        pp = pipeline_path(md)
        if not pp.exists():
            print("No pipeline generated yet. Run 'generate' first.", file=sys.stderr); sys.exit(1)
        _display(load_json(pp))

    elif args.command == "agents":
        agents = get_active_agents(resolve_matrix_dir(args.matrix_dir))
        if not agents:
            print("No pipeline generated yet.", file=sys.stderr); sys.exit(1)
        print(json.dumps(agents, indent=2))

    elif args.command == "gates":
        gates = get_active_gates(resolve_matrix_dir(args.matrix_dir))
        if not gates:
            print("No active gates (or no pipeline generated).", file=sys.stderr); sys.exit(1)
        print(json.dumps(gates, indent=2))

if __name__ == "__main__":
    main()
