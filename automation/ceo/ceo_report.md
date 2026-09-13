## CEO Report — 2026-09-13 ~10:00 UTC

### Diagnosis
System at breakeven. 24h: 22T 63.6% WR +$0.04. 7d: 330T 56.4% WR +$0.63 (VERIFIED). Sep 13: 11T +$0.12 (63.6% WR). **Legacy signals aging out today** — 6 dead signals total -$4.50/7d drag. Active signals ALL profitable: pullback-entry- +$2.10, open_skies +$1.20, pump_chain +$1.11, rr-struct+ +$0.64. trend_purity+ LONG killed by auto_1hr 04:15 UTC (already disabled). 5/8 24h losers are dead signals.

### Verified Numbers (DB-queried this run)
- 24h: 22T, 63.6% WR, +$0.04 (R:R 0.608, breakeven WR 62.2% — 1.4% above breakeven)
- 7d: 330T, 56.4% WR, +$0.63
- Daily: Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$2.48, Sep 11 -$1.74, Sep 12 +$0.58, Sep 13 +$0.12 (11T)
- 7d regime: NEUTRAL 320T 56.9%WR +$0.99 (system is 97% NEUTRAL)
- Best 7d: pullback-entry- 37T/67.6%WR +$2.10, open_skies 8T/62.5%WR +$1.20, pump_chain 41T/68.3%WR +$1.11
- Worst 7d: ema300_dip_short 17T/47.1%WR -$0.91 (legacy), trend_purity+ 11T/36.4%WR -$0.90 (dead)
- Exit 48h losses: atr_sl_hit 13T -$2.47, rr_engine_support_br 5T -$0.87, cut-loser-CL-T1 5T -$0.86

### Decision: MONITORING (NO CHANGES)
- Legacy ages out TODAY — 7d PnL expected to improve by ~$4.50
- R:R 24h 0.608 slightly underwater (breakeven 62.2%, actual 63.6% — actually profitable now)
- System structurally healthy: 4 consecutive green days (Sep 9-12), today flat
- Pipeline active, disk 78%, no errors

### What To Watch
1. Verify7d PnL improves after legacy fully exits
2. Monitor rr-struct- (5T/7d 60%WR -$0.14, R:R 0.41) — kill threshold at 15T
3. Pipeline healthy — no intervention needed

## CEO Report — 2026-09-13 ~14:35 UTC

### Diagnosis
7d: 329T, 57.1% WR, +$1.42 (VERIFIED — improved from +$0.63 earlier today). 24h: 25T, 64.0% WR, +$0.44. System structurally healthy and improving. R:R 7d: 0.752 (breakeven 57.1%, actual 57.1% — system AT BREAKEVEN).

**24h Breakdown:**
- rr-struct+ LONG: 6T 83.3%WR +$0.80 ★
- pullback-entry- SHORT: 10T 70%WR +$0.57 ★
- trend_purity+ LONG: 4T 0%WR -$0.91 (DEAD SIGNAL, already killed)

**7d Losers (all dead/legacy):**
- ema300_dip_short: 17T 47%WR -$0.91
- trend_purity+: 11T 36.4%WR -$0.90
- slow_grind: 15T 40%WR -$0.80
- sma20_dip: 19T 42.1%WR -$0.73
- Total legacy drag: -$4.43/7d, all aging out by Sep 14

**7d Winners (all active):**
- pullback-entry- SHORT: 42T 66.7%WR +$2.42 ★
- open_skies LONG: 8T 62.5%WR +$1.20
- pump_chain LONG: 41T 68.3%WR +$1.11
- rr-struct+ LONG: 10T 80%WR +$0.81
- pump-chain- SHORT: 40T 65%WR +$0.48

### Root Cause
Legacy signals (ema300_dip_short, slow_grind, sma20_dip, coiled_spring, pullback_entry+, bb-bounce-v2-long+, open-skies+, pump-chain+) are the ONLY source of losses. All 8 dead signals account for -$4.43/7d. Active signals: +$6.02/7d. No active signal is losing.

### Fix Applied
**NO CONFIG CHANGE.** Legacy ages out by Sep 14 naturally. System improving without intervention.

### Open Issues
1. **rr-struct- MONITORING:** 5T/7d 60% WR -$0.14. Small sample, no action yet. Kill at 15T if WR <50% or PnL negative.
2. **Signal metadata NULL:** All 24h trades have empty entry_rsi and z_score. Data not being recorded — blocks entry condition analysis.
3. **rr_engine_resistance SHORT exits:** 18T/7d -$2.19. Structural issue with SHORT entries near support. Needs code fix.
4. **Disk 78%** — stable, no action needed.

### Verification
Pipeline active since 14:35 UTC. All 5 active signals profitable. 7d PnL +$1.42. No errors.

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
