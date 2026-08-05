---
name: signal-backtest-methodology
description: Systematic backtest methodology for building and validating new trading signals in Hermes — multi-pair sweeps, survival analysis, exit-on-reverse-cross, per-token breakdowns, directional asymmetry, counter-trend vs trend-following variants, and dataset-size awareness.
tags: [backtest, signal-development, trading, methodology, counter-trend, mean-reversion]
category: trading
author: Hermes Agent
created: 2026-04-20
---

# Signal Backtest Methodology

Systematic approach for building and validating new trading signals in Hermes. Used to discover ma_fast (8/50 SHORT only) and r2_trend (R² regression SHORT only).

## When to Use

- Building a new signal (MA cross variants, regression, Bollinger, RSI variants, etc.)
- Testing if an existing signal should be LONG/SHORT only or both directions
- Discovering that one direction of a symmetric signal is catastrophic (common in bear markets)
- Finding the right EMA pair / window / threshold for a new indicator

## Core Principle: Survival Analysis First

**Always test exit-on-reverse-cross before fixed TP/SL exits.**

Fixed TP/SL exits create misleading win rates — reversals get classified as TP/SL hits, inflating WR but destroying P&L. Exit-on-reverse-cross gives realistic P&L because:
- A cross that reverses in 5 bars = small loss
- A cross that survives 500 bars = large gain (captured)
- TP at 1% clips winners that would have returned 10%

## Step-by-Step Process

### Step 1: Define the Signal Hypothesis

Before writing code, articulate:
- What does the signal detect? (EMA cross, regression slope, Bollinger break, etc.)
- What timeframe? (1m, 5m, 15m, 1h — test on what you have)
- LONG/SHORT or both?
- Entry trigger: what exact condition?
- Exit trigger: reverse of entry condition (preferred) or fixed TP/SL?

### Step 2: Build the Backtester

```python
def backtest_signal(closes, entry_fn, exit_fn):
    """
    closes: list of close prices, oldest first
    entry_fn(i): returns True if we should enter at candle i
    exit_fn(i): returns True if we should exit at candle i (after entry)
    Returns list of P&L percentages.
    """
    n = len(closes)
    trades = []
    in_pos = False
    entry_price = 0

    for i in range(n):
        if not in_pos:
            if entry_fn(i):
                in_pos = True
                entry_price = closes[i]
        else:
            if exit_fn(i):
                pnl = (closes[i] - entry_price) / entry_price * 100
                trades.append(pnl)
                in_pos = False

    return trades
```

### Step 3: Multi-Pair / Multi-Parameter Sweep

Test across parameter ranges, not single values. Example for EMA cross:

```python
pairs = [(5,50), (8,50), (12,50), (20,50), (20,100), (20,200), (50,100), (50,200)]
for fp, sp in pairs:
    longs, shorts = backtest_ema_cross(closes, fp, sp)
    net_long = sum(longs)
    net_short = sum(shorts)
```

Always test **both directions separately** — asymmetry is common.

### Step 4: Per-Token Breakdown

After finding a promising parameter set, break down by individual token:

```python
for tok in tokens:
    longs, shorts = backtest(closes[tok])
    # Track: n trades, WR%, net P&L, avg P&L, pos_sum, neg_sum
```

This reveals which tokens drive the P&L. SAGA (+119% on shorts) vs AVAX (+20%) is meaningful.

### Step 5: Survival Analysis

Test whether the signal's separation/predictive factor correlates with survival time:

```python
# For each cross: record separation_pct, bars_before_reverse
# Group by sep bucket: 0-0.1%, 0.1-0.2%, 0.2-0.5%, 0.5-1.0%, >1%
# Report median survival bars per bucket
```

This tells you: does the signal's "quality" metric predict how long before reversal?

### Step 6: Dataset Size vs Speed Tradeoff

- Full universe (150+ tokens) = 5-10 min runtime, comprehensive
- Top 10-15 tokens = 30-60 sec, good for rapid iteration
- Use full universe for final validation after parameter selection

### Step 7: Directional Asymmetry Check

Common pattern: one direction is catastrophic, other is profitable.

If one direction shows >3x more signals and strongly negative P&L → consider making it SHORT-only or dropping it.

## Key Findings Captured

### MA Cross Signal Discovery (2026-04-20)

Tested 8 EMA pairs across 163 tokens, exit-on-reverse-cross:

| Pair | Longs P&L | Shorts P&L | Net |
|------|-----------|------------|-----|
| 5/50 | -1800% | **+6784%** | +4984% |
| 8/50 | -2219% | **+6434%** | +4214% |
| 20/50 | -2396% | **+6328%** | +3932% |
| 20/200 | -697% | **+196%** | -501% |

**Lesson:** All pairs show catastrophic longs, profitable shorts. The bear market amplifies this. 8/50 chosen as sweet spot for signal frequency vs quality.

### R² Regression — Two Distinct Strategies Discovered (2026-04-20 / 2026-04-21)

**1. Trend-following (SHORT only) — r2_trend_signals.py (1m, existing)**
Tested on 1m: slope<0 AND price below regression line (ride the downtrend).
- LB=16, R2=0.60: +2843% net SHORT (38% WR)
- Works on 1m; 15m was all negative (dataset regime mismatch)

**2. Counter-trend / Mean reversion (BOTH directions) — r2_rev_5m_signals.py (5m, new)**
Tested on 5m (416 days): price DEVIATED from trend direction = bet on reversal.
- LONG: downtrend (slope<0) AND price BELOW line → oversold bounce
- SHORT: uptrend (slope>0) AND price ABOVE line → overextended fade
- LB=8, R2=0.40: 52-55% WR across both directions, +622%/+510% net

**Lesson:** Always test BOTH "with the trend" AND "against the trend" variants.
Same R² indicator produced a profitable signal in both modes — just on different
timeframes and with opposite entry logic. T's pivot to "can we go against it"
was the key unlock.

### Separation = Survival Predictor

Survival analysis on EMA crosses:

| Sep range | Median bars | Interpretation |
|-----------|-------------|----------------|
| 0.0-0.1% | 26 bars | Noise crosses |
| 0.1-0.2% | 50 bars | Short-term |
| 0.5-1.0% | 349 bars | Medium-term |
| >1.0% | 698 bars | Strong trend |

**Lesson:** Separation is a real predictor of trend duration. Use it for confidence scoring, not just filtering.

## Regime-Filtered Backtesting for Counter-Trend Signals

When a counter-trend signal direction fails (e.g., SHORT is negative), the fix is rarely just a different X threshold — it's usually a regime filter.

**The pattern:**
- Signal fires in ALL conditions → counter-trend signals get lost in ranging chop
- Add a broader market-regime filter to restrict the direction to genuine trend environments
- Example: EMA9/SMA20 gap SHORT was -0.026% PNL across all bars, but +0.017% when restricted to price below falling 50 SMA

**How to find the right regime filter:**
```
1. Classify each bar using a BROADER indicator than your signal
   (e.g., signal uses 20 SMA → regime uses 50 SMA)
   
2. Regime rules:
   - BULL: price > SMA AND SMA rising
   - BEAR: price < SMA AND SMA falling
   - NEUTRAL: everything else
   
3. For counter-trend signals (SHORT in uptrend, LONG in downtrend):
   - Only count signals where entry bar is in the opposite regime
   - Compare: ALL signals vs REGIME-filtered signals
```

**Key findings from EMA9/SMA20 SHORT retest (2026-04-27):**
```
Token   All SHORT PNL   Bear-regime SHORT PNL   Improvement
AVAX      +0.159%         +0.185%               +0.026%
ARB       +0.081%         +0.123%               +0.042%
ATOM      +0.053%         +0.059%               +0.006%
LINK      +0.076%         +0.064%               -0.012%
ETH       -0.026%         -0.032%               no improvement
ADA       -0.106%         -0.108%               no improvement
DOT       -0.160%         -0.144%               +0.016%
```
Regime filtering improved SHORT on 5/7 tokens that had enough bear-bar samples.

## Asymmetric Threshold Tuning Per Direction

LONG and SHORT almost always need different X/threshold values. Test them independently:

```
SHORT_X_VALUES = [0.002, 0.003, 0.005, 0.008, 0.010, 0.015]
LONG_X_VALUES  = [0.002, 0.003, 0.005, 0.008, 0.010, 0.015]

for x_long in LONG_X_VALUES:
    for x_short in SHORT_X_VALUES:
        long_results = backtest(..., min_gap_pct_long=x_long)
        short_results = backtest(..., min_gap_pct_short=x_short)
```

**Common asymmetry patterns:**
- LONG needs looser threshold (catches bigger moves, more patient)
- SHORT needs tighter threshold (bear moves are faster/sharper, need earlier entry)
- Example from EMA9/SMA20: LONG X=0.008 optimal, SHORT X=0.005 optimal

**When to disable a direction entirely:**
- If NO X value produces positive PNL even with regime filtering → disable it
- Re-test every few weeks/months as market conditions change

## Common Pitfalls

1. **Fixed exits create fake WR** — always compare with exit-on-reverse first
2. **Only testing 1-2 tokens** — noise, need 15+ for confidence
3. **Testing on wrong timeframe** — 1m results don't transfer to 15m if dataset periods differ
4. **Assuming symmetry** — LONG and SHORT are almost always asymmetric in practice
5. **Not testing enough parameter combos** — sweeps reveal sweet spots you wouldn't guess
6. **Thin data producing misleading results** — ~4.8 days of 5m (1275 candles) showed different
   best params than 416 days. Always verify findings with maximum available history before
   building signals. Short datasets can lucky-sample into wrong conclusions.
7. **Binance backfill pagination** — when fetching from Binance klines endpoint with
   startTime/endTime pagination, `limit` must be <= Binance's max (1000). If you use
   `chunk_size > 1000` and break on `len(candles) < chunk_size`, you'll break after
   the first request every time (1000 < 1500 is always true). Use `binance_limit = 1000`
   for the break check, keep larger chunk_size only for memory management.

## Files Created

- `/root/.hermes/scripts/backtest_ma_cross.py` — EMA cross parameter sweep backtester
- `/root/.hermes/scripts/ma_fast_signals.py` — 8/50 EMA SHORT-only signal (outcome of backtest)
- `/root/.hermes/scripts/r2_trend_signals.py` — R² regression SHORT-only signal, trend-following on 1m
- `/root/.hermes/scripts/r2_rev_5m_signals.py` — R² mean reversion signal, counter-trend on 5m (both directions)
- `/root/.hermes/scripts/backtest_r2_trend.py` — R² backtester (single-token detailed)
- `/root/.hermes/scripts/sweep_r2_5m_counter.py` — Full universe R² counter-trend sweep
- `/root/.hermes/scripts/sweep_r2_5m_fast.py` — Sampled sweep for rapid iteration (every Nth candle)

## Verification

After building the signal, always verify:
1. AST parse valid
2. Return type is `int` (not tuple)
3. Both LONG/SHORT or SHORT-only as designed
4. Source prefix correct
5. Cooldown written correctly (or passed to position_manager)
6. DB write confirmed
