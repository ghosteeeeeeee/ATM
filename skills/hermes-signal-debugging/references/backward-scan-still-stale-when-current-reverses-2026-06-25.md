# Backward Scan Still Fires Stale Signals When Current Bar Reverses (2026-06-25)

**Severity:** P1 — backward scan was supposed to fix this. It didn't fully.

**Found in:** `signals/accel_300.py` after the 2026-06-23 backward-scan fix. Confirmed via 8 of 12 accel-300- losing SHORT trades (UMA #12196, ASTER #12194, TAO #12191, FET #12195, ENS #12190, ONDO #12188, ENS #12187, UMA #12189) where price was ABOVE EMA300 at signal time but the trade was opened as SHORT.

## The Pattern

The 2026-06-23 fix changed the loop from `for i in range(PERIOD+LOOKBACK, len(closes)-1)` to `for i in range(len(closes)-2, PERIOD+LOOKBACK-1, -1)`. This correctly returns the MOST RECENT qualifying bar, not the oldest.

But the fix is INCOMPLETE. The signal still fires on the most recent bar where price was below EMA, even when the CURRENT bar is above EMA. The detector picks bar 503 (4.9 hours before signal time) because that's the most recent bar where price was below EMA — but the trade is opened at the CURRENT bar's time, where price is above EMA.

The signal direction is set to SHORT based on bar 503's data. The trade is opened at the live bar where price is above EMA. The trade gets squeezed.

## T's Intuition (which is correct)

"if it crossed 4 hours ago, and now a new (opposite) cross happened 10 mins ago, it should have picked the current accelerating cross over the 4 hours ago ones, because it is going backwards."

The backward scan handles this case — if a new cross happened recently, the loop finds the new bar FIRST. But if NO new cross has happened recently (price stayed above EMA for 4 hours), the loop finds the OLDEST within-stale-window qualifying bar. The fix is incomplete because it doesn't require the current bar to match the signal bar's direction.

## Symptom Pattern

User reports: "the longs are getting forwarded as shorts" or "wrong direction signals". 24h analysis shows winning accel-300- SHORT trades have `bars_from_latest < 5` and current gap matching signal direction. Losing trades have `bars_from_latest > 30` AND current gap OPPOSITE to signal direction.

## Diagnostic Recipe

For each losing accel-300- SHORT trade:
1. Get the signal record from `signals_hermes_runtime.db` (or trades.signal column)
2. Get the open time and the price at that time
3. Compute EMA300 from 700 1m prices ending at open time (same as detector)
4. Check: was price BELOW EMA at the latest bar (i = len(closes)-1)?
5. If NO, the signal direction is wrong for the current bar — the trade should not have fired

```python
import sqlite3
from datetime import datetime, timezone

db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = db.cursor()

# Trade open time → unix timestamp
target = int(datetime(2026, 6, 24, 23, 31, 6, tzinfo=timezone.utc).timestamp())

# Get 700 1m prices ending at this timestamp
c.execute('''SELECT timestamp, price FROM (
    SELECT timestamp, price FROM price_history 
    WHERE token = ? AND timestamp <= ?
    ORDER BY timestamp DESC LIMIT 700
) sub ORDER BY timestamp ASC''', ('UMA', target))
rows = c.fetchall()
closes = [r[1] for r in rows]

# Compute EMA300
ema = [None] * 299 + [sum(closes[:300]) / 300]
k = 2.0 / 301
for j in range(300, len(closes)):
    ema.append(closes[j] * k + ema[-1] * (1 - k))

# Check current bar (last index) direction
current_above = closes[-1] > ema[-1]
print(f"Last bar: price={closes[-1]:.6f}, EMA={ema[-1]:.6f}, ABOVE={current_above}")
print(f"For SHORT signal at this bar: {'CONSISTENT' if not current_above else 'WRONG DIRECTION'}")
```

## The Two Missing Checks

The 2026-06-23 fix added backward scan but missed TWO additional requirements:

### Missing Check #1: Current bar must match signal direction

After the loop finds the signal bar `i`, before returning, add:
```python
# CURRENT-BAR CONSISTENCY CHECK
# If the current (latest) bar is in the OPPOSITE direction, the signal is stale.
last_idx = len(closes) - 1
if direction == 'SHORT' and closes[last_idx] > ema300[last_idx]:
    continue  # latest bar above EMA — SHORT signal from 4h ago is stale
if direction == 'LONG' and closes[last_idx] < ema300[last_idx]:
    continue  # latest bar below EMA — LONG signal from 4h ago is stale
```

### Missing Check #2: STALE_LOOKBACK too lenient

`ACCEL_300_STALE_LOOKBACK = 400` (≈6.7 hours of 1m data) allows signals from any bar in the last 6.7 hours. This should be ~5-10 bars (5-10 minutes max) for accel-300 since the signal is supposed to be capturing a FRESH acceleration.

```python
# In hermes_constants.py
ACCEL_300_STALE_LOOKBACK = 10  # was 400 — tightened 2026-06-25
```

Either fix alone helps; both together close the bug. Fix #1 alone: still allows 6.7-hour-old signals in narrow windows. Fix #2 alone: still fires stale signals in narrow windows if current bar happens to match.

## Why The 2026-06-23 Audit Missed This

The 2026-06-23 audit was triggered by 31% of signals firing with direction wrong vs the actual price-vs-EMA relationship at signal-write time. The fix changed scan direction. The audit verified: "FIX 2026-06-23: Scan BACKWARD from the latest bar so the FIRST match is the MOST RECENT qualifying bar. Previously scanned forward with break-on-first-match, which returned the OLDEST qualifying bar."

The fix correctly addressed the OLDEST-vs-MOST-RECENT distinction. But it didn't address the MOST-RECENT-vs-CURRENT distinction. The 2026-06-23 audit sample was at the time when the issue was "signals are hours old." After the fix, signals are no longer hours old, but they can still be MINUTES old (32-296 minutes based on observed 24h data) and the current bar can have already reversed.

The 2026-06-25 re-discovery came from T's observation: "the accel_300.py was designed so when the price is above the EMA300 and accelerating upward that is a LONG, when price is below the EMA300 and accelerating downward(!) that is a SHORT. the signal is not comuting EMA300, or the longs are getting forwarded as horsts, what's going on?"

T's question was the key — the 2026-06-23 fix changed HOW the bar is found, but didn't add a check that the FOUND bar's direction is still valid at trade time.

## Related Skill Pattern

This is a generalization of the 2026-06-23 forward-vs-backward-scan bug, but the lesson is DIFFERENT. The 2026-06-23 lesson was: "iteration order determines what `break` returns." The 2026-06-25 lesson is: "ANY backward-scan fix must also verify the latest bar's state matches the signal bar's state, not just rely on finding the most recent qualifying bar."

**General principle for signal direction bugs:** When a signal captures a snapshot of market state (gap, cross, momentum), the fix must ensure BOTH:
1. The snapshot is the most recent one (backward scan)
2. The snapshot's direction is still valid at trade time (current-bar consistency)

(1) without (2) → fires signals on stale bar data, gets squeezed.
(2) without (1) → fires oldest qualifying bar, but at least the direction is right.

## Diagnostic Value of `gap_pct` vs `gap_growth` Distinction

`signals.value` stores `gap_growth` (the WIDENING of the gap), not `gap_pct` (the CURRENT gap). When investigating direction bugs, look at BOTH:
- `gap_pct` = (price - ema) / ema × 100 at the signal bar — what direction the signal says
- `gap_growth` = gap_pct - gap_pct_at_cross — how much the gap has widened

A SHORT signal with `gap_pct=-0.79%` (price 0.79% below EMA at signal bar) and `gap_growth=-0.30%` (gap widening) is internally consistent. But if the CURRENT bar's `gap_pct` is +0.39% (price now above EMA), the signal direction is wrong for trade time.

## Future Audit Checklist Addition

When auditing any signal detector with backward scan, verify:
1. The detector picks the most recent qualifying bar (backward scan ✓)
2. **The current bar's state matches the signal bar's direction** ← new check
3. The STALE_LOOKBACK gate uses a tight threshold (5-10 bars for fast signals)
4. The signal `value` field stores the direction-relevant metric (gap_pct, not just gap_growth)
5. The trade open time is within 1-2 minutes of the signal time (otherwise the signal is stale even if "fresh")

This complements the 2026-06-23 lesson (`forward-scan-stale-bar-2026-06-23.md`) — both are about preventing stale signals but at different stages of the detection pipeline.
