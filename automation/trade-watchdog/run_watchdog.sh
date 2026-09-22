#!/bin/bash
# Trade Watchdog — runs the opencode agent with the watchdog prompt
# Called by hermes-trade-watchdog.timer every 30 minutes

set -euo pipefail

PROMPT_FILE="/root/.hermes/automation/trade-watchdog/trade_watchdog_prompt.md"
LOG_DIR="/root/.hermes/logs"
LOG_FILE="${LOG_DIR}/trade-watchdog.log"
LOCK_FILE="/tmp/hermes-trade-watchdog.lock"

# Ensure log dir exists
mkdir -p "$LOG_DIR"

# Lock check — prevent overlapping runs
if [ -f "$LOCK_FILE" ]; then
    lock_age=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -lt 300 ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [SKIP] Watchdog already running (lock age: ${lock_age}s)" >> "$LOG_FILE"
        exit 0
    fi
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [WARN] Stale lock (${lock_age}s), removing" >> "$LOG_FILE"
    rm -f "$LOCK_FILE"
fi

# Create lock
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [START] Trade Watchdog" >> "$LOG_FILE"

# Step 1: Collect data and run analysis (fast, no LLM needed)
cd /root/.hermes
python3 scripts/trade_watchdog.py >> "$LOG_FILE" 2>&1

# Step 2: Run opencode agent for deep analysis
PROMPT=$(cat "$PROMPT_FILE")
opencode run --port 4099 -p "$PROMPT" >> "$LOG_FILE" 2>&1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [DONE] Trade Watchdog" >> "$LOG_FILE"
