#!/bin/bash
# Brain Auditor — runs via opencode, same pattern as auto_1hr
# Queries session brain + trade data, generates recommendations + creative improvements

LOCK_FILE="/tmp/hermes-session-active.lock"
LOCK_TTL=3600
PROMPT_FILE="/root/.hermes/automation/brain-auditor/brain_auditor_prompt.md"
LOCK_TMP="/tmp/brain_auditor_lock_note.md"

# Session lock check — deterministic guard (BUG 2 fix: restored)
: > "$LOCK_TMP"
if [ -f "$LOCK_FILE" ]; then
    lock_age=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0)))
    if [ "$lock_age" -lt "$LOCK_TTL" ]; then
        echo "[SESSION-LOCK] Human session active (${lock_age}s old) — report only"
        cat > "$LOCK_TMP" << 'LOCKEOF'

## ⚠️ SESSION LOCK ACTIVE
A human session is active. You may ONLY:
- Query the session brain and trade data
- Generate recommendations and creative ideas
- Write to audit_recommendations.json and kanban

DO NOT modify hermes_constants.py or any parameter files.
DO NOT enable/disable signals.
DO NOT change any code.
LOCKEOF
    fi
fi

cat "$PROMPT_FILE" "$LOCK_TMP" | timeout 1200 /root/.opencode/bin/opencode run --port 4099
rm -f "$LOCK_TMP"
