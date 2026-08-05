# Phantom Trades / Ghost Signal Root Cause — 2026-05-19

## Summary

AVAX/AAVE/NEAR/SUSHI/BRETT opened and closed on HL in <10s intervals. PostgreSQL has no record of the open. Guardian created `guardian_orphan` records with WRONG entry prices. Root cause is **signal lifecycle architecture**, not guardian.

## The Failure Chain

```
Pipeline (e.g. 20:50): decider_run → brain.py → mirror_open succeeds on HL
                                          → DB INSERT into PostgreSQL FAILS
                                          → sys.exit(1)
                         signal marked EXECUTED in SQLite
                         AAVE position orphaned on HL (no DB record)

Guardian (e.g. 20:52): Detects AAVE orphan via HL positions API
                       Closes HL position (fill = WRONG entry price, should be actual entry)
                       Creates guardian_orphan trade #10205 with entry = close price
                       Closes trade #10205 immediately
                       Result: PnL is noise, real HL history lost
```

## Guardian Log Evidence

```
20:52:10 — Orphan AAVE detected (HL has position, DB has no record)
20:52:11 — Guardian closes AAVE on HL (fill 88.293) ← WRONG entry price
20:52:17 — Guardian creates guardian_orphan #10205 (entry=88.304) ← close price, not entry
20:52:22 — Guardian closes #10205 (exit=88.295, pnl=-0.01)

20:53:30 — Orphan AVAX detected
20:53:31 — Guardian closes AVAX on HL (fill 9.1322) ← WRONG entry price
20:53:37 — Guardian creates guardian_orphan #10206 (entry=9.1323) ← close price, not entry
20:53:42 — Guardian closes #10206 (exit=9.1310, pnl=-0.01)
```

## Why DB INSERT Fails (Root Cause #1)

brain.py `add_trade()` PostgreSQL INSERT can fail silently. When it does:
- `mirror_open` already succeeded — HL position is live
- `sys.exit(1)` fires → decider_run sees RC=1 → fires rollback
- **But**: if `sig_id=None` (legacy hot-set signals), rollback SQL `WHERE signal_id=%s` matches nothing
- Signal stays `decision='EXECUTED', executed=1` in signals DB
- No trade in PostgreSQL, no position on HL (orphan)
- Guardian detects orphan, closes it, creates WRONG record

## Why Guardian Orphan Records Have Wrong Entry Price (Root Cause #2)

When guardian creates an orphan record to capture a pre-existing HL position:
```python
# hl-sync-guardian.py:1169 — WRONG
trade_id = add_orphan_trade(
    coin, direction, entry_px, amount_usdt, lev, sl_price, tp_price
)
# Uses entry_px from hl_pos (current market price at detection time)
# Should use: get_realized_pnl(coin, start_ms)['entry_price']
```

The guardian uses `entry_px` from the HL positions API (the price at which the position was detected) instead of the actual weighted-average entry price from HL fill history.

## Signal Lifecycle Race Condition (Root Cause #3)

```
decider_run line 1869: mark_signal_executed(token, direction, sig_id=None)
                       Sets decision='EXECUTED' BEFORE calling brain.py

brain.py: mirror_open succeeds → DB INSERT fails → sys.exit(1)

decider_run: rollback_signal_executed(token, direction, signal_id=None)
             SQL: UPDATE signals SET decision='APPROVED', executed=0
                  WHERE signal_id=None — MATCHES NOTHING

signal_compactor: Runs BETWEEN brain.py failure and rollback
                  Finds AAVE EXECUTED signal → marks it EXPIRED
                  New AAVE PENDING signal created

Rollback: Updates OLD signal (now EXPIRED), new signal stays PENDING
Result: signals.json shows AAVE EXECUTED from old signal, no trade exists
```

## 5 Root Causes Identified

| # | Root Cause | File | Impact |
|---|-----------|------|--------|
| 1 | PostgreSQL INSERT fails silently after mirror_open succeeds | brain.py | Phantom HL positions |
| 2 | Guardian orphan uses `entry_px` (close price) not actual HL entry price | hl-sync-guardian.py:1169 | Corrupted PnL |
| 3 | Signal marked EXECUTED before brain.py runs | decider_run.py:1869 | Race condition |
| 4 | Compactor expires EXECUTED signals without verifying DB trade exists | signal_compactor.py | Orphaned signals |
| 5 | `POSITION_SIZE_USD=50.0` hardcoded in decider_run | decider_run.py:140 | Should use hermes_constants |

## Fix Plan (Not Yet Implemented)

### Fix 1: Link signal to trade_id on success
- Add `trade_id INTEGER` column to signals table
- `mark_signal_executed(signal_id, trade_id)` — update trade_id on success
- Only expire EXECUTED signals where `trade_id IS NOT NULL`

### Fix 2: Fix guardian orphan entry price
- Use `get_realized_pnl(coin, start_ms)['entry_price']` instead of `entry_px`
- Guardian already calls `get_realized_pnl` for other fields — just use it for entry too

### Fix 3: Don't mark signal EXECUTED until brain.py confirms
- Move `mark_signal_executed()` to AFTER brain.py returns successfully
- Or: use a PENDING state first, then update to EXECUTED on success

### Fix 4: Compactor — only expire signals with verified trades
- `WHERE decision='EXECUTED' AND trade_id IS NOT NULL` — only expire signals with actual trades
- Signals with EXECUTED but no trade_id are orphans → don't expire, alert

### Fix 5: Import DEFAULT_TRADE_SIZE_USDT in decider_run
- Replace `POSITION_SIZE_USD = 50.0` with `from hermes_constants import DEFAULT_TRADE_SIZE_USDT`

## Diagnostic Commands

```bash
# Check signals DB for phantom EXECUTED signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, decision, signal_id, trade_id, created_at FROM signals \
   WHERE token='AAVE' ORDER BY created_at DESC LIMIT 5"

# Check PostgreSQL for guardian orphan trades
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"SELECT id, token, status, entry_price, exit_price, pnl_usdt, close_reason, guardian_closed, open_time FROM trades WHERE guardian_closed=true ORDER BY id DESC LIMIT 5\")
for r in cur.fetchall(): print(r)
cur.close(); conn.close()
"

# Check HL fill history for actual entry prices
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_realized_pnl, get_trade_history
import time
start = int((time.time() - 600) * 1000)  # last 10 min
fills = get_trade_history(start)
for f in fills:
    if f['coin'].upper() in {'AAVE','AVAX','NEAR','SUSHI','BRETT'}:
        print(f['coin'], f['dir'], f['sz'], f['px'], f['closed_pnl'])
"
```

## Key Lesson

**Guardian is working correctly.** It detects orphans and closes them. The problem is upstream: brain.py DB INSERT fails, leaving phantom HL positions. The guardian's job is to close orphans — it does that. The real fix is preventing the DB INSERT failure in brain.py and fixing the signal lifecycle race.

The `guardian_orphan` trades with wrong entry prices are a symptom, not the cause. Fix the DB INSERT failure and the orphan trades go away.