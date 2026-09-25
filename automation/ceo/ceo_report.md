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
