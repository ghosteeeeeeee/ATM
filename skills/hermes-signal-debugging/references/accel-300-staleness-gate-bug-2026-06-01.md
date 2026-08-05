# accel-300 Staleness Gate Bug — SNX/ME SHORT False Positives

**Date:** 2026-06-01  
**Signal:** accel-300 SHORT direction  
**Symptom:** SHORTs firing for tokens (ME, UNI, CHIP, FET) that subsequently hit atr_sl_hit. User disagreed with calls.

---

## Root Cause: Line 353 — Inverted Condition for SHORT Staleness

### The Bug

```python
# BUGGY (original):
if direction == 'SHORT' and gap_pcts[newest_idx] <= 0:
    continue  # BLOCKS valid SHORT (gap negative = price below EMA = correct)

# FIXED:
if direction == 'SHORT' and gap_pcts[newest_idx] >= 0:
    continue  # BLOCKS stale SHORT (gap positive = price crossed back above EMA = no longer SHORT)
```

### Why the Original Was Wrong

For SHORT direction:
- `gap_pcts[newest_idx] <= 0` → **TRUE** when price is BELOW EMA (gap negative) → BLOCKS valid SHORT → WRONG
- `gap_pcts[newest_idx] >= 0` → **TRUE** when price has crossed BACK ABOVE EMA (gap positive) → BLOCKS stale SHORT → CORRECT

For LONG direction (unchanged):
- `gap_pcts[newest_idx] >= 0` → **TRUE** when price is ABOVE EMA (gap positive) → BLOCKS stale LONG → CORRECT

### Mechanics of the Bug

The staleness gate at line 348-358 fires ONLY when `i < newest_idx` (signal detected at older bar, not at newest bar). So the bug affected signals where:
- Signal detected at bar `i` (e.g., bar 646 for ME SHORT)
- Newest bar at detection time had `gap >= 0` (price already crossed back above EMA)
- The buggy `<= 0` would evaluate TRUE for valid SHORT (gap negative) → BLOCK valid signal
- After fix: `>= 0` correctly blocks only stale SHORTs (gap positive = no longer SHORT)

### The Signal That Prompted Investigation

```
ME SHORT PENDING 70.0% accel-300-,rs-r172
Price at signal: $0.0848
Current ME price (2026-06-01 ~00:20): $0.08621
Current gap: +1.17% (price ABOVE EMA) — signal was correct at detection, stale now
```

### Debugging Path

1. Run `detect_accel_300(token, prices)` — check if signal fires
2. Inspect `gap_pcts` at newest_idx for both directions
3. Check staleness gate logic: `i < newest_idx` vs `i >= newest_idx`
4. For SHORT: correct check is `gap_pcts[newest_idx] >= 0` (block stale)
5. For LONG: correct check is `gap_pcts[newest_idx] <= 0` (block stale)

### Key File

`/root/.hermes/scripts/signals/accel_300.py` line 353

### Verification

```python
# After fix, verify with concrete trace:
from signals.accel_300 import _get_1m_prices, _ema_series, PERIOD, LOOKBACK, LOOKBACK_1M
prices = _get_1m_prices('ME', lookback=LOOKBACK_1M)
closes = [p['price'] for p in prices]
ema300 = _ema_series(closes, PERIOD)
gap_pcts = [(closes[i] - ema300[i]) / ema300[i] * 100 if ema300[i] else None for i in range(len(closes))]
newest_idx = len(closes) - 2
direction = 'SHORT'
print(f"gap_pcts[newest_idx] = {gap_pcts[newest_idx]:.4f}")
print(f"direction=SHORT, gap >= 0 → BLOCK (stale): {gap_pcts[newest_idx] >= 0}")
```

### Related Behavior

Staleness gate only applies when `i < newest_idx`. Signals detected at `i = newest_idx` (the second-to-last bar) skip the staleness gate entirely. This is correct by design — the newest bar is the detection bar, so no staleness check needed.

---

## Additional accel-300 Bugs Found This Session

### Bug 1: Regime Filter Reading Stale candles.db

- **File:** `accel_300.py` line ~362
- **Issue:** Regime filter was reading from `candles.db` which was 3+ days stale (last update 2026-05-28)
- **Fix:** Changed to read from `signals_hermes.db` `price_history` table (0.2 min stale)
- **Symptom:** XLM slope was -0.00004 (wrong, blocking LONG) vs actual +0.00008 (correct, allowing LONG)
- **Reference:** `accel-300-long-blocked-2026-05-31.md` in references/

### Bug 2: SHORT Expansion Gate Removed

- **Location:** Lines ~318-320 (removed the entire SHORT branch)
- **Issue:** Condition 4c expansion gate (`gap_now < gap_at_cross + MIN_GAP_EXPANSION`) was fundamentally broken for negative gaps (asymmetric comparison)
- **Fix:** Removed SHORT expansion gate entirely; condition 4a (gap growth) already captures SHORT acceleration
- **AI Engineer audit:** Both patches verified correct

---

## accel-300 Signal Flow Summary

```
1. Was_above/was_below check (LOOKBACK=30 bars) — must have crossed EMA recently
2. Cond2: |gap| >= MIN_GAP_PCT (0.20% for both LONG/SHORT, abs value)
3. Cond3: Persistent for PERSISTENCE_BARS (3 bars) — price consistently above/below EMA
4. Cond4a: Avg gap growth >= MIN_GAP_GROWTH (0.03%) — accelerating away from EMA
   - LONG: gap_now - gap_then (gap growing positive)
   - SHORT: gap_then - gap_now (gap growing more negative)
5. Cross bar search (LOOKBACK=30 bars): bars_since_cross = i - cross_bar
6. Cond: bars_since_cross >= 1 and <= 10
7. Cond4b (if bars_since_cross > 3): marginal acceleration — delta_last < delta_prev (SHORT)
8. Cond4c (LONG only): gap expansion gate — gap_now >= gap_at_cross + MIN_GAP_EXPANSION
9. Final verify at bar i: price still above/below EMA, gap sign and magnitude correct
10. Staleness gate (if i < newest_idx): newest bar must also confirm direction
    - LONG: gap_pcts[newest_idx] >= 0 → BLOCK (stale)
    - SHORT: gap_pcts[newest_idx] >= 0 → BLOCK (stale)  ← FIXED from <= 0
    - abs(gap) at newest must be >= MIN_GAP_PCT threshold
11. Regime filter: slope from OLS on 50-bar price_history must match direction
```

---

## Constants (hermes_constants.py)

```
ACCEL_300_MIN_GAP_EXPANSION = 0.10  # percent — may need lowering (Bug 2)
ACCEL_300_MIN_GAP_GROWTH = 0.03     # percent
MIN_GAP_PCT_SHORT = 0.20
MIN_GAP_PCT_LONG = 0.20
PERIOD = 300
LOOKBACK = 30
PERSISTENCE_BARS = 3
LOOKBACK_1M = 700
ACCEL_300_COOLDOWN_MIN = 1
ACCEL_300_TOKEN_ALLOWLIST = set()  # empty = no filter
```