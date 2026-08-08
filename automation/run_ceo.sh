#!/bin/bash
# Port 4099 avoids conflict with interactive opencode sessions on default port
# Timeout: 5 minutes (300s) — CEO should be fast, not comprehensive

LOCK_FILE="/tmp/hermes-session-active.lock"
LOCK_TTL=3600

# ── Session Lock Check ──────────────────────────────────────────────────────
# If human session is active (<1h old), skip parameter changes
if [ -f "$LOCK_FILE" ]; then
    lock_age=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0)))
    if [ "$lock_age" -lt "$LOCK_TTL" ]; then
        echo "[SESSION-LOCK] Human session active (${lock_age}s old, TTL=${LOCK_TTL}s) — CEO skipping parameter changes"
        # Still run CEO for monitoring/reporting, but inject lock notice into prompt
        PROMPT_ADDITION="

## ⚠️ SESSION LOCK ACTIVE
A human session is active (lock age: ${lock_age}s). You may ONLY:
- Monitor system status
- Write reports
- Log observations

DO NOT modify hermes_constants.py or any parameter files.
DO NOT enable/disable signals.
DO NOT change kill switches.
"
    else
        echo "[SESSION-LOCK] Lock expired (${lock_age}s > ${LOCK_TTL}s) — removing"
        rm -f "$LOCK_FILE"
        PROMPT_ADDITION=""
    fi
else
    PROMPT_ADDITION=""
fi

# ── Run CEO ─────────────────────────────────────────────────────────────────
timeout 600 bash -c "cat /root/.hermes/automation/ceo_prompt.md <(echo '$PROMPT_ADDITION') | /root/.opencode/bin/opencode run --port 4099"
