# 24h Signal Quality Audit — Winners vs Losers
## May 24, 2026 | 49 trades | 36.7% WR | -$0.32 net

---

## Core Finding

```
profit-monster:  14 trades, avg +1.14%  → ALL winners
atr_sl_hit:      30 trades, avg -0.61% → ALL losers
```

All profit from profit-monster. All losses from ATR SL. ATR TP/SL system is net negative.

---

## Losing Trade Pattern (8 tokens analyzed)

| Token | Direction | Signal at Entry | z | conf | Problem |
|-------|-----------|----------------|---|---|---------|
| ONDO | LONG | zscore_pump_long | 2.44 | 73 | Consolidation — z-spike at resistance was mean-reversion, not momentum |
| SUSHI | LONG | zscore_pump_long | 2.61-3.70 | 80-88 | ALL in consolidation — repeated fires at same level |
| ADA | LONG | RS only | — | 63-75 | Pure RS without z-score = falling knife |
| GRIFFAIN | SHORT | zscore_pump_short | -4.81 | 88 | Blow-off bottom (z<-3.5) treated as bearish — was reversal setup |
| TAO | SHORT | zscore_pump_short | -2.13 to -3.16 | 80-84 | Repeated zscore fires in chop |
| LIT | SHORT | zscore_pump_short | -2.01 to -2.81 | 80-81 | Same pattern — high conf zscore in non-trending market |
| AVNT | LONG | zscore_pump_long | 2.42-4.28 | 80-88 | 4+ zscore fires in 3h — same consolidation bounce |
| CHIP | SHORT | zscore_pump_short | -2.15, -2.68 | 74-76 | Confirmed zscore in sideways chop |

### Key Observations on Losers

1. **zscore-pump fires REPEATEDLY in consolidation** — 4-10 fires over 2-4 hours, z=2.0-3.5, conf 74-88
   - No momentum confirmation (momentum_state=null, rsi=null in all signals)
   - Treats a 2.5σ bounce in a range the same as a 2.5σ spike in a trending move

2. **DIVERGENCE check didn't block blow-off bottoms** — GRIFFAIN z=-4.81 conf=88 was EXECUTED
   - DIVERGENCE_EXTREME_Z=3.5 should block, but signal went through

3. **Pure RS signals are falling knives** — ADA LONG had no zscore, only RS conf 63-75

---

## Winning Trade Pattern (6 tokens analyzed)

| Token | Direction | Signal at Entry | z | conf | What Was Different |
|-------|-----------|----------------|---|---|---|
| MON | LONG | zscore_pump_long | 2.27 | 88 | Brief single fire — not repeated. Quick clean move |
| SKY | LONG | zscore_pump_long | 2.25-3.30 | 76-84 | Sustained momentum, held 7+ hours |
| TIA | SHORT | zscore_pump_short | -3.10 | 88 | Short at resistance with momentum confirmation |
| XRP | LONG | zscore_pump_long | 2.23-3.01 | 81-85 | Brief entry window, strong clean move |
| IP | LONG | zscore_pump_long | 2.45-3.33 | 80-88 | Brief, clean — profit-monster exit |
| ENS | LONG | RS only | — | 88 | RS conf high enough alone |

Winners tend to: brief entry windows (1-2 fires), clean directional moves (not bounces).

---

## OPP/SAME Ratio — Strongest Signal Quality Indicator

Prior 83-trade analysis (60-min window around open):

| Ratio | Trades | WR | Avg PnL |
|-------|--------|-----|---------|
| Opp>>Same (ratio≥2) | 3 | 0% | -103.1% |
| Opp>Same | 20 | 30% | -31.0% |
| Opp=Same | 6 | 66.7% | +29.4% |
| Opp<Same | 50 | 46% | +24.8% |
| 0 opposing | 2 | 0% | -71.8% |

**Key: "Opp<Same but not zero" is the sweet spot. Opp=Same (balanced) has highest WR.**

---

## ATR TP/SL — Phase k-scaling is BROKEN in practice

```python
# position_manager.py line 1576:
ms = get_momentum_stats(token)
momentum_by_token[token] = ms  # or None if failed

# tpsl_utils.py line 108:
if momentum_stats is None:
    return base_k  # NO phase tightening when momentum_stats is None!
```

Every signal in SQLite: momentum_state=null, rsi_14=null, macd_hist=null.
If get_momentum_stats() returns None → base_k used → no phase k-scaling.

### ATR Floor Dominates Everything

For atr_pct=1.5%, k=1.0: raw sl_pct = 1.5%, MIN_SL_PCT = 1.0% floor → 1.0% effective.
Phase multipliers (0.01-0.07) exist but floor overrides whenever k×atr×mult < MIN_SL_PCT.

### ATR Constants (verified live 2026-05-24)

```python
ATR_SL_MIN_INIT    = 0.01    # 1.0% new trade floor (comment wrong: says 0.05%)
ATR_SL_MAX_INIT    = 0.015   # 1.5% new trade cap
ATR_SL_MIN_ACCEL  = 0.01    # 1.0% established trade floor
ATR_TP_MIN_ACCEL  = 0.015   # 1.5% established TP floor
ATR_K_LOW_VOL     = 0.5     # atr_pct < 1%
ATR_K_NORMAL_VOL  = 1.0     # atr 1-3%
ATR_K_HIGH_VOL    = 0.25    # atr > 3%
K_PHASE_ACCEL_STALL = 0.06  # stalling + accelerating
K_PHASE_ACCEL_FAST  = 0.07  # fast momentum
K_PHASE_EXH_STALL   = 0.02
K_PHASE_EXH_FAST    = 0.03
K_PHASE_EXT_STALL   = 0.01
K_PHASE_EXT_FAST    = 0.02
```

---

## Constants-Only Fixes (No Code Changes)

```python
# Signal quality
ZSCORE_PUMP_THRESHOLD = 3.0          # was 2.5 — higher threshold
ZSCORE_PUMP_LOOKBACK = 150           # was 70 — longer lookback  
ZSCORE_PUMP_COOLDOWN_BARS = 20       # was 5 — longer cooldown
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 2.5  # was 3.5 — tighter
RS_DECIDER_MIN_TOUCHES = 300         # was 200 — stricter RS levels

# ATR TP/SL  
ATR_SL_MIN_INIT = 0.015              # was 0.01 — wider 1.5% floor
ATR_SL_MAX_INIT = 0.020              # was 0.015 — wider cap
ATR_SL_MIN_ACCEL = 0.0075           # was 0.01 — tighter 0.75%
ATR_TP_MIN_ACCEL = 0.010           # was 0.015 — tighter TP
```

---

## Code Changes Needed

1. **RSI filter in zscore_pump** — require RSI > 50 for LONG, RSI < 50 for SHORT
2. **Fix momentum_stats passing** — debug why get_momentum_stats() returns None → phase bypass
3. **Block blow-off bottoms** — z < -3.5 on SHORT = reversal signal not continuation
4. **OPP/SAME ratio check in decider** — block when opposing > same-dir in 60-min window

---

## Subagent Corrections (vs main analysis)

| Metric | Main | Verified | Notes |
|--------|------|---------|-------|
| Trade count | 50 | 49 | +1 timing |
| Net PnL | -$0.14 | -$0.32 | understated |
| Win rate | 38% | 36.7% | close |
| profit-monster | 15 | 14 | close |
| atr_sl_hit | 30 | 30 | exact |
| momentum_state null | all null | computed but None in practice | not a pipeline bug |