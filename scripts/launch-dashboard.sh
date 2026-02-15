#!/usr/bin/env bash
# launch-dashboard.sh — (Re)launch the Matrix Dashboard for an active session
# Usage: bash launch-dashboard.sh [project-dir]
#
# Can be called at any time during a session to reopen the dashboard
# if it was accidentally closed.
set -euo pipefail

PROJECT_DIR="$(cd "${1:-.}" && pwd)"
MATRIX_DIR="${PROJECT_DIR}/.matrix"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DASHBOARD_SCRIPT="${SKILL_DIR}/scripts/matrix-dashboard.py"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[MATRIX]${NC} $1"; }
warn() { echo -e "${YELLOW}[MATRIX]${NC} $1"; }

# Validate prerequisites
if [ ! -d "$MATRIX_DIR" ]; then
    echo "Error: No .matrix/ directory found at ${MATRIX_DIR}" >&2
    echo "Start a session first with /neo <prd>" >&2
    exit 1
fi

if [ ! -f "$DASHBOARD_SCRIPT" ]; then
    echo "Error: Dashboard script not found at ${DASHBOARD_SCRIPT}" >&2
    exit 1
fi

# Check if dashboard is already running for this .matrix dir
EXISTING_PID=$(pgrep -f "matrix-dashboard.py --matrix-dir ${MATRIX_DIR}" 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    warn "Dashboard already running (PID: ${EXISTING_PID}). Kill it first? Relaunching anyway."
    kill "$EXISTING_PID" 2>/dev/null || true
    sleep 0.5
fi

DASHBOARD_CMD="cd '${PROJECT_DIR}' && python3 '${DASHBOARD_SCRIPT}' --matrix-dir '${MATRIX_DIR}'"

if command -v osascript &>/dev/null; then
    # macOS: detect current terminal app
    TERM_APP=$(osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' 2>/dev/null || echo "")

    case "$TERM_APP" in
        iTerm*|iTerm2)
            osascript -e "
                tell application \"iTerm\"
                    tell current window
                        create tab with default profile
                        tell current session
                            write text \"${DASHBOARD_CMD}\"
                        end tell
                    end tell
                end tell
            " &>/dev/null &
            ;;
        Warp)
            osascript -e "
                tell application \"Warp\"
                    activate
                    delay 0.3
                end tell
                tell application \"System Events\"
                    tell process \"Warp\"
                        keystroke \"t\" using command down
                        delay 0.3
                        keystroke \"${DASHBOARD_CMD}\"
                        key code 36
                    end tell
                end tell
            " &>/dev/null &
            ;;
        *)
            osascript -e "
                tell application \"Terminal\"
                    activate
                    do script \"${DASHBOARD_CMD}\"
                end tell
            " &>/dev/null &
            ;;
    esac
    log "Dashboard launched in new ${TERM_APP:-Terminal} tab."
elif command -v tmux &>/dev/null && [ -n "${TMUX:-}" ]; then
    tmux split-window -h "cd '${PROJECT_DIR}' && python3 '${DASHBOARD_SCRIPT}' --matrix-dir '${MATRIX_DIR}'"
    log "Dashboard launched in tmux pane."
elif command -v gnome-terminal &>/dev/null; then
    gnome-terminal -- bash -c "${DASHBOARD_CMD}" &>/dev/null &
    log "Dashboard launched in new terminal."
else
    log "Could not auto-launch. Run manually:"
    log "  python3 ${DASHBOARD_SCRIPT} --matrix-dir ${MATRIX_DIR}"
fi
