#!/usr/bin/env python3
"""dna-fingerprint.py — Codebase DNA analysis for Neo Orchestrator.

Analyzes an existing codebase to generate a "DNA profile" capturing coding style,
patterns, and conventions. This profile is injected into every agent's context so
their output is indistinguishable from the existing codebase.

Usage:
    python3 dna-fingerprint.py analyze [project-dir] [--matrix-dir .matrix]
    python3 dna-fingerprint.py show [--matrix-dir .matrix]
    python3 dna-fingerprint.py instructions [--matrix-dir .matrix]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXTENSIONS = {
    "typescript": (".ts", ".tsx"), "javascript": (".js", ".jsx"),
    "python": (".py",), "go": (".go",),
}
ALL_EXTENSIONS = tuple(ext for exts in EXTENSIONS.values() for ext in exts)
MAX_SAMPLE = 50
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "__pycache__",
             "vendor", ".matrix", "coverage", ".turbo", ".cache"}
FRAMEWORK_MAP = {
    "next": "next.js", "nuxt": "nuxt", "gatsby": "gatsby", "express": "express",
    "fastify": "fastify", "koa": "koa", "react": "react", "vue": "vue",
    "svelte": "svelte", "angular": "angular",
}
DEP_PATTERNS = {
    "zustand": ("state_management", "zustand"), "redux": ("state_management", "redux"),
    "@reduxjs/toolkit": ("state_management", "redux-toolkit"),
    "mobx": ("state_management", "mobx"), "jotai": ("state_management", "jotai"),
    "recoil": ("state_management", "recoil"),
    "@tanstack/react-query": ("data_fetching", "react-query"), "swr": ("data_fetching", "swr"),
    "zod": ("validation", "zod"), "yup": ("validation", "yup"), "joi": ("validation", "joi"),
    "prisma": ("orm", "prisma"), "@prisma/client": ("orm", "prisma"),
    "drizzle-orm": ("orm", "drizzle"), "typeorm": ("orm", "typeorm"),
    "graphql": ("api_style", "graphql"), "@apollo/client": ("api_style", "graphql"),
    "@trpc/server": ("api_style", "trpc"), "trpc": ("api_style", "trpc"),
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    if not Path(path).exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def dominant(counter, threshold=0.6):
    total = sum(counter.values())
    if total == 0:
        return "unknown"
    top, count = counter.most_common(1)[0]
    return top if count / total >= threshold else "mixed"


def classify_case(name):
    if "_" in name and name == name.upper():
        return "UPPER_SNAKE"
    if "_" in name:
        return "snake_case"
    return "PascalCase" if name[0].isupper() else "camelCase"


# --- Discovery ---

def discover_files(project_dir):
    all_files = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            p = Path(root) / f
            if p.suffix in ALL_EXTENSIONS:
                all_files.append(p)
    src = [f for f in all_files if "src" in f.parts]
    other = [f for f in all_files if "src" not in f.parts]
    return (src + other)[:MAX_SAMPLE], len(all_files)


def detect_language(files):
    counts = Counter()
    for f in files:
        for lang, exts in EXTENSIONS.items():
            if f.suffix in exts:
                counts[lang] += 1
    return counts.most_common(1)[0][0] if counts else "unknown"


# --- Config analysis ---

def analyze_configs(project_dir):
    root = Path(project_dir)
    result = {"framework": {"name": None, "version": None}, "patterns": {},
              "test_framework": "unknown", "strict_mode": False, "formatting": {}}

    # package.json
    pkg = load_json(root / "package.json")
    if pkg:
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for key, name in FRAMEWORK_MAP.items():
            if key in deps:
                ver = deps[key].lstrip("^~>=").split(".")[0]
                result["framework"] = {"name": name, "version": f"{ver}.x"}
                break
        for dep, (cat, label) in DEP_PATTERNS.items():
            if dep in deps:
                result["patterns"][cat] = label
        for fw in ("vitest", "jest", "mocha"):
            if fw in deps:
                result["test_framework"] = fw
                break

    # tsconfig.json
    ts = load_json(root / "tsconfig.json")
    if ts:
        result["strict_mode"] = ts.get("compilerOptions", {}).get("strict", False)

    # .prettierrc
    for name in (".prettierrc", ".prettierrc.json"):
        prettier = load_json(root / name)
        if prettier:
            result["formatting"] = {
                "semicolons": prettier.get("semi", True),
                "quotes": "single" if prettier.get("singleQuote") else "double",
                "trailing_commas": prettier.get("trailingComma", "es5"),
                "indent_width": prettier.get("tabWidth", 2),
                "indent": "tabs" if prettier.get("useTabs") else "spaces",
            }
            break

    return result


# --- Source analysis (single pass) ---

def analyze_source(lines, files, config):
    # Counters
    c = {k: Counter() for k in ("var_case", "func_case", "class_case", "const_case",
         "import_style", "import_path", "indent", "indent_w", "semi", "quotes",
         "type_pref", "returns", "test_style", "test_pattern")}
    barrel = False
    try_catch = custom_err = err_boundary = jsdoc = file_headers = False
    comment_lines = func_count = class_count = 0
    in_block = in_func = False
    func_lines = 0
    brace_depth = 0
    func_lengths = []
    mock_pattern = "unknown"
    describe_count = test_call_count = 0

    for i, line in enumerate(lines):
        s = line.strip()

        # Naming: variables
        m = re.search(r'\b(?:const|let|var)\s+([a-zA-Z_]\w*)\s*[=:]', line)
        if m:
            n = m.group(1)
            if n.isupper() and "_" in n:
                c["const_case"]["UPPER_SNAKE"] += 1
            else:
                c["var_case"][classify_case(n)] += 1

        # Naming: functions
        for pat in (r'\bfunction\s+([a-zA-Z_]\w*)', r'\bdef\s+([a-zA-Z_]\w*)',
                     r'\b(?:const|let)\s+([a-zA-Z_]\w*)\s*=\s*(?:async\s*)?\('):
            m = re.search(pat, line)
            if m:
                c["func_case"][classify_case(m.group(1))] += 1

        # Naming: classes
        m = re.search(r'\bclass\s+([a-zA-Z_]\w*)', line)
        if m:
            c["class_case"][classify_case(m.group(1))] += 1
            class_count += 1

        # Imports
        if re.match(r'^import\s+\{', line):
            c["import_style"]["named"] += 1
        elif re.match(r'^import\s+\w', line):
            c["import_style"]["default"] += 1
        if re.search(r"""from\s+['"]\.\.?/""", line):
            c["import_path"]["relative"] += 1
        elif re.search(r"""from\s+['"][@\w]""", line):
            c["import_path"]["absolute"] += 1
        if re.match(r"""^export\s+(\{.*\}\s+from|[\*]\s+from)\s+['"]""", line):
            barrel = True

        # Formatting: indent
        if line and line[0] == "\t":
            c["indent"]["tabs"] += 1
        elif line and line[0] == " ":
            c["indent"]["spaces"] += 1
            w = len(line) - len(line.lstrip(" "))
            if w in (2, 4, 8):
                c["indent_w"][w] += 1

        # Formatting: semicolons
        if s and not s.startswith("//") and not s.startswith("/*"):
            if re.search(r'[a-zA-Z0-9\)\]\'\"]\s*;$', s):
                c["semi"]["true"] += 1
            elif re.search(r'[a-zA-Z0-9\)\]\'\"]\s*$', s) and not s.endswith("{"):
                c["semi"]["false"] += 1

        # Formatting: quotes (from imports)
        if "import" in line:
            c["quotes"]["single"] += len(re.findall(r"'[^']*'", line))
            c["quotes"]["double"] += len(re.findall(r'"[^"]*"', line))

        # Types
        if re.match(r'^(?:export\s+)?interface\s+', line):
            c["type_pref"]["interface"] += 1
        if re.match(r'^(?:export\s+)?type\s+\w+\s*=', line):
            c["type_pref"]["type"] += 1
        if re.search(r'\)\s*:\s*\w+.*\{', line):
            c["returns"]["true"] += 1
        elif re.search(r'\)\s*\{', line):
            c["returns"]["false"] += 1

        # Errors
        if re.search(r'\btry\s*\{', line):
            try_catch = True
        if re.search(r'class\s+\w+Error\s+extends\s+Error', line):
            custom_err = True
        if "ErrorBoundary" in line or "errorBoundary" in line:
            err_boundary = True

        # Comments
        if s.startswith("/**"):
            jsdoc = True
            in_block = True
            comment_lines += 1
            if i < 5:
                file_headers = True
            continue
        if s.startswith("/*"):
            in_block = True
            comment_lines += 1
            continue
        if in_block:
            comment_lines += 1
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("//") or s.startswith("#"):
            comment_lines += 1
            if i < 3:
                file_headers = True

        # Tests
        if re.search(r'\bdescribe\s*\(', line):
            describe_count += 1
        if re.search(r'\b(?:it|test)\s*\(', line):
            test_call_count += 1
        if mock_pattern == "unknown":
            if "vi.mock" in line or "vi.fn" in line:
                mock_pattern = "vi.mock"
            elif "jest.mock" in line or "jest.fn" in line:
                mock_pattern = "jest.mock"

        # Metrics: function length tracking
        if re.search(r'\b(?:function|def)\b', line) or re.search(r'=>\s*\{', line):
            func_count += 1
            if in_func and func_lines > 0:
                func_lengths.append(func_lines)
            in_func = True
            func_lines = 0
            brace_depth = 0
        if in_func:
            func_lines += 1
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0 and func_lines > 1:
                func_lengths.append(func_lines)
                in_func = False
                func_lines = 0

    # Trailing commas: count from counters
    trailing = Counter()
    for line in lines:
        if re.search(r',\s*$', line.rstrip()):
            trailing["all"] += 1
        elif re.search(r'[a-zA-Z0-9]\s*[\}\]]', line.rstrip()):
            trailing["none"] += 1

    # File naming
    file_case = Counter()
    for f in files:
        n = f.stem
        if n.startswith("__") or n.startswith("."):
            continue
        if "-" in n:
            file_case["kebab-case"] += 1
        elif "_" in n:
            file_case["snake_case"] += 1
        elif n[0].isupper():
            file_case["PascalCase"] += 1
        else:
            file_case["camelCase"] += 1

    # File lengths
    file_lens = []
    for f in files:
        try:
            file_lens.append(len(f.read_text(encoding="utf-8", errors="ignore").splitlines()))
        except OSError:
            pass

    # Test file patterns
    test_files = [f for f in files if ".test." in f.name or ".spec." in f.name or f.name.startswith("test_")]
    c["test_pattern"]["*.test.*"] = len([f for f in test_files if ".test." in f.name])
    c["test_pattern"]["*.spec.*"] = len([f for f in test_files if ".spec." in f.name])
    c["test_style"]["describe-it"] = describe_count
    c["test_style"]["test"] = test_call_count

    # Co-located tests
    test_dirs = {f.parent for f in test_files}
    src_dirs = {f.parent for f in files if f not in test_files}
    co_located = bool(test_dirs & src_dirs) if test_files else False

    # Formatting: merge config over detected (config wins)
    fmt_cfg = config.get("formatting", {})
    detected_fmt = {
        "indent": dominant(c["indent"]) if c["indent"] else "spaces",
        "indent_width": c["indent_w"].most_common(1)[0][0] if c["indent_w"] else 2,
        "semicolons": dominant(c["semi"]) == "true",
        "quotes": dominant(c["quotes"]) if c["quotes"] else "single",
        "trailing_commas": dominant(trailing) if trailing else "none",
    }
    formatting = {**detected_fmt, **fmt_cfg}

    # API style from source if not in deps
    patterns = dict(config.get("patterns", {}))
    if "api_style" not in patterns:
        rest = len(re.findall(r'\b(get|post|put|delete|patch)\s*\(', "\n".join(lines), re.I))
        gql = len(re.findall(r'\b(useQuery|useMutation|gql|graphql)\b', "\n".join(lines)))
        patterns["api_style"] = "graphql" if gql > rest else "REST"

    avg_func = round(sum(func_lengths) / len(func_lengths)) if func_lengths else 0
    avg_file = round(sum(file_lens) / len(file_lens)) if file_lens else 0
    style = "functional" if func_count > class_count * 3 else "class-based" if class_count > func_count else "mixed"
    total = len(lines)

    return {
        "conventions": {
            "naming": {
                "variables": dominant(c["var_case"]) if c["var_case"] else "camelCase",
                "functions": dominant(c["func_case"]) if c["func_case"] else "camelCase",
                "classes": dominant(c["class_case"]) if c["class_case"] else "PascalCase",
                "constants": dominant(c["const_case"]) if c["const_case"] else "UPPER_SNAKE",
                "files": dominant(file_case) if file_case else "kebab-case",
            },
            "imports": {
                "style": dominant(c["import_style"]) if c["import_style"] else "named",
                "path_style": dominant(c["import_path"]) if c["import_path"] else "absolute",
                "barrel_exports": barrel,
            },
            "formatting": formatting,
            "types": {
                "preferred": dominant(c["type_pref"]) if c["type_pref"] else "interface",
                "explicit_returns": dominant(c["returns"]) == "true" if c["returns"] else False,
                "strict_mode": config.get("strict_mode", False),
            },
            "errors": {
                "pattern": "try-catch" if try_catch else "unknown",
                "custom_errors": custom_err,
                "error_boundary": err_boundary,
            },
            "tests": {
                "framework": config.get("test_framework", "unknown"),
                "style": dominant(c["test_style"]) if c["test_style"] else "test",
                "file_pattern": dominant(c["test_pattern"]) if c["test_pattern"] else "*.test.*",
                "co_located": co_located,
                "mocking": mock_pattern,
            },
            "comments": {
                "density_per_100_lines": round((comment_lines / total) * 100, 1) if total else 0,
                "jsdoc": jsdoc,
                "file_headers": file_headers,
            },
        },
        "patterns": patterns,
        "metrics": {
            "avg_function_length": avg_func,
            "avg_file_length": avg_file,
            "max_file_length": max(file_lens) if file_lens else 0,
            "class_vs_functional": style,
            "abstraction_depth": min(5, max(1, avg_func // 10 + 1)) if avg_func else 2,
        },
    }


# --- Instruction generation ---

def generate_instructions(profile):
    c, p, m = profile["conventions"], profile["patterns"], profile["metrics"]
    f, lang = c["formatting"], profile["language"]
    lang_name = "TypeScript" if lang == "typescript" else lang.capitalize()
    parts = [
        f"Write {lang_name} with {f['quotes']} quotes, "
        f"{'with' if f['semicolons'] else 'no'} semicolons, {f['indent_width']}-space indent.",
        f"Use {c['imports']['style']} imports with {c['imports']['path_style']} paths.",
    ]
    if lang == "typescript":
        pref = "interfaces" if c["types"]["preferred"] == "interface" else "type aliases"
        parts.append(f"Prefer {pref} over {'types' if pref == 'interfaces' else 'interfaces'}.")
    if p.get("validation"):
        parts.append(f"Use {p['validation'].capitalize()} for validation.")
    ts = c["tests"]
    if ts["framework"] != "unknown":
        parts.append(f"Tests use {ts['framework']} with {ts['style']} blocks in {ts['file_pattern']} files.")
    parts.append(f"Functions should average {m['avg_function_length']} lines.")
    n = c["naming"]
    parts.append(f"Use {n['variables']} for variables/functions, {n['classes']} for classes/components, "
                 f"{n['files']} for files.")
    fw = profile.get("framework", {})
    if fw.get("name"):
        parts.append(f"Framework: {fw['name']} {fw.get('version', '')}.")
    return " ".join(parts)


# --- Commands ---

def analyze_project(project_dir, matrix_dir):
    project_dir = os.path.abspath(project_dir)
    files, total_count = discover_files(project_dir)
    if not files:
        print("Error: No source files found.", file=sys.stderr)
        sys.exit(1)

    all_lines = []
    for f in files:
        try:
            all_lines.extend(f.read_text(encoding="utf-8", errors="ignore").splitlines())
        except OSError:
            pass

    config = analyze_configs(project_dir)
    analysis = analyze_source(all_lines, files, config)

    profile = {
        "generated_at": now_iso(),
        "project_root": project_dir,
        "files_analyzed": len(files),
        "total_source_files": total_count,
        "language": detect_language(files),
        "framework": config["framework"],
        **analysis,
        "agent_instructions": "",
    }
    profile["agent_instructions"] = generate_instructions(profile)

    save_json(Path(matrix_dir) / "construct" / "dna-profile.json", profile)
    print(json.dumps(profile, indent=2))
    return profile


def show_profile(matrix_dir):
    profile = load_json(Path(matrix_dir) / "construct" / "dna-profile.json")
    if not profile:
        print("Error: No DNA profile found. Run 'analyze' first.", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(profile, indent=2))
    return profile


def show_instructions(matrix_dir):
    profile = load_json(Path(matrix_dir) / "construct" / "dna-profile.json")
    if not profile:
        print("Error: No DNA profile found. Run 'analyze' first.", file=sys.stderr)
        sys.exit(1)
    print(profile.get("agent_instructions", ""))
    return profile.get("agent_instructions", "")


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Neo Orchestrator DNA Fingerprint Analyzer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_a = sub.add_parser("analyze", help="Analyze a codebase and generate DNA profile")
    p_a.add_argument("project_dir", nargs="?", default=".", help="Project root directory")
    p_a.add_argument("--matrix-dir", default=".matrix", help="Path to .matrix directory")

    p_s = sub.add_parser("show", help="Display current DNA profile")
    p_s.add_argument("--matrix-dir", default=".matrix", help="Path to .matrix directory")

    p_i = sub.add_parser("instructions", help="Print agent instructions string")
    p_i.add_argument("--matrix-dir", default=".matrix", help="Path to .matrix directory")

    args = parser.parse_args()
    if args.command == "analyze":
        analyze_project(args.project_dir, args.matrix_dir)
    elif args.command == "show":
        show_profile(args.matrix_dir)
    elif args.command == "instructions":
        show_instructions(args.matrix_dir)


if __name__ == "__main__":
    main()
