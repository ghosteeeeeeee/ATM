---
name: mtf-macd-backtest-findings
description: "Empirical backtest findings for MTF-MACD tuning (2026-04-18): validated signal params, counterintuitive discoveries, and what NOT to do."
category: trading
---

# MTF-MACD Backtest Findings (2026-04-18)

## Backtest Script
`/root/.hermes/scripts/backtest_mtf_1h15m1m.py` — self-contained backtest using local `candles.db`.
Run with: `python3 backtest_mtf_1h15m1m.py [token1 token2 ...]`

## Validated Signal Parameters

| Param | Value | Notes |
|-------|-------|-------|
| MACD Fast | 10 | faster than standard 12 — catches earlier |
| MACD Slow | 20 | faster than standard 26 |
| MACD Signal | 7 | tighter than standard 9 |
| z-score threshold | 3.0 | key entry filter |
| Entry TF | 15m + 1H | histogram agreement confirms move has legs |
| Exit TF | 1H | histogram flip exits |

**Result:** 83% WR, +1.394% avg, -0.8% DD (47 trades over 30 days, all LONG)

## The Counterintuitive Finding

**NOT mean-reversion.** This was the initial hypothesis (buy when stretched = reversal), but it failed.

- z > 3.0 means price is **3 standard deviations above mean** — extremely elevated
- In this regime, elevated price CORRELATES with continued upside, not reversal
- "Buy when stretched AND momentum confirms" = momentum continuation at extremes
- The histogram (15m + 1H both > 0) confirms the move has directional strength

## What Failed

1. **First-cross reversal** (enter when z first crosses threshold): too sparse, by the time z crosses the move already happened
2. **Standard MACD crossover** (no z filter): 48% WR, barely profitable
3. **z < 0.5 filter** (buy only in "normal" territory): loses money — catching the move early matters
4. **SHORT side**: all SHORT trades were losers. z > 3.0 + hist agreement is a LONG-only signal in this market regime
5. **Slow MACD** (12/26/9 standard): worse than Fast=10/Slow=20/Sig=7

## Why z > 0.5 Was Blocking Everything

The old `z_1h > 0.5` filter was blocking nearly ALL signals in backtests:
- Most of the time, z_1h sits between 0.5 and 2.0
- These mid-range z values produce the worst trades (45-50% WR)
- The signal only becomes high-quality when z > 2.5-3.0

## BLACKLIST Still Applies

`BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, LINK` are blocked from SHORT.
This is correct — the SHORT side doesn't work in this regime regardless.

## Code Change

**File:** `/root/.hermes/scripts/signal_gen.py` — `_run_mtf_macd_signals()`

```python
# OLD: z_1h > 0.5 blocking LONGs, crossover-based entry
# NEW (2026-04-18):
Z_MACD_THRESH = 3.0
MACD_FAST, MACD_SLOW, MACD_SIG = 10, 20, 7

xo_1h  = _macd_crossover(token, 60*1)
xo_15m = _macd_crossover(token, 15)
h_15m = xo_15m[0] if xo_15m else None
h_1h  = xo_1h[0]  if xo_1h  else None

mtf_macd_direction = None
if z_1h is not None and z_1h > Z_MACD_THRESH:
    if h_15m > 0 and h_1h > 0:
        mtf_macd_direction = 'LONG'
    elif h_15m < 0 and h_1h < 0:
        mtf_macd_direction = 'SHORT'
```

Confidence: `min(75, 45 + (abs(z_1h) - 3.0) * 10)`

## Limitations

- **z > 3.0 is very selective** — ~47 trades/30 days across 10 tokens ≈ 1-2 signals/token/month
- Most signal generation still comes from `hzscore`, `pct-hermes`, `vel-hermes` confluences
- MTF-MACD fires rarely but with high conviction when it does
- Data in `candles.db` is ~8 hours stale — backtest uses recent data, live may differ
- 30-day backtest window may not capture all market regimes
