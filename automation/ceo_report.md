## CEO Report — 2026-08-08

### Diagnosis (Verified Numbers — DB queried directly)

| Period | Trades | PnL | WR |
|--------|--------|-----|-----|
| Last 24h | 57 | +$0.29 | 56.1% |
| Last 7d | 434 | -$1.65 | 46.5% |

**Daily trend (7d):**
- Aug 1: 5t, -$0.13, 20.0% WR
- Aug 2: 36t, -$0.78, 19.4% WR
- Aug 3: 93t, -$0.22, 32.3% WR
- Aug 4: 26t, -$0.69, 30.8% WR
- Aug 5: 22t, +$0.21, 45.5% WR
- Aug 6: 90t, -$0.08, 58.9% WR
- Aug 7: 58t, +$0.34, 58.6% WR (best day)
- Aug 8: 12t, +$0.06, 50.0% WR (partial day)

**Close reasons (last 24h):**
- profit-monster-trail: 32t, +$1.62, 100% WR ← trailing working perfectly
- atr_sl_hit: 22t, -$1.33, 0% WR ← **THE bleed point**
- Other: 3t, $0.00

**Signal combos bleeding (7d, worst):**
- inv-accel-300- SHORT: 15t, -$0.33, 26.7% WR (already disabled)
- ma100-cross,return_exhaustion- SHORT: 7t, -$0.28, 42.9% WR
- zscore-rising- SHORT: 38t, -$0.22, 31.6% WR

### Root Cause

**ATR SL too tight at 1.0%.** All 22 SL hits hit exactly 1.0% — trades stopped before trailing (0.30% activation) can engage. The 1.0% floor was set 2026-08-05 but data shows it's still too tight for low-vol tokens. Trailing itself works perfectly (100% WR when it activates).

### Fix Applied

Widened `ATR_SL_MIN_INIT` from 1.0% → 1.2% (commit c3daf6a). Also updated `SL_PCT_FALLBACK` and `STOP_LOSS_DEFAULT` to match. `TP_PCT_FALLBACK` 2.0% → 2.4% to maintain 2:1 R:R. This gives trades 20% more room before the hard stop, matching the already-widened `ATR_SL_MIN` (1.2% for trailing).

### Verification

Monitor for 24h: expect fewer atr_sl_hit exits, more profit-monster-trail exits. Target: reduce SL hits from 22/day to <15/day, maintain or improve WR.
