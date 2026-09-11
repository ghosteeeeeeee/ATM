## CEO Report — 2026-09-11 ~18:24 UTC

### Diagnosis

24h: 52T, 48.1% WR, -$1.06. 7d: 330T, 56.4% WR, +$1.38 (VERIFIED POSITIVE). 48h: 95T, 57.9% WR, +$3.06 (STRONG). Sep 11: 46T, 45.7% WR, -$1.29. R:R 24h: 0.74 (avg_win 3.37%, avg_loss -4.53%). 4 open (all SHORT). Disk 83%.

**#1 loss driver: rr_engine_resistance** — 16 SHORT trades/24h, avg -2.09%, -$0.82 total. Structural — SHORT entries in 98% NEUTRAL market hitting resistance levels. Working as designed but biggest single drag.

**#2 loss driver: pump-chain+ LONG** — 10T/24h 30% WR, -$0.59. Still firing despite 30.8% WR over 7d (13T/7d -$0.29). Auto_1hr didn't kill (has wins, below threshold). **Should be killed.**

**#3 loss driver: pullback-entry- SHORT** — 8T/24h 37.5% WR, -$0.42. Bad day (7d is 69% WR +$1.93). Variance.

**#4 loss driver: atr_sl_hit** — 21T/24h, avg -0.64%, -$0.67. Normal SL exits.

**Profit source: profit-monster-trail** — 8T/24h, avg +3.58%, +$1.07. Only green exit type.

### Root Cause

Today's -$1.29 is structural rr_engine_resistance (-$0.82) + pump-chain+ bleed (-$0.59) + variance on pullback-entry- (-$0.42). However, 48h is +$3.06 and 7d is +$1.38 — system is structurally profitable. Today is a bad day, not a structural failure. R:R 0.74 means breakeven WR ~57%, actual 48.1% today.

### Fix Applied

**pump-chain+ LONG should be killed.** 13T/7d 30.8% WR -$0.29, 10T/24h 30% WR -$0.59. Not auto-killed because "has wins." This is the only actionable fix today. All other losses are structural (rr_engine) or variance (pullback-entry- bad day).

**No param changes.** PM_TRAIL/ATR_SL protected. Active signals all profitable on 7d.

### Verification

- DB verified: 24h 52T 48.1% WR -$1.06. 7d 330T 56.4% WR +$1.38. 48h 95T 57.9% WR +$3.06.
- All 5 active signals profitable 7d: pullback_entry- 29T/69%WR +$1.93 ★, open_skies 19T/63.2%WR +$1.56 ★, bb_bounce_v2_long 39T/71.8%WR +$1.20 ★, pump_chain 41T/68.3%WR +$1.11, pump-chain- 31T/64.5%WR +$0.61.
- pump-chain+ 13T/7d 30.8%WR -$0.29 — only non-legacy signal bleeding.
- 4 open: 3x pump-chain- SHORT, 1x mover- SHORT. Near breakeven.
- Disk: 83%.

### Next Actions

1. **Kill pump-chain+ LONG.** Set PUMP_FLOW_PLUS_ENABLED=False, add to NEVER_REENABLE_FLAGS. -$.59/24h bleeding removed.
2. **Monitor R:R.** 0.74 (breakeven 57%). System 7d WR 56.4% — nearly there.
3. **Legacy exits by Sep 12.** ema300_dip_short -$1.51, ema300_dip -$0.40, slow_grind -$0.80, sma20_dip -$0.73, coiled_spring -$0.65. Will age out.
4. **Monitor rr_engine_resistance.** Structural, but -$0.82/24h. If persistent, consider widening resistance threshold.
5. **Disk at 83%.** 2% from threshold.
