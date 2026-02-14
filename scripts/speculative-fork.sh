#!/usr/bin/env bash
# speculative-fork.sh — Speculative architecture forking for Neo Orchestrator
# Usage: bash speculative-fork.sh fork <name> "<description>" [project-dir]
#        bash speculative-fork.sh list [project-dir]
#        bash speculative-fork.sh compare [project-dir]
#        bash speculative-fork.sh pick <fork-name> [project-dir]
#        bash speculative-fork.sh abort [project-dir]
set -euo pipefail

COMMAND="${1:?Usage: speculative-fork.sh <fork|list|compare|pick|abort> [args...]}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[FORK]${NC} $1"; }
err() { echo -e "${RED}[FORK]${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[FORK]${NC} $1"; }

# ── Helpers ──────────────────────────────────────────────────────────────────

post_to_blackboard() {
    local agent="$1" event_type="$2" data="$3" matrix_dir="$4"
    python3 "$SKILL_DIR/scripts/blackboard.py" post "$agent" "$event_type" "$data" \
        --matrix-dir "$matrix_dir" 2>/dev/null || true
}

ensure_forks_dir() {
    local matrix_dir="$1"
    mkdir -p "$matrix_dir/forks"
}

read_index() {
    local matrix_dir="$1"
    local index="$matrix_dir/forks/index.json"
    if [ -f "$index" ]; then
        cat "$index"
    else
        echo "null"
    fi
}

write_index() {
    local matrix_dir="$1" content="$2"
    echo "$content" > "$matrix_dir/forks/index.json"
}

# ── fork <name> <description> [project-dir] ─────────────────────────────────

do_fork() {
    local name="${2:?Usage: speculative-fork.sh fork <name> \"<description>\" [project-dir]}"
    local description="${3:?Usage: speculative-fork.sh fork <name> \"<description>\" [project-dir]}"
    local project_dir="${4:-.}"
    local matrix_dir="$project_dir/.matrix"

    if [ ! -d "$matrix_dir" ]; then
        err "No .matrix/ directory found. Run init-matrix.sh first."
        exit 1
    fi

    cd "$project_dir"

    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        err "Not a git repository."
        exit 1
    fi

    ensure_forks_dir "$matrix_dir"
    local branch="matrix/fork/$name"
    local base_commit
    base_commit="$(git rev-parse HEAD)"
    local now
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    # If first fork, create the pre-fork tag and index
    local index
    index="$(read_index "$matrix_dir")"
    if [ "$index" = "null" ]; then
        log "First fork — tagging current state as matrix/pre-fork"
        git tag -f "matrix/pre-fork" HEAD
        write_index "$matrix_dir" "$(python3 -c "
import json
print(json.dumps({
    'status': 'active',
    'pre_fork_commit': '$base_commit',
    'pre_fork_tag': 'matrix/pre-fork',
    'forks': ['$name'],
    'winner': None,
    'created_at': '$now'
}, indent=2))
")"
    else
        # Append fork name to existing index
        python3 -c "
import json
with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)
if '$name' in idx['forks']:
    raise SystemExit('Fork $name already exists')
idx['forks'] = [*idx['forks'], '$name']
with open('$matrix_dir/forks/index.json', 'w') as f:
    json.dump(idx, f, indent=2)
"
    fi

    # Create the branch from current HEAD (pre-fork point)
    git checkout -b "$branch" 2>/dev/null || {
        err "Branch $branch already exists."
        exit 1
    }

    # Write fork metadata
    python3 -c "
import json
print(json.dumps({
    'name': '$name',
    'description': '$description',
    'branch': '$branch',
    'created_at': '$now',
    'status': 'active',
    'base_commit': '$base_commit',
    'metrics': None
}, indent=2))
" > "$matrix_dir/forks/${name}.json"

    post_to_blackboard "oracle" "DECISION_MADE" \
        "{\"action\":\"fork_created\",\"fork\":\"$name\",\"description\":\"$description\",\"branch\":\"$branch\"}" \
        "$matrix_dir"

    log "Fork '${name}' created on branch ${branch}"
    log "Switched to branch ${branch} — start building."
}

# ── list [project-dir] ──────────────────────────────────────────────────────

do_list() {
    local project_dir="${2:-.}"
    local matrix_dir="$project_dir/.matrix"

    if [ ! -f "$matrix_dir/forks/index.json" ]; then
        warn "No forks found."
        exit 0
    fi

    python3 -c "
import json, os

with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)

print()
print('\033[0;36m  Active Speculative Forks\033[0m')
print('  ' + '=' * 58)

for name in idx['forks']:
    path = os.path.join('$matrix_dir', 'forks', name + '.json')
    if not os.path.exists(path):
        continue
    with open(path) as f:
        fork = json.load(f)
    status_color = {
        'active': '\033[0;32m',
        'picked': '\033[0;36m',
        'discarded': '\033[0;31m',
        'aborted': '\033[1;33m',
    }.get(fork['status'], '\033[0m')
    nc = '\033[0m'
    score = ''
    if fork.get('metrics') and fork['metrics'].get('score') is not None:
        score = f\"  score={fork['metrics']['score']}\"
    print(f\"  {status_color}{fork['status']:10s}{nc}  {fork['name']:20s}  {fork['branch']}{score}\")
    print(f\"             {fork['description']}\")

print()
print(f\"  Winner: {idx.get('winner') or 'undecided'}\")
print()
"
}

# ── compare [project-dir] ───────────────────────────────────────────────────

do_compare() {
    local project_dir="${2:-.}"
    local matrix_dir="$project_dir/.matrix"

    if [ ! -f "$matrix_dir/forks/index.json" ]; then
        err "No forks to compare."
        exit 1
    fi

    cd "$project_dir"
    local original_branch
    original_branch="$(git rev-parse --abbrev-ref HEAD)"

    python3 -c "
import json
with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)
print(' '.join(idx['forks']))
" | read -r -a fork_names || true

    local base_commit
    base_commit="$(python3 -c "
import json
with open('$matrix_dir/forks/index.json') as f:
    print(json.load(f)['pre_fork_commit'])
")"

    # Gather metrics for each fork
    for fname in "${fork_names[@]}"; do
        local fork_file="$matrix_dir/forks/${fname}.json"
        [ -f "$fork_file" ] || continue

        local status
        status="$(python3 -c "import json; print(json.load(open('$fork_file'))['status'])")"
        [ "$status" = "active" ] || continue

        local branch
        branch="$(python3 -c "import json; print(json.load(open('$fork_file'))['branch'])")"

        git checkout "$branch" --quiet 2>/dev/null || continue

        # Count diff stats against base
        local files_changed=0 lines_added=0 lines_removed=0
        local diff_stat
        diff_stat="$(git diff --shortstat "$base_commit"...HEAD 2>/dev/null || echo "")"
        if [ -n "$diff_stat" ]; then
            files_changed="$(echo "$diff_stat" | grep -oE '[0-9]+ file' | grep -oE '[0-9]+' || echo 0)"
            lines_added="$(echo "$diff_stat" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo 0)"
            lines_removed="$(echo "$diff_stat" | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || echo 0)"
        fi

        # Run tests if available
        local tests_pass=0 tests_total=0 coverage=0
        if [ -f "package.json" ]; then
            local test_output
            test_output="$(npm test -- --coverage 2>&1 || npx jest --coverage 2>&1 || npx vitest run --coverage 2>&1 || echo "")"
            tests_total="$(echo "$test_output" | grep -oE 'Tests:\s+[0-9]+' | grep -oE '[0-9]+' | tail -1 || echo 0)"
            tests_pass="$(echo "$test_output" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo 0)"
            coverage="$(echo "$test_output" | grep -oE '(All files|Statements|Lines)\s*\|\s*[0-9.]+' | grep -oE '[0-9.]+' | head -1 || echo 0)"
        fi
        [ -z "$tests_pass" ] && tests_pass=0
        [ -z "$tests_total" ] && tests_total=0
        [ -z "$coverage" ] && coverage=0

        # Count dependencies added
        local deps_added=0
        local pkg_diff
        pkg_diff="$(git diff "$base_commit"...HEAD -- package.json 2>/dev/null || echo "")"
        if [ -n "$pkg_diff" ]; then
            deps_added="$(echo "$pkg_diff" | grep -cE '^\+\s*"[^"]+":' || echo 0)"
        fi

        # Read cost from .matrix/costs.json
        local est_cost="0.00"
        if [ -f "$matrix_dir/costs.json" ]; then
            est_cost="$(python3 -c "
import json
with open('$matrix_dir/costs.json') as f:
    costs = json.load(f)
fork_costs = [c for c in costs.get('entries', []) if c.get('fork') == '$fname']
total = sum(c.get('cost', 0) for c in fork_costs)
print(f'{total:.2f}')
" 2>/dev/null || echo "0.00")"
        fi

        # Store metrics
        python3 -c "
import json
with open('$fork_file') as f:
    fork = json.load(f)
fork['metrics'] = {
    'files_changed': int('${files_changed:-0}' or 0),
    'lines_added': int('${lines_added:-0}' or 0),
    'lines_removed': int('${lines_removed:-0}' or 0),
    'tests_pass': int('${tests_pass:-0}' or 0),
    'tests_total': int('${tests_total:-0}' or 0),
    'coverage': float('${coverage:-0}' or 0),
    'deps_added': int('${deps_added:-0}' or 0),
    'est_cost': float('${est_cost:-0}' or 0),
    'score': None
}
with open('$fork_file', 'w') as f:
    json.dump(fork, f, indent=2)
"
    done

    # Return to original branch
    git checkout "$original_branch" --quiet 2>/dev/null || true

    # Score and display comparison table
    MATRIX_DIR_ABS="$(cd "$matrix_dir" && pwd)"
    export MATRIX_DIR_ABS
    python3 << 'PYEOF'
import json, os, sys

matrix_dir = os.environ.get("MATRIX_DIR_ABS", ".matrix")

with open(os.path.join(matrix_dir, "forks", "index.json")) as f:
    idx = json.load(f)

forks = []
for name in idx["forks"]:
    path = os.path.join(matrix_dir, "forks", name + ".json")
    if not os.path.exists(path):
        continue
    with open(path) as f:
        fork = json.load(f)
    if fork["status"] != "active" or not fork.get("metrics"):
        continue
    forks.append(fork)

if len(forks) < 2:
    print("\033[0;31m[FORK]\033[0m Need at least 2 active forks with metrics to compare.")
    sys.exit(1)

# Compute scores
max_tests = max((f["metrics"]["tests_total"] for f in forks), default=1) or 1
max_cov = 100.0
min_deps = min((f["metrics"]["deps_added"] for f in forks), default=0)
max_deps = max((f["metrics"]["deps_added"] for f in forks), default=1) or 1
min_lines = min((f["metrics"]["lines_added"] for f in forks), default=0)
max_lines = max((f["metrics"]["lines_added"] for f in forks), default=1) or 1
min_cost = min((f["metrics"]["est_cost"] for f in forks), default=0)
max_cost = max((f["metrics"]["est_cost"] for f in forks), default=1) or 0.01
min_files = min((f["metrics"]["files_changed"] for f in forks), default=0)
max_files = max((f["metrics"]["files_changed"] for f in forks), default=1) or 1

for fork in forks:
    m = fork["metrics"]
    test_ratio = (m["tests_pass"] / m["tests_total"]) if m["tests_total"] > 0 else 1.0
    score = 0
    score += 30 * test_ratio                                                     # tests passing
    score += 20 * (m["coverage"] / max_cov)                                       # coverage
    score += 15 * (1 - (m["deps_added"] - min_deps) / max(max_deps - min_deps, 1))  # fewer deps
    score += 15 * (1 - (m["lines_added"] - min_lines) / max(max_lines - min_lines, 1))  # simplicity
    score += 10 * (1 - (m["est_cost"] - min_cost) / max(max_cost - min_cost, 0.01))  # lower cost
    score += 10 * (1 - (m["files_changed"] - min_files) / max(max_files - min_files, 1))  # fewer files
    m["score"] = round(score)

    # Write back
    path = os.path.join(matrix_dir, "forks", fork["name"] + ".json")
    with open(path, "w") as f:
        json.dump(fork, f, indent=2)

def stars(score):
    filled = min(5, score // 20)
    return "\u2605" * filled + "\u2606" * (5 - filled)

# Build table
names = [f["name"] for f in forks]
col_w = [max(18, len(n) + 4) for n in names]

def pad(s, w):
    return s + " " * max(0, w - len(s))

sep_inner = "\u2550" * 18
header_sep = "\u2550".join(["\u2550" * 18] + ["\u2550" * w for w in col_w])
row_sep = "\u2550".join(["\u2550" * 18] + ["\u2550" * w for w in col_w])

print()
print("\u2554" + "\u2550" * (20 + sum(col_w) + len(col_w) * 3) + "\u2557")
print("\u2551  SPECULATIVE FORK COMPARISON" + " " * (sum(col_w) + len(col_w) * 3 - 10) + "\u2551")

# Header row
h = "\u2551" + pad("  Metric", 18) + "\u2551"
for i, name in enumerate(names):
    h += pad("  " + name, col_w[i]) + "\u2551"
print("\u2560" + "\u2550" * 18 + "\u2566" + "\u2566".join(["\u2550" * w for w in col_w]) + "\u2563")
print(h)
print("\u2560" + "\u2550" * 18 + "\u256C" + "\u256C".join(["\u2550" * w for w in col_w]) + "\u2563")

def row(label, values):
    r = "\u2551" + pad("  " + label, 18) + "\u2551"
    for i, v in enumerate(values):
        r += pad("  " + str(v), col_w[i]) + "\u2551"
    print(r)

metrics_rows = [
    ("Files changed",  [str(f["metrics"]["files_changed"]) for f in forks]),
    ("Lines added",    [str(f["metrics"]["lines_added"]) for f in forks]),
    ("Lines removed",  [str(f["metrics"]["lines_removed"]) for f in forks]),
    ("Tests passing",  [f'{f["metrics"]["tests_pass"]}/{f["metrics"]["tests_total"]}' for f in forks]),
    ("Coverage",       [f'{f["metrics"]["coverage"]:.0f}%' for f in forks]),
    ("Dependencies",   [f'+{f["metrics"]["deps_added"]}' for f in forks]),
    ("Est. cost",      [f'${f["metrics"]["est_cost"]:.2f}' for f in forks]),
]

for label, values in metrics_rows:
    row(label, values)

print("\u2560" + "\u2550" * 18 + "\u256C" + "\u256C".join(["\u2550" * w for w in col_w]) + "\u2563")
row("SCORE", [f"{stars(f['metrics']['score'])} ({f['metrics']['score']})" for f in forks])
print("\u255A" + "\u2550" * 18 + "\u2569" + "\u2569".join(["\u2550" * w for w in col_w]) + "\u255D")
print()

best = max(forks, key=lambda f: f["metrics"]["score"])
print(f"\033[0;32m[FORK]\033[0m Recommendation: pick '{best['name']}' (score {best['metrics']['score']})")
print()
PYEOF
}

# ── pick <fork-name> [project-dir] ──────────────────────────────────────────

do_pick() {
    local name="${2:?Usage: speculative-fork.sh pick <fork-name> [project-dir]}"
    local project_dir="${3:-.}"
    local matrix_dir="$project_dir/.matrix"

    if [ ! -f "$matrix_dir/forks/${name}.json" ]; then
        err "Fork '${name}' not found."
        exit 1
    fi

    cd "$project_dir"

    local status
    status="$(python3 -c "import json; print(json.load(open('$matrix_dir/forks/${name}.json'))['status'])")"
    if [ "$status" != "active" ]; then
        err "Fork '${name}' is not active (status: ${status})."
        exit 1
    fi

    local main_branch
    main_branch="$(git rev-parse --abbrev-ref HEAD)"
    # If we're on a fork branch, switch to the pre-fork state first
    if [[ "$main_branch" == matrix/fork/* ]]; then
        main_branch="$(python3 -c "
import json, subprocess
with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)
commit = idx['pre_fork_commit']
# Find the branch that contains this commit (excluding fork branches)
result = subprocess.run(['git', 'branch', '--contains', commit], capture_output=True, text=True)
for line in result.stdout.strip().split('\n'):
    b = line.strip().lstrip('* ')
    if not b.startswith('matrix/fork/'):
        print(b)
        break
else:
    print('main')
")"
    fi

    git checkout "$main_branch" --quiet 2>/dev/null

    local fork_branch="matrix/fork/$name"
    log "Merging fork '${name}' into ${main_branch}..."
    git merge "$fork_branch" --no-ff -m "merge: picked fork ${name}" || {
        err "Merge conflict. Resolve manually, then re-run pick."
        exit 1
    }

    # Update all fork statuses
    python3 -c "
import json, os

with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)
idx['winner'] = '$name'
idx['status'] = 'resolved'

for fork_name in idx['forks']:
    path = os.path.join('$matrix_dir', 'forks', fork_name + '.json')
    if not os.path.exists(path):
        continue
    with open(path) as f:
        fork = json.load(f)
    fork['status'] = 'picked' if fork_name == '$name' else 'discarded'
    with open(path, 'w') as f:
        json.dump(fork, f, indent=2)

with open('$matrix_dir/forks/index.json', 'w') as f:
    json.dump(idx, f, indent=2)
"

    # Delete all fork branches
    python3 -c "
import json
with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)
for name in idx['forks']:
    print('matrix/fork/' + name)
" | while read -r branch; do
        git branch -D "$branch" 2>/dev/null || true
    done

    # Remove pre-fork tag
    git tag -d "matrix/pre-fork" 2>/dev/null || true

    post_to_blackboard "oracle" "DECISION_MADE" \
        "{\"action\":\"fork_picked\",\"winner\":\"$name\",\"losers\":$(python3 -c "
import json
with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)
print(json.dumps([n for n in idx['forks'] if n != '$name']))
")}" \
        "$matrix_dir"

    log "Fork '${name}' merged. Losers discarded. Pre-fork tag removed."
}

# ── abort [project-dir] ────────────────────────────────────────────────────

do_abort() {
    local project_dir="${2:-.}"
    local matrix_dir="$project_dir/.matrix"

    if [ ! -f "$matrix_dir/forks/index.json" ]; then
        err "No forks to abort."
        exit 1
    fi

    cd "$project_dir"

    local main_branch
    main_branch="$(git rev-parse --abbrev-ref HEAD)"
    if [[ "$main_branch" == matrix/fork/* ]]; then
        main_branch="main"
    fi

    # Switch to main and reset to pre-fork
    git checkout "$main_branch" --quiet 2>/dev/null || git checkout main --quiet 2>/dev/null
    if git tag -l "matrix/pre-fork" | grep -q .; then
        warn "Resetting to pre-fork state..."
        git reset --hard "matrix/pre-fork"
    fi

    # Delete all fork branches
    python3 -c "
import json
with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)
for name in idx['forks']:
    print('matrix/fork/' + name)
" | while read -r branch; do
        git branch -D "$branch" 2>/dev/null || true
    done

    # Mark all forks as aborted
    python3 -c "
import json, os

with open('$matrix_dir/forks/index.json') as f:
    idx = json.load(f)
idx['status'] = 'aborted'

for fork_name in idx['forks']:
    path = os.path.join('$matrix_dir', 'forks', fork_name + '.json')
    if not os.path.exists(path):
        continue
    with open(path) as f:
        fork = json.load(f)
    fork['status'] = 'aborted'
    with open(path, 'w') as f:
        json.dump(fork, f, indent=2)

with open('$matrix_dir/forks/index.json', 'w') as f:
    json.dump(idx, f, indent=2)
"

    # Remove pre-fork tag
    git tag -d "matrix/pre-fork" 2>/dev/null || true

    log "All forks aborted. Returned to pre-fork state."
}

# ── Dispatch ────────────────────────────────────────────────────────────────

case "$COMMAND" in
    fork)    do_fork "$@" ;;
    list)    do_list "$@" ;;
    compare) do_compare "$@" ;;
    pick)    do_pick "$@" ;;
    abort)   do_abort "$@" ;;
    *)
        err "Unknown command: $COMMAND"
        err "Usage: speculative-fork.sh <fork|list|compare|pick|abort> [args...]"
        exit 1
        ;;
esac
