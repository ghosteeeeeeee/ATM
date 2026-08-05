# Support/Resistance Flip Trap — 1m Lookback Fix (2026-05-24)

## Incident

BCH and UMA both entered as LONG on support levels (`rs-s72`, `rs-s69`) that had become resistance. Price bounced off the old broken level and reversed against the trade.

- **BCH:** LONG entry $350.29, resistance at $352-355 (old broken support), pnl_pct=-0.13%
- **UMA:** LONG entry $0.459, resistance at $0.465-0.47 (old broken support), pnl_pct=-0.25%

Both signals had `zscore-pump+` confluence — direction was correct but the support was no longer valid as support.

## Root Cause

`signals/rs.py` `_level_recently_broken()` had a **20-candle (20-minute) lookback** hardcoded for level-invalidation detection.

An old support level broken 2 days ago is invisible to this check. The system sees "price near support $350" and fires the signal — even though that support was broken and is now resistance sitting 1-2% above entry.

**The system only checks 1m timeframe for level invalidation.** HTF regime and multi-timeframe analysis are not used in the RS flip detection.

## The Fix

### 1. New constant in hermes_constants.py

```python
RS_LEVEL_BROKEN_LOOKBACK = 500  # candles to check for level-invalidation (was hardcoded 20) — ~8hrs on 1m; catches support/resistance flips
```

Added after `RS_DECIDER_MIN_TOUCHES` (line ~262).

### 2. rs.py updated — import from hermes_constants

**Before:**
```python
def _level_recently_broken(candles: list, level: float, lookback: int = 20) -> bool:
```

**After:**
```python
def _level_recently_broken(candles: list, level: float, lookback: Optional[int] = None) -> bool:
    from hermes_constants import RS_LEVEL_BROKEN_LOOKBACK
    if lookback is None:
        lookback = RS_LEVEL_BROKEN_LOOKBACK
```

Both call sites (lines 516, 548) pass no explicit lookback — they use the constant.

### 3. Optional: RS_DECIDER_MIN_TOUCHES raise

Memory note: consider raising from 200 → 500. BCH's signal had `rs-s72` (72 touches — below current threshold, already penalized). Higher touch counts = structurally stronger levels less likely to flip.

## Why 500 Candles (~8 hours on 1m)?

- Catches any level broken in the current trading session or the prior one
- Aligns with typical support/resistance flip timescales on 1m
- 4700-candle total lookback means the system still sees the full price history for level detection
- 500 is a balance: wide enough to catch flips, not so wide it rejects valid setups

## Files Changed

- `/root/.hermes/scripts/hermes_constants.py` — added `RS_LEVEL_BROKEN_LOOKBACK = 500`
- `/root/.hermes/scripts/signals/rs.py` — `_level_recently_broken()` lookback now from hermes_constants

## Related

- `references/reversal-trap-pattern-2026-05-21.md` — reversal trap analysis (different issue: tight SL, not level flip)
- `references/zscore-pump-extreme-z-losses-2026-05-24.md` — zscore extreme z-losses (different issue: blow-off entries)