#!/bin/bash
# Port 4099 avoids conflict with interactive opencode sessions on default port
cat /root/.hermes/automation/ceo_prompt.md - <<'TASK' | /root/.opencode/bin/opencode run --port 4099

---

# YOUR TASK: Daily Strategic Review

Run a full strategic review right now. Read the files below, analyze the data, and output your executive summary.

## Context Files to Read
1. `automation/trading_log.md` — recent trade analysis and decisions
2. `scripts/hermes_constants.py` — current system parameters
3. `/var/www/hermes/data/trades.json` — recent trade data (closed array)
4. `data/signals_hermes_runtime.db` — signal outcomes

## Analysis Steps

### 1. System Health Check
- Verify kill switches: TL_BREAK_ENABLED, ACCEL_300_ENABLED, BOLLINGER_SQUEEZE_ENABLED should all be False
- Check blacklist enforcement: no blacklisted tokens should appear in recent trades
- Check pipeline status: `systemctl is-active hermes-pipeline`
- Check HL sync: `systemctl is-active hermes-hl-sync-guardian`
- Check trailing stops: does `data/trailing_stops.json` exist?

### 2. Trading Performance (last 24h)
- Query signal_outcomes (24h, dedup with trade_id IS NOT NULL): signal type, token, WR, PnL
- Identify: best/worst signals, best/worst tokens, overall WR and PnL
- Check trade frequency: trades per hour

### 3. Parameter Assessment
- Are the current trailing params (activation=0.25%, distance=0.50%) appropriate?
- Is ATR_SL_MIN at 0.8% working or too tight/wide?
- Is SIGNAL_FILTER_SPEED_MIN at 35 causing trade starvation?

### 4. Decisions Required
Based on your analysis, make specific recommendations:
- Which signals should be enabled/disabled?
- Which tokens should be blacklisted/unblacklisted?
- Which parameters should be adjusted?
- Should live trading continue or pause?

### 5. Output Format
Write your executive summary to `automation/ceo_report.md` with:
- System health status
- Performance summary
- Key decisions made
- Parameter changes recommended (with rationale)
- Risks and open questions

Be concise. Lead with decisions, not analysis.
TASK
