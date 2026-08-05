# pump_hunter Bypasses Hot-Set — Critical Execution Path Bug

## Issue (2026-05-12)

`pump_hunter.py` writes trades **directly to PostgreSQL brain DB**, bypassing the entire hot-set gate:

```python
# pump_hunter.py:363-408 — _create_brain_record()
cur.execute("""
    INSERT INTO trades (
        token, direction, amount_usdt, entry_price, hl_entry_price,
        exchange, paper, server, status, open_time,
        pnl_usdt, pnl_usdt, leverage, signal,
        sl_distance, trailing_activation, trailing_distance,
        is_guardian_close, guardian_closed
    )
    SELECT %s, %s, %s, %s, %s, 'Hyperliquid', false, 'Hermes', 'open', NOW(),
           0, 0, %s, 'pump_hunter',  # signal='pump_hunter' marks it
           0.03, 0.01, 0.01, FALSE, FALSE
    WHERE NOT EXISTS (
        SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open'
    )
    RETURNING id
""", (...))
```

**Effect:** ASTER SHORT traded at 04:26 without appearing in `hotset.json` or going through `decider_run.py` execution gate.

## Why It Happens

pump_hunter is triggered by a separate systemd timer (`hermes-pump-hunter.timer`) that fires independently of the pipeline. Its execution path:
```
pump_hunter.timer → hermes-pump-hunter.service → pump_hunter.py --live
                                                 ↓
                                          _create_brain_record()
                                                 ↓ direct PostgreSQL INSERT
                                          brain DB (bypasses hot-set entirely)
```

## Why It's Dangerous

1. **No hot-set filter** — pump_hunter can open positions in tokens that WR gate would block
2. **No regime filter** — decider_run's counter-regime trap is bypassed
3. **No survival rounds check** — pump_hunter doesn't respect hot-set discipline
4. **No confluence requirement** — single-source signals can trigger live trades
5. **Guardian confusion** — guardian sees an "orphan" position with no signal_source matching open trade in signals DB

## The Stuck Signals Problem

`hermes-signal-compactor.timer` was DISABLED since April 29. Result:
- signal_compactor never ran → APPROVED signals never expired
- APEX SHORT (03:56), ZK LONG (03:50), LTC SHORT (03:50), FIL SHORT (03:50), SKY SHORT (03:47) all stuck as APPROVED
- These signals predate the trend_purity requirement (trend_purity- was added 2026-05-12)
- They can't expire because signal_compactor isn't running to mark them EXPIRED

## Fix Required

1. **Re-enable signal_compactor timer:**
   ```bash
   systemctl enable hermes-signal-compactor.timer
   systemctl start hermes-signal-compactor.timer
   ```

2. **Fix pump_hunter to route through hot-set gate:**
   - Remove direct PostgreSQL INSERT from pump_hunter
   - Instead: write a signal to signals DB (like other signal scripts)
   - Let signal_compactor handle it normally
   - Or: add pump_hunter to signals_runner.py so it goes through the normal pipeline

## Diagnostic Query — Stuck APPROVED Signals

```python
# Check for old APPROVED signals that never expired
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.execute("""
    SELECT token, direction, decision, source, created_at,
           ROUND((julianday('now') - julianday(created_at)) * 1440, 1) as age_min
    FROM signals
    WHERE decision='APPROVED' AND executed=0
    ORDER BY age_min DESC
""")
# age_min > 60 = stuck (should have been expired by signal_compactor)
```

## Root Cause Chain

```
2026-04-29: hermes-signal-compactor.timer disabled
     ↓
signal_compactor.py never runs
     ↓
APPROVED signals never expire (signal_compactor does EXPIRED transitions)
     ↓
Old signals accumulate in DB
     ↓
T sees "stuck signals" in UI
     ↓
pump_hunter bypasses hot-set → trades without signal_compactor vetting
```