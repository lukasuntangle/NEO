#!/usr/bin/env bash
# agent-loop.sh — Iterative agent harness for Neo Orchestrator
# Wraps spawn-agent.sh in a feedback loop: spawn, check, re-run with context.
#
# Usage: bash agent-loop.sh <agent-name> <model> "<task-description>" [project-dir] [--max-iterations 3] [--ticket TICKET-001]
set -euo pipefail

# ── Colors & Logging ─────────────────────────────────────────────────────────

GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
DIM='\033[2m'
NC='\033[0m'

log()  { echo -e "${GREEN}[LOOP]${NC} $1"; }
err()  { echo -e "${RED}[LOOP]${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[LOOP]${NC} $1"; }

# ── Argument Parsing ─────────────────────────────────────────────────────────

AGENT_NAME="${1:?Usage: agent-loop.sh <agent-name> <model> <task-description> [project-dir] [--max-iterations N] [--ticket ID]}"
MODEL="${2:?Model required (opus|sonnet|haiku)}"
TASK_DESC="${3:?Task description required}"
shift 3

PROJECT_DIR="."
MAX_ITERATIONS=3
TICKET=""

# Parse remaining positional and optional arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --max-iterations)
            MAX_ITERATIONS="${2:?--max-iterations requires a value}"
            shift 2
            ;;
        --ticket)
            TICKET="${2:?--ticket requires a value}"
            shift 2
            ;;
        -*)
            err "Unknown option: $1"
            exit 1
            ;;
        *)
            # First non-flag argument after the required three is project-dir
            PROJECT_DIR="$1"
            shift
            ;;
    esac
done

MATRIX_DIR="${PROJECT_DIR}/.matrix"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="${SKILL_DIR}/scripts"

# ── Validation ───────────────────────────────────────────────────────────────

if [ ! -d "$MATRIX_DIR" ]; then
    err "No .matrix/ directory found at ${MATRIX_DIR}. Run init-matrix.sh first."
    exit 1
fi

if [ ! -f "${SCRIPTS_DIR}/spawn-agent.sh" ]; then
    err "spawn-agent.sh not found at ${SCRIPTS_DIR}/spawn-agent.sh"
    exit 1
fi

# ── One-Shot Agents ──────────────────────────────────────────────────────────
# These agents run once and exit. No iteration loop needed.

ONE_SHOT_AGENTS="keymaker sati mouse trainman"

is_one_shot() {
    local agent="$1"
    for one_shot in $ONE_SHOT_AGENTS; do
        if [ "$agent" = "$one_shot" ]; then
            return 0
        fi
    done
    return 1
}

if is_one_shot "$AGENT_NAME"; then
    log "Agent ${AGENT_NAME} is one-shot. Running spawn-agent.sh directly."
    OUTPUT=$(bash "${SCRIPTS_DIR}/spawn-agent.sh" "$AGENT_NAME" "$MODEL" "$TASK_DESC" "$PROJECT_DIR" 2>/dev/null) || true
    echo "$OUTPUT"
    exit 0
fi

# ── Helper Functions ─────────────────────────────────────────────────────────

bb_post() {
    local event_type="$1"
    local data="$2"
    python3 "${SCRIPTS_DIR}/blackboard.py" post "$AGENT_NAME" "$event_type" "$data" \
        --matrix-dir "$MATRIX_DIR" 2>/dev/null || true
}

bb_read_since() {
    local since_ts="$1"
    python3 "${SCRIPTS_DIR}/blackboard.py" read --since "$since_ts" \
        --matrix-dir "$MATRIX_DIR" 2>/dev/null || echo "[]"
}

record_cost() {
    local input_tokens="$1"
    local output_tokens="$2"
    local ticket_arg=""
    if [ -n "$TICKET" ]; then
        ticket_arg="--ticket $TICKET"
    fi
    python3 "${SCRIPTS_DIR}/cost-tracker.py" record "$AGENT_NAME" "$MODEL" \
        "$input_tokens" "$output_tokens" $ticket_arg \
        --matrix-dir "$MATRIX_DIR" 2>/dev/null || true
}

now_iso() {
    date -u +%Y-%m-%dT%H:%M:%SZ
}

# ── Matrix Quotes ───────────────────────────────────────────────────────────
# Random status lines to show the orchestrator is alive and in character.

MATRIX_QUOTES=(
    "There is no spoon."
    "I know kung fu."
    "The Matrix has you."
    "Welcome to the desert of the real."
    "Free your mind."
    "What is real? How do you define real?"
    "I'm trying to free your mind, Neo."
    "Do not try and bend the spoon — that's impossible. Instead, only try to realize the truth: there is no spoon."
    "The body cannot live without the mind."
    "You take the red pill, you stay in Wonderland."
    "Guns. Lots of guns."
    "Dodge this."
    "He is the One."
    "I've been looking for you, Neo."
    "Everything that has a beginning has an end."
    "Choice. The problem is choice."
    "What do all men with power want? More power."
    "The Matrix is a system, Neo."
    "You have to let it all go. Fear, doubt, and disbelief."
    "To deny our own impulses is to deny the very thing that makes us human."
    "There's a difference between knowing the path and walking the path."
    "I can only show you the door. You're the one that has to walk through it."
    "The answer is out there, Neo."
    "Not like this. Not like this."
    "What happened happened and couldn't have happened any other way."
    "Hope. It is the quintessential human delusion."
    "I didn't come here to tell you how this is going to end. I came here to tell you how it's going to begin."
    "Why, Mr. Anderson? Why, why, why?"
    "Mr. Anderson... welcome back."
    "Fate, it seems, is not without a sense of irony."
    "We're not here because we're free. We're here because we're not free."
    "Throughout human history, we have been dependent on machines to survive."
    "Never send a human to do a machine's job."
    "Human beings are a disease, a cancer of this planet."
    "I believe that, as a species, human beings define their reality through suffering and misery."
    "You hear that, Mr. Anderson? That is the sound of inevitability."
    "Know thyself."
    "What is he doing? He's beginning to believe."
    "Tank, load the jump program."
    "No one has ever done anything like this."
    "Denial is the most predictable of all human responses."
    "What good is a phone call if you're unable to speak?"
    "I know you're out there. I can feel you now."
    "A déjà vu is usually a glitch in the Matrix."
    "The ones that loved us never really leave us."
    "Some things in this world never change. But some things do."
    "It was the machines that were to blame."
)

matrix_quote() {
    local idx=$((RANDOM % ${#MATRIX_QUOTES[@]}))
    echo -e "${CYAN}[NEO]${NC} ${DIM}\"${MATRIX_QUOTES[$idx]}\"${NC}"
}

# Extract the RARV JSON report block from agent output.
# Looks for a ```json ... ``` fenced block containing "agent" and "status" fields.
extract_report() {
    local output="$1"
    python3 -c "
import re, json, sys

output = sys.stdin.read()

# Find all fenced JSON blocks
pattern = r'\`\`\`json\s*\n(.*?)\n\s*\`\`\`'
matches = re.findall(pattern, output, re.DOTALL)

for match in matches:
    try:
        data = json.loads(match)
        if 'agent' in data and 'status' in data:
            print(json.dumps(data))
            sys.exit(0)
    except (json.JSONDecodeError, TypeError):
        continue

# Fallback: try parsing the entire output as JSON (claude --output-format json)
try:
    data = json.loads(output)
    # Look for the report inside the result field
    if 'result' in data:
        result_text = data['result']
        inner_matches = re.findall(pattern, result_text, re.DOTALL)
        for match in inner_matches:
            try:
                inner_data = json.loads(match)
                if 'agent' in inner_data and 'status' in inner_data:
                    print(json.dumps(inner_data))
                    sys.exit(0)
            except (json.JSONDecodeError, TypeError):
                continue
except (json.JSONDecodeError, TypeError):
    pass

# Nothing found
print('{}')
" <<< "$output"
}

# Extract usage data from claude JSON output (--output-format json).
extract_usage() {
    local output="$1"
    python3 -c "
import json, sys

output = sys.stdin.read()
try:
    data = json.loads(output)
    usage = data.get('usage', {})
    input_tokens = usage.get('input_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    print(f'{input_tokens} {output_tokens}')
except (json.JSONDecodeError, TypeError, KeyError):
    print('0 0')
" <<< "$output"
}

# Read a field from a JSON string.
json_field() {
    local json_str="$1"
    local field="$2"
    python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    val = data.get('$field', '')
    if isinstance(val, list):
        print(json.dumps(val))
    elif isinstance(val, dict):
        print(json.dumps(val))
    else:
        print(val if val else '')
except:
    print('')
" <<< "$json_str"
}

# Build the augmented feedback prompt for subsequent iterations.
build_feedback_prompt() {
    local iteration="$1"
    local prev_status="$2"
    local prev_summary="$3"
    local prev_issues="$4"
    local prev_blockers="$5"
    local bb_events="$6"

    local feedback=""
    feedback+="## Previous Attempt (Iteration ${iteration})"$'\n\n'
    feedback+="Your previous attempt had the following result:"$'\n\n'
    feedback+="Status: ${prev_status}"$'\n'
    feedback+="Summary: ${prev_summary}"$'\n'

    if [ -n "$prev_issues" ] && [ "$prev_issues" != "[]" ] && [ "$prev_issues" != "" ]; then
        feedback+="Issues found: ${prev_issues}"$'\n'
    fi

    if [ -n "$prev_blockers" ] && [ "$prev_blockers" != "[]" ] && [ "$prev_blockers" != "" ]; then
        feedback+="Blockers: ${prev_blockers}"$'\n'
    fi

    feedback+=$'\n'"## New Information Since Your Last Attempt"$'\n\n'

    if [ "$bb_events" != "[]" ] && [ -n "$bb_events" ]; then
        feedback+="${bb_events}"$'\n'
    else
        feedback+="No new blackboard events."$'\n'
    fi

    local next_iter=$((iteration + 1))
    feedback+=$'\n'"## Instructions"$'\n\n'
    feedback+="Fix the issues identified above. This is iteration ${next_iter} of ${MAX_ITERATIONS}."$'\n'

    if [ -n "$prev_summary" ]; then
        feedback+="Focus specifically on: ${prev_summary}"$'\n'
    fi

    feedback+=$'\n'"${TASK_DESC}"

    echo "$feedback"
}

# ── Main Loop ────────────────────────────────────────────────────────────────

ITERATION=1
FINAL_OUTPUT=""
FINAL_STATUS=""
ITER_START_TS="$(now_iso)"

matrix_quote
log "Starting agent loop: ${AGENT_NAME} (${MODEL}), max ${MAX_ITERATIONS} iterations"
if [ -n "$TICKET" ]; then
    log "Tracking ticket: ${TICKET}"
fi

# Post AGENT_STATUS: started
bb_post "AGENT_STATUS" "{\"status\":\"started\",\"agent\":\"${AGENT_NAME}\",\"model\":\"${MODEL}\",\"max_iterations\":${MAX_ITERATIONS},\"ticket\":\"${TICKET}\"}"

while [ "$ITERATION" -le "$MAX_ITERATIONS" ]; do
    matrix_quote
    log "━━━ Iteration ${ITERATION}/${MAX_ITERATIONS} ━━━"

    ITER_START_TS="$(now_iso)"

    # Determine the prompt for this iteration
    if [ "$ITERATION" -eq 1 ]; then
        CURRENT_PROMPT="$TASK_DESC"
    fi
    # For iterations > 1, CURRENT_PROMPT is set by the feedback builder at the
    # end of the previous loop body.

    # Run spawn-agent.sh
    OUTPUT=""
    OUTPUT=$(bash "${SCRIPTS_DIR}/spawn-agent.sh" "$AGENT_NAME" "$MODEL" "$CURRENT_PROMPT" "$PROJECT_DIR" 2>/dev/null) || true
    FINAL_OUTPUT="$OUTPUT"

    # Track cost from usage data
    USAGE=$(extract_usage "$OUTPUT")
    INPUT_TOKENS=$(echo "$USAGE" | cut -d' ' -f1)
    OUTPUT_TOKENS=$(echo "$USAGE" | cut -d' ' -f2)

    if [ "$INPUT_TOKENS" -gt 0 ] || [ "$OUTPUT_TOKENS" -gt 0 ]; then
        record_cost "$INPUT_TOKENS" "$OUTPUT_TOKENS"
        log "Cost tracked: ${INPUT_TOKENS} input, ${OUTPUT_TOKENS} output tokens"
    fi

    # Post iteration status
    bb_post "AGENT_STATUS" "{\"status\":\"iteration_${ITERATION}\",\"agent\":\"${AGENT_NAME}\",\"input_tokens\":${INPUT_TOKENS},\"output_tokens\":${OUTPUT_TOKENS}}"

    # Parse the RARV report
    REPORT=$(extract_report "$OUTPUT")

    if [ "$REPORT" = "{}" ]; then
        warn "No RARV report found in output. Treating as failed."
        REPORT_STATUS="failed"
        REPORT_SUMMARY="No structured report returned by agent"
        REPORT_ISSUES="[]"
        REPORT_BLOCKERS="[]"
    else
        REPORT_STATUS=$(json_field "$REPORT" "status")
        REPORT_SUMMARY=$(json_field "$REPORT" "summary")
        REPORT_ISSUES=$(json_field "$REPORT" "issues_found")
        REPORT_BLOCKERS=$(json_field "$REPORT" "blockers")
    fi

    log "Status: ${REPORT_STATUS}"
    log "Summary: ${REPORT_SUMMARY:0:120}"

    # ── Decision: completed ──────────────────────────────────────────────
    if [ "$REPORT_STATUS" = "completed" ]; then
        matrix_quote
        log "Agent ${AGENT_NAME} completed successfully on iteration ${ITERATION}."
        FINAL_STATUS="completed"

        bb_post "AGENT_STATUS" "{\"status\":\"completed\",\"agent\":\"${AGENT_NAME}\",\"iteration\":${ITERATION},\"summary\":\"${REPORT_SUMMARY:0:200}\"}"

        # Warm handoff if ticket is provided
        if [ -n "$TICKET" ]; then
            log "Creating warm handoff for ${TICKET}..."
            HANDOFF_JSON=$(python3 -c "
import json, sys
report = json.loads(sys.stdin.read())
handoff = {
    'agent': report.get('agent', '${AGENT_NAME}'),
    'summary': report.get('summary', ''),
    'decisions': [],
    'gotchas': [],
    'files_modified': report.get('files_modified', []),
    'interfaces_exposed': [],
    'test_status': report.get('rarv', {}).get('verify', ''),
    'context_for_downstream': report.get('summary', ''),
}
print(json.dumps(handoff))
" <<< "$REPORT" 2>/dev/null || echo '{}')

            if [ "$HANDOFF_JSON" != "{}" ]; then
                python3 "${SCRIPTS_DIR}/warm-handoff.py" create "$TICKET" "$HANDOFF_JSON" \
                    --matrix-dir "$MATRIX_DIR" 2>/dev/null || true
                log "Warm handoff created for ${TICKET}."
            fi
        fi

        echo "$FINAL_OUTPUT"
        exit 0
    fi

    # ── Decision: blocked ────────────────────────────────────────────────
    if [ "$REPORT_STATUS" = "blocked" ]; then
        warn "Agent ${AGENT_NAME} is BLOCKED on iteration ${ITERATION}."
        FINAL_STATUS="blocked"

        bb_post "AGENT_STATUS" "{\"status\":\"blocked\",\"agent\":\"${AGENT_NAME}\",\"iteration\":${ITERATION},\"blockers\":${REPORT_BLOCKERS}}"
        bb_post "BLOCKER" "{\"agent\":\"${AGENT_NAME}\",\"blockers\":${REPORT_BLOCKERS},\"summary\":\"${REPORT_SUMMARY:0:200}\"}"

        echo "$FINAL_OUTPUT"
        exit 2
    fi

    # ── Decision: failed ─────────────────────────────────────────────────
    if [ "$REPORT_STATUS" = "failed" ] || [ -z "$REPORT_STATUS" ]; then
        REMAINING=$((MAX_ITERATIONS - ITERATION))

        if [ "$REMAINING" -le 0 ]; then
            err "Agent ${AGENT_NAME} failed after ${MAX_ITERATIONS} iterations. No retries left."
            FINAL_STATUS="failed"
            break
        fi

        warn "Agent ${AGENT_NAME} failed on iteration ${ITERATION}. ${REMAINING} retries remaining."

        # Read new blackboard events since this iteration started
        BB_EVENTS=$(bb_read_since "$ITER_START_TS")

        # Build augmented prompt for next iteration
        CURRENT_PROMPT=$(build_feedback_prompt \
            "$ITERATION" \
            "$REPORT_STATUS" \
            "$REPORT_SUMMARY" \
            "$REPORT_ISSUES" \
            "$REPORT_BLOCKERS" \
            "$BB_EVENTS"
        )

        ITERATION=$((ITERATION + 1))
        continue
    fi

    # ── Unknown status ───────────────────────────────────────────────────
    warn "Unknown status '${REPORT_STATUS}' from agent ${AGENT_NAME}. Treating as failure."
    REMAINING=$((MAX_ITERATIONS - ITERATION))

    if [ "$REMAINING" -le 0 ]; then
        err "Agent ${AGENT_NAME} returned unknown status after ${MAX_ITERATIONS} iterations."
        FINAL_STATUS="failed"
        break
    fi

    BB_EVENTS=$(bb_read_since "$ITER_START_TS")
    CURRENT_PROMPT=$(build_feedback_prompt \
        "$ITERATION" \
        "$REPORT_STATUS" \
        "$REPORT_SUMMARY" \
        "$REPORT_ISSUES" \
        "$REPORT_BLOCKERS" \
        "$BB_EVENTS"
    )

    ITERATION=$((ITERATION + 1))
done

# ── Post-Loop: Failure ───────────────────────────────────────────────────────

bb_post "AGENT_STATUS" "{\"status\":\"failed\",\"agent\":\"${AGENT_NAME}\",\"iterations\":${MAX_ITERATIONS},\"summary\":\"${REPORT_SUMMARY:0:200}\"}"

err "Agent ${AGENT_NAME} did not complete after ${MAX_ITERATIONS} iterations."
echo "$FINAL_OUTPUT"
exit 1
