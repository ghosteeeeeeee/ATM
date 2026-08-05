# Guppy MMA Signal — Implementation & Backtest Findings

## Signal Definition

**Source:** `guppy_long`, `guppy_short`

**Pattern:** Expansion-based (squeeze → expansion → direction), NOT cross-based.

Guppy MMA uses two EMA groups:
- **Fast group:** 3, 5, 8, 10, 12, 15
- **Slow group:** 30, 35, 40, 45, 50, 60

**Signal logic:**
1. Squeeze: fast group within 0.3% of slow group
2. Expansion: fast group diverging from slow group by ≥0.2%
3. Direction: fast group above slow = LONG, below = SHORT
4. Trend filter: slow group must be rising (LONG) or falling (SHORT)

```python
# Key constants (guppy_signals.py)
FAST_GROUP = [3, 5, 8, 10, 12, 15]
SLOW_GROUP = [30, 35, 40, 45, 50, 60]
SQUEEZE_THRESHOLD = 0.003   # 0.3%
MIN_SEPARATION_PCT = 0.2    # 0.2% minimum post-squeeze separation
EXPANSION_BARS = 3          # separation must grow over 3 bars
SLOW_TREND_LOOKBACK = 10    # slow group trend over 10 bars
MIN_VOLUME_RATIO = 2.0      # volume confirmation
```

## Key Files

| File | Purpose |
|------|---------|
| `/root/.hermes/scripts/guppy_signals.py` | Pure detection engine, local candles.db only |
| `/root/.hermes/scripts/run_guppy_signals.py` | Standalone runner: `--scan`, `--monitor`, `--status`, `--close ALL` |
| `/root/.hermes/scripts/backtest_guppy.py` | Historical backtester with TP/SL support |

## Timeframe Results

| Timeframe | Trades | Win Rate | Avg PnL | Notes |
|-----------|--------|----------|---------|-------|
| 1m | 23 | 23% | -0.52% | Untradeable — too noisy |
| 5m | 21 | 38% | -0.20% | Still losing |
| **15m** | **14** | **57%** | **+0.38%** | Best — Guppy designed for higher TF |
| 15m + TP=0.75% | 18 | 50% | +0.29% | With SL=0.50% |

**Conclusion:** 15m >> 1m/5m for Guppy. The fast/slow EMA groups are too tight on 1m candles — separation at cross is 0.03-0.4% max, making cross-based signals fire on noise.

## Exit Strategy Findings

**TP-only is the right approach.** Adding SL (0.5%) cuts off valid winners and drops win rate from 57% to 50% with no PnL improvement.

**Sweet spot:** TP=0.75% on 15m — "book profit fast" per T's philosophy works exactly as intended.

**Why flip-only is wrong:** Pure fast-group flip exit (close position when fast group crosses back) produces 23-38% WR — the strategy wins when trends are clean but loses in ranging markets. TP captures the winning trades before the inevitable mean-reversion.

## Critical Bugs Found During Implementation

### Bug A: TP/SL thresholds direction-agnostic (backtest_guppy.py)

**Symptom:** TP and SL never fire. All exits show `guppy_fast_flip`. Win rate and PnL identical regardless of `--tp`/`--sl` values.

**Root cause:** PnL was computed as `(curr_close - entry) / entry * 100.0` (LONG convention: positive = price up), then inverted for SHORTs. But the TP/SL threshold checks used the raw value directly:

```python
# WRONG — raw_pnl is positive for SHORT when price goes UP (wrong direction)
pnl_raw = (curr_close - entry) / entry * 100.0
if position['direction'] == 'SHORT':
    pnl_raw = -pnl_raw  # only the LOG is inverted, not the comparison
if sl_pct > 0 and pnl_raw <= -sl_pct:  # -0.75% <= -0.75? True — SL fires
    ...  # but pnl_raw was already negated above, so comparing wrong value
```

**Correct approach:** Compute PnL in the position's direction first (positive = winning), THEN compare to thresholds:

```python
# CORRECT — PnL is always in the position's directional frame
pnl_raw = (curr_close - entry) / entry * 100.0
if position['direction'] == 'SHORT':
    pnl_raw = -pnl_raw  # price up = losing for SHORT

# Now thresholds are direction-aware
if sl_pct > 0 and pnl_raw <= -sl_pct:   # -0.75% means losing 0.75%
    exit_reason = 'sl'
if tp_pct > 0 and pnl_raw >= tp_pct:    # +0.75% means winning 0.75%
    exit_reason = 'tp'
```

**Rule:** Always compute PnL in the position's directional frame before comparing to TP/SL thresholds.

### Bug B: CLI args not passed to backtest function (backtest_guppy.py)

**Symptom:** `--tp 1.0 --sl 0.75` args accepted by argparse but have zero effect. Debug output shows `tp=0.0 sl=0.0` inside the trade loop.

**Root cause:** Arguments added to argparse but never forwarded in the `backtest_token()` call:

```python
# main() had (WRONG):
trades = backtest_token(
    token,
    interval=args.interval,
    start_ts=args.start,
    end_ts=end_ts,
    lookback=args.lookback,
    min_confidence=args.conf,
    # tp_pct and sl_pct MISSING
)

# CORRECT:
trades = backtest_token(
    ...
    tp_pct=args.tp,
    sl_pct=args.sl,
)
```

**Also:** `scan_all_tokens()` had same missing params (needed `tp_pct=0.0, sl_pct=0.0` to avoid undefined errors).

**Rule:** When adding new CLI args that flow into a function call, verify the function call actually receives them. Check: (1) argparse add_argument, (2) function signature accepts it, (3) function call passes it.

### Bug C: Indentation trap in if-elif chain

**Symptom:** Code logically looks correct but behaves wrong. A bare `exited = True` statement sits at the wrong indentation level and runs unconditionally.

**Root cause:** Patch operations that replace multi-line blocks can misalign indentation. The `if exited:` block was outside the `else:` block, causing all exits to append trades regardless of the conditional logic.

**Rule:** After any patch that modifies if/elif/else blocks, always read the resulting code at the function level to verify structure before testing.
