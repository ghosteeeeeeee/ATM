#!/bin/bash
# Weekly MoE Panel — runs via opencode, same pattern as brain-auditor.
# Directed by T: plans/t-vacation-mode-2026-10-14.md ("wire the MoE in on a regular basis").
# Cadence: Monday 09:00 UTC (hermes-moe-panel.timer).

LOCK_FILE="/tmp/hermes-session-active.lock"
LOCK_TTL=3600
PROMPT_FILE="/root/.hermes/automation/moe-panel/moe_panel_prompt.md"
REPORT_DIR="/root/.hermes/automation/moe-panel/reports"
MOE_LOCK="/tmp/hermes-moe-panel.lock"
LOCK_NOTE="/tmp/moe_panel_lock_note.md"
# ponytail: port 4101 — brain-auditor owns 4099 hourly at :30; avoid clash if both run
PORT=4101

# Prevent overlapping MoE runs (panel can run 30-60 min)
exec 9>"$MOE_LOCK"
if ! flock -n 9; then
    echo "[MOE-PANEL] Another MoE panel run holds the lock — exiting"
    exit 0
fi

mkdir -p "$REPORT_DIR"

# Session lock check — deterministic guard (same as brain-auditor)
: > "$LOCK_NOTE"
if [ -f "$LOCK_FILE" ]; then
    lock_age=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0)))
    if [ "$lock_age" -lt "$LOCK_TTL" ]; then
        echo "[SESSION-LOCK] Human session active (${lock_age}s old) — report only"
        cat > "$LOCK_NOTE" << 'LOCKEOF'

## ⚠️ SESSION LOCK ACTIVE
A human session is active. You may ONLY:
- Query data and produce a recommendations report.
- Write the report to automation/moe-panel/reports/ and a kanban note.

DO NOT modify hermes_constants.py or any parameter files.
DO NOT enable/disable signals or gates.
DO NOT change any code.
LOCKEOF
    fi
fi

cat "$PROMPT_FILE" "$LOCK_NOTE" | timeout 3600 /root/.opencode/bin/opencode run --port "$PORT"
rc=$?
rm -f "$LOCK_NOTE"
echo "[MOE-PANEL] finished rc=$rc"
exit $rc
