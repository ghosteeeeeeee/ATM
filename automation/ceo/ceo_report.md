## CEO Report — 2026-08-15 (latest run)

### Diagnosis
System flat/positive, eval windows closing tomorrow. Verified DB: 24h 57T +$0.07 (49.1% WR — FLAT). 7d 459T -$1.36 (51.0% WR). Exit-type R:R 0.38:1 (PM_TRAIL avg +0.29% vs ATR_SL avg -0.76%) — still inverted. Overall R:R 1.23:1 (avg win +0.64% vs avg loss -0.52%) — healthy. 3 open $0 flat. 48h exits: ATR_SL 48T -$3.67 (dominant loss), profit-monster-trail 70T +$2.08, profit-monster-T1 12T +$0.69. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 +$0.20 (recovering).

### Root Cause
Exit-type R:R inverted because ATR_SL trades (-0.76% avg) dominate losses while PM_TRAIL trades (+0.29% avg) capture only 38% of that magnitude. The 0.40% trailing activation helps but many trades reverse before reaching it. This is structural — eval windows need final data before further tuning.

### Fix Applied
NO CHANGES — eval windows close tomorrow (Aug 17). 6 eval windows active: PM_TRAIL 0.60% act/0.50% dist, ATR_TP_K_MULT 2.5, TRAIL_ACT 0.40%, SIGNAL_FILTER_SPEED_MIN 30, COIN_TRACKER_HOT_MIN_COMPOSITE 45. Changing now invalidates results. System positive 2 consecutive days (Aug 15 +$0.20, Aug 16 partial +$0.25).

### Verification
24h 57T +$0.07 (49.1% WR) — flat, acceptable. 7d stars intact: return_exhaustion_long 3T 100% +$0.39, hzscore+,mover+ 5T 80% +$0.17, r2-trend-long2 17T 64.7% +$0.19, bb_bounce+ 22T 63.6% +$0.25, ct-hot+ 20T 60.0% +$0.27. Legacy losers closing: wave_catcher+ 8T 37.5% -$0.42, range_breakout+ 8T 25% -$0.41, trend_momentum 6T 16.7% -$0.37 (all disabled). Coin tracker: BTC comp=58.0 accumulation BULL, DOGE comp=57.6, SOL comp=56.1.

### Next Actions
1. **Aug 17 (TOMORROW):** Evaluate all 6 windows. CRITICAL: exit-type R:R must ↑ from 0.38:1. If still <0.5:1 → widen ATR_SL_MIN 1.0%→1.25% (gives trades more room before SL hit)
2. **Post-eval:** If R:R still inverted → lower PM_TRAIL_ACTIVATE_PCT or tighten entry filters
3. **Monitor:** ct-hot+ WR (must >55%), daily trades (must stay >30T), coin_tracker signals
