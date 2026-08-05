# accel-300+ RS-Support Combos — 2026-05-07 Findings

## What Works: accel-300+ + Strong Support Level

The best-performing signals in the live data are `accel-300+` combined with
support levels from `rs.py` that have high touch counts (rs-s48, rs-s72, etc.).

| Combo | Result | Notes |
|-------|--------|-------|
| `accel-300+,rs-s48` | PURR +4.74%, GRIFFAIN +5.26% | 48-touch support |
| `accel-300+,rs-s140` | +287% | 140-touch support |
| `accel-300+,rs-s72` | +298% | 72-touch support |
| `accel-300+,rs-s44` | +154% | 44-touch support |
| `accel-300+,rs-s150,trend_purity+` | GRIFFAIN +5.26% | 150-touch + trend |
| `accel-300+,momentum,mtf-macd,rsi` | DASH +4.80% | 4-way momentum combo |

## Why This Pattern Works

- `accel-300+` detects upward price momentum acceleration in 1m candles
- `rs-sNN` confirms price is at a strong support level with N historical touches
- The support level provides a floor — price bounces from it
- `trend_purity+` or `momentum,mtf-macd,rsi` confirm the trend direction
- Together: momentum above, support below = high-probability LONG entry

## rs-sNNN Source Meaning

In rs.py, the source tag is `rs-s{touch_count}` for support and `rs-r{touch_count}` for resistance.
- `rs-s48` = support level touched 48 times historically
- `rs-r72` = resistance level touched 72 times historically
- Higher touch count = more validated level = stronger signal

## Implementation Consideration

To add `accel-300+,rs-sNN` combos as a named signal type:

1. Both signals must fire on the SAME token within the same time window
2. The compactor merges them when they share token+direction+time window
3. To explicitly boost this combo: add to GOOD_STANDALONE_SIGNALS with high weight
4. Minimum 30 trades required before adding — small samples are misleading

## Anti-Pattern (Don't Combine)

- `accel-300+` + `pct-hermes+` — pct-hermes+ blocks accel-300+ via ACCEL_300_BLOCK_COSIGS
- `accel-300+` + `ma-cross-5m+` — also blocked by ACCEL_300_BLOCK_COSIGS
- Both blocks are based on stale May 6 data — may need re-evaluation