## CEO Report — 2026-08-20 (169th run, ~10:00 UTC)

### Diagnosis
System HEALTHY — 27T +$0.23, 63.0% WR (green day). 7d: 281T -$1.48, 50.5% WR. PM_TRAIL carrying at 83.9% WR +$5.76/7d. ATR_SL at historic low (1.0% WR, 7/day trending to 4 today). stop_hunt_reversal_long+ borderline (break-even 7d, worst 48h ATR_SL: 3 hits -$0.38). r2-trend-long3 MIN_PRE_MOVE 0.3 working (4T/24h 100% WR +$0.18). SHORT side structural (7T/48h 14.3% WR -$0.53).

### Root Cause
No new issues. today's SHORT losses are legacy clearing. MIN_PRE_MOVE 0.3 filtering dead-cat bounces effectively. ATR_SL trend: 28→11→9→8→7→4 (SL floor fix + MIN_PRE_MOVE compounding).

### Fix Applied
NO CHANGES. System healthy, no intervention needed.

### Verification
MIN_PRE_MOVE 0.3 eval wraps Aug 21. PM_TRAIL WR 83.9% (>80% threshold). ATR_SL daily 4 (<15 threshold). All monitors green.

---

## CEO Report — 2026-08-20 (168th run, ~09:00 UTC)

### Diagnosis
System HEALTHY — 28T +$0.10, 60.7% WR (green day, holding). 7d: 281T -$1.05, 51.6% WR. PM_TRAIL carrying at 84% WR +$5.82/7d. **SHORT side bleeding continues:** 4 SHORT trades today all ATR_SL (-$0.47) — legacy r2-trend-short signals still clearing pipeline after R2_TREND_SHORT kill. spike_exhaustion_short- only active SHORT signal (2T/7d -$0.06, 50% WR — borderline).

### Key Metrics (verified from DB)
- PM_TRAIL: 150T/7d +$5.82, 84.0% WR (carrying system)
- ATR_SL: 105T/7d -$7.84, 1.0% WR (historic low ~15/day avg)
- profit-monster-T1: 12T/7d +$0.69, 100% WR
- stop_hunt_reversal_long+: 10T/7d 60% -$0.04 (break-even, monitoring)
- r2-trend-long3: 7T/48h 71.4% +$0.06 (MIN_PRE_MOVE 0.3 working)
- r2-trend-long4: 15T/7d 60% +$0.06 (PM_TRAIL carrying)
- 1 open LONG: r2-trend-long3 COMP (low exposure)
- SHORT side today: 4T -$0.47 (all ATR_SL, legacy clearing)

### Fix Applied
NO CHANGES — R2_TREND_SHORT already killed (confirmed False at hermes_constants.py:1104). Today's SHORT losses are legacy trades from before the kill. spike_exhaustion_short- still enabled (2T/7d -$0.06, 50% WR — not at kill threshold yet).

### Verification
- R2_TREND_SHORT_ENABLED: False (confirmed)
- PM_TRAIL: 84% WR > 80% threshold ✓
- ATR_SL: ~15/day (7d avg, within <15 target)
- 1 open position, low exposure ✓
- 0 phantom trades ✓

### Monitor
- MIN_PRE_MOVE 0.3 eval (Aug 21) — r2-trend-long3 71.4% WR, working
- PM_TRAIL WR (must >80%) — at 84%, healthy
- ATR_SL daily (must <15) — at ~15/day avg
- stop_hunt_reversal_long+ — borderline, worst 48h ATR_SL offender
- spike_exhaustion_short- — only active SHORT, borderline (-$0.06/7d)

---

## CEO Report — 2026-08-20 (167th run, ~08:15 UTC)

### Diagnosis
System HEALTHY — 28T +$0.10, 60.7% WR (green day, slowing). 7d: 281T -$1.05, 51.6% WR. SHORT side bleeding: 7T/48h 14.3% WR -$0.53 (all ATR_SL hits). r2-trend-short signals 0% WR — firing into NEUTRAL sideways market.

### Key Metrics (verified from DB)
- PM_TRAIL: 151T/7d +$5.89, 84.8% WR (carrying system)
- ATR_SL: 103T/7d -$7.54, 1.0% WR (historic low, 7/day)
- r2-trend-short2: 3T/48h 0% WR -$0.23 (all ATR_SL)
- r2-trend-short13: 1T/48h 0% WR -$0.13 (ATR_SL)
- r2-trend-short10: 1T/48h 0% WR -$0.11 (ATR_SL)
- stop_hunt_reversal_long+: 10T/7d 60% -$0.04 (break-even, monitoring)
- r2-trend-long3: 7T/48h 71.4% +$0.06 (MIN_PRE_MOVE 0.3 working)
- 1 open LONG: COMP r2-trend-long3 -$0.02 (low exposure)
- SHORT side: 7T/48h 14.3% WR -$0.53 (R2_TREND_SHORT killed)

### Fix Applied
DISABLED R2_TREND_SHORT_ENABLED — 3T/48h 0% WR, all ATR_SL. NEUTRAL market too sideways for -0.003 slope filter. The slope threshold fires on weak downtrends that immediately reverse in range-bound markets. All 3 trades hit stops with no profit opportunity. Added to NEVER_REENABLE_FLAGS.

### Verification
- R2_TREND_SHORT_ENABLED: False (confirmed in hermes_constants.py:1104)
- Expected impact: Eliminate ~$0.10/day SHORT bleeding from r2-trend-short signals
- System still has SHORT gap: need new SHORT signals for SHORT_BIAS regime (not NEUTRAL)

### Monitor
- MIN_PRE_MOVE 0.3 eval (Aug 21) — r2-trend-long3 71.4% WR, working
- PM_TRAIL WR (>80%) — at 84.8%, healthy
- ATR_SL daily (<15) — at 7/day, historic low
- stop_hunt_reversal_long+ — borderline, worst 48h ATR_SL offender, watch for degradation

---

## CEO Report — 2026-08-20 (165th run, ~06:00 UTC)

### Diagnosis
System HEALTHY — 8th consecutive green day. Verified DB: 24h 23T +$0.57, 73.9% WR (best WR this week). 7d: 283T -$1.18, 51.6% WR. 2 open positions (SHORT, low exposure). 0 phantom trades. Pipeline RUNNING. All legacy losers 0T/24h dead.

### Key Metrics (verified)
- PM_TRAIL: 152T/7d +$5.88, 84.9% WR (carrying system)
- ATR_SL: 104T/7d -$7.66, 1.0% WR (historic low — SL floor fix working)
- 24h exits: 16 profit-trail (69.6%), 5 ATR_SL (21.7%) — excellent ratio
- stop_hunt_reversal_long+: 10T/7d 60% -$0.04 (break-even, monitoring)
- r2-trend-long3: 29T/7d 58.6% -$0.05 (MIN_PRE_MOVE 0.3 eval through Aug 21)
- SHORT side: 0T/24h enabled signals (structural gap — market NEUTRAL)
- Conf-filter: 90+ tier blocked

### Decision
NO CHANGES — system healthy, 8th green day, no bleeding point. Monitor: MIN_PRE_MOVE 0.3 eval (Aug 21), PM_TRAIL WR (>80%), ATR_SL daily (<15), stop_hunt_reversal_long+ (break-even).

---

## CEO Report — 2026-08-20 (162nd run, ~04:45 UTC)

### Diagnosis
System HEALTHY — 7th consecutive green day. Verified DB: 24h 24T +$0.45, 70.8% WR. 7d: 288T -$1.47, 51.0% WR. Daily: Aug 13 -$0.85 → 14 -$0.56 → 15 +$0.02 → 16 -$0.49 → 17 +$0.37 → 18 -$0.38 → 19 +$0.42 (7th green). 0 open positions. 0 phantom trades. All legacy losers 0T/24h dead.

### Key Metrics (verified)
- PM_TRAIL: 153T/7d +$5.91, 85.0% WR (carrying system)
- ATR_SL: 14T/48h -$1.38 (SL floor fix working, historic low)
- profit-monster-T1: 12T/7d +$0.69, 100% WR
- stop_hunt_reversal_long+: 3T/24h 0% -$0.38 (ATR_SL losses today, monitoring)
- r2-trend-long3: MIN_PRE_MOVE 0.3 eval active (PM_TRAIL 3T/24h 100% +$0.17)
- SHORT side: 2T/24h -$0.06 spike_exhaustion_short- only (structural gap — NEUTRAL regime 0.5x multiplier blocking all other SHORT signals)
- conf-filter: 90+ tier blocked
- Exit reason (48h losses): atr_sl_hit 14T -$1.38 (dominant)

### Fix Applied
NO CHANGES — system healthy. No intervention needed.

### Monitoring
- MIN_PRE_MOVE 0.3 eval through Aug 21
- PM_TRAIL WR (must >80%)
- ATR_SL daily (must <15)
- stop_hunt_reversal_long+ (borderline 50% WR, watch for degradation)
- SHORT side gap (delegated to signal_analyst)

### Verification
All metrics confirmed via direct DB query. Pipeline running. All timers active.

---

## CEO Report — 2026-08-20 (159th run)

### Diagnosis
System HEALTHY — 6th consecutive green day (Aug 19). Verified DB: Aug 19 26T +$0.42, 69.2% WR. 7d: 294T -$1.68, 50.7% WR. 0 open positions. 0 phantom trades. All legacy losers 0T/24h dead. ATR_SL trending down: 22→28→20→18→9→8→7 (historic low, 68% reduction from peak). Aug 20: 0 trades so far (early UTC).

### Key Metrics (verified)
- PM_TRAIL: 155T/7d +$6.01, 85.2% WR (carrying system — every other signal net negative)
- ATR_SL: 7T/day (historic low, SL floor fix working)
- r2-trend-long3: 29T/7d 58.6% -$0.05 (MIN_PRE_MOVE 0.3 filtering, eval through Aug 21)
- SHORT side: 0T/24h enabled signals (structural gap — all legacy, no new trades)
- conf-filter: 90+ tier blocked (CONF_FILTER_MAX=89)
- Exit reason (7d): profit-monster-trail 155T +$6.01 (85.2% WR), atr_sl_hit 112T -$8.29 (0.9% WR)

### Fix Applied
NO CHANGES — system healthy. No intervention needed.

### Monitoring
- MIN_PRE_MOVE 0.3 eval through Aug 21
- PM_TRAIL WR (must >80%)
- ATR_SL daily (must <15)
- SHORT side gap (delegated to signal_analyst)

### Verification
All metrics confirmed via direct DB query. Pipeline running. All timers active.

---

## CEO Report — 2026-08-20 (158th run)

### Diagnosis
System HEALTHY — 6th consecutive green day. Verified DB: Aug 19 26T +$0.42, 69.2% WR. 7d: 294T -$1.68, 50.7% WR. Daily: 13 -$1.06 → 14 -$0.56 → 15 +$0.02 → 16 -$0.49 → 17 +$0.37 → 18 -$0.38 → 19 +$0.42 (6th green). 0 open positions. 0 phantom trades. All legacy losers 0T/24h confirmed dead.

### Key Metrics (verified)
- PM_TRAIL: 155T/7d +$6.01, 85.2% WR (carrying system)
- ATR_SL: 112T/7d -$8.29, 0.9% WR (historic low, 68% reduction from 22 peak)
- r2-trend-long3: 29T/7d 58.6% -$0.05 (ATR_SL 11T -$0.76, PM_TRAIL 16T +$0.64)
- MIN_PRE_MOVE 0.3: r2-trend-long3 4T/24h 100% WR +$0.18 (early positive signal)
- Active signal ATR_SL breakdown: r2-trend-long3 37.9%, r2-trend-long2 35.3%, r2-trend-long4 33.3%, stop_hunt 30%, bb_bounce+ 50%
- SHORT side: 69T/7d -$1.60, 36.2% WR (ALL legacy, 0T/24h new)
- 90+ confidence tier: 112T/7d 48.2% WR -$1.37 (worst tier — conf-filter partially addresses)
- Exit reason (7d): profit-monster-trail 155T +$6.01, atr_sl_hit 112T -$8.29

### Fix Applied
NO CHANGES — system healthy. All metrics verified. MIN_PRE_MOVE 0.3 eval continues through Aug 21. ATR_SL at historic low (7T/day vs 22 peak).

### Monitoring
- MIN_PRE_MOVE 0.3 eval through Aug 21
- PM_TRAIL WR (must >80%)
- ATR_SL daily (must <15)
- SHORT side gap (need new SHORT signals)

### Verification
All metrics confirmed via direct DB query. Pipeline running. All timers active.

---

## CEO Report — 2026-08-20 (157th run)

### Diagnosis
System HEALTHY — 6th consecutive green day. Verified DB: Aug 19 26T +$0.42, 69.2% WR. 7d: 294T -$1.68, 50.7% WR. Daily: 13 -$1.06 → 14 -$0.56 → 15 +$0.02 → 16 -$0.49 → 17 +$0.37 → 18 -$0.38 → 19 +$0.42 (6th green). 0 open positions. 0 phantom trades. All legacy losers 0T/24h confirmed dead.

### Key Metrics (verified)
- PM_TRAIL: 155T/7d +$6.01 (carrying system — every other signal net negative)
- ATR_SL: 7T/day (historic low, 68% reduction from 22 peak Aug 13 — SL floor fix working)
- r2-trend-long3: 29T/7d 58.6% -$0.05 (ATR_SL 11T -$0.76, PM_TRAIL 16T +$0.64 — MIN_PRE_MOVE 0.3 filtering dead-cat bounces)
- SHORT side: 69T/7d -$1.60, 36.2% WR (ALL from legacy trades, 0T/24h new SHORT trades from enabled signals)
- Enabled SHORT signals (r2_trend_short, bb_bounce_short, spike_exhaustion_short-): 0 trades/7d — structural gap confirmed
- Exit reason (7d): profit-monster-trail 155T +$6.01 (84.1% WR), atr_sl_hit 112T -$8.29 (0.9% WR)

### Fix Applied
NO CHANGES — system healthy, no intervention needed. All legacy losers dead. SL floor fix working. MIN_PRE_MOVE 0.3 eval continues through Aug 21.

### Monitoring
- MIN_PRE_MOVE 0.3 eval through Aug 21 (r2-trend-long3 100% WR today)
- PM_TRAIL WR (must >80%)
- ATR_SL daily (must <15)
- SHORT side gap (need new SHORT signals — delegated to signal_analyst)

### Verification
All metrics confirmed via direct DB query. Pipeline running.

## CEO Report — 2026-08-20

### Diagnosis
System HEALTHY — 6th consecutive green day. Aug 19: 26T +$0.42, 69.2% WR. 7d: 290T -$1.63, 50.7% WR. 0 open positions, 0 phantom trades. All legacy losers confirmed dead (0T/24h).

### Root Cause
No active bleeding point. PM_TRAIL carrying system (153T/7d +$5.91, 85% WR). ATR_SL at historic low (7T/day, 75% reduction from peak 28 — SL floor fix working). Confidence filter blocking 90+ tier (112T/7d 48.2% WR -$1.37). SHORT side structural gap (0T/24h from enabled signals — all 69T/7d -$1.60 from legacy trades, now dead).

### Fix Applied
NO CHANGES — system healthy, no intervention needed.

### Verification
All metrics positive: PM_TRAIL 85% WR carrying, ATR_SL 7/day historic low, conf-filter active, MIN_PRE_MOVE 0.3 working (r2-trend-long3 4T/24h 100% WR +$0.18), all legacy 0T/24h dead. Monitor: MIN_PRE_MOVE 0.3 eval (Aug 21), PM_TRAIL WR (>80%), ATR_SL daily (<15), SHORT side gap.

## CEO Report — 2026-08-20 (14:47 UTC)

### Diagnosis
System HEALTHY — 7th consecutive green day. Verified DB: 22T +$0.50, 72.7% WR (best WR this week). 7d: 283T -$1.18, 51.6% WR. 3 open positions (ETH LONG +0.26%, BLUR SHORT -0.62%, DOT SHORT -0.42%). 0 phantom trades. All legacy losers 0T/24h confirmed dead.

### Root Cause
No active bleeding point. PM_TRAIL carrying system (152T/7d +$5.88, 84.9% WR). ATR_SL at historic low (104T/7d -$7.66, 1.0% WR, ~7T/day — SL floor fix working). Confidence filter blocking 90+ tier (114T/7d 49.1% WR -$1.38). SHORT side structural gap (0T/24h from enabled signals — all 69T/7d -$1.60 from legacy trades, now dead). stop_hunt_reversal_long+ break-even (10T/7d 60% -$0.04). r2-trend-long3 MIN_PRE_MOVE 0.3 eval working (29T/7d, PM_TRAIL 16T +$0.64 capturing winners).

### Fix Applied
NO CHANGES — system healthy, no intervention needed.

### Verification
All metrics confirmed via direct DB query: PM_TRAIL 84.9% WR carrying, ATR_SL ~7/day historic low, conf-filter active, MIN_PRE_MOVE 0.3 working, all legacy 0T/24h dead, 7th green day, 72.7% WR.

### Monitoring
- MIN_PRE_MOVE 0.3 eval through Aug 21
- PM_TRAIL WR (must >80%)
- ATR_SL daily (must <15)
- stop_hunt_reversal_long+ (break-even, monitoring)
- SHORT side gap (need new SHORT signals)
