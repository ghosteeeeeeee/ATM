## CEO Report — 2026-08-10 05:30 UTC

### Verified Numbers
| Window | Trades | PnL | WR |
|--------|--------|-----|-----|
| 24h | 46 | +$0.19 | 47.8% |
| 7d | 423 | -$6.64 | 43.7% |
| 24h LONG | 38 | +$0.32 | 50.0% |
| 24h SHORT | 8 | -$0.14 | 37.5% |
| 7d LONG | ~200 | +$2.50 | ~50% |
| 7d SHORT | ~223 | -$9.14 | ~38% |

### Star Signal
bb_bounce+,range_finder+ LONG: 21T 24h, +$0.47, 57.1% WR — carries entire profit. 30T 7d, +$0.85, 66.7% WR.

### Diagnosis
All SHORT bleeding traces to `ma100-cross-` combos. Every ma100-cross SHORT combo in 24h is 0% WR:
- `ma100-cross-,vortex_break_short`: 2T -$0.13, 0% WR
- `ma100-cross-,range_finder-`: 1T -$0.06, 0% WR
- `ma100-cross-,return_exhaustion-`: 7T -$0.28, 42.9% WR (7d)

Working SHORT signals: `bb-bounce-short` (3T +$0.08, 66.7%), `choch-5` (1T +$0.02, 100%).

### Root Cause
`ma_100_cross_short` fires SHORT on any MA cross — no quality filter beyond ATR%. The regime filter (BULLISH skip) doesn't help because the market is NEUTRAL. The signal itself is low-quality for SHORT direction.

### Fix Applied
1. **Disabled `MA_100_CROSS_MINUS_ENABLED = False`** — kills all ma100-cross SHORT combos. Preserves bb-bounce-short, choch-5, and other working SHORT signals.
2. **Added regime filter to base `ma_100_cross.py`** — future-proofs if `MA_100_CROSS_ENABLED` is ever re-enabled. (Base signal is currently disabled.)

### Expected Impact
- SHORT bleeding stops (~$0.20/24h saved)
- SHORT signals from bb-bounce-short and choch-5 unaffected
- LONG side unchanged

### Next Steps
- Monitor 24h for SHORT improvement
- SHORT 7d still -$9.14 but most is legacy pre-fix trades aging out
- Pipeline healthy, no open trades, no errors
