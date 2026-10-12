# Plan: grind-breakout-v2 — Coin-Tracker Integration (DEFERRED)

**Status:** DEFERRED — revisit based on how the current window-based firing performs
**Created:** 2026-10-12
**Trigger:** If current signal misses too many breakouts due to polling-based detection

## Problem

The signal checks all conditions on a single bar. In reality, conditions develop across multiple bars (MEGA: compression at 11:40, breakout at 12:45, volume at 12:50). This causes missed signals.

## Current Approach (Active)

Window-based check in signal script:
- BB compression: BB < 3% in last 10 bars
- BB expansion: current BB > 2x min BB in window
- Breakout: price > 20-bar high (current bar)
- Volume: volume > 2.5x average (current bar)

Still polling-based (~1 min interval). May miss alignments between signal runs.

## Proposed: Coin-Tracker Integration

Add compression state tracking to coin_tracker.db, which already monitors all coins every 5 minutes.

### New Columns for coin_<TOKEN> tables

| Column | Type | Computation |
|--------|------|-------------|
| `bb_width` | FLOAT | BB(20, 2.0) width as % |
| `bb_min_10` | FLOAT | Min BB in last 10 bars |
| `bb_expansion` | FLOAT | bb_width / bb_min_10 |
| `resistance_20` | FLOAT | 20-bar high |
| `support_20` | FLOAT | 20-bar low |
| `vol_ratio` | FLOAT | vol_5m / 20-bar avg vol |
| `compression_state` | INT | 1 if BB < 3% in last 10 bars |
| `breakout_state` | INT | 1 if price > resistance, -1 if < support, 0 |

### How It Works

1. coin_tracker runs every 5 min — computes BB, resistance, volume ratio for all coins
2. Writes to coin_<TOKEN> tables
3. Signal script reads from coin_tracker instead of computing on the fly
4. Signal fires when: `compression_state=1 AND bb_expansion > 2.0 AND breakout_state != 0 AND vol_ratio > 2.5`

### Tradeoffs

| | Current (signal computes) | With coin_tracker |
|--|--------------------------|-------------------|
| Latency | ~1 min | ~5 min |
| CPU | Signal computes BB for 182 tokens every cycle | coin_tracker already reads all candles |
| Accuracy | Real-time | Up to 5 min stale |
| Maintenance | Logic in signal script | Logic in coin_tracker |

### Files to Modify

1. `scripts/coin_tracker.py` — add BB/resistance/volume computations in collect()
2. `scripts/coin_tracker_schema.py` — add new columns to coin_<TOKEN> tables
3. `scripts/signals/grind_breakout_v2.py` — read from coin_tracker instead of computing

### Edge Cases to Handle

1. **Weird order**: Volume surge before breakout — should still fire
2. **Stale data**: coin_tracker runs every 5 min — signal may read stale state
3. **Missing data**: New coins won't have history for BB computation
4. **Condition reset**: After FIRED, state should reset to IDLE

## Revisit Trigger

If the current window-based signal misses >50% of breakouts that meet all conditions, switch to coin-tracker integration.
