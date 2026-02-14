#!/usr/bin/env bash
# blind-review-prep.sh — Strip author info from diffs for Smith's blind review
# Usage: bash blind-review-prep.sh [project-dir]
# Output: cleaned diff to stdout
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# Ensure git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository." >&2
    exit 1
fi

# Get diff (staged + unstaged, or vs last commit)
DIFF=""
if ! git diff --cached --quiet 2>/dev/null || ! git diff --quiet 2>/dev/null; then
    DIFF=$(git diff HEAD 2>/dev/null || git diff 2>/dev/null || echo "")
elif git log -1 --oneline >/dev/null 2>&1; then
    DIFF=$(git diff HEAD~1..HEAD 2>/dev/null || echo "")
fi

if [ -z "$DIFF" ]; then
    echo "No changes to review." >&2
    exit 0
fi

# Strip author information:
# 1. Remove Author lines
# 2. Remove commit hashes
# 3. Remove dates
# 4. Remove email addresses
# 5. Remove "index" lines (contain hashes)
# 6. Keep only the actual diff content
echo "$DIFF" | sed \
    -e '/^Author:/d' \
    -e '/^Date:/d' \
    -e '/^commit [0-9a-f]/d' \
    -e 's/[a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]*\.[a-zA-Z]*/[REDACTED]/g' \
    -e '/^index [0-9a-f]/d' \
    -e '/^Merge:/d' \
    -e 's/Co-Authored-By:.*/Co-Authored-By: [REDACTED]/g'
