#!/usr/bin/env bash
# cleanup.sh — Session archival for Neo Orchestrator
# Usage: bash cleanup.sh [project-dir]
set -euo pipefail

PROJECT_DIR="${1:-.}"
MATRIX_DIR="${PROJECT_DIR}/.matrix"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"

GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[CLEANUP]${NC} $1"; }

if [ ! -d "$MATRIX_DIR" ]; then
    echo "No .matrix/ directory found. Nothing to clean." >&2
    exit 0
fi

# Update session status
python3 -c "
import json
from datetime import datetime, timezone
with open('$MATRIX_DIR/session.json') as f:
    s = json.load(f)
s['status'] = 'archived'
s['completed_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
with open('$MATRIX_DIR/session.json', 'w') as f:
    json.dump(s, f, indent=2)
"

# Clean up log files larger than 1MB
find "$MATRIX_DIR/logs" -type f -size +1M -exec truncate -s 100K {} \; 2>/dev/null || true

# Remove temporary files
rm -f "$MATRIX_DIR/sentinels/blind-diff.patch" 2>/dev/null || true

# Restore original Claude Code permissions if backup exists
SETTINGS_BACKUP="$MATRIX_DIR/settings.backup.json"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS_BACKUP" ]; then
    cp "$SETTINGS_BACKUP" "$CLAUDE_SETTINGS"
    log "Original Claude Code permissions restored."
fi

# Archive the session
ARCHIVE_NAME=".matrix_archive_${TIMESTAMP}"
cp -r "$MATRIX_DIR" "${PROJECT_DIR}/${ARCHIVE_NAME}"
log "Session archived to ${ARCHIVE_NAME}"

# Clean .matrix/ but preserve memory
rm -rf "$MATRIX_DIR/tickets" "$MATRIX_DIR/sentinels" "$MATRIX_DIR/construct" "$MATRIX_DIR/logs" "$MATRIX_DIR/source"
log "Working directories cleaned. Memory preserved."

log "Unplugged. Session complete."
