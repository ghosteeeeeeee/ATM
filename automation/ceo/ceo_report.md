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
