---
name: ma-cross-sep-tuning
description: Empirically tune the minimum EMA separation threshold (MIN_SEP_PCT) for MA crossover signals in Hermes. Tests SEP ranges, fast/slow combos, timeframes, and hold durations to find profitable signal configurations. Used when adding new MA cross signals or re-tuning existing ones.
tags: [hermes, signal-tuning, backtesting, ma-cross, ema]
triggers:
  - tune ma cross sep threshold
  - find optimal MIN_SEP_PCT for crossover
  - test new MA cross signal viability
  - ma cross firing too often
  - ma cross not profitable
related_skills:
  - per-token-signal-implementation  # wire new signals into pipeline after tuning
  - signal-backtest-methodology      # general backtest principles
---

# MA Crossover SEP Tuning — Empirical Methodology

## What This Is

When an MA crossover signal fires too often (low SEP), or is unprofitable, this skill provides the systematic backtest methodology to find the right minimum EMA separation (MIN_SEP_PCT) threshold. The key finding: SEP tuning is non-obvious — higher SEP doesn't always mean better profitability. You must test the full landscape.

## The Critical Discovery

**MA crossover signals on 5m candles are unprofitable at ALL SEP values tested** (0.10%–3.0%), across multiple fast/slow combos, with both early-exit and fixed-hold strategies. The existing ma_cross_signals.py (EMA 10×200 on **1m**) with SEP=0.05% and 12m hold IS profitable (+0.276% avg, WR=40.4%, n=52).

This means:
- 5m timeframe is too slow for MA cross — signal fires after the move is already exhausted
- 1m timeframe works better
- Lower SEP (more signals) can be more profitable than high SEP (fewer signals) if the additional signals have positive average PnL

## Backtest Framework

### Test Parameters

```python
# SEP range — must test fine-grained values (don't skip around)
SEPS = [0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30, 0.50, 0.75, 1.0, 1.5, 2.0, 3.0]

# Fast/slow combos (in candle units)
COMBOS = [
    (3, 15), (3, 20),   # very fast
    (5, 20), (5, 30),
    (6, 30), (8, 30), (8, 50),
    (10, 30), (10, 50), (10, 100),
    (12, 50), (12, 80),
]

# Hold durations
HOLDS = [3, 6, 12, 20, 30]  # in minutes (or candle units)
```

### Key Metrics Per Combo

Always report:
- `n` — signal count (need n≥10-15 for statistical significance)
- `WR%` — win rate
- `avg%` — average PnL per trade (the primary metric; positive = profitable)
- `avgW%` — average winner size
- `avgL%` — average loser size
- `big%` — % of trades with >1-2% gain (big moves caught)

### The Ratio That Matters

```
profitability ≈ WR * avgW / avgL
```

If avgW ≈ avgL, you need WR > 50% to be profitable.
If avgW > avgL significantly, lower WR can still be profitable.

## Step-by-Step Tuning Process

### Step 1 — Test Raw SEP Distribution First

Before testing combos, get the raw SEP distribution with fixed hold (12 candles):

```python
# For each SEP threshold, count all trades above that SEP
# This shows how n decays as SEP increases
# Look for where avg transitions from negative to positive
```

### Step 2 — Test Across Multiple Combos

Test all COMBOS × SEPS × HOLDS. Use sorted output by `avg` descending.

### Step 3 — Test Timeframes Separately

Test 1m and 5m separately — they have very different signal profiles:
- 1m: more signals, faster crosses, less lag
- 5m: fewer signals, more lag, slower confirmation

### Step 4 — Don't Use Early Exit in Backtest

Guardian handles stop-loss in live trading. Backtest with pure fixed hold to measure signal quality accurately.

## Success Criteria

A viable signal needs:
1. **avg > 0** (profitable per trade)
2. **n ≥ 10** (enough signals to trust the avg)
3. **avgW > avgL** in magnitude (winners bigger than losers) OR **WR > 50%**

If all three hold, it's worth wiring into the pipeline.

## Common Failure Modes

| Failure | Symptom | Cause |
|---------|---------|-------|
| All SEP negative | avg always < 0 | Signal is fundamentally unprofitable on this timeframe |
| High SEP only works | n too small at profitable SEP | Not enough signals — needs different EMA combo |
| Early exit kills returns | avgW drops when exit early | Guardian handles exits; backtest with fixed hold |
| Winners ≈ losers but WR < 50% | consistently ~45% WR | Signal is slightly negative; try lower timeframe |

## Files

- Backtest scripts: `/root/.hermes/scripts/sep_backtest.py`, `/root/.hermes/scripts/fast_ma_sweep.py`, `/root/.hermes/scripts/1m_fast_ma_sweep.py`, `/root/.hermes/scripts/ma_cross_1m_dist.py`
- Live signal: `/root/.hermes/scripts/ma_cross_signals.py` (1m EMA 10×200)
- 5m signal (unprofitable): `/root/.hermes/scripts/ma_cross_5m.py`
