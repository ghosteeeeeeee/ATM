# zscore-pump Overtiring Pattern — FET Case Study (2026-05-22)

## The Problem

zscore-pump fires correctly on direction but over-fires on the same sustained leg,
creating redundant entries in the hot-set. T called this "giant long condition" on FET.

## Symptom

- Lookback=100 (ZSCORE_PUMP_LOOKBACK): first signal fires 44 bars after the move starts
- Z(100) stayed > 3.0 for 12 consecutive bars (02:03–02:14), peaked at 4.19
- Cooldown=5 bars (~5 min): on a sustained move you get ~3 signals instead of 1 clean entry
- Leg tracking absent: re-fires even after z briefly dips below 2.0 then resumes

## Root Causes

1. **Lookback lag**: 100-bar lookback means zscore can't compute until bar 100+
   → first signal fires ~44 bars after move actually starts (01:16 spike at z=4.5
   but Z(100) first fires at 02:00)
2. **Short cooldown without leg tracking**: 5-bar cooldown expires while z is still
   elevated — no concept of "same leg still running"
3. **No lower threshold gate**: z between 1.5–2.0 re-enters without new confirmation

## ATR Context (why it's tricky)

FET ATR(14) ≈ $0.0001, which is 0.03–0.06% of price per bar. Individual bars
are mostly flat with 0.00% change. A z > 2.0 on a 0.05% bar isn't necessarily
a "momentum bar" — it's a statistically unusual reading in a quiet range.

## What T Wants

- "Consecutive bar" requirement: z > 2.0 for 3+ bars before firing (not just one cross)
- Or: ATR% floor — only fire when 1m_pct_change > 0.15% (filters micro-noise)
- Or: "leg tracking" — suppress re-fires while z stays above 1.5 (lower threshold)
- All three are valid approaches; the ATR% floor is simplest to implement

## Signal Fire Map (FET 3h window)

```
01:16  spike bar, Z(60)=4.5 — no Z(100) yet (need 100 bars)
01:19  Z(60)=2.53 first Z(60) LONG (lookback=60 kicks in)
02:00  Z(100)=2.20 FIRST Z(100) signal — 44 bars after spike
02:03  Z(100)=3.80 Strong ← 12-bar sustained cluster begins
02:10  Z(100)=4.19 Giant  ← peak
02:14  Z(100)=2.87 Medium
02:15-02:27  Z(100)=2.0-2.75 lingering (cooldown would allow re-fire)
02:28  Z(100)=1.73 below threshold — cooldown resets
02:33  Z(100)=2.01 fires again — same trend continuing
```

## Fix Options (in priority order)

1. **ATR% floor (simplest)**: add `abs(pct_change) >= 0.0015` gate in `detect_zscore_pump()`
2. **Consecutive bar requirement**: modify threshold check to require 3 consecutive bars
3. **Leg tracking via lower threshold**: suppress if z drops below 1.5 then re-crosses 2.0
   within N bars (same leg, not a new entry)
4. **Adaptive lookback**: for fast pumps, use shorter lookback (60) as the primary trigger
   and only use 100 when z(60) confirms — i.e. "double confirm" instead of waiting for 100

## Key Constants

```
ZSCORE_PUMP_LOOKBACK = 100   (current — causes lag)
ZSCORE_PUMP_THRESHOLD = 2.0  (firing threshold)
ZSCORE_PUMP_COOLDOWN_BARS = 5  (~5 min — too short for sustained moves)
ZSCORE_PUMP_DIVERGENCE_ENABLED = True
ZSCORE_PUMP_DIVERGENCE_LOOKBACK = 40
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 3.0
```

## Files Involved

- `/root/.hermes/scripts/signals/zscore_pump.py` — signal logic
- `/root/.hermes/scripts/hermes_constants.py` — ZSCORE_PUMP_* constants
- `/root/.hermes/data/candles.db` — candles_1m table for historical analysis
- `/root/.hermes/scripts/signal_compactor.py` — hot-set builder (reads zscore-pump signals)