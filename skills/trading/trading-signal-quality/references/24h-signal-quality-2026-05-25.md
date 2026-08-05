# 24h Signal Quality Deep Dive (2026-05-25)

## Summary Stats
30 trades | 14W/15L/1 flat | NET +$0.07 | avg +0.03%

| Exit Reason | Count | Avg PnL | WR |
|-------------|-------|---------|----|
| profit-monster | 13 | +1.01% | 100% |
| atr_sl_hit | 16 | -0.76% | 7% (only AXS SHORT) |

## Big Winners — What They Had in Common

| Token | Dir | PnL% | RS Touches | Regime | Signal |
|-------|-----|------|-----------|--------|--------|
| TIA | LONG | +1.25% | 546 | LONG_BIAS | rs-s546,zscore-pump+ |
| ME | SHORT | +1.11% | 560 | NEUTRAL | rs-r560,zscore-pump- |
| ENS | SHORT | +1.09% | 1934 | LONG_BIAS | rs-r1934,zscore-pump- |
| CAKE | SHORT | +1.08% | 148 | LONG_BIAS | rs-r148,zscore-pump- |
| AVAX | LONG | +1.06% | 4295 | LONG_BIAS | rs-s4295,zscore-pump+ |
| LINEA | LONG | +0.95% | 552 | LONG_BIAS | rs-s552,zscore-pump+ |
| GALA | LONG | +0.95% | 1296+2793 | LONG_BIAS | rs-s1296,rs-s2793,zscore-pump+ |
| ETH | LONG | +0.95% | 306 | LONG_BIAS | rs-s306,zscore-pump+ |

**Common factors:**
- RS support touches 300+ for LONG, OR RS resistance touches 500+ for SHORT (ENS 1934)
- All exits via profit-monster (TP +1%)
- 4h regime mostly LONG_BIAS — market momentum was UP

## Losses — What They Had in Common

| Token | Dir | PnL% | RS Touches | Regime | Signal |
|-------|-----|------|-----------|--------|--------|
| ZK | SHORT | -1.32% | 128 | SHORT_BIAS | rs-r128,zscore-pump- |
| BCH | LONG | -1.24% | 72+96 | NEUTRAL | rs-s72,rs-s96,zscore-pump+ |
| OP | SHORT | -1.13% | 116 | LONG_BIAS | rs-r116,zscore-pump- |
| ADA | SHORT | -1.01% | 156 | LONG_BIAS | rs-r156,zscore-pump- |
| ETH | SHORT | -0.98% | 8745 | LONG_BIAS | rs-r8745,zscore-pump- |
| CHIP | SHORT | -0.81% | 184 | NEUTRAL | rs-r184,zscore-pump- |
| LINEA | SHORT | -0.66% | 176 | LONG_BIAS | rs-r176,zscore-pump- |

**Common factors:**
- RS resistance touches 40-200 (WEAK) for SHORT signals
- Counter-regime SHORT in LONG_BIAS market (ETH SHORT, OP SHORT, ADA SHORT)
- All exits via atr_sl_hit

## RS Touch Count Thresholds — Clear Discontinuities

### LONG (support touches) — SOLID
```
touch  >= 40:   n=14, 57% WR, avg +0.31%
touch  >= 80:   n=13, 62% WR, avg +0.39%
touch  >= 100:   n=10, 70% WR, avg +0.59%
touch  >= 150:   n=9,  78% WR, avg +0.68%
touch  >= 200:   n=7,  86% WR, avg +0.87%  <- optimal threshold
touch  >= 300:   n=6,  83% WR, avg +0.86%
touch  >=1000:   n=2, 100% WR, avg +1.00%
```

### SHORT (resistance touches) — BROKEN
```
touch  >= 40:   n=16, 38% WR, avg -0.21%
touch  >= 100:   n=14, 29% WR, avg -0.32%
touch  >= 200:   n=8,  38% WR, avg -0.08%
touch  >= 300:   n=7,  43% WR, avg +0.05%
touch  >= 400:   n=6,  50% WR, avg +0.22%
```

## zscore-pump Direction Asymmetry

```
ZSCORE_LONG (zscore-pump+): n=14, 57% WR, avg +0.31%
ZSCORE_SHORT (zscore-pump-): n=16, 38% WR, avg -0.21%
```

LONG side is much stronger. zscore-pump+ works; zscore-pump- is catching falling knives.

## Regime Alignment — Surprising Result

```
REGIME-ALIGNED (4h LONG_BIAS + LONG direction): 8W/10L, 44% WR
COUNTER-REGIME (LONG_BIAS + SHORT direction):    6W/6L,  50% WR
```

Counter-regime SHORT trades won as often as aligned trades (50% vs 44%), and had better
per-trade PnL (winners at +1.02-1.10% vs aligned losers at -0.66 to -0.88%).

**BUT**: Level quality matters more than regime. Counter-regime winners (ENS=1934 touches,
CAKE=148 touches) were at well-established resistance. Counter-regime losers (ETH=8745,
OP=116, ADA=156) were at weak or massively-overestimated levels.

## signal_z_score Not Recorded — Pipeline Gap

All signal_z_score, signal_rsi_14, signal_macd_hist, _signal_metadata fields = NULL/empty in DB.
The z-score value computed by zscore_pump.py is NOT being passed through to the trade record.
Fix: where hl-sync-guardian.py or brain.py creates the trade, pull z_score from add_signal() output.

## Constants Recommendations

### High-priority
```python
RS_MIN_TOUCHES = 150          # was 8 — biggest lever for SHORT side
ZSCORE_PUMP_THRESHOLD = 3.5  # was 3.0 — tighten SHORT to reduce false entries
ZSCORE_PUMP_LOOKBACK_SHORT = 200  # separate SHORT lookback
```

### Low-priority
```python
RS_DECIDER_ZBONUS_TOUCHES = 100  # was 50 — require more before z-score bonus
RS_LONG_MIN_TOUCHES = 100     # minimum for LONG side
```

## See Also
- references/24h-signal-quality-deep-dive-2026-05-24.md — prior OPP/SAME ratio findings
