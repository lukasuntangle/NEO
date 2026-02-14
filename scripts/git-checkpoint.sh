#!/usr/bin/env bash
# git-checkpoint.sh — Atomic commits + rollback for Neo Orchestrator
# Usage: bash git-checkpoint.sh "<message>" [project-dir]
#        bash git-checkpoint.sh rollback <tag> [project-dir]
#        bash git-checkpoint.sh rollback-ticket <ticket-id> [project-dir]
set -euo pipefail

ACTION="${1:?Usage: git-checkpoint.sh <message> [project-dir] OR git-checkpoint.sh rollback <tag> [project-dir] OR git-checkpoint.sh rollback-ticket <ticket-id> [project-dir]}"
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

# --- Rollback to a tag ---
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

# --- Rollback a specific ticket's commits ---
if [ "$ACTION" = "rollback-ticket" ]; then
    TICKET_ID="${2:?Rollback-ticket requires a ticket ID (e.g., TICKET-007)}"
    PROJECT_DIR="${3:-.}"

    log "Finding commits for ${TICKET_ID}..."

    # Find all commits tagged with this ticket ID
    TICKET_COMMITS=$(git log --all --oneline --grep="\[${TICKET_ID}\]" --format="%H" 2>/dev/null || true)

    if [ -z "$TICKET_COMMITS" ]; then
        # Try finding by ticket tag
        TICKET_COMMITS=$(git log --all --oneline --grep="${TICKET_ID}" --format="%H" 2>/dev/null || true)
    fi

    if [ -z "$TICKET_COMMITS" ]; then
        err "No commits found for ${TICKET_ID}."
        err "Available ticket commits:"
        git log --oneline --grep="TICKET-" | head -10
        exit 1
    fi

    COMMIT_COUNT=$(echo "$TICKET_COMMITS" | wc -l | tr -d ' ')
    log "Found ${COMMIT_COUNT} commit(s) for ${TICKET_ID}."

    # Revert commits in reverse order (newest first)
    for commit in $TICKET_COMMITS; do
        SHORT=$(git rev-parse --short "$commit")
        MSG=$(git log -1 --format="%s" "$commit")
        log "Reverting ${SHORT}: ${MSG}"
        git revert --no-commit "$commit" 2>/dev/null || {
            warn "Could not cleanly revert ${SHORT}. Manual resolution may be needed."
            continue
        }
    done

    # Commit the revert
    git commit -m "revert: [${TICKET_ID}] rollback ${COMMIT_COUNT} commit(s)" --no-verify 2>/dev/null || true

    # Update ticket status if session exists
    if [ -f "$MATRIX_DIR/session.json" ]; then
        TICKET_FILE="${MATRIX_DIR}/tickets/${TICKET_ID}.json"
        if [ -f "$TICKET_FILE" ]; then
            python3 -c "
import json
with open('$TICKET_FILE') as f:
    t = json.load(f)
t['status'] = 'pending'
t['attempt'] = t.get('attempt', 1) + 1
t['context'] = (t.get('context') or '') + ' Rolled back by user.'
with open('$TICKET_FILE', 'w') as f:
    json.dump(t, f, indent=2)
"
            log "Ticket ${TICKET_ID} reset to pending (attempt +1)."
        fi
    fi

    log "Rollback of ${TICKET_ID} complete."
    exit 0
fi

# --- Regular checkpoint ---
MESSAGE="$ACTION"
TAG_NAME="matrix/${TIMESTAMP}"

# Extract ticket ID from message if present (e.g., "feat(TICKET-001): ...")
TICKET_ID=""
if echo "$MESSAGE" | grep -qoE 'TICKET-[0-9]+'; then
    TICKET_ID=$(echo "$MESSAGE" | grep -oE 'TICKET-[0-9]+' | head -1)
fi

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

# Build commit message with ticket ID tag for traceability
FULL_MESSAGE="${COMMIT_TYPE}: [matrix] ${MESSAGE}"
if [ -n "$TICKET_ID" ]; then
    FULL_MESSAGE="${COMMIT_TYPE}: [${TICKET_ID}] ${MESSAGE}"
fi

# Create commit
git commit -m "$FULL_MESSAGE" --no-verify 2>/dev/null || git commit -m "$FULL_MESSAGE" 2>/dev/null

# Create tag
git tag "$TAG_NAME" 2>/dev/null || true

# Create per-ticket tag if ticket ID is present
if [ -n "$TICKET_ID" ]; then
    TICKET_TAG="matrix/ticket/${TICKET_ID}/${TIMESTAMP}"
    git tag "$TICKET_TAG" 2>/dev/null || true
fi

# Record checkpoint in session
if [ -f "$MATRIX_DIR/session.json" ]; then
    COMMIT_HASH=$(git rev-parse --short HEAD)
    python3 -c "
import json
with open('$MATRIX_DIR/session.json') as f:
    s = json.load(f)
s['checkpoints'] = [*s.get('checkpoints', []), {
    'tag': '$TAG_NAME',
    'ticket_tag': '${TICKET_TAG:-}',
    'ticket_id': '${TICKET_ID:-}',
    'commit': '$COMMIT_HASH',
    'message': '''$MESSAGE''',
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
}]
with open('$MATRIX_DIR/session.json', 'w') as f:
    json.dump(s, f, indent=2)
"
fi

log "Checkpoint created: ${TAG_NAME} (${FULL_MESSAGE})"
if [ -n "$TICKET_ID" ]; then
    log "Ticket tag: ${TICKET_TAG}"
fi
