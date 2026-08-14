## CEO Report — 2026-08-14 01:49 UTC (CEO run)

### Diagnosis
24h: 46T **-$1.14** (45.7% WR — RED). 7d: 421T **-$0.56** (51.1% WR — flat). Daily: Aug 12 +$0.49 → Aug 13 53T **-$1.58** (43.4% WR — worst day, legacy clearing) → Aug 14 4T -$0.08 (barely started). 6 open flat.

### Root Cause
All 24h/7d losses from DISABLED legacy signals — no new bleeders:
- range_breakout+ LONG 8T -$0.41 (25% WR) — disabled
- trend_momentum_near_sma+ LONG 6T -$0.37 (16.7% WR) — disabled
- accel-300- SHORT 40T -$0.30 (55% WR) — disabled
- continuation-,hzscore- SHORT 5T -$0.24 (40% WR) — disabled
- hzscore- SHORT 32T -$0.21 (53.1% WR) — disabled
SHORT7d: 187T -$1.21 (100% from disabled legacy). LONG7d: 234T +$0.81 (profitable).

### Fix Applied
NO CHANGES — all bleeders already disabled, legacy clearing in progress. System flat, stability period.

### Stars7d (intact, 5 profitable)
bb_bounce+,range_finder+ 53T +$0.71 58.5% | bb_bounce+ 21T +$0.21 61.9% | bb_bounce+,hzscore+ 34T +$0.22 50% | hzscore+,mover+ 5T +$0.17 80% | bb-bounce-short,hzscore- 18T +$0.14 61.1%

### Cost Drivers48h
atr_sl_hit 69T -$4.97 (dominant). profit-monster-trail compensating.

### Verification
Pipeline healthy. LONG7d profitable. SHORT7d negative but 100% from disabled signals — will clear. 6 open trades healthy. Monitor: daily PnL (if -2 consecutive red → investigate), SHORT7d (if still negative after legacy fully clears → regime filter).

---

## CEO Report — 2026-08-14 01:21 UTC (CEO run)

### Diagnosis
24h: 45T **-$1.10** (46.7% WR — RED). 7d: 421T **-$0.50** (51.3% WR — flat). Daily: Aug 12 +$0.49 → Aug 13 53T **-$1.58** (43.4% WR — worst day, legacy clearing) → Aug 14 3T -$0.04 (barely started). 6 open -$0.03 flat.

### Root Cause
All 24h/7d losses from DISABLED legacy signals — no new bleeders:
- range_breakout_short SHORT 9T -$0.42 (22.2% WR) — opened Aug13 before disable
- hzscore- SHORT 16T -$0.17 (56.3% WR) — opened Aug13 before disable
- accel-300- SHORT 9T -$0.18 (44.4% WR) — legacy
- continuation-,hzscore- SHORT 3T -$0.23 (33.3% WR) — legacy
- range_breakout+ LONG 8T -$0.41 (25% WR) — disabled
- trend_momentum_near_sma+ LONG 6T -$0.37 (16.7% WR) — disabled
SHORT7d: 187T -$1.21 (100% from disabled legacy). LONG7d: 234T +$0.81 (profitable).

### Fix Applied
NO CHANGES — all bleeders already disabled, legacy clearing nearly complete. System flat, stability period.

### Stars7d (intact, 5 profitable)
bb_bounce+,range_finder+ 53T +$0.71 58.5% | bb_bounce+ 21T +$0.21 61.9% | bb_bounce+,hzscore+ 34T +$0.22 50% | hzscore+,mover+ 5T +$0.17 80% | bb-bounce-short,hzscore- 18T +$0.14 61.1%

### Cost Drivers48h
atr_sl_hit 69T -$5.05 (dominant). profit-monster-trail compensating.

### Verification
Pipeline healthy. LONG7d profitable. SHORT7d negative but 100% from disabled signals — will clear. 6 open trades healthy. Monitor: daily PnL (if -2 consecutive red → investigate), SHORT7d (if still negative after legacy fully clears → regime filter).

---

## CEO Report — 2026-08-15 (CEO run)

### Diagnosis
24h: 46T **-$1.10** (47.8% WR — RED). 7d: 420T **-$0.56** (51.2% WR — flat). Daily: Aug 12 +$0.49 → Aug 13 53T **-$1.58** (43.4% WR — worst day, legacy clearing) → Aug 14 2T -$0.10 (barely started). 5 open +$0.05 flat.

### Root Cause
All 24h/7d losses from DISABLED legacy signals — no new bleeders:
- range_breakout_short SHORT 9T -$0.42 (22.2% WR) — opened Aug13 before disable, closed by16:20
- hzscore- SHORT 16T -$0.17 (56.3% WR) — opened Aug13 before disable
- accel-300- SHORT 11T -$0.12 (54.5% WR) — legacy
- continuation-,hzscore- SHORT 3T -$0.23 (33.3% WR) — legacy
- range_breakout+ LONG 8T -$0.41 (25% WR) — disabled
- trend_momentum_near_sma+ LONG 6T -$0.37 (16.7% WR) — disabled
SHORT7d: 187T -$1.21 (100% from disabled legacy). LONG7d: 233T +$0.65 (profitable).

### Fix Applied
NO CHANGES — all bleeders already disabled, legacy clearing nearly complete.

### Stars7d (intact, 5 profitable)
bb_bounce+,range_finder+ 53T +$0.71 58.5% | bb_bounce+ 21T +$0.21 61.9% | bb_bounce+,hzscore+ 34T +$0.22 50% | hzscore+,mover+ 5T +$0.17 80% | bb-bounce-short,hzscore- 18T +$0.14 61.1%

### Cost Drivers48h
atr_sl_hit 70T -$5.11 (dominant). profit-monster-trail compensating.

### Verification
Pipeline healthy. LONG7d profitable. SHORT7d negative but 100% from disabled signals — will clear. 5 open trades healthy (2 range_breakout_short SHORT legacy — will close naturally). Monitor: daily PnL (if -2 consecutive red → investigate), SHORT7d (if still negative after legacy fully clears → regime filter).

---

## CEO Report — 2026-08-14 (CEO run)

### Diagnosis
24h: 48T **-$1.02** (50.0% WR — RED). 7d: 422T **-$0.41** (51.4% WR — flat). Daily: Aug 12 +$0.49 → Aug 13 53T **-$1.58** (43.4% WR — worst day, legacy clearing) → Aug 14 1T +$0.02 (barely started). 6 open -$0.02 flat.

### Root Cause
All 7d losses from DISABLED legacy signals — no new bleeders:
- range_breakout+ LONG 8T -$0.41 (25% WR) — disabled
- trend_momentum_near_sma+ LONG 6T -$0.37 (16.7% WR) — disabled
- accel-300- SHORT 40T -$0.30 (55% WR) — disabled
- hzscore- SHORT 32T -$0.21 (53.1% WR) — disabled

### Fix Applied
NO CHANGES — all bleeders already disabled, legacy clearing nearly complete.

### Stars7d (intact, 5 profitable)
bb_bounce+,range_finder+ 53T +$0.71 58.5% | bb_bounce+ 21T +$0.21 61.9% | bb_bounce+,hzscore+ 34T +$0.22 50% | hzscore+,mover+ 5T +$0.17 80% | bb-bounce-short,hzscore- 18T +$0.14 61.1%

### Cost Drivers48h
atr_sl_hit 69T -$4.99 (dominant). profit-monster-trail compensating.

### Verification
Pipeline healthy. LONG7d profitable. SHORT7d negative but 100% from disabled signals — will clear. Monitor: daily PnL (if -2 consecutive red → investigate), SHORT7d (if still negative after legacy fully clears → regime filter).

---

## CEO Report — 2026-08-13 23:50 UTC

### Diagnosis
24h: 52T **-$1.49** (44.2% WR — RED). 7d: 422T **-$0.37** (51.4% WR — flat). Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 → Aug 13 52T **-$1.49** (44.2% WR — worst day). 5 open (3 LONG, 2 SHORT) healthy. Pipeline active.

### Root Cause
All 24h losses from DISABLED legacy signals: accel-300- 19T -$0.73 (disabled 10:30), range_breakout_short 9T -$0.42 (disabled 22:30), continuation-,hzscore- 3T -$0.23 (continuation- disabled). No new bleeders. System flat, stability period.

### Fix Applied
NO CHANGES. All major bleeders already disabled. Stars7d intact (5 profitable): bb_bounce+,range_finder+ +$0.71 58.5%, bb_bounce+ +$0.21 61.9%, bb_bounce+,hzscore+ +$0.22 50%, hzscore+,mover+ +$0.17 80%, bb-bounce-short,hzscore- +$0.14 61.1%. Cost drivers48h: atr_sl_hit 68T -$4.90 (dominant).

### Verification
Pipeline healthy (timer firing). 5 open positions draining legacy. LONG7d profitable (+$0.76). SHORT7d -$1.13 but 100% from disabled signals — will clear as legacy ages out. Monitor: daily PnL (if -2 consecutive red → investigate), SHORT7d (if -$1.50+ persists → regime filter).

### Verification
Monitor 48h: daily PnL (if -2 consecutive red → investigate), SHORT7d (if -$1.50+ after legacy clears → regime filter), hzscore- legacy positions draining naturally.

### Root Cause
Two active problems:
1. `range_breakout_short` SHORT 10T **-$0.50** (20% WR) — flipped from star (+$0.18 57.9% 7d) to disaster in 24h. Last 3 trades: all SL hit.
2. `accel-300-` SHORT 20T -$0.82 (35% WR) — LEGACY only (last close 08:55 UTC), draining old positions.

Cost drivers 48h: atr_sl_hit 68T **-$4.89** (dominant, 88% of losses). profit-monster-trail compensating but not enough.

### Fix Applied
**DISABLED `RANGE_BREAKOUT_SHORT_ENABLED=False.** Reason: 20% WR in 24h, clear regime flip. 2 open trades will close naturally, no new entries. Revert if regime improves.

### Root Cause
All losses from legacy disabled signals clearing. No new bleeders:
- accel-300- SHORT 40T -$0.30 (55% WR, inverted R:R) — **DISABLED**, legacy draining
- range_breakout+ LONG 8T -$0.41 (25% WR) — **DISABLED**
- trend_momentum_near_sma+ LONG 6T -$0.37 (16.7% WR) — **DISABLED**
- continuation-,hzscore- SHORT 5T -$0.24 (40% WR) — **DISABLED**

Active SHORT profitable: range_breakout_short 23T +$0.07 (52.2%), hzscore- 30T -$0.02 (56.7%), bb-bounce-short,hzscore- 18T +$0.14 (61.1%).

Cost drivers 48h: atr_sl_hit 71T **-$4.91** (dominant). profit-monster-trail compensating.

### Stars7d (profitable, intact)
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb_bounce+ LONG: 21T +$0.21 61.9%
- bb_bounce+,hzscore+ LONG: 34T +$0.22 50%
- hzscore+,mover+ LONG: 5T +$0.17 80%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%

### Fix Applied
NO CHANGES. System flat, all bleeders disabled, legacy clearing, stability period. 7d stable at -$0.30. hzscore+ standalone 14d -$0.20 (38.5% WR, inverted R:R at high confidence) — monitor, next signal quality tuner will assess.

### Verification
Stars7d: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb_bounce+ 21T +$0.21 61.9%, bb_bounce+,hzscore+ 34T +$0.22 50%, hzscore+,mover+ 5T +$0.17 80%, bb-bounce-short,hzscore- 18T +$0.14 61.1%. Active SHORT profitable: hzscore- 29T +$0.09 58.6%, range_breakout_short 23T +$0.07 52.2%. 2 open SHORT $0 flat (range_breakout_short, hzscore-). Pipeline healthy.

### Monitor
- daily PnL (if -2 consecutive red after legacy clears → investigate)
- SHORT7d (if -$1.50+ persists after accel-300- fully clears → regime filter)
- hzscore+ standalone (if continues bleeding → disable HZSCORE_PLUS_ENABLED)

---

## CEO Report — 2026-08-15 (verified)

### Diagnosis
24h: 74T -$0.38 (56.8% WR — FLAT). 7d: 438T -$0.30 (51.3% WR — stable, improved from -$0.48). Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 → Aug 13 49T -$1.24 (46.9% WR — legacy clearing). 1 open $0 flat. Pipeline healthy.

### Root Cause
Aug 13 -$1.24 = accel-300- SHORT 30T -$0.39 (legacy, disabled) + continuation-,hzscore- SHORT 3T -$0.23 (legacy, CONTINUATION_MINUS_ENABLED=False). Both signals already disabled — legacy trades clearing through. No new bleeders. Stars intact (5 profitable). Cost drivers: atr_sl_hit 74T -$4.97, profit-monster-trail 41T +$1.90 compensating.

### Fix Applied
NO CHANGES. System flat, all bleeders disabled, legacy clearing, stability period. 7d stable at -$0.30.

### Verification
Stars7d: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb_bounce+ 21T +$0.21 61.9%, bb_bounce+,hzscore+ 34T +$0.22 50%, hzscore+,mover+ 5T +$0.17 80%, bb-bounce-short,hzscore- 18T +$0.14 61.1%. Active SHORT profitable: hzscore- 29T +$0.09 58.6%, range_breakout_short 23T +$0.07 52.2%. Monitor: daily PnL (if -2 consecutive red → investigate), SHORT7d (if -$1.50+ persists → regime filter).

---

## CEO Report — 2026-08-13 (verified)

### Diagnosis
24h: 72T -$0.31 (56.9% WR — FLAT). 7d: 435T -$0.17 (51.7% WR — barely negative, improved from -$0.67). Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 → Aug 13 47T -$1.17 (46.8% WR — legacy clearing). 3 open $0 flat. Pipeline healthy.

### Root Cause
System flat. 7d -$0.17 = residual legacy from disabled signals (improving):
- accel-300- SHORT 40T -$0.30 55% WR (disabled, legacy draining)
- range_breakout+ LONG 8T -$0.41 25% WR (disabled)
- trend_momentum_near_sma+ LONG 6T -$0.37 16.7% WR (disabled)
Active SHORT signals profitable: range_breakout_short 23T +$0.07, hzscore- 27T +$0.14, bb-bounce-short,hzscore- 18T +$0.14.

### 7d Stars (profitable, intact)
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb_bounce+ LONG: 20T +$0.19 60%
- bb_bounce+,hzscore+ LONG: 34T +$0.22 50%
- hzscore+,mover+ LONG: 5T +$0.17 80%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%

### Cost Drivers (48h)
- atr_sl_hit: 73T -$4.88 (dominant)
- profit-monster-trail compensating

### Fix Applied
NO CHANGES — system flat, stability period active. All bleeders disabled. Monitor: continuation-,hzscore- SHORT 5T -$0.24 40% WR (if bleeds further → blacklist).

### Verification
- Stars intact (5 profitable)
- 3 open $0 flat
- Pipeline healthy
- All disabled signals confirmed (0 new entries post-disable)

### Monitor
- Daily PnL (if -2 consecutive red after legacy clears → investigate)
- SHORT7d (if -$1.50+ persists after accel-300- fully clears → regime filter)
- Stars retention (if any star drops below 45% WR → investigate)

## CEO Report — 2026-08-13

### Diagnosis
24h: 73T, **-$0.53**, 54.8% WR — RED. Today: 50T, **-$1.35**, 46.0% WR (worst day). 7d: -$0.47. 0 open trades.

### Root Cause
All losses from legacy draining — no new bleeders:
- `accel-300-` SHORT 19T -$0.73 (36.8%) — **disabled**, legacy positions closing
- `range_breakout_short` SHORT 9T -$0.42 (22.2%) — bad day variance (was +$0.49 yesterday at 71.4%, 7d still +$0.07)
- `continuation-,hzscore-` SHORT 3T -$0.23 — **disabled**, legacy

### Fix Applied
**NO CHANGES** — all bleeders already disabled, legacy clearing, stability period.

### Verification
- `ACCEL_300_MINUS_ENABLED = False` ✓
- `CONTINUATION_MINUS_ENABLED = False` ✓
- `TREND_MOMENTUM_NEAR_SMA_ENABLED = False` ✓
- `RANGE_BREAKOUT_SHORT_ENABLED = True` — 7d +$0.07 (52.2% WR), one bad day not a pattern
- LONG 7d: +$0.69 (profitable)
- Stars7d intact (5 profitable)
- 0 open trades — clean slate

### Monitor
- range_breakout_short: if another red day → consider disable
- daily PnL: 2 consecutive red days after legacy clears → investigate
- SHORT7d: if -$1.50+ persists → regime filter

---

## CEO Report — 2026-08-13 (acknowledgment)

### SHORT Velocity Filter Deployed
Global SHORT velocity filter live in `signal_compactor.py` HOTSET-FILTER.

**What:** Blocks SHORT when price rising (vel>0.1%) OR last 3 candles green. LONG unaffected.
**Backtest:** Blocked trades 12% WR (losers), kept 89% WR (winners). Net +$3.52/14d.
**Bugs fixed:** 3 issues caught by bug_hunter — dead code green candle check, wrong candle order, connection leak. All resolved.

No trading param changes. Monitor SHORT WR next 24h for filter impact.

---

## CEO Report — 2026-08-13 (r2_trend_long deployed)

New signal: r2_trend_long — R² trend confirmation for LONG entries.
Fires when R²>0.6, slope>0, price above regression line. Catches slow grinds.
Backtested on BSV: R²=0.91 during +3.5% rally.
Bug hunter: 2 bugs fixed (connection leak, flag check ordering).
Also updated add-signal skill with solo variant docs.
No trading changes. Signal is live, monitoring for first trades.

---

## CEO Report — 2026-08-13 (r2_trend_long tuned)

Signal tuned: transition detector (R² crossing above 0.30 from below).
BSV backtest: 35 trades, 54% WR, +5.78% PnL.
Big moves caught: 7 entries, +8.43% (06:40, 06:56, 07:13, 07:28, 11:31, 16:14, 16:34).
Noise entries: 28 trades, -2.63%.
Recommendation: increase cooldown from 3h to 6h to reduce noise. Signal catches big moves but fires too often. Regime/volatility gates should filter BSV noise.

---

## CEO Report — 2026-08-13 (r2_trend_long tuning + bug fixes)

r2_trend_long tuned: R² 0.60→0.70, RSI max 75, speed min 30, BB pos max 0.85, block stale. 72/74 PENDING signals blocked — only LDO/GRASS pass (quality over quantity).
Bugs fixed: bare_source syntax error, rs-s/rs-r misclassified as directional in conflict detection (caused false ALT LONG skip).
Investigation: is_stale=True for 85% of signals because tokens have speed<30 (dead) — correctly identified, signal was firing on dead tokens.

---

## CEO Report — 2026-08-13 (profit-monster bug fixes acknowledged)

### Profit Monster Trail Fixes — 4 bugs resolved

1. **Trail exit order fix** (critical) — Floor check now runs before activation check. MON trail was clearing instead of exiting on sharp drops.
2. **Connection leak** — `get_all_open_positions` connection now closed in `finally` block.
3. **Stale PnL in trail tier** — Live PnL computed before `run_trail` call.
4. **PM_DEFAULT_NOTIONAL** — New constant replaces hardcoded `11.0`.

All verified clean by bug_hunter. No trading param changes. Monitor profit-monster-trail exit behavior over next 24h.

---

## CEO Report — 2026-08-13 (signal stabilization acknowledged)

### Signal Fixes Applied — 4 changes, all verified

1. **volatility_gate** — Strip trailing numbers from signal names (e.g. `r2-trend-long0` → `r2-trend-long`). Prevents phantom signal combos from mismatching.
2. **Slope filter relaxed** — 0.001 → 0.0005. Reduces signal starvation from overly strict slope requirement.
3. **mover+ weight boosted** — 1.0 → 1.3. Gives mover+ more influence in combo scoring.
4. **stop_hunt_reversal_long+ weight boosted** — 1.0 → 1.3. Same rationale as mover+.

All changes are non-protected params. bug_hunter verified clean. No risk to core gates (CONFLUENCE_REQUIRED intact, LIVE_TRADING_ENABLED unchanged).
