---
name: stale-trades
description: Audit and fix stale signals and stale positions in the Hermes trading pipeline. Checks signal staleness (APPROVED/PENDING/PURGE), position staleness (speed-based stall detection), and applies fixes.
tags: [hermes, trading, signals, positions, staleness]
author: Agent
created: 2026-04-05
updated: 2026-04-05
---

# Stale Trades — Audit & Fix

Checks and fixes two types of staleness in the Hermes pipeline:

## Type 1: Signal Staleness

| Rule | Condition | Action |
|------|-----------|--------|
| Stale APPROVED | APPROVED, not executed >1h | Mark EXPIRED |
| Stale PENDING | PENDING, never reviewed (rc=0), >3h old | Mark EXPIRED |
| PURGE | PENDING, rc≥5 (survived 5+ compaction cycles) | Mark EXPIRED |

**Why:** Stale APPROVED blocks new approvals. Stale PENDING pollutes the queue. PURGE catches signals stuck in pipeline forever.

## Type 2: Position Staleness (Speed-Based)

`check_stale_position()` in `position_manager.py`:

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Loser + stalled | pnl≤-1%, speed_pctl<33, vel<0.2%, 30+min | Cut position |
| Winner + stalled | pnl≥+1%, speed_pctl<33, vel<0.2%, 15+min | Cut position |

**Why:** Positions that are flat (stalled speed) for too long while at a loss are dead money. Winners that go flat should take profit before reversal.

## Quick Check

```bash
python3 /root/.hermes/skills/trading/stale-trades/scripts/check.py
```

## Full Audit + Fix

```bash
python3 /root/.hermes/skills/trading/stale-trades/scripts/check.py --fix
```

## Pipeline Integration

- **Signal staleness**: `cleanup_stale_signals()` in `ai_decider.py` runs every 10 min (via `run_pipeline.py`)
- **Position staleness**: `check_stale_position()` in `position_manager.py` runs every 1 min (via `position_manager` step)
- **APPROVED cleanup**: `cleanup_stale_approved()` called in `decider-run.py` each cycle

## Thresholds

| Parameter | Value | File |
|-----------|-------|------|
| `STALE_LOSER_MAX_LOSS` | -1.0% | position_manager.py:35 |
| `STALE_WINNER_MIN_PROFIT` | +1.0% | position_manager.py:34 |
| `STALE_LOSER_TIMEOUT_MINUTES` | 30 min | position_manager.py:33 |
| `STALE_WINNER_TIMEOUT_MINUTES` | 15 min | position_manager.py:32 |
| `STALE_VELOCITY_THRESHOLD` | 0.2%/5m | position_manager.py:37 |
| `SPEED_STALL_THRESHOLD` | 33 (percentile) | position_manager.py:315 |
| `PURGE_THRESHOLD` | rc≥5 | ai_decider.py:883 |
| `STALE_APPROVED_HOURS` | 1 hour | signal_schema.py:950 |

## Common Issues

1. **Stale APPROVED not clearing**: `cleanup_stale_approved()` not firing — check decider-run.py calls it
2. **PURGE not working**: rc counter not incrementing — check ai_decider compaction runs
3. **Positions not cutting at -1%**: trailing SL may be active — trailing overrides cut_loser
4. **Speed data missing**: SpeedTracker init failure — check `speed_tracker.py` imports
