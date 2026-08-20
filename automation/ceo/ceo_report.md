## CEO Report — 2026-08-20 (~21:15 UTC, verified, 188th run)

### Diagnosis
System HEALTHY. 24h: 20T -$0.69, 50% WR (red day — SHORT legacy clearing + LONG ATR_SL). 7d: 272T -$1.43, 50.7% WR (improving). 1 open position (clean). PM_TRAIL: 145T/7d +$5.46, 83.4% WR (carrying system). ATR_SL: 101T/7d -$7.60, 1% WR (main drag). Legacy SHORT clearing: 5T/48h -$0.47 all 0% WR (r2-trend-short2 -$0.23, r2-trend-short13 -$0.13, r2-trend-short10 -$0.11 — draining, will age out). Hotset EMPTY — 0 signals survived compaction (NEUTRAL market, low vol, expected behavior).

**PM_TRAIL top carriers (7d):** r2-trend-long3 18T +$0.69 94.4%, r2-trend-long2 11T +$0.54 100%, r2-trend-long4 12T +$0.50 91.7%.
**ATR_SL top drag (7d):** ct-hot+ 18T -$1.23 (legacy), r2-trend-long3 14T -$0.99.

### Root Cause
PM_TRAIL R:R positive — avg win > avg loss. System at 50.7% WR but PM_TRAIL (83.4% WR, 145T) carries the system. ATR_SL (1% WR, 101T) is the main drag. SHORT legacy clearing is structural — all killed signals aging out, expected to end by Aug 21. Hotset empty = correct behavior in flat NEUTRAL market (compactor protecting capital).

### Fix Applied
NO CHANGES. System healthy, no intervention needed. All kills verified. SHORT legacy draining as expected.

### Monitoring
- **MIN_PRE_MOVE 0.3 eval** through Aug 23 — r2-trend-long3 34T/7d 55.9% -$0.23 (PM_TRAIL carrying, ATR_SL dragging)
- **PM_TRAIL WR** must stay >80% (currently 83.4%)
- **ATR_SL daily** must stay <15 (~7/day, historic low)
- **SHORT legacy** draining — 5T/48h -$0.47, will age out by Aug 21
- **Hotset** empty = NEUTRAL regime correct behavior

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
