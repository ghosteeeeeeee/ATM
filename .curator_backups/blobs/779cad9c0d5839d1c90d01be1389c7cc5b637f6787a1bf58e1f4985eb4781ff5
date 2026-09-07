# Guppy MMA Signal — Session Findings 2026-05-04

---

## Core Architecture: Expansion, NOT Cross

**The signal definition matters more than the threshold tuning.**

Guppy MMA signals on 1m/5m candles do NOT fire on "cross + separation." At the moment of cross, separation is near-zero by definition. The correct signal definition is:

**Signal = squeeze → directional expansion, not cross + separation.**

Two key functions:
- `detect_expansion()` — fast group is currently expanding away from slow group (positive separation growing over N bars)
- `detect_cross_with_setup()` — look back 1-3 bars for a recent cross, but measure separation NOW (after the cross has room to develop)

The cross is informational only. The actual entry trigger is whether the groups are expanding apart right now.

---

## Why Cross + Separation Fails on 1m Candles

On 1m candles, fast group (EMA 3-15) and slow group (EMA 30-60) are too tight:
- At moment of cross: separation ≈ 0% by definition
- By the time separation reaches 0.5%, the cross is already 1-3 bars old
- MIN_SEPARATION_PCT=1.0 is never reached on 1m (max observed across 20+ tokens: 0.4%)

Tested across 20+ tokens, 3000 bars each:
- Best LONG separation at cross: 0.058% (AAVE)
- Best SHORT separation at cross: 12.575% (ATOM, extreme outlier)
- Most tokens: 0.03–0.4% max

---

## What Works: Expansion Signal

Signal fires when:
1. Fast group is expanding away from slow group (separation growing over 6 bars)
2. Separation exceeds 0.2% minimum threshold
3. Volume confirms (optional bonus)

**Results by timeframe:**
- 1m: 16-38% WR, negative avg PnL — ranging-market trap
- 5m: 38% WR on HYPE, still negative avg PnL
- 15m: signals fire cleanly (AIXBT SHORT, ASTER SHORT at 1.3%, 0.3% separation)

**Conclusion:** Guppy MMA needs 15m+ for the signal to be meaningful, OR a strong trend filter.

---

## Key Params (tuned 2026-05-04)

```python
SQUEEZE_THRESHOLD = 0.003    # 0.3% — informational only, not a gate
MIN_SEPARATION_PCT = 0.2      # 0.2% — minimum to confirm expansion
EXPANSION_BARS     = 6         # bars over which separation must be growing
```

Confidence scoring:
- Expansion >50%: +0.30
- Squeeze + 3+ bars: +0.20
- Separation >1.0%: +0.20
- Volume confirm (>1.2x avg): +0.10

---

## Bug Encountered: Duplicate Function Definition

After patching `detect_guppy_signal` and `_compute_confidence`, the old `_compute_confidence` (old signature: `squeeze, separation, direction, volume_confirm, cross_bars_ago`) remained in the file at line 537. New version at line 478 had new signature `in_squeeze, squeeze_bars, expansion_pct, separation, volume_confirm`. The call site used the new signature → `TypeError: _compute_confidence() got an unexpected keyword argument 'in_squeeze'`.

**Fix:** Remove the old version entirely. When refactoring function signatures via patch, always grep for ALL copies of the function name before and after the change.

---

## TP/SL Exits Added to Backtester

backtest_guppy.py now supports `--tp` and `--sl` CLI args:
- Exit priority: SL → TP → reverse signal → end_of_data
- TP/SL measured as % from entry price at each bar

---

## Files Built This Session

- `/root/.hermes/scripts/guppy_signals.py` — pure detection, local candles.db only, no HL API
- `/root/.hermes/scripts/run_guppy_signals.py` — standalone runner, `--scan`/`--monitor`/`--status`/`--close ALL`
- `/root/.hermes/scripts/backtest_guppy.py` — historical backtester with TP/SL grid search

---

## Next Steps

1. Try `--interval 15m` or `--interval 1h` — Guppy was designed for higher timeframes where trends are cleaner
2. Implement "squeeze → expansion → pullback entry" — wait for retest of slow group after breakout rather than chasing the initial move
3. Add ATR-based exits (volatility stops) instead of pure flip — T's philosophy: tight stops, book profit fast
4. Consider combining with a regime filter (z-score of price vs SMA) to avoid ranging markets
5. **Critical:** Squeeze definition needs "prior expansion" — a market that's been squeezed for 140 bars isn't a squeeze, it's ranging. Require expansion before compression to qualify as a true squeeze.
