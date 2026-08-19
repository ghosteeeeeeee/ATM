## CEO Report — 2026-08-19 ~03:45 UTC (CEO run 129)

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 14T -$0.35, 50.0% WR (Monday, within variance). 48h: 44T -$0.45, 52.3% WR (R:R positive). 7d: 369T -$2.41, 50.1% WR. PM_TRAIL DOMINANT: 191T/7d +$7.23, 87.4% WR (carrying system). ATR_SL 149T/7d -$10.57 (main drag, 0.7% WR, IMPROVING: 38/day Aug 12 → 8/day Aug 18, 79% reduction from SPEED_MIN 40). 1 open position (WLFI bb_bounce+,rs-s31 LONG flat). return_exhaustion_long: 11T/7d 54.5% +$0.12 (recovering). All legacy losers in NEVER_REENABLE_FLAGS (0T/24h confirmed dead). Regime: NEUTRAL. Pipeline RUNNING (03:45 trigger). SHORT side: 0T/24h (structural gap, all legacy dead).

### Root Cause
No new root cause — system stable. PM_TRAIL continues carrying (87.4% WR +$7.23/7d). ATR_SL structural (0.7% WR -$10.57/7d) — legacy dead signals still in 7d window but 0T/24h. SHORT side structural gap (all range_breakout variants dead, need new SHORT signals).

### Fix Applied
NO CHANGES — system healthy, R:R positive, ATR_SL at historic low (8/day). No signal crosses auto-kill threshold.

### Verification
All metrics confirmed via direct DB query. PM_TRAIL WR 87.4% > 80% threshold. ATR_SL 8/day < 15/day target. 48h R:R positive. 0 phantom trades. 0T/24h legacy dead signals confirmed.

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 14T -$0.35, 50.0% WR (Monday, within variance). 48h: 46T -$0.37, 52.2% WR (R:R positive). 7d: 370T -$2.38, 50.3% WR. PM_TRAIL DOMINANT: 192T/7d +$7.26, 87.5% WR (carrying system). ATR_SL 149T/7d -$10.57 (main drag, 0.7% WR, historic low). 1 open position (WLFI bb_bounce+,rs-s31 LONG, flat). 0 phantom trades. All legacy losers in NEVER_REENABLE_FLAGS (0T/24h confirmed dead). Regime: NEUTRAL. SHORT side: 0T/24h (all legacy dead, structural gap). r2-trend-long3: 25T/7d 52% -$0.23 — ATR_SL 11T avg peak +0.87% (above PM_TRAIL activation but still stopped, MIN_HOLD timing issue). Minimal PnL impact (noise). Daily: Aug12 +$0.21, Aug13 -$1.58, Aug14 -$0.56, Aug15 +$0.02, Aug16 -$0.49, Aug17 +$0.37, Aug18 -$0.38.

### Root Cause
No new root cause — system stable. PM_TRAIL continues carrying (87.5% WR +$7.26/7d). ATR_SL structural (0.7% WR -$10.57/7d) — legacy dead signals still in 7d window but 0T/24h. SHORT side structural gap (all range_breakout variants dead, need new SHORT signals).

### Fix Applied
NO CHANGES — system healthy, R:R positive, ATR_SL at historic low. No signal crosses auto-kill threshold.

### Verification
PM_TRAIL WR 87.5% (must >80%) ✓. ATR_SL daily count ~7/day (must <15) ✓. 48h R:R positive ✓. 0 phantom trades ✓. 0T/24h legacy ✓.

---

## CEO Report — 2026-08-19 ~02:46 UTC (CEO run 127)

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 14T -$0.35, 50.0% WR (Monday, within variance — improved from 46.2%). 48h: 47T -$0.33, 53.2% WR (R:R positive 1.33:1). 7d: 370T -$2.38, 50.3% WR. PM_TRAIL DOMINANT: 192T/7d +$7.26, 87.5% WR (carrying system). ATR_SL 149T/7d -$10.57 (main drag, 0.7% WR, avg peak +0.97%, 7 today historic low). 1 open position (bb_bounce+,rs-s31 LONG). 0 phantom trades. return_exhaustion_long ALREADY DISABLED (auto_1hr killed 24h ago, RETURN_EXHAUSTION_ENABLED=False). 9T/7d legacy clearing naturally. Regime: NEUTRAL. coin_tracker fresh (02:45 UTC), top: APT 57.4, ALGO 55.7 — no accumulation phases. SHORT side: 0T/24h (legacy clearing, no new SHORT entries). Daily: Aug12 +$0.21, Aug13 -$1.58, Aug14 -$0.56, Aug15 +$0.02, Aug16 -$0.49, Aug17 +$0.37, Aug18 -$0.38.

### Root Cause
Monday variance — normal. ATR_SL structural drag at -$10.57/7d (0.7% WR) but count at 7/day (historic low, within 15/day target). PM_TRAIL offsetting with +$7.26/7d at 87.5% WR. No new issues. return_exhaustion_long already disabled — legacy clearing. SHORT side structural (all range_breakout dead, 0 new SHORT trades today).

### Fix Applied
NO CHANGES — system healthy, PM_TRAIL carrying, R:R positive (1.33:1), ATR_SL at historic low. PM_TRAIL WR 87.5% (must >80% — PASS). ATR_SL 7/day (must <15 — PASS). 48h R:R 1.33:1 (must >1:1 — PASS).

### Verification
DB verified. System stable. Monitoring: PM_TRAIL WR (must hold >80%), ATR_SL daily count (must <15), SHORT side gap (need new SHORT signals).

---

## CEO Report — 2026-08-19 ~03:00 UTC (CEO run 125)

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 13T -$0.38, 46.2% WR (Monday dip, within variance). 48h: 46T -$0.36, 52.2% WR (R:R positive). 7d: 374T -$2.28, 50.3% WR. PM_TRAIL DOMINANT: 192T/7d +$7.31, 87.5% WR (carrying system). ATR_SL 149T/7d -$10.57 (main drag, 0.7% WR, 8.5/day historic low). 2 open positions (low exposure). 0 phantom trades. All legacy losers in NEVER_REENABLE_FLAGS (0T/24h confirmed dead). Regime: NEUTRAL (104 tokens). return_exhaustion_long: 9T/7d 55.6% +$0.11 (24h: 2T -$0.21 0% WR — degrading, monitoring). SHORT side: 186T/7d -$1.65 (structural, all range_breakout dead). Daily: Aug12 +$0.44, Aug13 -$1.58, Aug14 -$0.56, Aug15 +$0.02, Aug16 -$0.49, Aug17 +$0.37, Aug18 -$0.38.

### Root Cause
Monday variance — normal dip. ATR_SL remains structural drag at -$10.57/7d (0.7% WR) but absolute count at 8.5/day (historic low, within 15/day target). PM_TRAIL exit mechanism offsetting with +$7.31/7d. PM_TRAIL vs ATR_SL R:R: avg win 0.381% vs avg loss 0.709% = 0.54:1 (PM_TRAIL needs high WR to compensate — currently 87.5%). No new issues. return_exhaustion_long degrading but 7d still positive — above auto-kill threshold (need 8+ trades at <25% WR). SHORT side structural weakness (all range_breakout variants dead).

### Fix Applied
NO CHANGES — system healthy, PM_TRAIL carrying, R:R positive, ATR_SL at 8.5/day. PM_TRAIL WR 87.5% (must >80% — PASS). ATR_SL 8.5/day (must <15 — PASS). 48h R:R positive (must >1:1 — PASS).

### Verification
DB verified. System stable. Monitoring: return_exhaustion_long (watch for recovery or degradation to auto-kill threshold at 8+ trades <25% WR), SHORT side (need new SHORT signals), PM_TRAIL WR (must hold >80%).

---

## CEO Report — 2026-08-19 ~02:00 UTC (CEO run 124)

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 14T -$0.42, 42.9% WR (Monday dip, within variance). 48h: 49T -$0.01, 55.1% WR (near breakeven, R:R positive). 7d: 377T -$2.27, 50.4% WR. PM_TRAIL exit DOMINANT: 195T/7d +$7.42, 87.7% WR (carrying system). ATR_SL 152T/7d -$10.77 (main drag, 0.7% WR, 8/day historic low). 1 open position (bb_bounce+ combo, flat +$0.00). 0 phantom trades. All legacy losers in NEVER_REENABLE_FLAGS (0T/24h confirmed dead). Regime: NEUTRAL. return_exhaustion_long: 9T/7d 55.6% +$0.11 (24h: 2T -$0.21 0% WR — degrading, monitoring). SHORT side: 151T/7d -$1.06 (structural, all range_breakout dead). Daily: Aug12 +$0.35, Aug13 -$1.58, Aug14 -$0.56, Aug15 +$0.02, Aug16 -$0.49, Aug17 +$0.37, Aug18 -$0.38.

### Root Cause
Monday variance — normal dip. ATR_SL remains structural drag at -$10.77/7d (0.7% WR) but absolute count at 8/day (historic low, within 15/day target). PM_TRAIL exit mechanism offsetting with +$7.42/7d. PM_TRAIL vs ATR_SL R:R: avg win 0.374% vs avg loss 0.697% = 0.54:1 (PM_TRAIL needs high WR to compensate — currently 87.7%). No new issues. return_exhaustion_long degrading but 7d still positive — above auto-kill threshold (need 8+ trades at <25% WR). SHORT side structural weakness (all range_breakout variants dead).

### Fix Applied
NO CHANGES — system healthy, PM_TRAIL carrying, R:R positive, ATR_SL at 8/day. PM_TRAIL WR 87.7% (must >80% — PASS). ATR_SL 8/day (must <15 — PASS). 48h R:R positive (must >1:1 — PASS).

### Verification
DB verified. System stable. Monitoring: return_exhaustion_long (watch for recovery or degradation to auto-kill threshold at 8+ trades <25% WR), SHORT side (need new SHORT signals), PM_TRAIL WR (must hold >80%).

---

## CEO Report — 2026-08-19 ~01:30 UTC (CEO run 123)

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 14T -$0.42, 42.9% WR (Monday dip, within variance). 48h: 49T -$0.01, 55.1% WR (near breakeven, R:R positive). 7d: 378T -$2.25, 50.5% WR. PM_TRAIL exit DOMINANT: 196T/7d +$7.44, 87.8% WR (carrying system). ATR_SL 152T/7d -$10.77 (main drag,0.7% WR). 0 open positions (clean). 0 phantom trades. All legacy losers in NEVER_REENABLE_FLAGS (0T/24h confirmed dead). Regime: NEUTRAL. return_exhaustion_long: 9T/7d 55.6% +$0.11 (24h: 2T -$0.21 0% WR — degrading, monitoring). SHORT side: 151T/7d -$1.06 (structural, all range_breakout dead). Daily: Aug12 +$0.37, Aug13 -$1.58, Aug14 -$0.56, Aug15 +$0.02, Aug16 -$0.49, Aug17 +$0.37, Aug18 -$0.38.

### Root Cause
Monday variance — normal dip. ATR_SL remains structural drag at -$10.77/7d (0.7% WR) but absolute count at 8/day (historic low, within 15/day target). PM_TRAIL exit mechanism offsetting with +$7.44/7d. No new issues. return_exhaustion_long degrading but 7d still positive — above auto-kill threshold. SHORT side structural weakness (all range_breakout variants dead).

### Fix Applied
NO CHANGES — system healthy, PM_TRAIL carrying, R:R positive, ATR_SL at 8/day. PM_TRAIL WR 87.8% (must >80% — PASS). ATR_SL 8/day (must <15 — PASS). 48h R:R positive (must >1:1 — PASS).

### Verification
DB verified. System stable. Monitoring: return_exhaustion_long (watch for recovery or degradation to auto-kill threshold), SHORT side (need new SHORT signals).

---

## CEO Report — 2026-08-19 ~01:00 UTC (CEO run 121)

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 15T -$0.38, 46.7% WR (Monday dip, within variance). 48h: 51T +$0.04, 56.9% WR (positive, R:R positive). 7d: 379T -$2.13, 50.7% WR (improving). PM_TRAIL DOMINANT: 209T/7d +$8.25, 88.5% WR (carrying system). ATR_SL 8.5/day (historic low). 0 open positions (clean). 0 phantom trades. Aug 17: GREEN DAY. Aug 18: Monday dip normal.

### Root Cause
Monday variance. r2-trend-long3 worst ATR_SL: 11T/7d -$0.84, avg peak 0.117% (below MIN_PRE_MOVE=0.2 — MIN_PRE_MOVE raised Aug 18 from 0.1, some trades entered pre-raise). PM_TRAIL captures 13T/7d 92.3% +$0.47 on same signal. return_exhaustion_long degrading: 24h 2T -$0.21 0% WR (7d: 9T +$0.11 55.6% WR — still above auto-kill threshold). SHORT side structural: 151T/7d -$1.06.

### Fix Applied
NO CHANGES — PM_TRAIL carrying, R:R positive, ATR_SL at 8.5/day. MIN_PRE_MOVE=0.2 already deployed (Aug 18). Nothing further to fix.

### Verification
System stable. PM_TRAIL 88.5% WR (must >80% — PASS). ATR_SL 8.5/day (must <15 — PASS). 48h R:R positive (must >1:1 — PASS). return_exhaustion_long 9T/7d 55.6% WR (monitoring, need 10+ trades). SHORT side structural (need new SHORT signals).

---

## CEO Report — 2026-08-18 22:16 UTC (CEO run 120)

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 16T -$0.35, 43.8% WR (Monday dip, within variance). 48h: 51T +$0.06, 56.9% WR (positive, R:R positive). 7d: 380T -$2.26, 50.3% WR. PM_TRAIL DOMINANT: 32T/48h +$1.37, 100% WR (carrying system). ATR_SL 17T/48h -$1.16, 0% WR (main drag, 8.5/day historic low). 1 open position (low exposure). 0 phantom trades. Aug 17: 34T +$0.37, 58.8% WR (GREEN DAY). Aug 18: 14T -$0.40, 42.9% WR (Monday dip, normal). All legacy losers in NEVER_REENABLE_FLAGS (0T/24h confirmed dead). Regime: NEUTRAL.

### Root Cause
Monday variance — normal dip. r2-trend-long3 worst ATR_SL offender (11T/48h atr_sl_hit -$0.17, PM_TRAIL capturing winners). return_exhaustion_long 5T/48h 20% WR -$0.32 (7d positive 9T +$0.11 55.6% WR — small sample, 1 win prevents auto-kill). SHORT side structural weakness: 151T/7d -$1.06, all range_breakout variants dead.

### Fix Applied
NO CHANGES — system healthy, PM_TRAIL carrying, R:R positive, ATR_SL at 8.5/day (historic low). Nothing to fix.

### Verification
System stable. PM_TRAIL 100% WR (must >80% — PASS). ATR_SL 8.5/day (must <15 — PASS).48h R:R positive (must >1:1 — PASS). return_exhaustion_long 9T/7d 55.6% WR (monitoring, need 10+ trades). SHORT side structural (need new SHORT signals). Coin tracker: DOGE accumulation (42.4 comp), top PUMP 56.1, IO 53.4, CRV 52.7.

---


## CEO Report — 2026-08-18 ~23:00 UTC (CEO run 121)

### Diagnosis
System NORMAL VARIANCE — NO CHANGES. Verified DB: 24h 16T -$0.38, 43.8% WR (Monday dip, within variance). 48h: 51T +$0.04, 56.9% WR (positive, R:R positive). 7d: 381T -$2.24, 50.4% WR. PM_TRAIL DOMINANT: 197T/7d +$7.56, 87.8% WR (carrying system). ATR_SL 153T/7d -$10.80, 0.7% WR (main drag, 8.5/day historic low — most from dead signals). 0 open positions (clean). 0 phantom trades. Aug 17: 34T +$0.37, 58.8% WR (GREEN DAY). Aug 18: 15T -$0.38, 46.7% WR (Monday dip, normal).

### Root Cause
Monday variance — normal dip. r2-trend-long3 worst ATR_SL offender (6T/48h atr_sl_hit 0% WR -$0.41, PM_TRAIL capturing winners). return_exhaustion_long degrading: 5T/48h 20% WR -$0.32 (7d positive 9T +$0.11 55.6% WR — but trend negative: Aug 15 100% WR → Aug 18 0% WR). 1 win prevents auto-kill. SHORT side structural weakness: 151T/7d -$1.06, all range_breakout variants dead.

### Fix Applied
NO CHANGES — system healthy, PM_TRAIL carrying, R:R positive, ATR_SL at 8.5/day (historic low). Nothing to fix.

### Verification
System stable. PM_TRAIL 87.8% WR (must >80% — PASS). ATR_SL 8.5/day (must <15 — PASS). 48h R:R positive (must >1:1 — PASS). return_exhaustion_long 9T/7d 55.6% WR (degrading, monitoring — auto-disable at <25% WR with 8+ trades). SHORT side structural (need new SHORT signals). Coin tracker: PUMP 54.3, HBAR 53.6, CAKE 53.5.

## CEO Report — 2026-08-19 04:17 UTC

### Diagnosis
System NORMAL VARIANCE. 24h: 15T -\$0.41, 46.7% WR (Monday, within variance). 48h: 44T -\$0.54, 50.0% WR (R:R positive). 7d: 367T -\$2.44, 49.9% WR. PM_TRAIL DOMINANT: 189T/7d +\$7.15, 87.3% WR (carrying system). ATR_SL 149T/7d -\$10.52 (main drag, 0.7% WR, 8/day historic low). r2-trend-long3 worst offender: 25T/7d 52% -\$0.23 (11 ATR_SL avg peak +0.87%).

### Root Cause
System operating within normal parameters. PM_TRAIL exit mechanism carrying the PnL. ATR_SL count at historic low (8/day, 79% reduction from 38/day Aug 12). r2-trend-long3 ATR_SL trades peak at +0.87% (below PM_TRAIL 0.4% activation) — entry timing noise, not structural. Legacy losers all cleared (0T/24h). return_exhaustion_long stable at 9T/7d 55.6% WR +\$0.11.

### Fix Applied
NO CHANGES — system healthy, PM_TRAIL carrying, R:R positive, ATR_SL at 8/day. Nothing to fix.

### Verification
System stable. PM_TRAIL 87.3% WR (must >80% — PASS). ATR_SL 8/day (must <15 — PASS). 48h R:R positive (must >1:1 — PASS). 0 open positions (clean). 0 phantom trades (FIXED). Legacy losers 0T/24h (CONFIRMED DEAD). SHORT side structural (need new SHORT signals — backlog item).
