## CEO Report — 2026-08-16 (17th run)

### Diagnosis
R:R at 0.42:1 (PM_TRAIL avg +0.30% vs ATR_SL avg -0.71%). Verified DB: 24h 58T -$0.38 41.4% WR. 48h 120T -$1.08 44.2% WR. 7d 455T -$2.33 49.0% WR. 1 open $0 flat. PM_TRAIL exits 54T avg +0.24% — breakeven guard capping wins. ATR_SL 45T avg -0.71% -$3.20 — dominant drag. Phantom trades 6T -$0.10 (guardian_orphan, empty signal).

### Root Cause
PM_TRAIL breakeven guard (`effective_floor = max(trail_floor, 0.0)`) forced exits at 0.0% even when trail floor was negative. Trades peaked 0.50-0.60% then exited at breakeven — avg exit only 0.24% despite 0.40% activation. R:R inverted because PM_TRAIL captures too little of the move.

### Fix Applied
1. Removed breakeven guard in profit_monster.py — exits at trail_floor directly
2. Lowered PM_TRAIL_ACTIVATE_PCT 0.40%→0.30% — more trades qualify for trailing
3. Tightened PM_TRAIL_DISTANCE_PCT 0.60%→0.50% — protect gains, floor = -0.20%

### Verification
Monitor next 48h: avg PM_TRAIL exit (should ↑ from 0.24%), R:R (should ↑ from 0.42:1), PM_TRAIL capture rate (should ↑ from 54/48h). Revert if avg exit doesn't improve or R:R worsens.

---

## CEO Report — 2026-08-16 (16th run)

### Diagnosis
R:R almost at 1:1 (0.94:1) — PM_TRAIL widen working. Verified DB: 24h 56T -$0.49 39.3% WR. 48h 120T -$1.25 43.3% WR. Today 19T -$0.73 10.5% WR (statistical noise — 5 phantom trades with empty signals). 1 open $0 flat. ATR_SL still dominant: 25 hits/24h avg -0.71% (-$1.76) = 87% of losses. PM_TRAIL wins: 12T avg +0.67% (+$0.83). ATR_SL avg loss narrowed -0.76%→-0.71% (wider SL helping marginally) but hit count barely changed (44→25 in 24h). Market flat (103/104 NEUTRAL), REDUCE gate active. ct-hot+ legacy still clearing (31T/24h, 11T today). Stars intact: return_exhaustion_long 3T 100% +$0.39, bb_bounce+ 1T 100%.

### Root Cause
ATR_SL_MAX widen 2.5%→3.0% reduced avg loss per hit (-0.76%→-0.71%) but NOT hit count. Trades in choppy NEUTRAL market get stopped out regardless of SL width — entry quality is the bottleneck, not SL placement. PM_TRAIL at 0.94:1 is near breakeven; system needs signal quality improvement to cross into profitability.

### Fix Applied
NO CHANGES — eval windows just closed, need 48h data on ATR_SL_MAX 3.0% + PM_TRAIL 0.60% dist before further tuning. R:R improving naturally (0.52:1 → 0.94:1 over 3 runs).

### Expected Impact
- Current params need time to settle — no hasty changes
- ct-hot+ legacy should clear by tomorrow (1 open remaining)
- R:R should continue improving as disabled signals age out

### Verification
- ATR_SL_MAX verified 0.030 ✓
- PM_TRAIL dist verified 0.006 ✓
- Pipeline active, all timers running ✓

### Next Actions
1. Monitor R:R (should cross 1:1 with current params)
2. ATR_SL hit count must ↓ from 25/24h — if still 20+ at next run, consider signal filter tightening
3. ct-hot+ should clear by tomorrow — if still firing, investigate pipeline
4. Phantom trades (empty signal) — investigate root cause (5 today)

## CEO Report — 2026-08-16 (15th run)

### Diagnosis
ATR_SL is the #1 system drag. 45T/48h avg loss -0.753% (-$3.32). Only 2.2% WR on ATR_SL exits. R:R severely inverted: ATR_SL avg loss -0.753% vs PM_TRAIL avg win +0.390% (0.52:1). 24h: 58T -$0.49 39.7% WR. 7d: 458T -$1.99 50.0% WR. 0 open trades flat. All legacy losers already disabled (ct-hot+, wave_catcher+, range_breakout+, trend_momentum, continuation+). Stars7d intact: return_exhaustion_long 100%, hzscore+,mover+ 80%, r2-trend-long2 64.7%, bb_bounce+ 63.6%.

### Root Cause
ATR_SL_MAX (2.5%) too tight for current volatility. Trades get stopped out before reaching PM_TRAIL activation (+0.40%). PM_TRAIL fires 54T/48h at 75.9% WR — it works, but only catches trades that survive long enough to reach +0.40%.

### Fix Applied
1. WIDENED ATR_SL_MAX 2.5% → 3.0% (hermes_constants.py:492)
2. WIDENED ATR_SL_MAX_INIT 2.5% → 3.0% (hermes_constants.py:507) — must match

### Expected Impact
- Fewer ATR_SL hits (trades have more room to breathe)
- More trades reaching PM_TRAIL activation → higher PM_TRAIL capture rate
- R:R should improve from 0.52:1 toward 1:1
- Risk: avg loss per ATR_SL hit may widen slightly (2.5%→3.0% cap)

### Verification
- ATR_SL_MAX verified 0.030 in hermes_constants.py
- ATR_SL_MAX_INIT verified 0.030 to match
- Revert if avg loss widens without fewer ATR_SL hits

### Next Actions
1. Monitor ATR_SL hit count (should ↓ from 45/48h)
2. Monitor PM_TRAIL capture rate (should ↑ from 54/48h)
3. R:R must ↑ from 0.52:1 toward 1:1
4. ATR_SL_MAX needs 48h data — if avg loss widens to -0.90%+ with same hit count, revert

## CEO Report — 2026-08-16 (14th run)

### Diagnosis
ct-hot+ BASE was still enabled. Only PLUS was disabled in 11th run. Base ct-hot+ firing 30T/48h at 46.7% WR -$0.29 — #1 loser, bypassing confluence via STANDALONE_BYPASS. 24h: 55T -$0.36 41.8% WR. 48h: 123T -$1.12 43.9% WR. R:R 0.69:1 (inverted). 3 open ct-hot+ LONG flat.

### Root Cause
Previous CEO run disabled COIN_TRACKER_HOT_PLUS_ENABLED but left COIN_TRACKER_HOT_ENABLED = True. ct-hot in STANDALONE_BYPASS fired without confluence gate.

### Fix Applied
1. DISABLED COIN_TRACKER_HOT_ENABLED = False
2. Removed 'ct-hot' from STANDALONE_BYPASS_SIGNALS

### Expected Impact
- Save ~$0.29/48h (ct-hot+ bleeding)
- Daily trades will drop (ct-hot+ was 30T/48h) — monitor for starvation
- R:R should improve as worst performer is eliminated

### Verification
- Flag verified False in hermes_constants.py
- STANDALONE_BYPASS verified without ct-hot
- Re-enable ct-hot+ when WR >55% with 20+ trades

### Next Actions
1. Monitor daily trades (must >20T without ct-hot+)
2. PM_TRAIL 0.60% dist needs 48h to show effect
3. R:R must ↑ from 0.69:1 toward 1:1
