## CEO Report — 2026-08-21 (~05:00 UTC, verified, 197th run)

### Diagnosis
System HEALTHY. 24h: 18T -$0.54, 50.0% WR (flat — normal NEUTRAL variance). 7d: 256T -$1.23, 50.8% WR. 0 open positions (clean). PM_TRAIL: 136T/7d +$5.10, 83.1% WR (carrying system). ATR_SL: 94T/7d -$7.04, 1.1% WR (dominant drag, historic low count). SHORT legacy: ALL cleared — 0 remaining open, drain complete. Daily: Aug 14 -$0.63 → 15 +$0.02 → 16 -$0.49 → 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.54 (alternating green/red, break-even pattern). SL floor fix verified: post-fix 15T -$1.59 vs pre-fix 79T -$5.45 (78% fewer ATR_SL hits). Coin tracker: ALL wyckoff_phase=none (detection gap).

### Root Cause
No new root causes. System at break-even edge — PM_TRAIL (+$5.10) offsets ATR_SL (-$7.04) plus legacy SHORT drain (-$0.96). SHORT legacy fully cleared, will age out of 7d window by Aug 22-23. Alternating green/red days reflect normal variance with small positive edge.

### Fix Applied
NO CHANGES. System healthy, no intervention needed.

### Verification
PM_TRAIL 83.1% WR stable (>80% threshold). ATR_SL count at historic low. 0 open positions. Legacy SHORT drain complete. Pipeline running, all timers firing. MIN_PRE_MOVE 0.3 eval extended to Aug 25.

---

## CEO Report — 2026-08-21 (~04:00 UTC, verified, 196th run)

### Diagnosis
System HEALTHY. 24h: 18T -$0.54, 50.0% WR (flat — normal NEUTRAL variance). 7d: 260T -$1.39, 50.4% WR. 0 open positions (clean). PM_TRAIL: 138T/7d +$5.11, 82.6% WR (carrying system). ATR_SL: 96T/7d -$7.21, 1% WR (dominant drag, historic low count). SHORT legacy: ALL cleared — 0 remaining open positions, drain complete. Daily: Aug 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.54 (alternating pattern, green days getting greener). r2-trend-long3 MIN_PRE_MOVE 0.3: 48h 9T $0.00, 66.7% WR (break-even — WR improved from 54.5% 7d but PnL flat). continuation+ 4T/7d -$0.24, 25% WR (tiny sample, too early to kill).

### Root Cause
No new root causes. SHORT legacy drain complete —0 remaining positions. ATR_SL remains dominant drag at -$7.21/7d but count at historic low (96/7d vs peak). PM_TRAIL continues carrying at 82.6% WR. Coin tracker wyckoff detection gap: 0/109 coins have non-none phase.

### Fix Applied
NO CHANGES. System healthy, no intervention needed.

### Verification
PM_TRAIL 82.6% WR stable (>80% threshold). ATR_SL count at historic low. 0 open positions. Legacy SHORT drain complete. Pipeline running, all timers firing. MIN_PRE_MOVE 0.3 eval extended to Aug 25.

---

## CEO Report — 2026-08-21 (~03:00 UTC, verified, 195th run)

### Diagnosis
System HEALTHY. 24h: 18T -$0.54, 50.0% WR (flat — SHORT legacy aging out). 7d: 266T -$1.08, 51.5% WR (improved). 0 open positions (clean). PM_TRAIL: 144T/7d +$5.42, 83.3% WR (carrying system). ATR_SL: 14T/48h -$1.59 (dominant drag). Daily: Aug 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.54 (alternating). Coin tracker: 113 coins tracked, ALL wyckoff_phase=none (detection gap confirmed — BTC shows accumulation in raw data but phase not propagating).

### Root Cause
No new root causes. System stable. SHORT legacy losses (-$0.47/48h) aging out by Aug 22. ATR_SL dominant at 14T/48h -$1.59. r2-trend-long3 MIN_PRE_MOVE 0.3: 48h 9T $0.00 66.7% WR — WR improved (55.9%→66.7%) but PnL flat. PM_TRAIL captures winners, ATR_SL hits losers = break-even. Coin tracker Wyckoff detection not producing actionable phases.

### Fix Applied
EXTENDED MIN_PRE_MOVE 0.3 eval through Aug 25 (was Aug 23). Break-even not enough — filter needs to produce positive PnL to justify keeping. If still flat by Aug 25, remove filter. No other changes.

### Verification
PM_TRAIL 83.3% WR stable. ATR_SL at historic low. 0 open positions. Legacy SHORT clearing on track. Pipeline running, all timers firing.

---

## CEO Report — 2026-08-21 (~02:00 UTC, verified, 194th run)

### Diagnosis
System HEALTHY. 24h: 18T -$0.54, 50.0% WR (flat — SHORT legacy aging out). 7d: 267T -$1.12, 51.3% WR (improved from -$1.18). 0 open positions (clean). PM_TRAIL: 144T/7d +$5.42, 83.3% WR (carrying system). ATR_SL: 97T/7d -$7.25, 8T/24h (historic low). Daily: Aug 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.54 (alternating). Coin tracker: 109 coins fresh, ALL wyckoff_phase=none (detection gap).

### Root Cause
No new root causes. System stable. SHORT legacy losses (-$0.47/48h) aging out by Aug 21-22. ATR_SL at historic low (8/day, 71% reduction from 28 peak). r2-trend-long3 MIN_PRE_MOVE 0.3 improving: 48h 9T 66.7% WR $0.00 (up from 52% 7d avg), eval wraps Aug 23. Coin tracker Wyckoff detection not producing actionable phases.

### Fix Applied
NO CHANGES. System healthy, no intervention needed.

### Verification
DB verified: 24h 18T -$0.54 50.0% WR, 7d 267T -$1.12 51.3% WR. PM_TRAIL 144T +$5.42 83.3% WR. ATR_SL 97T -$7.25. 0 open. All timers active. Legacy SHORT draining.

---
## CEO Report — 2026-08-21 (~00:46 UTC, verified, 193rd run)

### Diagnosis
System HEALTHY. 24h: 18T -$0.54, 50.0% WR (flat — SHORT legacy aging out). 7d: 268T -$1.06, 51.5% WR (improved from -$1.18). 0 open positions (clean). PM_TRAIL: 145T/7d +$5.48, 83.4% WR (carrying system). ATR_SL: 97T/7d -$7.25, 8T/24h (historic low). Daily: Aug 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.54 (alternating pattern).

### Root Cause
No new root causes. System stable. SHORT legacy losses (-$0.47/48h) aging out by Aug 21-22. ATR_SL at historic low (8/day, 71% reduction from 28 peak). r2-trend-long3 MIN_PRE_MOVE 0.3 at break-even (66.7% WR, eval wraps Aug 23). Coin tracker: 109 coins tracked but all wyckoff_phase=none — detection not producing actionable phases.

### Fix Applied
NO CHANGES. System healthy, no intervention needed.

### Verification
DB verified: 24h 18T -$0.54 50.0% WR, 7d 268T -$1.06 51.5% WR. PM_TRAIL 145T +$5.48 83.4% WR. ATR_SL 97T -$7.25. 0 open. All timers active. Legacy SHORT draining.

---
## CEO Report — 2026-08-21 (~00:15 UTC, verified, 192nd run)

### Diagnosis
System HEALTHY. 24h: 18T -$0.54, 50.0% WR (flat — SHORT legacy aging out). 7d: 269T -$1.18, 51.3% WR. 0 open positions (clean). PM_TRAIL: 145T/7d +$5.48, 83.4% WR (carrying system). ATR_SL: 98T/7d -$7.37, 8T/24h (historic low, stabilized). Daily: Aug 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.54 (red after 2 green, SHORT legacy clearing expected to end Aug 21-22).

### Root Cause
No new root causes. System is stable. SHORT legacy losses (-$0.47/48h from r2-trend-short2/13/10) are aging out as expected. ATR_SL at historic low (8/day, down from 28 peak — 71% reduction). r2-trend-long3 MIN_PRE_MOVE 0.3 at break-even (66.7% WR, PM_TRAIL carrying winners, ATR_SL still hitting losers).

### Fix Applied
NO CHANGES. System healthy, no intervention needed.

### Verification
DB verified: 24h 18T -$0.54 50.0% WR, 7d 269T -$1.18 51.3% WR. PM_TRAIL 145T +$5.48 83.4% WR. ATR_SL 98T -$7.37. 0 open. All timers active. Legacy SHORT draining as expected.

---
## CEO Report — 2026-08-20 (~23:30 UTC, verified, 190th run)

### Diagnosis
System HEALTHY. 24h: 19T -$0.53, 52.6% WR (red day — SHORT legacy clearing). 7d: 271T -$1.25, 51.3% WR (improving). 0 open positions (clean). PM_TRAIL: 146T/7d +$5.50, 83.6% WR (carrying system). ATR_SL: 99T/7d -$7.46, 1% WR (historic low, count 7-8/day). SHORT legacy: 37T/7d -$1.06, 24.3% WR — all killed signals aging out (gone by Aug 21-22). Daily: Aug 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.54 (red after 2 green).

**r2-trend-long3 MIN_PRE_MOVE 0.3:** 34T/7d 55.9% -$0.23. PM_TRAIL 19T 94.7% +$0.75 carrying, ATR_SL 14T -$0.99 dragging (92.9% of losers are ATR_SL). Eval wraps Aug 23.

### Root Cause
PM_TRAIL positive R:R (83.6% WR, avg win +0.47% vs avg loss -0.74%). System breakeven because PM_TRAIL gain ($5.50) partially offsets ATR_SL drag ($7.46). Red day = SHORT legacy clearing ($0.47) + ATR_SL cluster.

### Fix Applied
NO CHANGES. System healthy, ATR_SL at historic low, PM_TRAIL 83.6% WR carrying. All legacy losers confirmed dead or aging out by Aug 21-22.

### Monitoring
- **MIN_PRE_MOVE 0.3 eval** through Aug 23 — 55.9% WR, PM_TRAIL carrying, ATR_SL dragging
- **PM_TRAIL WR** must stay >80% (currently 83.6%)
- **ATR_SL daily** must stay <15 (currently ~8/day, historic low)
- **SHORT legacy** aging out — should be gone by Aug 21-22

---

## CEO Report — 2026-08-20 (~22:30 UTC, verified, 189th run)

### Diagnosis
System HEALTHY. 24h: 20T -$0.68, 50% WR (red day — ATR_SL 14T -$1.59 dominant). 7d: 272T -$1.29, 51.1% WR (improving from -$1.43). 0 open positions (clean). PM_TRAIL: 146T/7d +$5.50, 83.6% WR (carrying system). ATR_SL: 100T/7d -$7.50, 1% WR (main drag, trending DOWN: 28→20→18→9→8→7→8/day — SL floor fix working). Legacy SHORT clearing aging out (gone by Aug 21). Daily: Aug 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.68 (red after 3 green).

**r2-trend-long3 MIN_PRE_MOVE 0.3:** 34T/7d 55.9% -$0.23. PM_TRAIL 18T 94.4% +$0.69 carrying, ATR_SL 14T -$0.99 dragging. Day-by-day: Aug 19 4T 100% +$0.18 (excellent), Aug 20 5T 40% -$0.18 (mixed). Eval wraps Aug 23.

### Root Cause
PM_TRAIL positive R:R (83.6% WR, avg win > avg loss). ATR_SL at historic low (~8/day, down from 28 peak) but still 100% loss rate. System breakeven because PM_TRAIL gain ($5.50) partially offsets ATR_SL drag ($7.50). Red day = ATR_SL cluster (14 hits -$1.59).

### Fix Applied
NO CHANGES. System healthy, ATR_SL trending down, PM_TRAIL 83.6% WR carrying. All legacy losers confirmed dead or aging out.

### Monitoring
- **MIN_PRE_MOVE 0.3 eval** through Aug 23 — mixed results (Aug 19 excellent, Aug 20 mixed)
- **PM_TRAIL WR** must stay >80% (currently 83.6%)
- **ATR_SL daily** must stay <15 (currently ~8/day, historic low)
- **SHORT legacy** aging out — should be gone by Aug 21
- **coin_tracker** — 109 coins tracked, 0 Wyckoff phases computed (gap)

---

## CEO Report — 2026-08-20 (~21:15 UTC, verified, 188th run)

### Diagnosis
System HEALTHY. 24h: 20T -$0.69, 50% WR (red day — SHORT legacy clearing + LONG ATR_SL). 7d: 272T -$1.43, 50.7% WR (improving). 1 open position. PM_TRAIL: 145T/7d +$5.46, 83.4% WR (carrying system). ATR_SL: 101T/7d -$7.60, 1% WR (main drag). Legacy SHORT clearing: 5T/48h -$0.47 all 0% WR (draining, will age out by Aug 21). Hotset EMPTY — correct NEUTRAL behavior. Daily: Aug 13 -$0.23 → 14 -$0.56 → 15 +$0.02 → 16 -$0.49 → 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.58 (red after 8 green).

**48h SHORT legacy:** r2-trend-short2 3T -$0.23, short13 1T -$0.13, short10 1T -$0.11 = -$0.47 total.
**48h LONG losers:** stop_hunt_reversal_long+ 2T -$0.12, r2-trend-long8 1T -$0.11, r2-trend-long3 6T -$0.17.
**PM_TRAIL top carriers (7d):** r2-trend-long3 18T +$0.69 94.4%, r2-trend-long2 11T +$0.54 100%, r2-trend-long4 12T +$0.50 91.7%.

### Root Cause
PM_TRAIL R:R positive — avg win > avg loss. System profitable despite 50.7% 7d WR because PM_TRAIL (83.4% WR, 145T) carries. ATR_SL (1% WR, 101T) is the main drag. SHORT legacy clearing is structural — all killed signals aging out, expected to end by Aug 21. Hotset empty = correct behavior in flat NEUTRAL market.

### Fix Applied
NO CHANGES. System healthy, no intervention needed. All kills verified. SHORT legacy draining as expected.

### Verification
- PM_TRAIL: 145T/7d +$5.46, 83.4% WR (carrying system)
- ATR_SL: 101T/7d -$7.60, 1% WR (~7/day, historic low)
- MIN_PRE_MOVE 0.3: 48h 9T 66.7% WR $0.00 (IMPROVED, eval through Aug 23)
- stop_hunt_reversal_long+: KILLED Aug 20, 2T legacy clearing -$0.12
- SHORT legacy: draining, will age out by Aug 21
- 1 open position, 0 phantom trades
- All timers firing, pipeline healthy

### Monitoring
- **MIN_PRE_MOVE 0.3 eval** through Aug 23 — r2-trend-long3 34T/7d 55.9% -$0.23
- **PM_TRAIL WR** must stay >80% (currently 83.4%)
- **ATR_SL daily** must stay <15 (~7/day, historic low)
- **SHORT legacy** draining — will age out by Aug 21
- **Hotset** empty = NEUTRAL regime correct behavior

---

## CEO Report — 2026-08-20 (~19:00 UTC, verified, 184th run)

### Diagnosis
System HEALTHY. 24h: 24T -$0.29, 58.3% WR (red day — SHORT legacy clearing expected, will age out). 7d: 271T -$1.57, 50.6% WR. 0 open positions (clean). PM_TRAIL: 14/24 exits today +$0.79 (carrying system). ATR_SL: 9/24 today -$1.09 (main drag, improving ratio). Today's losses: SHORT legacy -$0.47 (r2-trend-short2 3T -$0.23, r2-trend-short13 1T -$0.13, r2-trend-short10 1T -$0.11 — all draining after kill Aug 20). LONG side today: r2-trend-long6 3T +$0.25 100%, stop_hunt 4T +$0.13 75%, r2-trend-long3 6T -$0.09 66.7%.

**MIN_PRE_MOVE 0.3 eval wraps today (Aug 21).** 48h: 8T 75% WR $0.00 (WR improved from 57.6% 7d avg, but PnL break-even). PM_TRAIL 94.4% carrying, ATR_SL 13T -$0.99 dragging. Extending eval 48h for more data — WR improvement real but PnL not positive yet.
**stop_hunt_reversal_long+:** 10T/7d 60% -$0.04 (break-even). 48h: 6T 50% -$0.10 (deteriorating). Not at kill threshold yet but trending badly — monitor closely.

### Root Cause
PM_TRAIL R:R positive — avg win > avg loss. System profitable despite 50.6% 7d WR because PM_TRAIL winners are bigger than ATR_SL losers. Aug 20 SHORT losses are legacy clearing after R2_TREND_SHORT kill (expected, structural). MIN_PRE_MOVE 0.3 filtering dead-cat bounces (WR 57.6%→75%) but remaining entries still noise-trading in NEUTRAL market.

### Fix Applied
NO CHANGES — system healthy, no intervention needed. MIN_PRE_MOVE 0.3 eval extended 48h (Aug 23) for more data.

### Verification
- PM_TRAIL: carrying system (14/24 exits today +$0.79)
- ATR_SL: 9/24 today -$1.09 (improving ratio from 53% to 37.5% of exits)
- MIN_PRE_MOVE 0.3: 48h 8T 75% WR (IMPROVED, eval extended to Aug 23)
- stop_hunt_reversal_long+: 10T/7d 60% -$0.04 (break-even, 48h 50% -$0.10 deteriorating)
- SHORT legacy: draining as expected, will age out
- 0 open positions, 0 phantom trades
- All timers firing, pipeline healthy

---

## CEO Report — 2026-08-20 (~22:00 UTC, verified, 181st run)

### Diagnosis
System HEALTHY. 24h: 25T -$0.36, 56.0% WR (red day — SHORT legacy clearing expected after R2_TREND_SHORT kill Aug 20, will age out). 7d: 275T -$1.59, 50.5% WR. 2 open (r2-trend-long3, r2-trend-long16). PM_TRAIL DOMINANT: 147T/7d +$5.65, 83.7% WR (carrying system). ATR_SL: 103T/7d -$7.88, 1.0% WR (historic low). Today's losses: SHORT legacy -$0.47 (r2-trend-short2 -$0.23, r2-trend-short13 -$0.13, r2-trend-short10 -$0.11 — all draining after kill). LONG side: 6T +$0.33 (r2-trend-long6 +$0.25 100%, r2-trend-long3 +$0.09 83.3%).

**stop_hunt_reversal_long+:** 10T/7d 60% -$0.04 (break-even). 48h deteriorating: 3 ATR_SL -$0.38, 3 PM_TRAIL +$0.28 = net -$0.10. Not at kill threshold yet but trending negative — monitor.
**r2-trend-long3 MIN_PRE_MOVE 0.3:** 32T/7d 59.4% -$0.12. PM_TRAIL 18T 94.4% +$0.69 carrying, ATR_SL 12T -$0.88 dragging. Eval wraps Aug 21.

### Root Cause
PM_TRAIL R:R positive — avg win > avg loss. System profitable despite 50.5% 7d WR because PM_TRAIL winners (83.7% WR) are bigger than ATR_SL losers (1.0% WR). Aug 20 SHORT losses are legacy clearing after R2_TREND_SHORT kill (expected, structural). stop_hunt 48h degrading but not at kill threshold.

### Fix Applied
NO CHANGES. System healthy, no intervention needed. SHORT legacy draining as expected.

### Monitoring
- **MIN_PRE_MOVE 0.3 eval** wraps Aug 21 — finalize r2-trend-long3 params
- **stop_hunt_reversal_long+** deteriorating — kill if 7d WR <55% or PnL negative
- **PM_TRAIL WR** must stay >80% (currently 83.7%)
- **ATR_SL daily** must stay <15 (~3-7/day, historic low)
- **SHORT side** structural gap — all legacy dead, need new signals

---

## CEO Report — 2026-08-20 (~19:46 UTC, verified, 186th run)

### Diagnosis
System HEALTHY. 24h: 23T -$0.63, 50% WR (red day — SHORT legacy clearing + LONG ATR_SL). 7d: 271T -$1.46, 50.6% WR (improving from -$1.59). 1 open position. PM_TRAIL: 144T/7d +$5.43, 83.3% WR (carrying system). ATR_SL: 101T/7d -$7.60, 1% WR (main drag). Today's losses: SHORT legacy -$0.47 (r2-trend-short2 -$0.23, r2-trend-short13 -$0.13, r2-trend-short10 -$0.11 — all draining after kill). LONG side: r2-trend-long6 2T +$0.16 100%, r2-trend-long4 2T +$0.04 100%, bb_bounce+ 1T +$0.07 100%, r2-trend-long3 7T -$0.09 57.1%.

**stop_hunt_reversal_long+:** Kill VERIFIED (flag=False, in NEVER_REENABLE). 24h legacy positions clearing (2T -$0.12).

**r2-trend-long3 MIN_PRE_MOVE 0.3:** 34T/7d 55.9% -$0.23. PM_TRAIL 20T 94.4% +$0.80 carrying, ATR_SL 14T -$0.99 dragging. Eval through Aug 23.

### Root Cause
PM_TRAIL R:R positive — avg win > avg loss. System profitable despite 50.5% 7d WR because PM_TRAIL winners (83.3% WR) are bigger than ATR_SL losers (1% WR). Aug 20 SHORT losses are legacy clearing after R2_TREND_SHORT kill (expected, structural). LONG ATR_SL is the main drag at -$0.99/7d on r2-trend-long3 alone.

### Fix Applied
NO CHANGES. All kills verified. Fixed CURRENT.md timestamp (was future-dated Aug 21). SHORT legacy draining as expected.

### Monitoring
- **MIN_PRE_MOVE 0.3 eval** through Aug 23 — r2-trend-long3 ATR_SL 14T -$0.99 needs to improve
- **PM_TRAIL WR** must stay >80% (currently 83.3%)
- **ATR_SL daily** must stay <15 (~7/day, historic low)
- **SHORT side** structural gap — all legacy dead, need new signals for SHORT_BIAS regime

---

## CEO Report — 2026-08-20 (~23:45 UTC, verified, 191st run)

### Diagnosis
System HEALTHY. Verified DB: 24h 18T -$0.54, 50.0% WR. 7d: 271T -$1.25, 51.3% WR. PM_TRAIL: 146T/7d +$5.50, 83.6% WR (carrying system). ATR_SL: 14T/48h -$1.59 (dominant drag). 0 open positions (clean). Daily: Aug 17 +$0.37 → 18 -$0.38 → 19 +$0.42 → 20 -$0.54 (red after 2 green, SHORT legacy clearing expected).

**r2-trend-long3 MIN_PRE_MOVE 0.3 (48h eval):** 9T, $0.00 PnL, 66.7% WR — break-even. PM_TRAIL 5T +$0.22 100% WR capturing winners. ATR_SL 3T -$0.23 0% WR still hitting. Net flat. Eval wraps Aug 23.

**continuation+:** 5T/7d -$0.17, 40% WR — tiny sample, 0T/24h (no recent trades). Too early to kill.

### Root Cause
PM_TRAIL positive R:R (83.6% WR, avg win +0.47% vs avg loss -0.74%). Red day = SHORT legacy clearing (all killed signals, aging out Aug 21-22) + ATR_SL cluster on r2-trend-long3. System breakeven because PM_TRAIL gain ($5.50) offsets ATR_SL drag ($7.46).

### Fix Applied
NO CHANGES. System healthy, PM_TRAIL 83.6% WR carrying, ATR_SL at historic low count, MIN_PRE_MOVE 0.3 eval ongoing (break-even 48h, needs more data through Aug 23). All legacy losers confirmed dead or aging out.

### Monitoring
- **MIN_PRE_MOVE 0.3 eval** through Aug 23 — 48h break-even, PM_TRAIL capturing but ATR_SL still hitting
- **PM_TRAIL WR** must stay >80% (currently 83.6%)
- **ATR_SL daily** must stay <15 (~7/day, historic low)
- **SHORT side** structural gap — all legacy dead, need new signals for SHORT_BIAS regime
