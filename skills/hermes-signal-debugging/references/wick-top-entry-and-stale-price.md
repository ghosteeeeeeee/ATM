# Wick-Top Entries + Stale Price ATR Bug

Two distinct issues that cause fast stop-outs after entry:

---

## Issue 1: Entries at Momentum Peaks (Wick Tops)

**Root cause:** `accel-300+`, `hzscore-`, `vel-hermes+` and similar momentum signals can fire most strongly at the exact top of a price spike — when momentum is most overextended. The signal is technically correct (momentum IS strong at that moment), but entering there is the worst possible timing because mean reversion kicks in immediately.

**Symptom:** Entry at or near the high/wick of a 1m candle, immediate stop-out within seconds to minutes on a normal pullback. The ATR SL is correctly placed; the entry price was the problem.

**Real trades (2026-05-05):**
| Trade | Direction | Entry Price | Entry Was | SL | Outcome |
|-------|-----------|-------------|-----------|----|---------|
| DASH #8549 | LONG | $46.828 | 1m candle HIGH | $46.590 | -0.77%, 3s |
| ME #8550 | LONG | $0.10570 | Local peak | $0.105489 | -0.22%, 3s |
| SUSHI #8551 | SHORT | $0.21848 | Local peak | $0.218676 | +0.11%, 58s |

DASH entry was at the exact high of the 19:24 candle ($46.828). The next candle opened at $47.11 then immediately collapsed to $46.47 — a normal pullback that hit the correctly-placed SL.

**How to distinguish from the stale-price bug:**
- Stale-price bug: SL is 0.3-0.5% tighter than it should be due to wrong entry price in ATR computation
- Wick-top entry: SL is correctly placed relative to entry price, but entry was at an unsustainable extreme

**Diagnostic query:**
```sql
SELECT token, direction, entry_price, stop_loss, ROUND((entry_price - stop_loss)/entry_price*100, 3) AS sl_pct
FROM trades 
WHERE server='Hermes' AND status='closed' 
  AND close_reason = 'atr_sl_hit'
  AND created_at > datetime('now', '-7 days')
ORDER BY created_at DESC;
```
If sl_pct varies wildly (some 0.2%, some 1.5%), the entries themselves are inconsistent — likely a mix of wick-top entries and normal entries.

---

## Issue 2: Stale Entry Price in signal_compactor._live_price()

**Root cause:** `signal_compactor._live_price()` fetches price from signals DB:
```python
cur.execute(
    "SELECT price FROM signals WHERE token=? ORDER BY created_at DESC LIMIT 1", (tok,)
)
```
This is the last recorded signal's price, not the current market price. When no signal has been generated for several minutes, this price is stale.

**Stale price flows through:**
1. `_live_price()` → used at line ~1391 to build hot-set.json entry
2. → `decider_run.execute_trade()` → `brain.add_trade()` (recorded as `entry_price`)
3. → `position_manager._collect_atr_updates()` reads `entry_price` from DB position
4. → `_compute_initial_sl_tp()` uses it for ATR computation → **wrong SL**

**Effect:** If signals DB has $46.30 but market is $46.55, the SL is ~0.5% tighter than designed. Normal 1m wicks then hit the too-tight stop.

**Example:** DASH signals DB had $46.469 at 19:24 but market was $46.828 — a 0.77% discrepancy that made the SL ~0.25% tighter than intended. Combined with a wick-top entry, this created a double-punch problem.

**Fix required:** `_live_price()` should fetch from `hype_cache.get_allMids()` or HL `/info` API, not signals DB.

---

## Combined Effect

Both issues can occur together: a stale price makes the SL tighter than intended, AND the entry was at a wick top where normal pullback is expected. This explains why seemingly reasonable ATR SLs (0.5-1.0%) were still hit within seconds.

**Prevention:** When multiple momentum signals confluent at a price extreme, flag it as a high-risk entry even if the hot-set threshold is met. The system has no candle-body vs wick detection at the 1m level — a signal that scores highly at a local price extreme is more likely a false signal than a true one.
