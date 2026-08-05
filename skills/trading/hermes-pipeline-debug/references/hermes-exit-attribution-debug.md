---
name: hermes-exit-attribution-debug
description: Debug why two trades with identical outcomes (both hit SL) have different close_reason/exit_reason values, or why a trade's guardian_closed flag doesn't match expectations. Trace which execution path (guardian self-close, guardian breach-handler, pipeline ATR monitor, cascade flip) closed a trade.
category: trading
tags: [hermes, trading, close-reason, guardian, exit-attribution]
---

# Hermes Exit Attribution Debug

## When to Use
- Two trades both hit SL but have different `close_reason` values (e.g., `SL triggered` vs `atr_sl_hit`)
- A trade shows `guardian_closed=True` but you expect the pipeline to have closed it (or vice versa)
- Need to understand which system closed a specific trade
- `exit_reason` in brain.db doesn't match the actual close mechanism

## Diagnostic SQL

Run this first to see the key attribution fields:

```sql
SELECT token, direction, entry_price, exit_price, pnl_pct,
       exit_reason, close_reason,
       is_guardian_close, guardian_closed, guardian_reason,
       signal, strategy, close_time
FROM trades
WHERE token IN ('TOKENA', 'TOKENB')
  AND close_time >= '2026-04-28 00:00';
```

Key interpretation:
- `guardian_closed = TRUE` → guardian closed it (self-close OR breach handler)
- `guardian_closed = FALSE` → pipeline closed it (position_manager, decider_run, etc.)
- `is_guardian_close = TRUE` → trade was originally created by guardian (orphan recovery)

## The Three Guardian Close Paths

### Path 1: Self-Close (UNPROTECTABLE coins)
HL rejects TP/SL trigger orders for coins on `UNPROTECTABLE_COINS` list (hl-sync-guardian.py line ~36).
Guardian computes SL/TP locally and fires `market_close()` when price breaches.

- `close_reason` = `'SL triggered'` or `'TP triggered'`
- `guardian_closed = TRUE`
- `is_guardian_close = FALSE` (unless it was also an orphan recovery)
- Code: `_monitor_self_close()` → `close_position_hl()`

### Path 2: Breach Handler (normal coins with stored SL)
Guardian checks live HL positions against stored `stop_loss`/`target` in brain.db.

- `breach_reason = 'breach_SL'` or `'breach_TP'`
- `guardian_closed = TRUE`
- Code: `check_hl_breach()` in hl-sync-guardian.py, lines ~3070-3217

### Path 3: Orphan Recovery Close
Guardian finds an HL position with no corresponding paper trade, creates paper trade first, then closes it.

- `guardian_closed = TRUE`
- `is_guardian_close = TRUE`
- `close_reason` = `'PHANTOM_CLOSE'` or `'HL_CLOSED'` or `'MANUAL_CLOSE'`

## The Pipeline Close Paths

### Path 4: Pipeline ATR SL Monitor
Pipeline's own SL/TP tracking fires independently of HL's trigger system.

- `close_reason` = `'atr_sl_hit'` (or other pipeline-side reason)
- `guardian_closed = FALSE`
- `is_guardian_close = FALSE`

### Path 5: Cascade Flip
Cascade flip closes losing positions per `CASCADE_FLIP_PCT_LOSER`.

- `close_reason` set by cascade_flip logic
- `guardian_closed = FALSE`

## Quick Reference: Reason Strings by Path

| Close Path | close_reason | guardian_closed |
|---|---|---|
| Self-close (UNPROTECTABLE) | `SL triggered` | TRUE |
| Breach handler | `breach_SL` | TRUE |
| Orphan recovery | `PHANTOM_CLOSE` | TRUE |
| Pipeline ATR SL | `atr_sl_hit` | FALSE |
| Cascade flip | `cascade_flip` | FALSE |
| Manual | `manual_close` | FALSE |

## Debug Steps

1. **Query DB fields first** — `guardian_closed`, `is_guardian_close`, `exit_reason`, `close_reason` tell you 90% of the story
2. **Check UNPROTECTABLE list** — if coin is on it and `guardian_closed=TRUE`, it's self-close path
3. **Grep for the reason string** to find the closing code:
   ```bash
   grep -rn "SL triggered\|atr_sl_hit\|breach_SL" /root/.hermes/scripts/
   ```
4. **Check guardian log** — `/root/.hermes/logs/sync-guardian.log` — search for the coin symbol
5. **Check pipeline log** — `/root/.hermes/logs/pipeline.log` — search for the coin + close_reason
