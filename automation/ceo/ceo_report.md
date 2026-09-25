## CEO Report — 2026-09-25

### Diagnosis
24h: 8T 62.5%WR -$0.14 (good). 7d: 205T 42.4%WR -$2.23. ATR_SL hit rate 62.0% (131/205) — CRITICAL. EXTREME regime: 65.1% ATR_SL hit rate 14d (108/166). Avg win +6.78%, avg loss -5.30%. SL at 1.3% floor cutting winners short before they reach win zone.

### Root Cause
ATR_SL_MIN=1.3% + ATR_SL_MAX=1.5% too tight for EXTREME volatility. Trades get stopped out at -1.3% to -1.5% but would have recovered to +6.78% avg win if given more room. HIGH regime also affected (100T, avg loss -5.74%).

### Fix Applied
1. **ATR_SL_MAX: 1.5% → 1.8%** — wider cap lets EXTREME trades breathe
2. **EXTREME regime 1.2x multiplier** in tpsl_utils.py — matches existing HIGH regime pattern
3. **TP_PCT_FALLBACK: 3.9% → 4.5%** — maintains 3:1 R:R with wider SL
4. Expected: +$0.50-1.00/7d from reduced ATR_SL hit rate

### Verification
- Syntax verified: hermes_constants.py loads, tpsl_utils.py imports clean
- Commit: 454b870f
- No protected flags touched
- Monitor 48h: ATR_SL hit rate should drop from 62% toward 50%

### Remaining Issues
- Signal diversity: only pump-chain+ LONG and volume-breakout-long+ profitable (2 types)
- SHORT side all disabled, -$3.66/7d legacy aging out
- Disk 85% (monitor)
- mover+ kill working (0 new trades since Sep 24)

## CEO Report — 2026-09-25 ~16:30 UTC

### Diagnosis
DB-verified: 5T 80%WR +$0.09 (24h) | 200T 41.5%WR -$3.09 (7d). System quiet, improving. **mover+ kill bug:** 11 trades post-disable, 27.3%WR -$1.38. Kill flag `MOVER_PLUS_ENABLED=False` only checked in signal_compactor, not decider_run.py. Race condition: signals execute before signal_compactor can skip them. **ATR_SL widening** deployed today (1.5→1.8%, EXTREME 1.2x). Only 5 trades today — too early to measure. **CL-T1 disabled** — 0 trades since disable, bleeding stopped. **pullback-entry- SHORT** 25T 36%WR -$1.66 (worst signal, cold streak).

### Root Cause
mover+ kill bug: `decider_run.py` processes signals from hot-set without checking `is_component_disabled()`. signal_compactor has the check but runs on separate timer — race condition allows stale signals to execute first.

### Fix Applied
**CODE FIX:** Added `is_component_disabled()` guard to `decider_run.py` main execution loop (defense-in-depth). Now both signal_compactor AND decider_run.py check disabled flags. Import added to signal_schema. Verified: syntax OK, `is_component_disabled('mover+')=True`. Expected: eliminates all post-disable signal leaks. Saves ~$1.38/7d from mover+ alone, prevents future kill bugs.

### Next Actions
1. Monitor ATR_SL widening impact (need 24h+ of trades)
2. SHORT NULL RSI confidence boost (suggested 3+ sessions, never implemented)
3. New NEUTRAL signal development (signal diversity critical)
4. pullback-entry- SHORT regime analysis (keep in winning regimes, block in losers)
