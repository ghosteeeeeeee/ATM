---
name: open-position-stage-query
description: Query live wave phase, velocity, and ATR context for already-open Hermes trades using speed_history.json and atr_cache.json. Use when T asks about the current stage (accelerating, quiet, decelerating) of an open position.
trigger: "what stage is [COIN] in?, accelerating or decelerating?, ATR context for open trade, wave phase for open position, which mechanism is tracking the SL?, is trailing being used?, how many SL systems are active?"
---

# Open Position Stage Query

## Trigger
When T asks about the current wave phase, acceleration, velocity, or ATR context of an **already-open trade** — e.g. "what stage is AXS in?", "is this position accelerating or decelerating?", "what's the ATR for this open trade?"

Not for pre-trade signals (those come from hotset.json with wave_phase already computed). This is for open positions being actively monitored.

## Data Sources

### speed_history.json
- Path: `/root/.hermes/data/speed_history.json`
- Structure: `{ "SYMBOL": [ {"price": float, "ts": float}, ...] }`
- ~60 recent ticks per token, updated continuously
- Used to compute: velocity (%/hr), acceleration, wave_phase (accelerating/decelerating/quiet/near-flat)

### atr_cache.json
- Path: `/root/.hermes/data/atr_cache.json`
- Structure: `{ "SYMBOL": {"atr": float, "ts": float} }`
- Current ATR14 per token
- Used to assess volatility context and proximity to SL/TP

### trades.json
- Path: `/var/www/hermes/data/trades.json`
- Current entry, SL, TP, pnl_pct, leverage for all open positions

## How to Compute Wave Phase

```python
import json

# Load speed history for token
with open('/root/.hermes/data/speed_history.json') as f:
    d = json.load(f)
ticks = d.get('SYMBOL', [])

# Compute velocity per tick interval
vels = []
for i in range(1, len(ticks)):
    dt = ticks[i]['ts'] - ticks[i-1]['ts']
    dp = ticks[i]['price'] - ticks[i-1]['price']
    pct = dp / ticks[i-1]['price']
    vph = pct / dt * 3600 if dt > 0 else 0  # % per hour
    vels.append((dt, pct, vph))

# Compare recent vs older velocity
recent_v = [v[2] for v in vels[-6:]]
older_v = [v[2] for v in vels[-12:-6]]
avg_recent = sum(recent_v) / len(recent_v)
avg_older = sum(older_v) / len(older_v)
accel = avg_recent - avg_older

if avg_recent > 0.05:
    wave_phase = "accelerating"
elif avg_recent < -0.05:
    wave_phase = "decelerating"
else:
    wave_phase = "quiet/near-flat"
```

## Quick Terse Output Format

When T asks "what stage is X in?", return:
- Wave phase (accelerating / decelerating / quiet/near-flat)
- Velocity trend (avg recent vs prior)
- Entry vs current vs SL vs TP
- ATR % of price
- Distance to SL and TP in %

## SL/TP Mechanism Audit (Secondary Investigation)

### The Three Mechanisms

**1. position_manager._collect_atr_updates() — THE ATR engine**
- File: `/root/.hermes/scripts/position_manager.py`
- Reads `highest_price`/`lowest_price` from DB, computes SL as `peak × (1 - k × atr%)`
- Close decision: `check_atr_tp_sl_hits()` → reason `atr_sl_hit` or `atr_tp_hit`
- Guardian note at line 1028: "SL/TP is owned by position_manager's ATR trailing engine"

**2. hl-sync-guardian._check_hard_stops() — emergency backup**
- File: `/root/.hermes/scripts/hl-sync-guardian.py` line 1538
- Only fires for positions where `atr_managed IS NULL OR atr_managed = FALSE`
- Pure price-based: if price crosses stored DB SL/TP by >0.1%, closes immediately

**3. HL trigger orders (initial, now stale)**
- Written by `brain.py` lines 451-455 at position open
- They become stale as ATR engine tightens SL/TP each cycle
- Cleanup happens when ATR hit fires

### Dead Fields to Watch For

`trailing_activation` and `trailing_distance` are **written to DB** but **never read and used as a trigger**. The ATR engine does NOT check these fields. They are legacy dead fields.

### How to Audit a Specific Trade

```bash
# 1. Check atr_managed flag
psql $DB_URL -c "SELECT id, token, atr_managed, stop_loss, target, trailing_activation, trailing_distance FROM trades WHERE token='AXS' AND status='open';"

# 2. Check which system wrote the SL
grep -n "SL/TP is owned" /root/.hermes/scripts/hl-sync-guardian.py

# 3. Check if trailing_activation is ever READ (not just written)
grep -rn "trailing_activation" /root/.hermes/scripts/ | grep -v "\.bak\|WHERE\|VALUES\|INSERT\|SELECT\|UPDATE" | grep -v "trailing_activation ="
```

## Notes
- speed_history.json ticks are at ~10s intervals with some irregularity — don't treat as exactly uniform
- Some tokens in atr_cache may have stale ATR (check `ts` field)
- wave_phase in hotset.json (pre-trade) is computed differently — don't conflate the two
