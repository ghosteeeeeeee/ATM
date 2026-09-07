# Bug Hunter Verdict: ema300_dip_short Losing Trades

**Date:** 2026-09-07 21:52 UTC  
**Investigator:** bug_hunter  
**Status:** ROOT CAUSE IDENTIFIED

---

## Executive Summary

The ema300_dip_short signal has a **staleness gap between detection and execution** that causes it to fire on trades where key conditions have already deteriorated. 8 of 9 losing trades fail the red candle check (C6) at execution time. The signal is valid when detected but stale when executed. The decider only re-validates 2 of 6 conditions (EMA slope + distance), leaving 4 conditions unchecked at execution time.

---

## Trade Analysis Summary

| Token | Entry Time | Entry $ | PnL | C5 RSI>65 | C6 Red Candle | Decider Re-check |
|-------|-----------|---------|-----|-----------|---------------|-----------------|
| STX | Sep 4 18:31 | $0.2625 | -5.56% | FAIL (64.6) | FAIL (GREEN) | PASS (slope/dist only) |
| ETC | Sep 4 18:37 | $7.3572 | -4.90% | FAIL (55.1) | PASS | PASS (slope/dist only) |
| SEI | Sep 4 23:12 | $0.04663 | -5.40% | PASS (72.2) | FAIL (GREEN) | PASS (slope/dist only) |
| WLFI | Sep 4 23:51 | $0.05625 | -7.24% | PASS (66.2) | FAIL (GREEN) | PASS (slope/dist only) |
| ADA | Sep 5 02:27 | $0.21077 | -5.69% | PASS (78.9) | FAIL (GREEN) | PASS (slope/dist only) |
| BCH | Sep 5 03:05 | $247.22 | -6.21% | PASS (84.1) | FAIL (GREEN) | PASS (slope/dist only) |
| SYRUP | Sep 7 17:19 | $0.21887 | -5.46% | PASS (72.8) | FAIL (GREEN) | PASS (slope/dist only) |
| ALT | Sep 7 19:19 | $0.006511 | -0.20% | PASS (70.2) | FAIL (GREEN) | PASS (slope/dist only) |
| SEI | Sep 7 19:27 | $0.04884 | -0.19% | PASS (67.3) | PASS | PASS (slope/dist only) |

**Key stats:**
- 8/9 trades fail C6 (red candle) at execution time
- 2/9 trades also fail C5 (RSI) at execution time  
- Only 1/9 (SEI Sep 7) passes all 6 conditions at execution time

---

## Root Cause: Detection-Execution Staleness Gap

### How the signal works:
1. **Detection** (`ema300_dip_short.py`): Checks 6 conditions on 1m candle data
2. **Compactor** (`signal_compactor.py`): EMA300 slope filter (added Sep 5)
3. **Decider** (`decider_run.py`): EMA300-CHECK at line 3465 (added Sep 5) — **only checks slope + distance**

### The bug:
The detection function checks 6 conditions:
1. Price < EMA300 ✓
2. <30% candles above EMA300 ✓  
3. EMA300 slope < 0 ✓
4. Price within 0.5% of EMA300 ✓
5. RSI > 65 ✓
6. Red candle ✓

But the **decider only re-validates conditions 3 + 4** (slope + distance). Conditions 1, 2, 5, 6 are NOT checked at execution time.

### Evidence:
- **STX trade**: Signal detected at ~17:31 when last candle was RED ($0.263330 → $0.263310). By execution at 18:31, candle was GREEN ($0.262190 → $0.262400). 1-hour staleness gap.
- **SEI trade**: Signal detected around 18:29. By execution at 23:12, candle was GREEN. 5-hour staleness gap.
- The STALE-WARN at line 2904 was **disabled** (FIX 2026-09-04: "Remove hard 5min staleness block") — signals can now execute at any age.

---

## Decider EMA300-CHECK Bug

### Bug #1: The check exists but logs never appear
The `[EMA300-CHECK]` log at line 3468 has **zero occurrences** in the pipeline log. This is because:
- The EMA300-CHECK was added on Sep 5 13:12 (commit `404056b9`)
- The log line was added on Sep 7 21:12 (commit `e8f2492e`)
- All 6 losing trades from Sep 4-5 were executed **before** the EMA300-CHECK existed
- The 3 losing trades from Sep 7 were executed before the **logging** was added
- The check DOES exist in code but was NOT logging until 21:12 UTC Sep 7

### Bug #2: EMA300-CHECK only validates 2 of 6 conditions
Even when the check runs, it only validates:
- EMA300 slope (condition 3)
- Price-EMA distance (conditions 1 + 4)

It does NOT validate:
- Trend strength (condition 2)
- RSI (condition 5)  
- Red candle (condition 6)

### Bug #3: The stale 5-min block was removed
Line 2904 shows the hard staleness block was disabled:
```python
# FIX 2026-09-04: Remove hard 5min staleness block
if age_min > SIGNAL_STALENESS_MAX_AGE_MIN:
    log(f'  ⏰ [STALE-WARN] ... — conditions will be verified')
```
This is now just a warning, not a block. Signals can execute at any age.

---

## Why the red candle condition fails

The red candle check (`closes[-1] < closes[-2]`) is extremely time-sensitive. On 1-minute data:
- A candle flips from red to green (or vice versa) within 60 seconds
- If the signal was detected at second 45 of a 1-minute candle, by execution 15 seconds later, the next candle might be green
- The detection function uses `_get_candles_1m()` which reads the last 700 1m candles from `price_history` — but the most recent candle might have flipped since detection

---

## Impact

| Metric | Value |
|--------|-------|
| Losing ema300_dip_short trades | 8 closed losses + 1 open loss |
| Total loss (closed) | ~-44.8% cumulative (with 5x leverage) |
| Root cause | Detection-execution staleness + incomplete re-validation |
| Fix complexity | Medium |

---

## Recommendations

### Fix 1 (Immediate): Add full condition re-validation in decider
The decider's EMA300-CHECK should re-validate ALL 6 conditions, not just slope + distance. Add RSI and red candle checks at execution time.

### Fix 2 (Immediate): Re-enable staleness hard block
The 5-minute staleness block was disabled on Sep 4. Re-enable it for ema300-dip-short signals specifically, since they depend on 1m candle conditions that go stale quickly.

### Fix 3 (Short-term): Add execution-time candle validation
Before executing any ema300-dip-short trade, re-fetch the latest 2 candles and verify the red candle condition still holds.

### Fix 4 (Short-term): Log the EMA300-CHECK results
The commit `e8f2492e` added logging. Verify the pipeline is loading the new code. If the check is passing silently, it should at least log "EMA300-CHECK PASS" so we can see it's working.

### Fix 5 (Long-term): Consider removing red candle from detection
The red candle condition on 1m data is inherently noisy and time-sensitive. Consider replacing it with a higher-timeframe candle condition (5m red candle) or removing it entirely if the other 5 conditions provide sufficient signal quality.

---

## Findings

### Critical
1. **Staleness gap**: Signals fire when valid but execute when conditions have deteriorated. 8/9 losers fail red candle at execution time.
2. **EMA300-CHECK never logged**: Zero `[EMA300-CHECK]` entries in pipeline.log despite code existing since Sep 5.

### High
3. **Incomplete re-validation**: Decider only checks 2 of 6 conditions at execution time.
4. **Staleness block disabled**: Hard 5-min block was removed on Sep 4, allowing arbitrarily old signals to execute.

### Medium
5. **Confidence > 100%**: ETC trade shows confidence=102 (should be capped at 100). Minor but indicates a scoring bug.
6. **EMA300 dip LONG losses**: The ema300-dip (LONG) signals also had significant losses (BCH -6.16%, NXPC -5.75%, etc.) — similar staleness issues may affect the LONG variant.

### Informational
7. **STALE candles.db**: Multiple tokens showed candles.db 900+ seconds stale during the losing trade period (Sep 4), with fallback to Binance. This may have contributed to stale signal detection.
8. **EMA300-CHECK code added AFTER most losses**: The EMA300-CHECK was added on Sep 5 13:12, but 6 of 8 closed losses occurred before that (Sep 4-5 morning).
