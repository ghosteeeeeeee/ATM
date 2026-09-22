#!/bin/bash
# Trade Watchdog — runs the opencode agent with the watchdog prompt
# Called by hermes-trade-watchdog.timer every 30 minutes

set -euo pipefail

PROMPT_FILE="/root/.hermes/automation/trade-watchdog/trade_watchdog_prompt.md"
OPENCODE="/root/.opencode/bin/opencode"
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

# Step 2: Run opencode agent for deep analysis (with timeout)
AGENT_OUTPUT="/tmp/watchdog_agent_analysis.txt"
if cat "$PROMPT_FILE" | timeout 480 "$OPENCODE" run --port 4099 > "$AGENT_OUTPUT" 2>>"$LOG_FILE"; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [OK] Opencode agent completed" >> "$LOG_FILE"
    # Merge agent analysis into recommendations file
    python3 -c "
import json, sys
from datetime import datetime, timezone

recs_path = '/root/.hermes/data/watchdog_recommendations.json'
try:
    with open(recs_path) as f:
        recs = json.load(f)
except:
    recs = {}

# Read agent output
try:
    with open('$AGENT_OUTPUT') as f:
        agent_text = f.read()
    if agent_text.strip():
        recs['deep_analysis'] = agent_text
        recs['agent_timestamp'] = datetime.now(timezone.utc).isoformat()
        with open(recs_path, 'w') as f:
            json.dump(recs, f, indent=2)
        print('Agent analysis merged into recommendations')
except Exception as e:
    print(f'Failed to merge agent output: {e}')
" >> "$LOG_FILE" 2>&1
else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [WARN] Opencode agent failed or timed out (exit $?)" >> "$LOG_FILE"
fi
rm -f "$AGENT_OUTPUT"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [DONE] Trade Watchdog" >> "$LOG_FILE"
