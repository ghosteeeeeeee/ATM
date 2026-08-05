# RS Signal Fix — 2026-05-07

## ⚠️ INCOMPLETE FIX — Wrong File (2026-05-08)
Patches were applied to `signals/rs.py` (new/migrated version) but the **live pipeline**
uses `rs_signals.py` (old version imported directly by `signal_gen.py` line 2234).
See `hermes-signal-debugging` SKILL.md §"Two separate RS implementations" for full diagnosis.

**Evidence of incomplete fix**: Last RS signals written at `2026-05-07 20:02:47` — all 180
RS signals in DB are EXPIRED. Pipeline ran at 00:32 with zero new RS writes. The old
`_level_recently_broken()` (high=low=close always) is still killing all RS signals.

**Fix**: Apply the same 4 patches to `rs_signals.py` OR consolidate to single implementation.

## Problem
RS signals were writing to DB (signal_type='support_resistance') but touch counts were
10-100x too high (BTC 402, SOL 2778, CRV 20398). All signals had bounce=False.

## Root Cause — 5 bugs in rs.py

### Bug 1: `_build_level_touches` — fixed 0.15% threshold on close-only data
`price_history` is **close-only** (open=high=low=close for every candle).
The hardcoded 0.15% threshold counted every tiny price drift as a "touch":
- BTC ($80K, 0.15% = $120/candle) — every close within $120 of level = touch
- SOL ($180, 0.15% = $0.27/candle) — every close within $0.27 of level = touch
- CRV ($0.24, 0.15% = $0.00036/candle) — effectively every candle = touch → 20K touches

**Fix:** ATR-normalized threshold — `0.20 × ATR(14)` adapts to volatility:
```python
threshold = atr_value * _BOUNCE_THRESH_ATR  # 0.20 × ATR(14)
```
Result: BTC=12 touches (was 402), SOL=44 (was 2778), CRV=171 (was 20398).

### Bug 2: `_bounce_confirmation` — candle-direction logic on close-only candles
`c['close'] > c['open']` is ALWAYS True (close=open) → bounce bonus never fires.
Also used `c['low']`/`c['high']` which equal close.

**Fix:** ATR-normalized proximity + subsequent price movement:
```python
# Support bounce: price touched level (within ATR threshold) then moved UP
for i, c in enumerate(recent):
    if abs(c['close'] - level) < thresh:  # touched
        if i + 1 < len(recent):
            if recent[i+1]['close'] > c['close'] * 1.0005:
                return True
```

### Bug 3: `_level_recently_broken` — used high/low on close-only candles
`high < level < low` is ALWAYS False (high=low=close) → every level appears unbroken.
Result: broken-level gate was silently failing.

**Fix:** Use close values:
```python
# Resistance broken: opened below level, closed above
if opened < level < closed:
    return True
```

### Bug 4: ATR band filter (0.30–0.60 ATR) rejecting valid signals
`_RS_ATR_BAND_SOFT_MIN = 0.30`, `_RS_ATR_BAND_SOFT_MAX = 0.60` — if price was
0.30-0.60 ATRs from a level → REJECTED. In trending markets, price is frequently
within 0.30 ATR of a structural level. This was the primary reason RS was producing
0 rows in earlier sessions.

**Fix:** Removed the band filter entirely. `_price_near_level` (within 1.20 ATR)
and `_level_recently_broken` are sufficient guards.

### Bug 5: Confidence formula overscaled for new touch counts
Old formula: `3 + touch_count` → touch_count=402 gave +405 bonus (impossible).
New formula: log-scale `3 + int(log1p(max(0, touch_count-1)) * 2.5)`:
- 1 touch → +3, 5 touches → +6, 12 touches → +7, 50 touches → +9, 100+ → +9 (cap)

## Results After Fix
| Metric | Before | After |
|--------|--------|-------|
| Speed | 9.3s | 9.2s ✅ |
| BTC touch count | 402 | **12** |
| SOL touch count | 2778 | **44** |
| DASH touch count | 462 | **26** (in winner range!) |
| Signals written | 115 | **132** |
| bounce=True | 0% | Working (IP, ORDI) |
| Merged RS signals | 20 | **37** |

## Key Insight: `price_history` Is Close-Only Data
The `price_history` table stores orderbook mid-price snapshots. Every OHLCV field
is identical (open=high=low=close). Any indicator relying on candle direction,
high/low spread, or fixed-% thresholds is broken on this data source.

**Verified working:** ATR (uses close-close differences), rolling max/min (finds
swing highs/lows from close series), swing-based level detection.

**Broken on this data:** Candle direction bounce confirmation, ATR band proximity
filters using high/low, fixed-% touch thresholds (non-volatility-normalized).

## Winning Touch Count Ranges (from signal_outcomes archive)
- **rs-s16 to rs-s150**: 100% WR, avg peak +343%
- **rs-s < 16**: borderline, low confidence
- **rs-s > 150**: stale level, 0% WR (levels become support/resistance at exactly
  16-150 touches; beyond that they're either broken or no longer relevant)

## Naming Convention — Already Correct
RS source field format IS correct: `rs-s{touch_count}` (e.g., `rs-s44`).
This format was found in signal_outcomes winners: `accel-300+,rs-s48` (PURR +474%),
`accel-300+,rs-s150` (GRIFFAIN +526%), `accel-300+,rs-s72` (DASH +344%).

The `signal_type='support_resistance'` is the DB column value — the source field
is what matters for merging and display.

## Files Changed
- `/root/.hermes/scripts/signals/rs.py` — 5 bugs fixed
