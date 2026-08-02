# Plan: Decider Gate Reform — Reduce Hot-Set Signal Blocking

## Problem Statement
The decider blocks too many hot-set candidates at execution time. The hot-set is a curated candidate pool (built by signal_compactor with blacklist/whitelist filtering), but the decider then applies additional heavy filters that reject most candidates:

- `conf-1s` — single-source rejection
- `speed=0%` — stale token block
- Loss cooldown — same token+direction after loss
- Wrong-side learning — historical counter-move penalty
- Win rate < 50% (3+ trades) — direction paused

Current outcome: 8 skipped, 1 entered per cycle. The system is too restrictive.

## Goal
Reduce unnecessary blocking while preserving genuine risk protection. The hot-set should be the last word on candidates — the decider should execute, not re-filter.

## Proposed Changes

### 1. Remove or soften wrong-side learning gate
Win-rate learning is valid but the penalty (conf -15 → skip below 55%) is too aggressive. Consider:
- Lower the penalty to -5 or -10
- Raise the skip threshold to conf < 45% instead of 55%
- Or remove entirely and let the trade sizing manage risk

### 2. Remove win-rate direction pause
`WR < 50% on 3 trades` pauses a direction. With only 3 trades this is statistically meaningless. Options:
- Raise minimum trades to 10 before pausing
- Remove entirely
- Replace with total PnL check (e.g., pause if -10% cumulative PnL on that direction)

### 3. Speed=0% — keep but log differently
This is a genuine stale-data guard. Keep it but the signal_compactor should already be filtering stale tokens. Consider moving this check upstream to compactor.

### 4. Loss cooldown — keep
This is legitimate risk management. Don't touch.

### 5. conf-1s — keep
Single-source signals are genuinely lower quality. But consider: if the source is a well-validated signal (e.g., `accel-300+`), allow it through on its own merit rather than blanket blocking all `conf-1s`.

## Implementation Steps
1. Read decider_run.py and identify all gate locations with line numbers
2. For each gate: measure how many signals it blocks per cycle (add logging)
3. Apply changes incrementally — one gate at a time
4. Backtest impact on closed trades before deploying to live

## Files to Modify
- `/root/.hermes/scripts/decider_run.py` — gates at lines ~1548-1601

## Verification
- Before: 8 skipped / 1 entered
- After: target 3-4 skipped / 5-6 entered (per cycle)
- Monitor: win rate, avg PnL per trade, stop-loss hit rate
