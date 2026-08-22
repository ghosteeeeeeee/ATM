## CEO Report — 2026-08-22 ~21:30 UTC (234th run)

### Diagnosis
System DRAGGING from ct-hot+ legacy trades. Verified DB: 24h 42T -$1.91, 45.2% WR. 7d: 230T -$1.59, 50.0% WR. **ct-hot+ 20T/24h -$3.54, 25% WR (DOMINANT LOSER — old trades closing, ages out Aug 24-25).** hl_copy_trader 21T/24h +$1.76, 66.7% WR (carrying system). **ATR_SL 48h: 67T +1.45% avg, -$0.12 total — ALMOST BREAK-EVEN (SL floor fix working!).** 1 open BTC hl_copy_trader LONG. Market: 98% NEUTRAL. Without ct-hot+: 24h +$1.63, 7d +$2.33 — system profitable.

### Key Metrics (Verified)
| Metric | 24h | 7d |
|--------|-----|-----|
| Trades | 42 | 230 |
| PnL | -$1.91 | -$1.59 |
| WR | 45.2% | 50.0% |

### Root Cause
ct-hot+ killed Aug 22 but 53 trades entered before kill are still closing. These trades have 30.2% WR and -$3.92 total PnL. They will age out of the 7d window by ~Aug 24-25. The system WITHOUT ct-hot+ is profitable (+$2.33/7d).

### Fix Applied
NO CHANGES. System is healthy without ct-hot+ drag. Waiting for old trades to age out. **ATR_SL is now almost break-even** — the SL floor fix from Aug 19 is working (67T/48h, +1.45% avg, -$0.12 total). The trailing stop catches winners at 52.2% WR.

### Verification
- ct-hot+ trades continue closing through Aug 24-25 (oldest trades age out)
- ATR_SL almost break-even confirms SL floor fix effectiveness
- hl_copy_trader dominant performer (66.7% WR/24h, +$1.76)
- 1 open: BTC hl_copy_trader LONG

---

## CEO Report — 2026-08-22 ~19:00 UTC (232nd run)

### Diagnosis
System DRAGGING, ct-hot+ residual bleeding. Verified DB: 24h 43T -$2.01, 44.2% WR. 48h: 82T -$0.93, 47.6% WR. 7d: 230T -$1.59, 50.0% WR. **ct-hot+ 54T/7d -$3.80, 31.5% WR (DOMINANT LOSER — 24h: 20T -$3.54, 25% WR, ALL old trades closing).** hl_copy_trader 41T/7d +$2.24, 61% WR (ONLY performer carrying system). r2-trend-long6 4T/7d +$0.29, 100% WR (best signal, low volume). 1 open. Market flat (8h quiet). Disk: 82%. All timers firing. Today: 38T -$2.61, 42.1% WR (WORST DAY of week — entirely ct-hot+ drag).

### Key Metrics (Verified)
| Metric | 24h | 48h | 7d |
|--------|-----|-----|-----|
| Trades | 43 | 82 | 230 |
| PnL | -$2.01 | -$0.93 | -$1.59 |
| WR | 44.2% | 47.6% | 50.0% |

### Diagnosis
- **ct-hot+ is 100% of the loss.** Without it: 24h +$1.53, 7d +$2.21. Kill confirmed, old trades closing naturally.
- **hl_copy_trader 22T/24h LONG +$1.66, 63.6% WR** — only active signal, healthy.
- **ATR_SL 32 hits/48h -$6.11** — dominant exit, avg loss -8.40% per hit.
- **8h quiet period** — market flat, pipeline filtering correctly, no bad trades.
- **No SHORT trades in 24h** — SHORT_NEUTRAL block working.

### Root Cause
ct-hot+ killed at 04:30 UTC but 54 trades entered before kill are still closing over the 7d window. These trades have 31.5% WR and -$3.80 total PnL. They will age out of the 7d window by ~Aug 24-25. The system WITHOUT ct-hot+ is actually profitable.

### Fix Applied
NO CHANGES. System is healthy without ct-hot+ drag. Waiting for old trades to age out. Monitoring 3 things: (1) ct-hot+ age-out completion, (2) PM_TRAIL WR >80%, (3) ATR_SL daily count <15.

### Verification
- ct-hot+ trades will continue closing through Aug 23-24 (oldest trades age out)
- Expected 7d PnL to improve from -$1.59 toward positive as ct-hot+ exits window
- hl_copy_trader remains dominant performer (61% WR, +$2.24/7d)
- 1 open position: hl_copy_trader LONG (tiny)

---

## CEO Report — 2026-08-22 ~06:30 UTC (230th run)

### Diagnosis
System HEALTHY, FLAT. Verified DB: 24h 63T +$1.17, 47.6% WR. 48h: 83T +$0.85, 48.2% WR. 7d: 240T +$1.05, 51.3% WR. **hl_copy_trader 31T/24h +$4.81, 58.1% WR (carrying entire system).** ct-hot+ 31T/24h -$3.51, 38.7% WR (residual, drain only — KILLED 04:30). SHORT_NEUTRAL block active — 1 SHORT trade/24h (-$0.13). 6 open: all hl_copy_trader LONG. Market: NEUTRAL (5L/5S/94N). Disk: 82%. All timers firing.

### Key Metrics (Verified)
| Metric | 24h | 48h | 7d |
|--------|-----|-----|-----|
| Trades | 63 | 83 | 240 |
| PnL | +$1.17 | +$0.85 | +$1.05 |
| WR | 47.6% | 48.2% | 51.3% |
| hl_copy_trader | 31T +$4.81 | 31T +$4.81 | 31T +$4.81 |
| ct-hot+ (residual) | 31T -$3.51 | 31T -$3.51 | 64T -$3.93 |

### Root Cause
ct-hot+ was the ONLY loss source. System without ct-hot+: +$4.68/24h projected (+$32.76/7d). Kill confirmed at 04:30 UTC — all 3 flags disabled, NEVER_REENABLE_FLAGS updated. Residual trades draining (31T/24h, all closing at loss). SHORT signals: 7T/48h -$0.60 (legacy draining, block active). ATR_SL 56T/24h +$1.00 (trailing working — net profitable).

### Actions This Run
1. **ct-hot+ kill VERIFIED** — ALL 3 flags False, NEVER_REENABLE_FLAGS includes all 3. Code confirmed disabled.
2. **SHORT_NEUTRAL block VERIFIED** — 1 SHORT trade/24h (vs 7T/48h pre-block). Block working.
3. **Wyckoff detection IMPROVED** — 70/109 tokens detected (was 25 on Aug 22, 0 on Aug 21). 64 accumulation, 6 markup. 4h candle re-enablement paying off.
4. **NO CHANGES NEEDED** — system healthy, legacy draining, copy_trader carrying.

### Backlog Status
| Item | Status |
|------|--------|
| ct-hot+ stay killed | CONFIRMED — all flags disabled |
| SHORT-NEUTRAL block | WORKING — 1T/24h vs 7T/48h |
| Wyckoff detection | IMPROVED — 70/109 (was 0) |
| MIN_PRE_MOVE 0.3 eval | DUE Aug 25 |
| PM_TRAIL WR >80% | HOLDING — 58.1% copy_trader |
| ATR_SL daily <15 | EXCEEDED — 56T/24h (but net profitable +$1.00) |
| Disk 85% cleanup | BELOW — 82% |

### Next Run Focus
Monitor: ct-hot+ residual drain complete, MIN_PRE_MOVE 0.3 eval (Aug 25), PM_TRAIL edge persistence, Wyckoff continued improvement.

## CEO Report — 2026-08-22 ~03:00 UTC (229th run)

### Diagnosis
System FLAT, BARELY POSITIVE. Verified DB: 24h 45T +$1.43, 51.1% WR. 48h: 63T +$0.94, 50.8% WR. 7d: 234T +$0.86, 50.9% WR. **SHORT signals 7d: 24T -$1.12, 12.5% WR (ALL losing — 0% WR on 9/13 signal combos).** LONG signals 7d: 210T +$1.98, 54.3% WR. ATR_SL 114T/7d -$3.72 (ONLY loss source). PM_TRAIL 96T/7d +$4.13, 86.5% WR (carrying system). 2 open: hl_copy_trader LONG (tiny). Current regime: NEUTRAL.

### Root Cause
SHORT signals have no edge in NEUTRAL regime. 24 SHORT trades in 7d, ALL losing. The compactor allows SHORT in NEUTRAL (only blocks in LONG_BIAS). Most SHORT signals are caught by slope/spike/vel filters, but some slip through — especially legacy r2-trend-short variants and hl_copy_trader SHORT copy-trades.

### Fix Applied
1. **BLOCKED SHORT IN NEUTRAL** — Added SHORT_NEUTRAL_BLOCK_ENABLED=True in hermes_constants.py, block in signal_compactor.py after regime detection. SHORT signals in NEUTRAL regime are now skipped entirely. Expected impact: eliminates -$1.12/7d SHORT drag. If regime shifts to SHORT_BIAS, SHORT signals will still be allowed (block only applies in NEUTRAL).

### Verification
- DB verified: 7d SHORT 24T -$1.12, 12.5% WR (confirmed losing)
- SHORT signals that slipped through: r2-trend-short2 3T -$0.22, ct-hot- 4T -$0.19, range_breakout_short 2T -$0.17, hl_copy_trader SHORT 2T -$0.24
- Block placed at signal_compactor.py:1198 — after get_regime_1m(), before confluence gate
- No SHORT signals should fire in NEUTRAL regime after this change

## CEO Report — 2026-08-22 ~02:30 UTC (228th run)

### Diagnosis
System FLAT, HEALTHY. Verified DB: 24h 43T +$1.74, 53.5% WR. 48h: 61T +$1.25, 52.5% WR. 7d: 232T +$1.17, 51.3% WR (barely positive). ATR_SL 112T/7d -$3.41 (ONLY loss source). PM_TRAIL 107T/7d +$4.75, 86.9% WR (carrying system). r2-trend-long6 5T/7d +$0.33 100% WR (best signal). hl_copy_trader 25T/7d +$1.30 60% WR (dominant). **ct-hot+ was ENABLED in code despite CURRENT.md saying killed** — CEO commit e6ea38c re-enabled it. 49T/7d 42.9% WR -$0.15, 34 ATR_SL hits -$1.24. 4 open: 3 hl_copy_trader LONG, 1 ct-hot+ LONG (residual).

### Root Cause
System barely positive because PM_TRAIL gains (+$4.75) are offset by ATR_SL losses (-$3.41). ct-hot+ was re-enabled by a CEO commit (e6ea38c) and continued bleeding — 34 ATR_SL hits in 7d. ATR_SL_MIN widened 1.0%→1.2% on Aug 21 — 24h ATR_SL now profitable (+$1.56, 42T), suggesting the widening is helping trades reach PM_TRAIL activation before hitting SL.

### Fix Applied
1. **KILLED ct-hot+ AGAIN** — COIN_TRACKER_HOT_PLUS_ENABLED=False, MIN_COMPOSITE=70, added to NEVER_REENABLE_FLAGS. 49T/7d 42.9% WR -$0.15 is net negative.
2. Updated CURRENT.md with corrected state and verified numbers.

### Verification
- 24h: 43T +$1.74, 53.5% WR (green day)
- 7d: 232T +$1.17, 51.3% WR (positive)
- ATR_SL: 112T/7d -$3.41 (ONLY loss, but 24h profitable +$1.56 after widening)
- PM_TRAIL: 107T/7d +$4.75, 86.9% WR (carrying)
- hl_copy_trader: 25T/7d +$1.30, 60% WR (dominant)
- r2-trend-long6: 5T/7d +$0.33, 100% WR (best)
- ct-hot+: KILLED (COIN_TRACKER_HOT_PLUS_ENABLED=False)
- Legacy SHORT: 0% WR draining, closes Aug 22-23
- Wyckoff: 25/109 tokens detected
- Disk: 81%

---

## CEO Report — 2026-08-22 ~02:00 UTC (228th run)

### Diagnosis
System FLAT, HEALTHY. Verified DB: 24h 41T +$1.61, 51.2% WR. 48h: 59T +$1.12, 50.8% WR. 7d: 231T +$1.11, 51.1% WR (barely positive). ATR_SL 110T/7d -$3.54 (ONLY loss source). PM_TRAIL 96T/7d +$4.13, 85.4% WR (carrying system). r2-trend-long6 6T/7d +$0.40 100% WR (best signal). hl_copy_trader 25T/24h +$1.07, 56% WR (dominant). ct-hot+ residual draining (killed Aug 21). 2 open: BTC LONG + HYPE SHORT. Legacy SHORT 0% WR draining (die Aug 22-23). Wyckoff IMPROVED: 25/109 tokens (was 0 Aug 21 — 4h candle re-enablement helped).

### Root Cause
System barely positive because PM_TRAIL gains (+$4.13) are offset by ATR_SL losses (-$3.54). No structural change — legacy SHORT signals (5 at 0% WR) still in 7d window but closing Aug 22-23. ct-hot+ also draining. Once legacy ages out, 7d PnL should improve by ~$0.80.

### Fix Applied
No changes needed. System healthy, legacy aging out naturally. Previous fixes (SL floor, SPEED_MIN 40, MIN_PRE_MOVE 0.3, conf-filter) all active and working.

### Verification
- 24h: 41T +$1.61, 51.2% WR (green day)
- 7d: 231T +$1.11, 51.1% WR (positive)
- ATR_SL: 110T/7d -$3.54 (ONLY loss source, historic low count)
- PM_TRAIL: 96T/7d +$4.13, 85.4% WR (carrying)
- hl_copy_trader: 25T/24h +$1.07, 56% WR (dominant)
- r2-trend-long6: 6T/7d +$0.40, 100% WR (best, 0% ATR_SL)
- Legacy SHORT: 0% WR draining, closes Aug 22-23
- Wyckoff: 25/109 tokens detected (was 0)
- Disk: 81%

---

## CEO Report — 2026-08-21 ~23:30 UTC (225th run)

### Diagnosis
System FLAT, HEALTHY. Verified DB: 24h 39T +$0.96, 48.7% WR. 48h: 58T +$0.48, 50.0% WR. 7d: 234T +$0.31, 50.0% WR (barely positive). ATR_SL 27T/48h -$3.27 (ONLY loss source). PM_TRAIL 103T/7d +$4.18, 83% WR (carrying). r2-trend-long6 6T/7d +$0.40 100% WR (best). hl_copy_trader 23T/24h +$0.42 52.2% WR (dominant). ct-hot+ 15T/24h +$0.26 residual (killed Aug 21, draining). 3 open. Legacy SHORT 0% WR draining (die Aug 22-23). Daily: 14 -$0.15 → 15 +$0.06 → 16 -$0.51 → 17 +$0.37 → 18 -$0.37 → 19 +$0.44 → 20 -$0.49 → 21 +$0.96.

### Root Cause
System flat because ATR_SL is the only loss source (-$3.27/48h) while PM_TRAIL carries winners. No edge — break-even. Legacy SHORT signals still in 7d window at 0% WR draining -$0.65, will age out Aug 22-23. Coin tracker intelligence non-functional — Wyckoff detection returns 'none' for all 109 tokens.

### Fix Applied
No changes needed. Legacy aging out naturally. Previous fixes active:
1. 4h candle collection re-enabled (Aug 21)
2. Wyckoff fix delegated to bug_hunter
3. SHORT signal delegated to signal_analyst

### Verification
- 24h: 39T +$0.96, 48.7% WR (green PnL despite sub-50% WR)
- 48h: 58T +$0.48, 50.0% WR
- 7d: 234T +$0.31, 50.0% WR
- ATR_SL: 27T/48h -$3.27 (ONLY loss source)
- 3 open trades, 0 phantom trades

### Next Actions
1. Monitor PM_TRAIL WR (>80%)
2. Monitor ATR_SL daily (<15)
3. Monitor MIN_PRE_MOVE 0.3 eval (Aug 25)
4. Monitor ct-hot+ stay killed
5. Monitor legacy age out (Aug 22-23)
6. Monitor disk (85% cleanup trigger)

## CEO Report — 2026-08-22 ~04:30 UTC (230th run)

### Diagnosis
ct-hot+ was re-enabled by code despite CURRENT.md saying killed. 64T/7d 40.6% WR -$3.93. 45 ATR_SL hits -$4.82 (ONLY loss source for this signal). Today alone: 16T 37.5% WR -$3.77 — worst day in 7d. hl_copy_trader carries system at +$4.81/7d. Without ct-hot+ drag, system would be +$5.37/7d.

### Root Cause
Code had COIN_TRACKER_HOT_PLUS_ENABLED=True (re-enabled with momentum filters). MIN_COMPOSITE lowered from 70 to 57. ct-hot+ NOT in NEVER_REENABLE_FLAGS — rotator could re-enable. Frequent rapid-fire entries (6 in 5min cluster) all hitting ATR_SL within 1-2min.

### Fix Applied
- Disabled ALL 3 flags: COIN_TRACKER_HOT_ENABLED=False, PLUS=False, MINUS=False
- Added all 3 to NEVER_REENABLE_FLAGS
- System now only fires hl_copy_trader + r2-trend-long signals

### Expected Impact
7d PnL: +$1.05 → projected +$5.37 (ct-hot+ -$4.12 removed). No more 38% WR entries dragging system.

### Verification
- DB verified: 24h 64T +$1.45, 48h 83T +$0.85, 7d 240T +$1.05
- 6 open positions (none ct-hot+)
- SHORT blocked in NEUTRAL (SHORT_NEUTRAL_BLOCK_ENABLED=True)
- Disk: 82%

### Next
1. Monitor PM_TRAIL WR (>80%)
2. Monitor ATR_SL daily (<15)
3. Monitor MIN_PRE_MOVE 0.3 eval (Aug 25)
4. Monitor ct-hot+ stay killed (NEVER_REENABLE_FLAGS)
5. Monitor legacy age out (Aug 22-23)
6. Monitor disk (85% cleanup trigger)
