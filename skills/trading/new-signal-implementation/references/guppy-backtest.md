# Guppy MMA Backtest Results — 2026-05-04

## Setup
- 10 tokens: 0G, 2Z, AAVE, ACE, ADA, AERO, AI, AIXBT, ALGO, ALT
- Interval: 1m candles
- Lookback: 120 bars
- Min confidence: 0.60
- Exit: reverse guppy signal (fast group flips = exit)
- No fixed TP/SL

## Results

| Token | Trades | Win Rate | Avg PnL% |
|-------|--------|----------|----------|
| 0G | 1138 | 12.1% | -0.130% |
| 2Z | 913 | 23.0% | -0.018% |
| AAVE | 1001 | 22.4% | +0.009% |
| ACE | 1000 | 3.8% | -0.613% |
| ADA | 973 | 21.5% | +0.038% |
| AERO | 257 | 23.4% | +0.035% |
| AI | 1360 | 8.3% | -0.311% |
| AIXBT | 948 | 16.6% | -0.041% |
| ALGO | 1012 | 19.8% | +0.011% |
| ALT | 951 | 19.7% | +0.036% |
| **TOTAL** | **9553** | **16.1%** | **-0.119%** |

## Key Stats
- Win rate: 16.08%
- Best trade: +90.3%
- Worst trade: -18.7%
- Max drawdown: -18.7%
- Avg bars held: 459.3 (≈7.6 hours at 1m)
- Squeeze at entry: 97.5%

## Diagnosis
The 97.5% squeeze-at-entry rate means the signal almost exclusively fires on squeeze resolution (fast group crossing through slow group). Classic Guppy failure mode:
1. Fast group compresses toward slow group (squeeze)
2. Fast group punches through slow group (cross = signal fires)
3. Market snaps back, mean-reverts
4. Reverse cross = exit at small loss

The 16% win rate is consistent with a strategy that catches reversals rather than trends.

## What Would Fix It
See `references/guppy-mma-signal.md` — trend filter, stronger separation, momentum confirmation, or longer timeframe.
