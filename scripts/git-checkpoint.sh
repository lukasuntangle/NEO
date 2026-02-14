#!/usr/bin/env bash
# git-checkpoint.sh — Atomic commits + rollback for Neo Orchestrator
# Usage: bash git-checkpoint.sh "<message>" [project-dir]
#        bash git-checkpoint.sh rollback <tag> [project-dir]
set -euo pipefail

ACTION="${1:?Usage: git-checkpoint.sh <message> [project-dir] OR git-checkpoint.sh rollback <tag> [project-dir]}"
PROJECT_DIR="${2:-.}"
MATRIX_DIR="${PROJECT_DIR}/.matrix"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[CHECKPOINT]${NC} $1"; }
err() { echo -e "${RED}[CHECKPOINT]${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[CHECKPOINT]${NC} $1"; }

cd "$PROJECT_DIR"

# Ensure we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    err "Not a git repository. Initialize with 'git init' first."
    exit 1
fi

if [ "$ACTION" = "rollback" ]; then
    TAG="${2:?Rollback requires a tag name}"
    PROJECT_DIR="${3:-.}"

    if ! git tag -l "$TAG" | grep -q .; then
        err "Tag '$TAG' not found. Available matrix tags:"
        git tag -l "matrix/*" 2>/dev/null || echo "  (none)"
        exit 1
    fi

    warn "Rolling back to tag: $TAG"
    git checkout "$TAG"
    log "Rolled back to $TAG"
    exit 0
fi

# Regular checkpoint
MESSAGE="$ACTION"
TAG_NAME="matrix/${TIMESTAMP}"

# Stage all changes (excluding .matrix/)
git add -A -- ':!.matrix' ':!.matrix/**' 2>/dev/null || git add -A 2>/dev/null || true

# Check if there are changes to commit
if git diff --cached --quiet 2>/dev/null; then
    log "No changes to checkpoint."
    exit 0
fi

# Determine commit type from message
COMMIT_TYPE="chore"
case "$MESSAGE" in
    feat:*|feat\ *)    COMMIT_TYPE="feat" ;;
    fix:*|fix\ *)      COMMIT_TYPE="fix" ;;
    refactor:*)        COMMIT_TYPE="refactor" ;;
    test:*|test\ *)    COMMIT_TYPE="test" ;;
    docs:*|docs\ *)    COMMIT_TYPE="docs" ;;
    *)                 COMMIT_TYPE="chore" ;;
esac

# Create commit
FULL_MESSAGE="${COMMIT_TYPE}: [matrix] ${MESSAGE}"
git commit -m "$FULL_MESSAGE" --no-verify 2>/dev/null || git commit -m "$FULL_MESSAGE" 2>/dev/null

# Create tag
git tag "$TAG_NAME" 2>/dev/null || true

# Record checkpoint in session
if [ -f "$MATRIX_DIR/session.json" ]; then
    COMMIT_HASH=$(git rev-parse --short HEAD)
    python3 -c "
import json
with open('$MATRIX_DIR/session.json') as f:
    s = json.load(f)
s['checkpoints'] = [*s.get('checkpoints', []), {
    'tag': '$TAG_NAME',
    'commit': '$COMMIT_HASH',
    'message': '''$MESSAGE''',
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
}]
with open('$MATRIX_DIR/session.json', 'w') as f:
    json.dump(s, f, indent=2)
"
fi

log "Checkpoint created: ${TAG_NAME} (${FULL_MESSAGE})"
