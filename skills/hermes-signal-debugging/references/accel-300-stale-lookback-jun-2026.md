# accel-300 STALE_LOOKBACK=10 blocks all detection — Jun 2026

## Symptom
Dry-run shows0 signals across all 67 eligible tokens. AAVE has clear SHORT candidates at i=336,337,352,353 that pass Conditions 1-4 but are silently blocked downstream.

## Root Causes

### Bug 1 (CRITICAL): STALE_LOOKBACK=10 is mathematically incompatible with LOOKBACK_1M=700
- Detection starts at `PERIOD(300) + LOOKBACK(30) = bar330` (EMA warmup requirement)
- `bars_from_latest = len(closes) - 1 - i` at detection start (i=330) = 700-1-330 = **369**
- STALE_LOOKBACK=10 requires `bars_from_latest <= 10`
- Result: detection window collapses to almost nothing — only bar i=689 (last10 bars) can fire

```
LOOKBACK_1M (bars fetched): 700
PERIOD + LOOKBACK (detection start): 330
bars_from_latest at i=330: 369 >> STALE_LOOKBACK=10
Max valid detection i: 689 (only last 10 bars of700-bar window)
```

### Bug2: ema300[j-1] NoneType crash (line 293)
Cross-bar search iterates over j with `closes[j-1] >= ema300[j-1]` but `ema300[j-1]` can be None during EMA warmup period. Fixed by adding `ema300[j-1] is not None` guard.

### Bug 3: CHOP parameters not loosened as intended (hermes_constants.py comments)
- `ACCEL_300_CHOP_AVG_GAP_PCT=0.90` — comment says "loosen to 0.50" but was never changed
- `ACCEL_300_CHOP_CROSS_GAP_PCT=0.22` — comment says "loosen to 0.10" but was never changed
- AAVE cross_gap=-0.10< 0.22 → chop1=True; avg_gap=0.18 < 0.90 → chop3=True

## AAVE Trace (pre-fix)
```
i=336: SHORT, gap=-0.235%, cross_bar=332, bars_since_cross=4
 stale_lookback_check: bars_from_latest=363 > 10 → BLOCKED
  chop: cross_gap=-0.103< 0.22 → chop1=True; avg_gap=0.18 < 0.90 → chop3=True
i=337: SHORT, gap=-0.234%, bars_since_cross=5
  stale_lookback_check: bars_from_latest=362 > 10 → BLOCKED
  marginal_accel: delta_last=0.0016, delta_prev=0.2533 → PASSES
  chop: same chop blocks
```

## Recommended Fixes (pending T approval)
| Param | Current | Fix |
|---|---|---|
| `ACCEL_300_STALE_LOOKBACK` | 10 | 400 |
| `ACCEL_300_CHOP_AVG_GAP_PCT` | 0.90 | 0.50 |
| `ACCEL_300_CHOP_CROSS_GAP_PCT` | 0.22 | 0.10 |

Also consider increasing `ACCEL_300_LOOKBACK_1M` from 700 to 1200+ to capture longer cross history for tokens with extended trends.

## Also Found
- AAVE was on SHORT_BLACKLIST=88 tokens → not in eligible 67 tokens for dry-run
- 70 tokens delisted, 88 on SHORT_BLACKLIST, 5 with stale prices
- 67 tokens passed pre-checks (open position, recent trade, delist, blacklist, price age)
