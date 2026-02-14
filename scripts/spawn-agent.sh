#!/usr/bin/env bash
# spawn-agent.sh — Spawn a Matrix agent via claude CLI
# Usage: bash spawn-agent.sh <agent-name> <model> "<task-description>" [project-dir]
set -euo pipefail

AGENT_NAME="${1:?Usage: spawn-agent.sh <agent-name> <model> <task-description> [project-dir]}"
MODEL="${2:?Model required (opus|sonnet|haiku)}"
TASK_DESC="${3:?Task description required}"
PROJECT_DIR="${4:-.}"
MATRIX_DIR="${PROJECT_DIR}/.matrix"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_PROMPT_FILE="${SKILL_DIR}/agents/${AGENT_NAME}.md"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${MATRIX_DIR}/logs/${AGENT_NAME}_${TIMESTAMP}.log"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[SPAWN]${NC} $1"; }
err() { echo -e "${RED}[SPAWN]${NC} $1" >&2; }

# Validate inputs
if [ ! -d "$MATRIX_DIR" ]; then
    err "No .matrix/ directory found. Run init-matrix.sh first."
    exit 1
fi

if [ ! -f "$AGENT_PROMPT_FILE" ]; then
    err "Agent prompt not found: ${AGENT_PROMPT_FILE}"
    err "Available agents:"
    ls "${SKILL_DIR}/agents/" | sed 's/\.md$//' | while read -r a; do echo "  - $a"; done
    exit 1
fi

# Validate model
case "$MODEL" in
    opus|sonnet|haiku) ;;
    *)
        err "Invalid model: $MODEL. Must be opus, sonnet, or haiku."
        exit 1
        ;;
esac

# Read agent system prompt
AGENT_SYSTEM_PROMPT=$(cat "$AGENT_PROMPT_FILE")

# Build context from .matrix/
CONTEXT=""

# Include config
if [ -f "$MATRIX_DIR/config.json" ]; then
    CONTEXT="${CONTEXT}\n\n## Project Config\n\`\`\`json\n$(cat "$MATRIX_DIR/config.json")\n\`\`\`"
fi

# Include relevant memory (procedural first, then semantic)
if [ -d "$MATRIX_DIR/memory/procedural" ] && ls "$MATRIX_DIR/memory/procedural/"*.json 1>/dev/null 2>&1; then
    for mem_file in "$MATRIX_DIR/memory/procedural/"*.json; do
        CONTEXT="${CONTEXT}\n\n## Procedural Memory\n\`\`\`json\n$(cat "$mem_file")\n\`\`\`"
    done
fi

if [ -d "$MATRIX_DIR/memory/semantic" ] && ls "$MATRIX_DIR/memory/semantic/"*.json 1>/dev/null 2>&1; then
    for mem_file in "$MATRIX_DIR/memory/semantic/"*.json; do
        CONTEXT="${CONTEXT}\n\n## Semantic Memory\n\`\`\`json\n$(cat "$mem_file")\n\`\`\`"
    done
fi

# Include architecture if available
if [ -f "$MATRIX_DIR/construct/architecture.md" ]; then
    CONTEXT="${CONTEXT}\n\n## Architecture\n$(cat "$MATRIX_DIR/construct/architecture.md")"
fi

# Include OpenAPI spec if available
if [ -f "$MATRIX_DIR/construct/openapi.yaml" ]; then
    CONTEXT="${CONTEXT}\n\n## OpenAPI Spec\n\`\`\`yaml\n$(cat "$MATRIX_DIR/construct/openapi.yaml")\n\`\`\`"
fi

# Include ticket index for dispatchers
if [ "$AGENT_NAME" = "morpheus" ] || [ "$AGENT_NAME" = "neo" ]; then
    if [ -f "$MATRIX_DIR/tickets/index.json" ]; then
        CONTEXT="${CONTEXT}\n\n## Ticket Index\n\`\`\`json\n$(cat "$MATRIX_DIR/tickets/index.json")\n\`\`\`"
    fi
    if [ -f "$MATRIX_DIR/tickets/reservations.json" ]; then
        CONTEXT="${CONTEXT}\n\n## File Reservations\n\`\`\`json\n$(cat "$MATRIX_DIR/tickets/reservations.json")\n\`\`\`"
    fi
fi

# Build the full prompt
FULL_PROMPT="$(cat << PROMPTEOF
${AGENT_SYSTEM_PROMPT}

---

# Context

${CONTEXT}

---

# Your Task

${TASK_DESC}

---

# RARV Cycle

Follow this cycle for your task:
1. **Research**: Read all relevant files, understand the context, check memory for relevant strategies
2. **Analyze**: Implement your solution / perform your analysis
3. **Reflect**: Self-review your work — did you miss anything? Are there edge cases?
4. **Verify**: Run tests or validation to confirm correctness

Report your results in this structured format:

\`\`\`json
{
  "agent": "${AGENT_NAME}",
  "status": "completed|failed|blocked",
  "summary": "Brief description of what was done",
  "files_modified": [],
  "files_created": [],
  "issues_found": [],
  "blockers": [],
  "rarv": {
    "research": "What was read/reviewed",
    "analyze": "What was implemented/analyzed",
    "reflect": "Self-review findings",
    "verify": "Verification results"
  }
}
\`\`\`
PROMPTEOF
)"

# Update session agent count
python3 -c "
import json
with open('$MATRIX_DIR/session.json', 'r') as f:
    session = json.load(f)
session['agents_spawned'] = session.get('agents_spawned', 0) + 1
session['updated_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
with open('$MATRIX_DIR/session.json', 'w') as f:
    json.dump(session, f, indent=2)
"

log "Spawning ${AGENT_NAME} (${MODEL})..."
log "Task: ${TASK_DESC:0:80}..."

# Spawn the agent via claude CLI
# Use -p for print mode (non-interactive), --model for model selection
echo -e "${FULL_PROMPT}" | claude -p \
    --model "$MODEL" \
    --output-format json \
    2>"${LOG_FILE}.stderr" | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[1]:-$?}

if [ $EXIT_CODE -ne 0 ]; then
    err "Agent ${AGENT_NAME} exited with code ${EXIT_CODE}"
    if [ -f "${LOG_FILE}.stderr" ]; then
        err "Stderr: $(cat "${LOG_FILE}.stderr")"
    fi
    exit $EXIT_CODE
fi

log "Agent ${AGENT_NAME} completed. Log: ${LOG_FILE}"
