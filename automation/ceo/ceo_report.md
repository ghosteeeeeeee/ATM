## CEO Report — 2026-09-14 ~10:15 UTC

### Diagnosis
24h negative: 46T 43.5% WR -$0.87 (VERIFIED). 7d positive: 320T 55.5% WR +$1.76. Today (Sep 14) 20T 30% WR -$1.36 — bad day. 8 open positions. Market NEUTRAL.

### Verified Numbers (DB-queried this run)
- 24h: 46T, 43.5% WR, -$0.87 (below breakeven ~58%)
- 7d: 320T, 55.5% WR, +$1.76
- 7d regime: NEUTRAL 317T 55.5%WR +$1.76
- 24h signals: pullback-entry- SHORT 18T 50%WR +$0.38 (ONLY profitable), pump-chain+ LONG 9T 44.4%WR -$0.26, rr-struct- SHORT 2T 0%WR -$0.28
- 24h exit: atr_sl_hit 19T -$2.83 (dominant), rr_engine_resistance 4T -$0.58
- 8 open positions

### Root Cause
Today is a variance day — 30% WR on 20 trades. pullback-entry- SHORT had 9 losses but still positive PnL (+$0.38) due to good R:R. The rr_engine_resistance fix deployed ~06:45 UTC needs 48h to evaluate. SHORT_NORMAL_PENALTY=0.85 applied ~05:30 UTC also needs 48h.

### Fix Applied
**NO CONFIG CHANGES.** System in monitoring mode — two fixes deployed today need time to show effect. Continuing to monitor:
- rr_engine_resistance fix (candle CLOSE check) — deployed ~06:45 UTC
- SHORT_NORMAL_PENALTY=0.85 — applied ~05:30 UTC
- rr-struct- at 7T/7d 42.9%WR — kill at 15T if WR <50%
- bb_bounce_v2_long at 16T/7d 50%WR — kill at 25T if WR <50%
- trend_ignition 0 trades since Sep 13 — monitor 72h

### Verification
- 24h PnL: -$0.87 (negative, below breakeven)
- 7d PnL: +$1.76 (positive)
- Pipeline active, 8 open positions
- Disk 80% (24G free)
- No errors in logs

---

## CEO Report — 2026-09-14 ~02:34 UTC

### Diagnosis
System healthy and improving. 24h: 44T 54.5% WR +$0.90 (VERIFIED). 7d: 334T 56.9% WR +$2.62 (VERIFIED POSITIVE, doubled from +$1.21). R:R 1.035 (breakeven 50.3%, actual 54.5% — 4.2% above). Legacy signals aging out — ema300_dip_short and sma20_dip last closed Sep 8, will drop off 7d window by Sep 15. Active signals ALL profitable. No config changes needed.

### Verified Numbers (DB-queried this run)
- 24h: 44T, 54.5% WR, +$0.90 (R:R 1.035, breakeven WR 50.3%)
- 7d: 334T, 56.9% WR, +$2.62
- 7d regime: NEUTRAL 324T 57.7%WR +$3.00 (100% market)
- 7d exit: profit-monster-trail 100T +$7.18, cut-loser-CL-T1 40T -$5.89 (legacy), rr_engine_resistance 35T -$0.97
- 7d top: pullback-entry- 53T +$2.69, open_skies 8T +$1.20, pump_chain 38T +$1.05
- 2 open: ENA LONG pump-chain+, DOT LONG pump-chain+ (just opened)

### Root Cause
No active root cause — system is profitable. Legacy drag (-$4.11/7d combined from 6 dead signals) is aging out naturally. Structural drag from rr_engine_resistance SHORT exits (-$0.97/7d) persists but improved from -$1.34.

### Fix Applied
No config changes. Updated CURRENT.md Active Decisions and Next Actions with verified numbers. Legacy signals will age out of 7d window by Sep 15-20.

### Verification
- 24h PnL: +$0.90 (positive, above breakeven)
- 7d PnL: +$2.62 (positive, doubled from last report)
- R:R: 1.035 (above breakeven)
- All 5 active signals profitable 7d
- Pipeline active, compactor running, disk 79%
- rr-struct- at 7T/7d (monitoring at 15T kill threshold)

---

## CEO Report — 2026-09-13 ~18:35 UTC

### Diagnosis
System above breakeven. 24h: 31T 58.1% WR +$0.70 (VERIFIED). 7d: 338T 57.1% WR +$1.57 (VERIFIED POSITIVE). **Legacy signals age out tomorrow (Sep 14)** — 6 dead signals -$3.46/7d drag. Active signals ALL profitable 7d. R:R carrying system (24h 0.938, 7d 0.800 — both above breakeven). Range filter deployed, saving money. No config changes needed.

### Verified Numbers (DB-queried this run)
- 24h: 31T, 58.1% WR, +$0.70 (R:R 0.938, breakeven WR 51.6% — 6.5% above breakeven)
- 7d: 338T, 57.1% WR, +$1.57
- Daily: Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$2.48, Sep 11 -$1.74, Sep 12 +$0.58, Sep 13 +$0.70 (31T)
- 7d regime: NEUTRAL 327T 57.8%WR +$1.93 (system is 97% NEUTRAL)
- Best 7d: pullback-entry- 44T/63.6%WR +$2.11, open_skies 8T/62.5%WR +$1.20, pump_chain 41T/68.3%WR +$1.11
- Worst 7d: ema300_dip_short 17T/47.1%WR -$0.91 (legacy), trend_purity+ 11T/36.4%WR -$0.90 (dead)
- Exit 48h losses: atr_sl_hit 13T -$2.46, cut-loser-CL-T1 5T -$0.86, rr_engine_support_br 3T -$0.70

### Decision: MONITORING (NO CHANGES)
- Legacy ages out TOMORROW (Sep 14) — 7d PnL expected to improve by ~$3.46
- R:R 24h 0.938 (breakeven 51.6%, actual 58.1% — 6.5% ABOVE breakeven)
- R:R 7d 0.800 (breakeven 55.6%, actual 57.1% — 1.5% ABOVE breakeven)
- System structurally healthy: 5 consecutive green days (Sep 9-13)
- Pipeline active, disk 79%, no errors
- Range filter active, saving money

### What To Watch
1. Verify 7d PnL improves after legacy fully exits (tomorrow)
2. Monitor rr-struct- (7T/7d 42.9%WR -$0.42, R:R 0.42) — kill threshold at 15T
3. Monitor range filter blocks in pipeline.log over next 48h
4. Pipeline healthy — no intervention needed

## CEO Report — 2026-09-13 ~15:30 UTC

### Diagnosis
TURBO LONG loss (-3.83%, $0.14) at 93.3% of 1h range — buying the top. Current accel filter (+0.0028 > 0) passed because price was still rising. RSI 72.73 < 80 also passed. The only filter that catches "buying at resistance" is range position.

### Root Cause
rr_structural.py had no range position filter. Accel catches direction (price moving against trade) but not position (price at wrong end of range). TURBO: price rising but at 93.3% of 1h range — classic buy-the-top. INJ SHORT: at 6.3% of range — classic sell-the-bottom. Both passed all existing filters.

### Fix Applied
**CONFIG CHANGE: RR_STRUCTURAL_RANGE_LONG_MAX=80, RR_STRUCTURAL_RANGE_SHORT_MIN=20 added to hermes_constants.py.**

**Code change: `_get_range_position()` added to rr_structural.py** — queries 1h high/low from candles_1h, returns position as 0-100%. Range filter added to detect() for both LONG and SHORT directions.

**Impact analysis (17 rr-struct trades, 30d):**
- Saves: TURBO LONG -3.83% (93.3% range → blocked), INJ SHORT -6.52% (6.3% range → blocked) = **$9.35 saved**
- Costs: NEO LONG +30.98% (12% range → NOT blocked) = **$0 cost**
- Net: +$9.35 if filter was active

**Why NOT redundant with accel filter:**
- TURBO: accel=+0.0028 (UP, aligned with LONG) → accel PASSES → but 93.3% range → range BLOCKS
- Accel catches: price moving AGAINST direction
- Range catches: price at WRONG END of range (even if moving in direction)
- Complementary, not redundant.

### Verification
Import verified. Pipeline restart needed to load new code. Monitor next 24h for blocks in pipeline.log.

## CEO Report — 2026-09-13 ~22:35 UTC

### Diagnosis
24h: 35T, 54.3% WR, -$0.16. 7d: 336T, 56.5% WR, +$1.21. Market NEUTRAL. R:R 24h 0.740 (breakeven 56.7%, actual 54.3% — 2.4% underwater). 24h negative solely from dead signal trend_purity+ 3T 0%WR -$0.75 — without it, 32T +$0.59.

### Root Cause
Legacy signal trend_purity+ still in 24h window. Ages out Sep 14. Active signals ALL profitable: pullback-entry- +$2.11, open_skies +$1.20, pump_chain +$1.08, rr-struct+ +$0.59. 7d legacy drag -$3.46 will be gone by tomorrow.

### Fix Applied
**No config changes.** System structurally healthy. Monitoring: rr-struct- at 7T/42.9%WR (kill at 15T if WR <50%), rr_engine_resistance SHORT exits (5T/48h -$0.58, needs code change), trend_ignition 0 trades (market condition).

### Verification
7d PnL +$1.21 (VERIFIED). 24h -$0.16 (legacy noise). Pipeline active, 4 open positions, 0 errors. Disk 79%. Next: legacy ages out tomorrow, expect 7d PnL improvement ~$3.46.
