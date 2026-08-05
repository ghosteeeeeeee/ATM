# accel-300 Staleness Fix (2026-05-31)

## The Bug

Signal detected at bar `i` (price below EMA300 → valid SHORT), but by the time signal reaches hot-set, price has crossed back above EMA300 at newest bar `n-2`. The signal should be blocked as stale.

### Bug Cycle (3 iterations)

**Iteration 1 — Old code**: Final-verify checked `n-2` (newest bar) instead of `i` (detection bar).
- Signal fires at `i=395` (price below EMA, valid SHORT)
- Final-verify checks `n-2=698` (price now ABOVE EMA) → BLOCKED
- Result: blocked valid signals → Pattern 7 issue (subagent flagged it)

**Iteration 2 — My fix**: Changed final-verify to check `i` only.
- Signal fires at `i=395` (price below EMA, valid SHORT)
- Final-verify checks `i=395` (price below EMA) → PASSES
- But `n-2=698` is now above EMA → stale signal gets through
- Result: let stale signals through → **new bug introduced**

**Iteration 3 — Correct fix**: Check BOTH detection bar AND newest bar.
- When `i < n-2` (signal detected at older bar), verify BOTH bars:
  - Detection bar `i`: must confirm direction (below EMA for SHORT)
  - Newest bar `n-2`: must still confirm direction (still below EMA)
- If either bar contradicts the stated direction → block
- Result: stale signals blocked, valid signals pass

### The Fix in accel_300.py (lines ~350-372)

```python
# Staleness gate: if signal detected at older bar, newest bar must confirm
if i < newest_idx:
    newest_gap_pct = (closes[newest_idx] - ema_val_at_newest) / ema_val_at_newest * 100
    newest_above = closes[newest_idx] > ema_val_at_newest
    newest_abs_gap = abs(newest_gap_pct)
    # Block if newest bar contradicts direction
    if direction == 'SHORT' and not (newest_gap_pct < 0 and newest_abs_gap >= MIN_GAP_PCT_SHORT):
        return None
    if direction == 'LONG' and not (newest_gap_pct > 0 and newest_abs_gap >= MIN_GAP_PCT_LONG):
        return None
```

## Key Lesson

When fixing a staleness bug, do NOT replace the old check entirely. The old check (newest bar) was correct in intent — it prevented stale signals. The bug was that it checked the wrong bar for the detection logic. The correct fix: verify BOTH detection bar AND newest bar. Neither alone is sufficient.

Pattern: `old_check` was checking `n-2` incorrectly → replaced with `i`-only → stale signals leaked → add staleness gate back alongside `i` check.

## Verification

```python
# Run on tokens that were incorrectly tagged SHORT with price above EMA
tokens = ['ETH', 'DASH', 'PURR', 'AVAX', 'BLUR', 'PEOPLE']
# All 6 now correctly produce: No signal
# (price above EMA, signal was stale SHORT from when price was below)
```

## Related

- Pattern 7 fix context: detection-bar check was needed so right bar is verified
- The staleness gate adds newest-bar verification that was accidentally removed
- Bug originated from my own prior patch replacing n-2 with i-only