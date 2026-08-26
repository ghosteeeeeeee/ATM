# YOUR TASK: Quick Decision Required

price_collector timer is 30s. Two approaches to fix broken signal calculations:

## Option A: Split Architecture (RECOMMENDED)
- latest_prices: writes every 30s → exit management gets faster SL/TP reaction
- price_history: writes on minute boundaries only → signals stay at 60s bars, all constants calibrated
- One line change in signal_schema.py
- Zero signal code changes needed
- Exit management already reads latest_prices or HL API directly

## Option B: Revert to 60s
- Zero code changes
- Lose 30s exit freshness
- Back to status quo

## Option C: Full Migration (50 constants)
- 4-phase deploy, hours of work
- High regression risk
- Makes system resilient to future interval changes

Current system: 33T/24h, 39.4% WR, -$1.36. Not the time for risky changes.

DECISION: Which option? Reply with ONE LINE.
