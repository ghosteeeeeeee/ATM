# accel-300 Staleness Gate Bug (2026-05-31)

## Bug: Stale Signal Passed When Price Crossed Back Above EMA

### Symptom
accel-300 producing SHORT signals for tokens whose **current price is above EMA300**. All 6 hot-set tokens (ETH, DASH, AVAX, BLUR, PEOPLE, PURR) showed price above EMA300 but signal returned direction=SHORT.

### Root Cause
Signal detected at bar `i` (price below EMA → valid SHORT). While signal sat in hot-set, price crossed back above EMA300 at newer bar `n-2`. Original final-verify checked `n-2` instead of `i` → blocked valid signals (Pattern 7 fix gone wrong). Fix changed to check `i` only → let stale signals through. **Both extremes are wrong.**

The correct pattern: when `i < n-2` (signal detected at older bar), **BOTH** detection bar `i` AND newest bar `n-2` must confirm direction. Stale signals where price crossed back above/below EMA must be blocked at evaluation time.

### Fix Applied (lines 343-359 in accel_300.py)
```python
# Staleness gate: signal detected at older bar (i < n-2) — verify newest bar too
newest_idx = len(closes) - 2
if i < newest_idx:
    # Signal is stale — newest bar must also confirm direction
    if direction == 'LONG' and not (closes[newest_idx] > ema300[newest_idx]):
        continue
    if direction == 'SHORT' and not (closes[newest_idx] < ema300[newest_idx]):
        continue
    if gap_pcts[newest_idx] is not None:
        if direction == 'LONG' and gap_pcts[newest_idx] >= 0:
            continue
        if direction == 'SHORT' and gap_pcts[newest_idx] <= 0:
            continue
        if direction == 'LONG' and abs(gap_pcts[newest_idx]) < MIN_GAP_PCT_LONG:
            continue
        if direction == 'SHORT' and abs(gap_pcts[newest_idx]) < MIN_GAP_PCT_SHORT:
            continue
```

### Pattern: Dual-Bar Staleness Gate
For any signal detected at bar `i` where `i < newest_bar`:
1. Verify detection bar `i` confirms direction (original check)
2. Verify newest bar `n-2` also confirms direction (new staleness check)
3. If either contradicts → block signal

This applies to any signal type where price crossing back across EMA invalidates a previously-valid detection.

### Files
- `/root/.hermes/scripts/signals/accel_300.py` — lines 343-359 (staleness gate)
- `/root/.hermes/scripts/signals/accel_300.py` — lines 323-341 (detection bar verify)
- `/root/.hermes/scripts/signals/accel_300.py` — line 191 (detection loop: `for i in range(PERIOD + LOOKBACK, len(closes) - 1)`)

### Data Source Verified
`_get_1m_prices()` correctly reads 1m closes from `price_history` (signals_hermes.db). Freshness guard at 120s, data-gap guard at max(150s, mean+3σ). LOOKBACK_1M=700 bars. Bug was purely logic, not data.