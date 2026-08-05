# Persist Debug — SHORT SL Wrong (2026-05-18)

## Session Summary

**User's claim**: Sign error in SHORT-side ATR TP:SL logic — values are skipping hermes_constants and using defaults.

**Finding**: No sign error. TPSL engine (`tpsl_utils.compute_atr_sl_tp()`) is correct. The issue is display shows wrong values because PostgreSQL DB has stale fallback values — `_persist_atr_levels()` is either not writing or writing is failing silently.

## Concrete Data (pipeline log 04:24:06)

| Token | Direction | TPSL SL | Displayed SL | TPSL TP | Displayed TP | Delta |
|-------|-----------|---------|-------------|---------|-------------|-------|
| SNX | SHORT | 0.304210 | 0.308540 | 0.296380 | 0.2964 | +1.4% |
| UNI | SHORT | 3.423800 | 3.492564 | 3.354926 | 3.3549 | +2.0% |
| SKY | SHORT | 0.069178 | 0.070700 | 0.067914 | 0.0679 | +2.2% |

**TPSL formula**: `lowest_price * (1 + eff_sl_pct)` → anchor is `lowest_price` (correct)  
**Display formula**: `current_price * (1 + SL_PCT_FALLBACK=1.5%)` or `current_price * (1 + ATR_SL_MIN=0.5%)` → wrong anchor

## Root Cause Chain

1. `get_trade_params()` writes fallback SL at entry time (SL_PCT_FALLBACK=1.5%)
2. `_collect_atr_updates()` computes correct ATR SL/TP each cycle
3. `_persist_atr_levels()` should overwrite DB with new values — BUT pipeline log shows NO `[ATR] Updated` message for current cycle
4. `hermes-trades-api.py` reads from PostgreSQL → gets stale fallback values
5. Display shows wrong SL

## Key Diagnostic Commands

```bash
# Check if ATR updates are being persisted
grep "ATR Updated" /root/.hermes/logs/pipeline.log | tail -10
grep "PERSIST" /root/.hermes/logs/pipeline.log | tail -10

# TPSL log shows correct values (TPSL output to stdout/stderr)
# Display log shows wrong values (reads from PostgreSQL)

# Check PostgreSQL directly
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
cur = conn.cursor()
cur.execute(\"SELECT token, direction, entry_price, stop_loss, target, atr_managed FROM trades WHERE status='open' AND direction='SHORT'\")
for row in cur.fetchall():
    print(f'{row[0]} {row[1]}: entry={row[2]}, SL={row[3]}, TP={row[4]}, atr_managed={row[5]}')
"

# DB host unreachable from this context: 10.60.199.92 times out, localhost fails auth
# Must run from pipeline service context or Tokyo server
```

## Key Files

- `position_manager.py:1531` — `_collect_atr_updates()` — computes ATR, populates `_atr_updates`
- `position_manager.py:1710` — `_persist_atr_levels()` — writes `_atr_updates` to PostgreSQL
- `position_manager.py:1740` — `[PERSIST]` debug print — fires when DB write happens
- `position_manager.py:2352` — `[ATR] Updated X position SL/TP levels` — fires when `_atr_updates` non-empty
- `position_manager.py:1875` — `get_trade_params()` — fallback SL/TP at entry (wrong anchor for SHORT)
- `position_manager.py:1450-1493` — `_compute_dynamic_sl()` — legacy fallback, also wrong anchor
- `hermes-trades-api.py:202-223` — reads `stop_loss`/`target` from PostgreSQL
- `tpsl_utils.py:379-382` — SHORT SL/TP formula (correct: `lowest * (1 ± eff_pct)`)

## Why `[ATR] Updated` Was Absent

Pipeline log at 04:24:06:
```
[Position Manager] Open: 5 | Closed: 0 | Adjusted: 0
[Position Manager] Done
```

No `[ATR] Updated X position SL/TP levels` → `_atr_updates` was empty.

Possible causes:
1. Trailing gate blocking (current SL already matches ATR levels — but this doesn't explain why SHORT SL is 1.4-2.2% off)
2. ATR fetch returning `None` (Pattern 5 — stale cache + Binance fallback blocked)
3. `_collect_atr_updates()` skipping SHORT trades for some reason

## What To Add

1. **Debug to `_collect_atr_updates()`**: Print WHY each trade is/isn't included — `needs_sl`, `needs_tp`, `current_sl`, `computed new_sl`, whether ATR fetch succeeded, whether trailing gate blocked

2. **Debug to `_persist_atr_levels()`**: Print DB before/after values for every write, and explicitly when `_atr_updates` is empty (to confirm it was called but had nothing to do)

3. **Verify PostgreSQL write path**: Pipeline service uses peer auth via local socket — may fail silently if connection method is wrong

## SNX SHORT TP Mystery

TPSL log shows `eff_tp=1.500%` but TP=0.296380. Back-calculation:
```
TP = lowest * (1 - eff_tp) → 0.296380 = 0.303300 * (1 - x) → x = 2.273%
```
The displayed `eff_tp=1.500%` contradicts the actual TP value. Most likely:
- TP was set when `lowest_price` was different (lower)
- Trailing gate blocks loosening → TP stays at the tighter level even as `eff_tp` would suggest wider
- Or `eff_tp_pct` was floored at a higher value when TP was first set
