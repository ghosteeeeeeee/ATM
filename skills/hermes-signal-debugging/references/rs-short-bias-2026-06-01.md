# rs-s-broken SHORT Bias Root Cause Analysis
**Date:** 2026-06-01 | **Session focus:** signals/rs.py

## Finding

rs-s-broken fires ~9.8 times/hour per token (1 new row every ~5-6 min). Out of 11,889 total RS signals in the DB: 9,944 EXPIRED SHORT, 1,825 EXPIRED LONG.

### Root causes

1. **No freshness gate on broken levels.** `_level_recently_broken()` uses `RS_LEVEL_BROKEN_LOOKBACK=200` (~3+ hours). Once a support breaks, the `broken=True` flag stays active for all 200 candles — every scan cycle re-fires rs-s-broken on any price retrace back near the level.

2. **`_price_near_level` has no broken-level awareness.** The selection loop at line 467 picks `nearest_support` regardless of whether the level is broken. Price bounces back within proximity → same broken level selected again → rs-s-broken fires again.

3. **Market structure asymmetry.** In an uptrend, supports break frequently as price advances. Resistance levels break less often — `rs-r-broken` (LONG from broken resistance) fires, but the volume of support breaks in an uptrend is structurally higher.

4. **Merge window collision.** `add_signal()` merges within a 5-minute window keyed only on `token+direction` (not `token+direction+source`). rs-s-broken arrives every ~5-6 min — just outside each prior merge window — creating a new DB row each time instead of updating the existing one.

5. **No per-token cooldown on rs-s-broken.** Cooldown tracker is keyed by `token+direction+source`, so each new row is a separate firing event with independent cooldown.

### Signal flow for broken support

```
scan_rs_signals() calls detect_rs_signal()
  → _price_near_level() returns True (price still near broken support)
  → nearest_support selected (broken_support still nearest)
  → _level_recently_broken() returns True (200-candle window)
  → broken branch fires rs-s-broken SHORT
  → add_signal() creates new DB row (5-min merge window missed)
```

### Why LONG isn't similarly biased

The same broken-level re-firing would apply to `rs-r-broken` (LONG from broken resistance) — but in uptrend market structure, support levels break far more often than resistance levels. The asymmetry comes from market geometry, not a code bug.

### DB evidence

- `rs-s-broken`: 7,792 signals, all SHORT, 99%+ EXPIRED, ~9.8/hr per token
- rs-s (normal bounce): 1,817 signals, all LONG
- rs-r (resistance): 595 signals, all SHORT
- All RS signals: 10,032 SHORT : 1,825 LONG = 5.5:1 overall ratio

### Proposed fixes (not yet implemented)

1. **Reduce `RS_LEVEL_BROKEN_LOOKBACK`** from 200 → ~20 bars (30 min). A level broken 3 hours ago should not trigger repeated re-firing.

2. **Add freshness condition to broken branch** — only fire `rs-s-broken` if level was broken within last N bars (e.g., 20), not 200.

3. **Add distance check to broken branch** — if price hasn't moved at least 0.5 ATR away since the break, don't re-fire on the next scan.

### Key constants

- `RS_LEVEL_BROKEN_LOOKBACK=200` in hermes_constants.py:264 (used at runtime)
- `RS_LEVEL_LOOKBACK=20` in rs.py:36 (window for swing high/low detection)
- `RS_PROXIMITY_K=0.70` (proximity threshold as fraction of ATR)
- Merge window: 5 minutes in signal_schema.py:645