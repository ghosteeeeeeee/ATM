# Plan: MTF-MACD Cascade Reversal Backtest Experiment

## Goal
Add cascade reversal logic to `mtf_macd_backtest.py` exit handler and sweep the reversal_score threshold to find the optimal setting for improving win rate (WR).

## Context

### Current System
- **Entry**: ALL 3 TFs (4h + 1h + 15m) must agree direction = maximum conviction
- **Exit**: As soon as ANY TF flips direction → exit immediately
- **Problem**: Fast exits may cut winners short. Some TF flips are noise (only the small TF flips, larger TFs stay put), not real reversals.

### Cascade Insight (from `candle_db.detect_cascade_direction`)
Smaller TFs lead reversals. A **true reversal** looks like:
1. 15m flips FIRST (lead TF)
2. 1h follows
3. 4h confirms

A **false flip** (noise) = only 15m flips, 1h and 4h stay put.

`reversal_score` (0.0–1.0) measures how "complete" the cascade is:
- 0.0 = only lead TF flipped, larger TFs didn't follow = **noise → exit**
- 0.5 = lead TF + 1 larger TF flipped = **partial cascade → flip signal, maybe reverse?**
- 1.0 = all TFs flipped = **confirmed reversal → DON'T exit, reverse instead**

### Proposed Exit Logic Change

| reversal_score | Current Behavior | New Behavior |
|---|---|---|
| 0.0 | Exit | Exit (no change) |
| 0.5 | Exit | **Reverse** (partial cascade = real reversal starting) |
| 1.0 | Exit | **Reverse** (full cascade = confirmed reversal) |

**Key hypothesis**: Winners we cut short by exiting on first flip would have continued. By reversing on cascade signals, we:
- Stay in winning trades longer (，跟着趋势)
- Flip to the new direction instead of just stopping out

## Implementation Plan

### Step 1: Add Cascade Detection to Backtester

Add a new function `check_exit_with_cascade()` in `mtf_macd_backtest.py`:

```python
def detect_cascade_at_idx(idx, tfs_data, params):
    """
    Wrapper around candle_db.detect_cascade_direction.
    Returns cascade dict with reversal_score, cascade_direction, etc.
    """
    # Build tf_states dict: {tf_name: macd_state}
    # Need macd_above_signal and histogram_positive per TF
    ...
```

Modify `check_exit()` to accept a `reversal_threshold` param. At each candle check:
1. Run `detect_cascade_direction()`
2. If reversal_score >= threshold → **reverse** (flip direction, continue)
3. If any TF flipped but reversal_score < threshold → **exit** (current behavior)
4. If timeout → **exit**

### Step 2: Add Reversal to Trade Tracking

When a **reverse** happens mid-hold:
- Close position at current price (pnl calculated)
- Immediately open new position in cascade direction
- Track as two separate trades OR as one reversing trade

For simplicity: track as **two separate trades** with `exit_reason='cascade_reverse'`.

### Step 3: Sweep Reversal Threshold

New sweep parameter:
```python
REVERSAL_THRESHOLDS = [0.0, 0.25, 0.5, 0.75, 1.0]
# 0.0 = disabled (current behavior)
# 1.0 = only reverse on full cascade
```

Run full param sweep across all tokens. Compare:
- WR with cascade reversal vs. without
- Avg win size
- Total PnL
- Signal count (does reversal add more trades?)

### Step 4: Collect Per-Trade Data

When `--per-trade --cascade-reversal` flags are set, output:
```
token, direction, entry_p, exit_p, pnl_pct, exit_reason, reversal_score, ...
```

Per-trade output needed for analyzing:
- Which reversal_score thresholds catch real reversals
- Average "reversal depth" (how far did the new direction go?)

## Files to Change

| File | Change |
|---|---|
| `/root/.hermes/scripts/mtf_macd_backtest.py` | Add cascade exit logic, new sweep params, per-trade cascade fields |
| `/root/.hermes/scripts/candle_db.py` | Read-only (already has `detect_cascade_direction`) |

## CLI Additions

```bash
# Basic cascade sweep
python3 mtf_macd_backtest.py --tokens BTC,ETH,SOL --sweep --cascade-reversal

# Per-trade cascade analysis
python3 mtf_macd_backtest.py --token BTC --per-trade --cascade-reversal

# Sweep just reversal thresholds (fixed best-known params)
python3 mtf_macd_backtest.py --token BTC --per-trade --cascade-reversal --reversal-sweep
```

New arguments:
- `--cascade-reversal`: enable cascade reversal logic
- `--reversal-sweep`: sweep only REVERSAL_THRESHOLDS (not full MACD grid)
- `--reversal-threshold`: set fixed threshold (0.0–1.0)

## Expected Outputs

1. **Leaderboard comparison**: existing WR vs. cascade reversal WR across all param combos
2. **Per-trade analysis**: WR by reversal_score threshold, avg extension after reverse
3. **Key metric**: Does cascade reversal increase WR? Does it increase avg_win?

## Risks & Open Questions

**Q: Does reversing add slippage/cost that erodes gains?**
- We track round-trip PnL including both legs. Commission not modeled (negligible vs. % moves).

**Q: What if cascade reverses but the new direction also fails?**
- Per-trade tracking will show "reversal then timeout" or "reversal then stopped out" patterns.

**Q: Should we reverse only once per trade, or allow multiple reversals?**
- Limit to 1 reversal per trade to keep it simple. After first reverse, treat as a new trade with its own exit rules.

**Q: Does the backtest data (Binance candles) have sufficient resolution for 15m cascade detection?**
- Yes, 15m candles are native resolution. Cascade detection uses existing candle data directly.

## Validation

1. Run `python3 mtf_macd_backtest.py --token BTC --per-trade --cascade-reversal` — confirm no errors
2. Compare output with `--cascade-reversal` vs without for same params — WR should differ
3. Check that `exit_reason='cascade_reverse'` appears in per-trade output
4. Run sweep: `python3 mtf_macd_backtest.py --tokens BTC,ETH,SOL --sweep --cascade-reversal --workers 4`
