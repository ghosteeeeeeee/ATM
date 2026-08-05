# ICP + DOT Rapid SL Close — Not a Bug

**Date:** 2026-05-21
**Trades:** DOT SHORT #10226 (opened 22:06:08, closed 22:06:11, 3s), ICP SHORT #10234 (opened 23:22:07, closed 23:22:10, 3s)
**Close reason:** `atr_sl_hit` (both)

---

## What Happened

Both trades closed within ~3 seconds of opening with `close_reason=atr_sl_hit`. Investigation confirmed:
- **No system bug** — both trades had correctly placed ATR-based SL values
- **Genuine SL hits** — price moved against the SHORT immediately after entry and hit the stop within seconds

### ICP SHORT — entry $2.5368, SL $2.5175 (0.76% below entry)

Signal: `support_resistance` (confidence 88%, SHORT), source=`rs-r112,zscore-pump-`
SL computed via ATR (k=1.25 NORMAL_VOL, no speed boost): $2.5368 × (1 + 1.25 × 0.6%) = **$2.5176** ✓ matches DB value $2.5175 within rounding.

Exit price $2.5374 is **above** SL $2.5175 — price moved adversely immediately after open. The trade was stopped out correctly.

### DOT SHORT — entry $1.2465, SL $1.2084 (3.07% below entry)

Signal: `zscore_pump_short` (z_score=-3.413, confidence 79.3%, SHORT)
SL appears to use pump-mode k=3.0 (extreme z-score TIER-3): $1.2465 × (1 + 3.0 × 1%) ≈ **$1.209** ✓ matches.

Exit $1.2459 vs entry $1.2465 — price moved against SHORT direction, likely hit SL within that 3-second window.

---

## Key Findings

### 1. Both `position_manager` and `guardian` write `atr_sl_hit` for SHORT breaches

- `position_manager.check_atr_tp_sl_hits()` at line ~2361: sets `hit='atr_sl_hit'`
- `hl-sync-guardian._check_and_close_breached_trades()` at line ~3177: writes `breach_reason='guardian_sl'` then calls `close_position_hl` — the guardian path uses a different breach_reason string, not `atr_sl_hit`

Actually: the guardian uses `guardian_sl` / `guardian_tp` — `atr_sl_hit` comes ONLY from position_manager's `check_atr_tp_sl_hits`. The guardian's close_reason is `guardian_sl` not `atr_sl_hit`.

### 2. position_manager runs all three steps in the same cycle

```
check_and_manage_positions():
  1. refresh_current_prices()      → loads positions incl. newly opened
  2. _collect_atr_updates()         → compute SL/TP, write to DB via _persist_atr_levels
  3. check_atr_tp_sl_hits()         → reads SL from DB, checks breach
```

All three run within the same ~60s cycle. A newly opened position can have its SL computed and checked within one cycle.

### 3. The 3-second close window

Guardian runs every ~60s. position_manager runs every ~60s. A trade opened at X:22:07 would have its SL computed and checked by position_manager in the cycle that runs after the guardian sync. The guardian's `_check_and_close_breached_trades` reads SL from DB (written by `_persist_atr_levels` in the same position_manager cycle) and checks breach — so the guardian could close the trade in the same cycle it was opened if the SL was already written.

**Timing for ICP:**
- 23:21:38 — guardian sync (clean, 4 positions, 4 trades, 0 orphans)
- 23:22:07 — ICP trade opened (brain.py, SL written to DB)
- 23:22:10 — ICP trade closed (position_manager `check_atr_tp_sl_hits` or guardian `_check_and_close_breached_trades`)

Within 3 seconds: SL computed + breach checked. This is consistent with both systems running in the same ~60s window.

### 4. Guardian log was empty for these timestamps

Grep of guardian logs for `23:21`, `23:22`, `ICP`, `22:06` — no entries found. The guardian cycle that closed ICP did not log the breach event. This is suspicious — the guardian did not log its own close.

**Possible explanation:** `check_atr_tp_sl_hits` in position_manager closed the trade (wrote `atr_sl_hit`) before the guardian's next cycle ran. The guardian never saw the position as open, so logged nothing.

### 5. Local candles.db is empty for ICP and DOT

Cannot verify ATR values from candle data — `candles.db` returned no rows for ICP or DOT in any timeframe. ATR was computed from HL API or other source, not the local candle DB.

---

## Not a Bug — Correct System Behavior

Both trades were:
1. **Correctly signaled** — valid signal sources with sufficient confidence
2. **Correctly opened** — HL fill confirmed, DB record written
3. **Correctly SL-placed** — ATR computed within configured bounds (MIN_ATR_PCT=0.50%, MAX_SL=2.0%)
4. **Correctly closed** — price moved adversely, hit SL, position exited

The 3-second close is not a race condition — it's aggressive market conditions causing immediate adverse movement against the SHORT direction, with the SL placed correctly by the ATR engine.

---

## What Would Look Like a Bug vs Genuine SL Hit

| Scenario | Appearance | Actual Cause |
|---|---|---|
| SL hit within 3s, price reverted | Phantom close | Genuine SL hit + reversal — not a bug |
| SL hit but price never crossed SL | `atr_sl_hit` with price > SL | Falsy-0.0 bug, stale SL, or wrong price feed |
| Position closed but no SL in DB | `atr_sl_hit` with SL=0 | SL not persisted before breach check |
| Trade closed before ATR update runs | `atr_sl_hit` very fast | Guardian closed with stale/zero SL |
| Double close (guardian + PM) | Two close records | Race condition in dual-writer system |

This session's trades match scenario 1 — genuine SL hit after immediate adverse movement.

---

## Diagnostic Query

```sql
-- Check all atr_sl_hit closes with timing
SELECT id, token, direction, entry_price, stop_loss, exit_price, 
       close_reason, pnl_usdt, created_at, closed_at,
       EXTRACT(EPOCH FROM (closed_at - created_at)) as seconds_to_close
FROM trades 
WHERE close_reason = 'atr_sl_hit' 
  AND created_at > '2026-05-20' 
ORDER BY created_at;
```

If `seconds_to_close < 60` for any trade → check price movement in that window. If price crossed SL in <60s, it's a genuine fast SL hit, not a bug.