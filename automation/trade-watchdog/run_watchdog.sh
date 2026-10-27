#!/bin/bash
# Trade Watchdog — runs the opencode agent with the watchdog prompt
# Called by hermes-trade-watchdog.timer every 30 minutes

set -euo pipefail

PROMPT_FILE="/root/.hermes/automation/trade-watchdog/trade_watchdog_prompt.md"
OPENCODE="/root/.opencode/bin/opencode"
LOG_DIR="/root/.hermes/logs"
LOG_FILE="${LOG_DIR}/trade-watchdog.log"
LOCK_FILE="/tmp/hermes-trade-watchdog.lock"
AGENT_OUTPUT="/tmp/watchdog_agent_analysis.txt"

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

# Scrub secrets from watchdog artifacts — agent sessions echo .secrets.local greps
# to stderr which lands in LOG_FILE (BUG-036). Run on every exit.
scrub() {
    sed -i -E \
        -e 's/(PASSWORD=)[^[:space:]"]+/\1REDACTED/g' \
        -e 's/(TOKEN=)"[^"]*"/\1"REDACTED"/g' \
        -e 's/(SIGNING_KEY=)[^[:space:]"]+/\1REDACTED/g' \
        -e 's/ghp_[A-Za-z0-9]+/ghp_REDACTED/g' \
        "$LOG_FILE" 2>/dev/null || true
    [ -f "$AGENT_OUTPUT" ] && sed -i -E \
        -e 's/(PASSWORD=)[^[:space:]"]+/\1REDACTED/g' \
        -e 's/(TOKEN=)"[^"]*"/\1"REDACTED"/g' \
        -e 's/(SIGNING_KEY=)[^[:space:]"]+/\1REDACTED/g' \
        -e 's/ghp_[A-Za-z0-9]+/ghp_REDACTED/g' \
        "$AGENT_OUTPUT" 2>/dev/null || true
}

# Create lock
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"; scrub' EXIT

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [START] Trade Watchdog" >> "$LOG_FILE"

# Step 1: Collect data and run analysis (fast, no LLM needed)
cd /root/.hermes
python3 scripts/trade_watchdog.py >> "$LOG_FILE" 2>&1

# Step 1.5: Decide whether the LLM deep-analysis pass is worth running.
# The deterministic step above already emits every steer. Historically 44% of
# cycles (78/178) had zero open trades yet still burned a full agent session.
# CEO 2026-10-27: skip the agent when open_count < WATCHDOG_LLM_MIN_OPEN_TRADES.
# Safety valve: if the last agent analysis is older than WATCHDOG_LLM_STALE_HOURS
# we run anyway, so a flat system still gets periodic portfolio-level review.
# FAIL-OPEN: any error reading constants/config → run the agent (old behavior).
RUN_AGENT=1
SKIP_REASON=""
eval "$(python3 - <<'PYEOF'
import json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, '/root/.hermes/scripts')
try:
    from hermes_constants import WATCHDOG_LLM_MIN_OPEN_TRADES, WATCHDOG_LLM_STALE_HOURS
    recs_path = '/root/.hermes/data/watchdog_recommendations.json'
    open_count = None
    agent_age_h = None
    if os.path.exists(recs_path):
        with open(recs_path) as f:
            recs = json.load(f)
        open_count = recs.get('open_count')
        ts = recs.get('agent_timestamp')
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                agent_age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            except Exception:
                agent_age_h = None
    if open_count is None or int(open_count) < 0:
        # No data, or nonsense (negative is impossible from len()) → fail-open
        print('RUN_AGENT=1')
        print("SKIP_REASON=''")
    elif int(open_count) >= int(WATCHDOG_LLM_MIN_OPEN_TRADES):
        print('RUN_AGENT=1')
        print("SKIP_REASON=''")
    elif agent_age_h is not None and agent_age_h >= float(WATCHDOG_LLM_STALE_HOURS):
        # Flat, but agent analysis is stale → keep periodic review alive
        print('RUN_AGENT=1')
        print("SKIP_REASON=''" )
    else:
        print('RUN_AGENT=0')
        print(f"SKIP_REASON='open_count={open_count} < {WATCHDOG_LLM_MIN_OPEN_TRADES} and last agent analysis "
              f"{'unknown' if agent_age_h is None else f'{agent_age_h:.1f}h'} < {WATCHDOG_LLM_STALE_HOURS}h'")
except Exception as _e:
    # Fail-open: never let a config/parse error silence the watchdog
    print('RUN_AGENT=1')
    print(f"SKIP_REASON=''")
    print(f'# gate eval failed (fail-open): {_e}', file=sys.stderr)
PYEOF
)" || RUN_AGENT=1

if [ "$RUN_AGENT" != "1" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [SKIP-LLM] Agent pass skipped — ${SKIP_REASON}. Deterministic steers still emitted." >> "$LOG_FILE"
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [DONE] Trade Watchdog (deterministic only)" >> "$LOG_FILE"
    exit 0
fi

# Step 2: Run opencode agent for deep analysis (with timeout)
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
