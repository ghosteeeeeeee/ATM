# RS Support/Resistance Flip Pattern (2026-05-24)

## Symptom

BCH and UMA LONG trades entered on valid support (rs-s##) bounces but immediately reversed. The support level had **become resistance** — broken hours earlier, price rallied back to it, and the bounce entry caught the wrong side of the flip.

## Root Cause

`_level_recently_broken` in rs.py checks only whether the **target level itself** was recently broken. It does NOT check whether the nearest resistance (for LONG) or nearest support (for SHORT) above/below entry is an old level that has flipped polarity.

Two specific gaps:
1. `_level_recently_broken` lookback = 20 candles (20 min on 1m) — too short to catch levels broken hours ago
2. No "nearby opposing level" check: LONG enters at support, but if resistance is only 1-2% above, reward path is compressed

## The rs.py vs hermes_constants Constant Desync

**rs.py** has its own local constants (lines 35-41). They are NOT imported from hermes_constants:

| Constant | rs.py | hermes_constants.py |
|----------|-------|---------------------|
| `RS_PROXIMITY_K` | `0.70` | `1.20` |
| `RS_ATR_PERIOD` | `14` | `30` |
| `RS_LEVEL_LOOKBACK` | `20` | `300` |
| `RS_MIN_TOUCHES` | `3` | `8` |
| `RS_CLUSTER_ATR` | `0.50` | `0.75` |

This means changes to hermes_constants RS values **do not affect the live RS signal**. rs.py's local values are the source of truth.

## Fix Applied (2026-05-24)

1. **hermes_constants.py**: Added `RS_LEVEL_BROKEN_LOOKBACK = 500` — moved lookback from hardcoded 20 to constant
2. **rs.py**: `_level_recently_broken()` now imports and uses `RS_LEVEL_BROKEN_LOOKBACK` instead of hardcoded 20

**Note:** 500 (8.3 hours) may be too aggressive for AAVE (100% block rate on history). Recommended value is **200** (~3.3 hours on 1m). The 500 value was chosen to err on the side of caution but backtesting shows it over-blocks.

## What Would Have Caught BCH

- BCH support at $350 broken 25 hours before entry
- On 1m: 25 hours = ~1,500 candles
- LB=500 catches ~8 hours — **not enough for BCH case**
- LB=1500 would catch it but would block nearly all signals

The BCH case reveals the limit of the lookback approach for 1m-only systems. The complementary fix is checking nearby opposing level distance (RS_LONG_MAX_DIST_RESIST / RS_SHORT_MAX_DIST_SUPPORT) — but BCH's resistance was 21.9x ATR above entry, so even that wouldn't have blocked it.

## Diagnostic Query

```sql
-- Find recent RS signals with tight nearby resistance
SELECT token, direction, source, confidence, price, created_at
FROM signals
WHERE source LIKE 'rs-%'
  AND created_at > datetime('now', '-2 days')
ORDER BY created_at DESC;
```

## See Also

- `new-signal-implementation/references/rs-level-broken-lookback-backtest-2026-05-24.md` — full backtest data
- `signals/rs.py` lines 263-292 — `_level_recently_broken()` implementation
- `signals/rs.py` lines 35-41 — rs.py local constants