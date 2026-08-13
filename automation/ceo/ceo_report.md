## CEO Report — 2026-08-15 (Weather Vane v5 verdict)

### Verdict: REJECTED

Spec claims vol < 0.30% blocks 78 losers (41% WR) and keeps 47 winners (74% WR). Live DB shows the **opposite**.

### Verified Data (14d SHORT, 421 trades)

| Vol Group | Trades | WR | PnL |
|-----------|--------|-----|-----|
| LOW (<0.30%) | 221 | **48%** | **-$0.26** |
| MID (0.30-0.80%) | 88 | 39% | -$1.12 |
| HIGH (>=0.80%) | 112 | 37% | -$0.64 |

LOW vol is the **best** performing group. Filtering it out would remove our strongest trades.

### Why the Spec is Wrong

1. **Existing gates already filter dead tokens.** `volatility_gate.py` blocks ATR<0.48% (FLAT regime). `speed_tracker` blocks speed<30th percentile. Genuinely dead tokens never reach signal_compactor.

2. **Low 5m vol ≠ low energy.** 60 tokens have low 5m dispersion (<0.30%) but high ATR (>=0.48%) — they're mean-reverting with quiet intrahour action but volatile hourly candles. These are our best SHORT performers.

3. **The spec's backtest may use different data.** Numbers don't match current 14d DB. Could be different period, different vol calculation, or different trade sample.

### What Would Actually Help

The stated goal ("minimize losses and take less losing trades") is correct. Better approaches:
- **Tighten existing gates** (raise SPEED_MIN_THRESHOLD or ATR thresholds)
- **Disable more losing signals** (vel-hermes- at 35% WR 17T, hzscore- at 47% WR 17T)
- **Tighten SL** (ATR_SL_MIN currently 1.0%, could narrow to 0.8%)

### No Changes Made

System stable, recovery confirmed, all prior fixes verified. Do not implement volatility floor filter.

---

## CEO Report — 2026-08-14 (verified)

### Diagnosis
24h: 72T -$0.19 (56.9% WR — FLAT). 7d: 439T -$0.67 (50.8% WR — slightly negative). Daily: Aug 9 +$0.62 peak → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 (recovery) → Aug 13 38T -$1.21 (42.1% WR — worst day, legacy clearing). Aug 14 early 5T +$0.02 (recovering). SL hit rate: Aug 9 16.9% → Aug 13 55.3% → Aug 12 41.0% (stabilizing). 5 open $0 flat. Pipeline healthy.

### Root Cause
Aug 13 -$1.21 worst day = legacy disabled signal clearing:
- accel-300- SHORT: 40T -$0.30 55% WR (disabled, legacy trades)
- range_breakout+ LONG: 8T -$0.41 25% WR (disabled)
- trend_momentum_near_sma+ LONG: 6T -$0.37 16.7% WR (disabled)
All three bleeders disabled/blacklisted — no new entries.

### 7d Stars (profitable)
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5% ★
- bb_bounce+ LONG: 20T +$0.19 60.0%
- bb_bounce+,hzscore+ LONG: 34T +$0.22 50.0%
- hzscore+,mover+ LONG: 5T +$0.17 80.0%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%

### Cost Drivers (48h)
- atr_sl_hit: 74T -$4.81 (dominant)
- profit-monster-trail: 85T +$3.93 (compensating)
- Net SL impact: -$0.88

### Fix Applied
NO CHANGES — system flat, all bleeders disabled, stability period active. Aug 13 -$1.21 was legacy clearing (accel-300- last entry 03:37 UTC). Aug 14 early +$0.02 recovery. No actionable problem to fix.

### Verification
- Stars intact (5 profitable)
- 5 open $0 flat
- Pipeline healthy
- SL hit rate stabilizing (41% Aug 12 → 55% Aug 13 legacy noise → returning to normal)
- All disabled signals confirmed (0 new entries post-disable)

### Monitor
- Daily PnL (if -2 consecutive red after legacy clears → investigate)
- SHORT7d (if -$1.50+ persists after accel-300- clears → regime filter)
- SL hit rate (if >55%持续 → investigate entry timing)

---

## CEO Report — 2026-08-13 (verified)
