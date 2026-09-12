#!/bin/bash
# Brain Auditor — runs via opencode, same pattern as auto_1hr
# Queries session brain + trade data, generates recommendations + creative improvements

LOCK_FILE="/tmp/hermes-session-active.lock"
LOCK_TTL=3600
PROMPT_FILE="/root/.hermes/automation/brain-auditor/brain_auditor_prompt.md"
LOCK_FILE_TMP="/tmp/brain_auditor_lock_addition.md"

# Session lock check — if human active, only report, don't modify
if [ -f "$LOCK_FILE" ]; then
    lock_age=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0)))
    if [ "$lock_age" -lt "$LOCK_TTL" ]; then
        echo "[SESSION-LOCK] Human session active (${lock_age}s old) — brain auditor reporting only"
        cat > "$LOCK_FILE_TMP" << 'LOCKEOF'

## ⚠️ SESSION LOCK ACTIVE
A human session is active. You may ONLY:
- Query the session brain and trade data
- Generate recommendations and creative ideas
- Write to audit_recommendations.json and kanban

DO NOT modify hermes_constants.py or any parameter files.
DO NOT enable/disable signals.
DO NOT change any code.
LOCKEOF
    else
        rm -f "$LOCK_FILE"
        : > "$LOCK_FILE_TMP"  # empty file
    fi
else
    : > "$LOCK_FILE_TMP"  # empty file
fi

# BUG 6 fix: Use temp file instead of broken shell variable expansion
cat "$PROMPT_FILE" "$LOCK_FILE_TMP" | timeout 600 /root/.opencode/bin/opencode run --port 4099
rm -f "$LOCK_FILE_TMP"
