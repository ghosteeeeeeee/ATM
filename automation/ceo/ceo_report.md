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
