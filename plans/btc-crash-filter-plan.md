# BTC Flash Crash Filter — Comprehensive Plan

**Date:** 2026-08-22
**Status:** INITIAL FILTER DEPLOYED → NEEDS UPGRADE TO ACCELERATION DETECTION
**Author:** CEO (Hermes Trading System)

---

## Problem Statement

On 2026-08-22 at 05:08-05:11 UTC, BTC dropped ~2% in 3 minutes, triggering a market-wide cascade. **9 trades were wiped out (-$3.17 total).** 3 trades were even **opened DURING the crash** (MET, WLFI, BIGTIME) — the system had no crash detection.

### Root Cause Analysis

| Time | BTC Price | BTC 3m Chg | Event |
|------|-----------|------------|-------|
| 05:07 | $78,537 | -0.08% | Crash begins |
| 05:08 | $78,272 | -0.29% | Accelerating |
| 05:09 | $78,173 | -0.51% | WLFI & BIGTIME opened (LONG) |
| 05:10 | $77,846 | -0.88% | MET opened (LONG) |
| 05:11 | $76,939 | -2.08% | -1.5% threshold fires (TOO LATE) |
| 05:12 | $77,159 | -1.75% | Bounce begins |

**Key Insight:** The crash was **building** for 4 minutes (05:07→05:11). An absolute threshold (-1.5%) only fires AFTER the crash is complete. By then, trades are already open and suffering slippage.

---

## Current State (Deployed)

### What We Have
- `BTC_CRASH_BLOCK_THRESHOLD = -1.5%` (5m window on 1m candles)
- Checks BTC 1m candles, blocks ALL new entries when BTC drops >1.5% in 5 minutes
- Catches crashes AFTER they happen (05:11 trigger for 05:07-05:11 crash)

### What It Catches
- **0/3** trades opened during Aug 22 crash (WLFI, BIGTIME, MET all opened before trigger)
- **1/1** trades on Aug 21 crash (NOT at 09:02)
- **0/0** trades on Aug 19 crash (no positions open)

### What It Misses
- Trades opened DURING the build-up phase (05:07-05:10)
- Existing open positions that suffer slippage through SL

---

## Proposed Upgrade: BTC Acceleration Detection

### Concept
Instead of waiting for an absolute threshold, detect when BTC velocity is **negative AND accelerating** (getting more negative). This catches crashes 2-3 minutes earlier.

### Algorithm
```
vel_now = (btc_close[t] - btc_close[t-1]) / btc_close[t-1] * 100
vel_prev = (btc_close[t-1] - btc_close[t-2]) / btc_close[t-2] * 100

if vel_now < -0.15% AND vel_now < vel_prev:
    # BTC is falling AND accelerating — block entries
```

### Parameters (to backtest)
| Parameter | Initial Value | Description |
|-----------|---------------|-------------|
| `BTC_ACCEL_VEL_THRESHOLD` | -0.15% | Min velocity per 1m candle to trigger |
| `BTC_ACCEL_WINDOW` | 2 | Bars to compare acceleration |
| `BTC_ACCEL_BLOCK_DURATION` | 5 | Minutes to block entries after trigger |

### Why This Works
At 05:08: BTC velocity = -0.33% (1m), prev velocity = -0.05% → **accelerating** → BLOCK
At 05:09: BTC velocity = -0.13%, prev = -0.33% → decelerating → allow
At 05:10: BTC velocity = -0.34%, prev = -0.13% → **accelerating** → BLOCK

This would have caught WLFI (05:09:17) and BIGTIME (05:09:22) because the acceleration trigger fired at 05:08.

### Backtest Plan
1. Load all BTC 1m candles (Aug 15-22)
2. Compute velocity and acceleration for each bar
3. Identify all acceleration triggers
4. Check which trades would have been blocked
5. Measure: trades saved vs false positives vs winners lost

---

## Edge Cases to Handle

### 1. Flash Crash vs Gradual Decline
- **Flash crash** (Aug 22): BTC drops 2% in 3min, bounces immediately → acceleration filter catches it
- **Gradual decline**: BTC drops 0.5%/hour for 6 hours → acceleration filter does NOT trigger (velocity is stable)
- **Decision:** Acceleration filter is correct — gradual declines are trades we want to keep (trend following)

### 2. SHORT Entries During Crash
- Current filter blocks ALL entries (LONG and SHORT)
- **Should it block SHORT?** YES — cascade crashes cause liquidation cascades that can spike both directions
- **Alternative:** Allow SHORT entries during crash (fade the move) — risky, skip for now

### 3. Existing Open Positions
- Filter only blocks NEW entries, not manages existing positions
- **SL slippage** during cascades is unavoidable (price gaps through SL)
- **Mitigation:** Tighter `CUT_LOSER_PNL` or dynamic position sizing based on BTC volatility

### 4. False Positives
- BTC can drop 0.2% in 1 minute and recover — normal volatility
- **Solution:** Require acceleration (2 consecutive negative-velocity bars) + minimum velocity threshold

---

## Implementation Steps

### Phase 1: Backtest Acceleration Filter (TODO)
- [ ] Write backtest script for BTC acceleration detection
- [ ] Test thresholds: -0.10%, -0.15%, -0.20% velocity
- [ ] Measure: trades saved, false positives/day, winners lost
- [ ] Optimize parameters

### Phase 2: Implement Acceleration Filter (TODO)
- [ ] Add `BTC_ACCEL_VEL_THRESHOLD`, `BTC_ACCEL_WINDOW`, `BTC_ACCEL_BLOCK_DURATION` to hermes_constants.py
- [ ] Implement acceleration check in decider_run.py (before hot-set iteration)
- [ ] Keep existing absolute threshold as secondary check
- [ ] Test with paper trading

### Phase 3: Position-Level Protection (TODO)
- [ ] Dynamic `CUT_LOSER_PNL` based on BTC volatility (tighter during high vol)
- [ ] BTC volatility gate: reduce position size when BTC ATR is elevated
- [ ] Correlation check: don't open alt LONG when BTC is falling

### Phase 4: Monitoring & Tuning (TODO)
- [ ] Log all crash filter triggers (blocked trades, false positives)
- [ ] Weekly review: adjust thresholds based on data
- [ ] Dashboard: show crash filter status

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add acceleration params |
| `scripts/decider_run.py` | Add acceleration check logic |
| `scripts/btc_crash_monitor.py` | NEW: standalone BTC crash monitor (optional) |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives block good trades | Medium | Conservative threshold, acceleration requirement |
| Miss real crash | High | Keep absolute threshold as backup |
| Over-blocking in volatile markets | Medium | Weekly review, threshold tuning |
| Position sizing not adjusted | High | Phase 3: dynamic sizing based on BTC vol |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Crash trades blocked | 0/3 (Aug 22) | 3/3 |
| False positives/day | 0.7 | <1.0 |
| Winners lost | 0 | 0 |
| Total $ saved from crashes | $0.73 | >$2.00 |

---

## Related Constants

```python
# Existing (deployed 2026-08-22)
BTC_CRASH_BLOCK_ENABLED = True
BTC_CRASH_BLOCK_THRESHOLD = -1.5  # % in 5 minutes

# Proposed (Phase 2)
BTC_ACCEL_ENABLED = True
BTC_ACCEL_VEL_THRESHOLD = -0.15   # % per 1m candle
BTC_ACCEL_WINDOW = 2              # bars to compare
BTC_ACCEL_BLOCK_DURATION = 5      # minutes to block

# Existing (reference)
TIDE_ENABLED = True               # 3h BTC momentum (too slow for crashes)
CUT_LOSER_PNL = -2.0              # % PnL hard stop
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-22 | Deploy -1.5%/5m absolute filter | Quick win, catches post-crash entries |
| 2026-08-22 | Plan acceleration filter | Catches build-up phase (2-3 min earlier) |
| TBD | Optimize via backtest | Data-driven threshold selection |
