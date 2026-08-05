# accel-300+ Signal Quality Degradation — 2026-05-11

## Symptom

8 tokens (ATOM, AVAX, BSV, STRK, CAKE, SKR, GRIFFAIN, PEOPLE) opened as LONG within 15 minutes at ~20:02-20:17. All signals were `accel-300+` or `accel_300_long`. All 8 trades lost.

## Root Cause: Three Relaxations on 2026-05-10

### 1. MIN_GAP_PCT: 0.20 → 0.15
Thresholds for what qualifies as a "gap" (price change above EMA) were relaxed. Now catches weaker breakouts that don't have real momentum.

### 2. MIN_GAP_GROWTH_PCT: 0.05 → 0.03
The growth rate of the gap was relaxed, allowing more marginal acceleration to qualify.

### 3. TIMING FIX: fires on bars 0-3 after EMA cross
Previously the signal required some bars to confirm the cross. The TIMING FIX (lines 255-300) now fires immediately on bars 0-3 after EMA cross — the moment of maximum uncertainty.

## The Burst Pattern

All 8 tokens fired within 15 minutes. This is the signature of a parameter relaxation that caught a market-wide micro-rally — the kind of event that happens regularly in crypto. With tighter parameters, only the strongest breakouts would have fired.

## T's Intended Fix

> "I'm thinking the decider run should filter based on the regime from the linear regression of the last 100 bars on 1min prices."

This suggests T wants per-coin 1m LR regime filtering to act as a quality gate — only allowing LONG when the 1m regime is LONG_BIAS, and only allowing SHORT when SHORT_BIAS. This would have naturally filtered out 7 of the 8 simultaneous LONGs if most tokens had NEUTRAL or SHORT_BIAS on the 1m.

**Note:** The 1m LR regime is currently DISABLED (commented out in both signal_compactor.py and decider_run.py). Re-enabling it would address both the quality degradation and T's preference for per-coin regime filtering.

## Recommended Parameter Restoration

| Parameter | Was | Now | Suggested |
|-----------|-----|-----|-----------|
| MIN_GAP_PCT | 0.20 | 0.15 | 0.20 |
| MIN_GAP_GROWTH_PCT | 0.05 | 0.03 | 0.05 |
| bars_since_cross min | 0 | 0 | 1 (require at least 1 bar of confirmation) |

## Monitoring

```bash
# Check recent accel-300+ signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, signal_type, confidence, created_at \
   FROM signals WHERE signal_type='accel_300_long' ORDER BY created_at DESC LIMIT 20;"

# Count signals per token in last hour
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, COUNT(*) as cnt FROM signals \
   WHERE signal_type='accel_300_long' AND created_at > datetime('now', '-1 hour') \
   GROUP BY token ORDER BY cnt DESC;"
```