---
name: trend-signal-backtest
description: Backtest trend-following signals (ADX+DI, MACD acceleration) against Hermes candle database. Used to evaluate new signal types before implementation in signal_gen.py.
tags: [backtest, trend-following, macd, adx, signal-evaluation]
---

# Trend Signal Backtest Skill

## Purpose
Backtest trend-following signal theories against historical candle data before implementing in signal_gen.py. Tests ADX+DI and MACD acceleration approaches.

## Usage
```bash
cd /root/.hermes
python3 scripts/backtest_adx_macd.py
```

## Key Findings (2026-04-19)

### ADX+DI: NOT VIABLE
- WR consistently ~42-44% — worse than random
- Too many false signals in ranging markets
- ADX filter doesn't meaningfully improve MACD results
- Discard completely — do not use for trend filtering

### MACD Acceleration: VIABLE (Two Separate Regimes)

#### 1h+: LONG Side Works
Standard MACD(12,26,9) histogram crossing zero:

| Config | Hold | LONG WR | LONG Avg | N | SHORT WR | SHORT Avg |
|--------|------|---------|----------|---|----------|----------|
| MACD(12,26,9) | 8h | **55.6%** | **+0.49%** | 3262 | 53.9% | +0.10% |
| MACD(12,26,9) | 24h | **55.6%** | **+0.64%** | 3113 | 51.3% | +0.05% |

**Standard MACD(12,26,9) beats crypto-fast. LONG side is significantly stronger on 1h+.**

#### 1m/5m/15m: SHORT Side Works, LONG is Broken
On sub-1h timeframes, the LONG side consistently breaks (WR 33-45%, negative avg returns).
SHORT side is viable. Tested on 17 tokens, ~82hrs each:

| Config | Hold | SHORT WR | SHORT Avg | N |
|--------|------|----------|----------|---|
| MACD(3,8,3) | 50m | **53.3%** | **+0.48%** | 11k |
| MACD(3,8,3) | 60m | **53.3%** | **+0.59%** | 11k |
| MACD(3,10,5) | 60m | 52.9% | +0.56% | 7.5k |
| MACD(2,6,3) | 60m | 53.4% | +0.56% | 12k |

## Implementation Spec

### 1h MACD (Primary — LONG viable)
```
Signal type: 'macd_accel'
Sources: 'macd-accel+' (LONG), 'macd-accel-' (SHORT)
Logic:
  1. MACD(12,26,9) histogram crosses zero
  2. Histogram accelerating in direction of cross (slope > 0 over 4-bar lookback)
  3. Confidence: base 55, scale with acceleration (cap ~70)
  4. Forward window: 8h for signal count vs quality balance
```

### 1m MACD (Secondary — SHORT only)
```
Signal type: 'macd_accel'
Source prefix: 'macd-accel-'
Logic:
  1. MACD(3,8,3) histogram crosses below zero (SHORT only)
  2. Max hold: 50-60 bars (50-60 min)
  3. Confidence: 55 (WR edge ~53% vs 50% random)
  4. WARNING: Data is thin (~3 days, 19 tokens) — treat as experimental
```

## Data Source & Limitations
- **DB:** `/root/.hermes/data/candles.db`
- **Tables:** `candles_1m`, `candles_15m`, `candles_1h`, `candles_4h`
- **1h:** 170 tokens, ~96 days (2026-01-13 to 2026-04-19) — FULLY Viable
- **1m:** 19 tokens, ~3 days — THIN, statistically weak
- **15m:** ~14 days per token — marginal
- **Columns:** token, ts (unix), open, high, low, close, volume

## Speed Optimization: Pre-computed EMAs
Sub-1h backtests require computing EMAs per bar per token — O(n²) and times out.
**Fix:** Pre-compute full EMA series once, then test forward windows in seconds:

```python
# Pre-compute all EMAs once per token
ema_fast = ema(closes, fast)   # e.g., 3
ema_slow = ema(closes, slow)    # e.g., 8
ml = [f-s for f,s in zip(ema_fast, ema_slow)]
ema_sig = ema(ml, sig)          # e.g., 3
h = [m-s for m,s in zip(ml, ema_sig)]

# Now test all forward windows in seconds
for fwd in [5, 10, 15, 20, 30, 45, 60]:
    longs, shorts = [], []
    start = slow + sig + 1
    for i in range(start+1, len(h)):
        h_now = h[i]; h_prev = h[i-1]
        fi = i + fwd
        if fi >= len(closes): continue
        if h_prev <= 0 < h_now:
            longs.append((closes[fi] - closes[i]) / closes[i])
        elif h_prev >= 0 > h_now:
            shorts.append((closes[i] - closes[fi]) / closes[i])
```

Full working script: `/root/.hermes/scripts/backtest_adx_macd.py`

## Critical Finding (Updated 2026-04-20)

### SHORT Dominance Is NOT a Regime Artifact

The MACD sub-1h finding said SHORT dominance was "likely regime artifact."
**This is WRONG.** Independent EMA cross backtest (2026-04-20) confirms SHORT dominance across ALL pairs
on 163 tokens, 3+ months of 1m data, exit-on-reverse methodology:

| Pair | Signals | Long P&L | Short P&L | Net |
|------|---------|----------|-----------|-----|
| 5/50 | 29K | -1800% | **+6784%** | +4984% |
| 8/50 | 22.8K | -2219% | **+6434%** | +4214% |
| 12/50 | 18.8K | -2280% | **+6392%** | +4112% |
| 20/50 | 14.6K | -2396% | **+6328%** | +3932% |
| 20/200 | — | -697% | **+196%** | -501% |

Longs are catastrophic across ALL pairs in this dataset. Shorts work. The asymmetry is structural.

**Practical implication:** When designing a new MA-type signal on sub-1h timeframes, default to SHORT only.
If both directions are needed, test them separately and let results decide — do not assume symmetry.

## Critical Bugs Found During Implementation

### Bug 1: ADX Rolling Computation is Expensive
Computing ADX at every bar for 170 tokens × 800 candles = ~136,000 ADX computations. **This times out.**

**Fix:** Only compute ADX at signal crossover points (on-demand):
```python
def compute_adx_at(highs, lows, closes, idx, period=14, window=200):
    start = max(1, idx - window)
    # ... compute ADX only for this window
```

### Bug 2: MACD Index Alignment
`compute_macd(closes[:i])` must align with the correct candle index. Store results in a dict keyed by
index, not by position in the MACD array.

```python
macd_data = {}
for i in range(SLOW+SIG, len(closes)):
    r = compute_macd(closes[:i], FAST, SLOW, SIG)
    if r: macd_data[i] = r[2][-1]  # key by closes index, not array position
```

### Bug 3: 1m Data is Thin
Only ~3 days of 1m data per token. Backtest results on 1m have wide confidence intervals.
Do not over-index on 1m backtest results for production decisions.

## Data Source
- **DB:** `/root/.hermes/data/candles.db`
- **Tables:** `candles_1m`, `candles_15m`, `candles_1h`, `candles_4h`
- **Tokens:** 170 | **Period:** ~96 days (2026-01-13 to 2026-04-19)
- **Columns:** token, ts (unix), open, high, low, close, volume

## Files
- `/root/.hermes/scripts/backtest_adx_macd.py` — full backtest script

## Related
- rsi-backtest: mean-reversion signal evaluation
- mtf-macd-backtest-findings: existing MTF-MACD results
- surfing-gap-analysis: compare Surfing philosophy against live signals
