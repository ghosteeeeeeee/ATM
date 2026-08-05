# accel-300 Early Entry — Chop Filter vs Momentum Acceleration — Jun 2026

## Symptom
accel-300 fires 0 signals. Market shows trending tokens (XLM, ONDO, AAVE with clear EMA crosses). STALE_LOOKBACK=10 was already identified as broken in accel-300-stale-lookback-jun-2026.md, but even after loosening stale gates, chop filter still blocks 100% of candidates.

## Key Finding: Chop Filter Contradicts Early Detection

The chop filter (`CHOP_AVG_GAP_PCT`, `CHOP_CROSS_GAP_PCT`) is fundamentally incompatible with "catch signals as early as possible."

**AVNT SHORT is the textbook case:**
- Cross at21:26 UTC, gap = -0.11% (barely through EMA — very small)
- 2 bars later, gap expanded to -0.53%
- Final gap reached -1.72% (30 min after cross)
- **gap expansion ratio: 120x** (from -0.014% cross gap to -1.72%)

AVNT fails the chop filter because:
- `CHOP_CROSS_GAP_PCT=0.22` → cross gap of 0.014% is rejected
- `CHOP_AVG_GAP_PCT=0.90` → avg gap of 0.17% is rejected

The signal was correct. The filter was wrong. The chop filter was designed to suppress choppy markets but it also suppresses the exact pattern it's trying to catch — a small cross followed by massive acceleration.

## The Right Tool for Each Job

| Job | Right gate | Wrong gate |
|-----|-----------|-----------|
| "Is this cross recent?" | STALE_BARS (bars_since_cross), STALE_LOOKBACK (bars_from_latest) | CHOP_AVG_GAP_PCT |
| "Is price accelerating away from EMA?" | MIN_GAP_GROWTH, MIN_GAP_PCT | CHOP_CROSS_GAP_PCT |
| "Is this a choppy market?" | Regime slope, price volatility | avg gap around cross |

Chop filter uses `avg_gap` (average gap around the cross bar) to detect chop — but for early-entry signals, the gap IS the signal, not a sign of chop. A small initial gap that explodes is exactly what we want.

## Confluence of Blocking Gates

With current params (STALE_LOOKBACK=10, CHOP_AVG=0.90, CHOP_CROSS=0.22):
- STALE gates block 100% of candidates (bfl always100+)
- After stale loosened (STALE_BARS=80, STALE_LOOKBACK=400, chop unchanged): chop blocks 100%
- After stale + chop loosened (CHOP_AVG=0.50, CHOP_CROSS=0.10): 32 signals fire

## Param Impact Matrix (67 tokens scanned)

| Config | STALE_BARS | STALE_LOOKBACK | CHOP_AVG | CHOP_CROSS | Signals |
|--------|-----------|---------------|---------|---------|---------|
| current | 10 | 10 | 0.90 | 0.22 | 0 |
| stale_only | 80 | 400 | 0.90 | 0.22 | 0 |
| loose_chop | 80 | 400 | 0.50 | 0.10 | 32 |
| no_chop | 80 | 400 | 0.05 | 0.01 | 172 |

## Recommended Fixes (pending T approval)

| Param | Current | Proposed | Effect |
|-------|---------|----------|--------|
| `ACCEL_300_STALE_BARS` | 10 | 80 | Allow crosses up to 80min old |
| `ACCEL_300_STALE_LOOKBACK` | 10 | 400 | Allow detection bars up to 400min from latest |
| `ACCEL_300_CHOP_AVG_GAP_PCT` | 0.90 | 0.05 | Effectively disable — only blocks extreme calm |
| `ACCEL_300_CHOP_CROSS_GAP_PCT` | 0.22 | 0.01 | Effectively disable — AVNT cross at 0.014% is valid |

Alternative (conservative): keep CHOP_AVG=0.50, CHOP_CROSS=0.10 → 32 signals.

## Also Found: ema300 NoneType Crash

Line ~501: cross-bar search `closes[j-1] >= ema300[j-1]` crashes when `ema300[j-1]` is None (EMA warmup). Fixed with `ema300[j-1] is not None` guard.

## Debug Pattern

```python
# Full param impact test — run before and after any constant change
configs = [
    ("current",   10,  10,  0.90, 0.22),
    ("stale_only", 80, 400, 0.90, 0.22),
    ("loose_chop", 80, 400, 0.50, 0.10),
    ("no_chop",   80, 400, 0.05, 0.01),
]
# Count signals per config to measure impact of each gate
```

## Lesson

When a filter designed for one purpose (chop detection) suppresses the signal it's trying to catch (early momentum acceleration), it's the wrong filter for early detection. The stale gates already handle recency — chop is redundant and counterproductive.
