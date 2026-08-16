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
