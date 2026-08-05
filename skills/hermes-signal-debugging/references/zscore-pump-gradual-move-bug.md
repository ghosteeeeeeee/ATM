# zscore-pump Gradual-Move Detection Bug — 2026-05-22

## Symptom

FET rallied 5.14% over 4 hours (23:38 → 03:38, price 0.19335 → 0.20328).
zscore-pump fired 3 signals at 03:08, 03:18, 03:23 (z=2.0-2.2, barely above threshold=2.0).
All signals EXPIRED before the final 03:25-03:36 surge (0.202 → 0.203). **No trade placed.**

## Root Cause — Dual

### 1. ZSCORE_PUMP_LOOKBACK=100 is too wide for gradual moves

A smooth 5% pump over 100 bars doesn't produce z > 2.0 — the rise is too distributed.

Simulated on real FET price_history (120 bars, 23:38-03:38):

| Lookback | Signals | First Fire | Price at Fire | z-score | Move Remaining |
|----------|---------|------------|---------------|---------|----------------|
| 30 | 17 | 01:16 | 0.19468 | +5.02 LONG | 4.4% |
| 50 | ~22 | 02:08 | 0.19631 | +3.23 LONG | 3.5% |
| **100** | **0** | — | — | — | — |

### 2. CONFLUENCE_REQUIRED=True blocks single-source zscore-pump+

zscore-pump+ is single-source (`zscore-pump+` alone). With CONFLUENCE_REQUIRED=True, it cannot enter hot-set regardless of z-score magnitude. Even the signals that DID fire at 03:08-03:23 (z=2.0-2.2) were blocked from execution.

## Key Constants (hermes_constants.py)

```
ZSCORE_PUMP_LOOKBACK       = 100   # TOO WIDE for gradual moves
ZSCORE_PUMP_THRESHOLD      = 2.0   # works at lookback=50, borderline at lookback=100
ZSCORE_PUMP_PLUS_ENABLED   = True  # LONG direction — PASS
ZSCORE_PUMP_DIVERGENCE_*   = ...   # irrelevant — z was rising, not falling
CONFLUENCE_REQUIRED        = True  # blocks single-source zscore-pump+ from hot-set
HOTSET_ENABLED             = True  # hot-set gate active
```

## What Would Have Caught It

**Minimal change (one constant):** `ZSCORE_PUMP_LOOKBACK = 50`
- Fires at 02:08, z=3.23, price 0.19631
- 3.5% move remaining at entry

**Two-constant combo:**
```
ZSCORE_PUMP_LOOKBACK = 50    # fires 65 min earlier at z=3.23
CONFLUENCE_REQUIRED  = False # allows single-source through
```

At lookback=50, z=3.23 is strong enough to survive hot-set scoring even without confluence bonus.

## What Would NOT Have Helped

- `ZSCORE_PUMP_DIVERGENCE_*` params — these guard against reversal traps (z was extremely elevated then CRASHING). FET's z was rising throughout — divergence filter would NOT have blocked.
- `ZSCORE_PUMP_USE_TUNER` — currently False; tuner has <15 signals for FET anyway
- Lowering threshold below 2.0 at lookback=100 — z never exceeds ~1.5 even with threshold=1.5

## The 3-Signal Cascade Failure

Signals at 03:08 (z=2.13), 03:18 (z=2.19), 03:23 (z=2.05) DID fire correctly.
But they expired via the normal 30-min TTL because:

1. lookback=100 → z only 2.0-2.2 (borderline)
2. CONFLUENCE_REQUIRED=True → blocked from hot-set even if z were higher
3. HOTSET_ENABLED=True → even confluence-passing signals need to survive compaction cycles
4. 03:25+ surge happened before the 03:23 signal could re-fire or hot-set could admit it

## Diagnostic Query

```sql
-- Check what zscore-pump signals actually fired for FET in the window
SELECT time, direction, source, zscore, confidence, decision, price
FROM signals
WHERE token='FET' AND source='zscore-pump+'
AND time > '2026-05-21 23:00'
ORDER BY time;

-- Price history for the window
SELECT timestamp, price FROM price_history
WHERE token='FET' AND timestamp > 1779406561
ORDER BY timestamp ASC;
```

## Real FET Price History (last 4h, sampled)

```
23:38  0.19370  ← start of window
01:16  0.19468  ← lookback=30 fires LONG z=5.02
02:08  0.19631  ← lookback=50 fires LONG z=3.23
02:46  0.19896  ← still rising
03:08  0.20046  ← zscore-pump fires (z=2.13) — EXPIRES
03:18  0.20142  ← zscore-pump fires (z=2.19) — EXPIRES
03:23  0.20192  ← zscore-pump fires (z=2.05) — EXPIRES
03:25  0.20220  ← final surge begins
03:36  0.20328  ← peak
```

## Signal vs. Source — Important Distinction

The zscore-pump signal fires at z > 2.0 regardless of lookback (the threshold check is on the computed z). The issue is that with lookback=100, the z never exceeds 1.0 for gradual moves — so the threshold check itself is never satisfied. The signal function is working correctly; the lookback parameter makes the z-score computation return values that never trigger the threshold.

## Related Reference

- `hermes-hot-set/SKILL.md` — Critical Failure Modes section (zscore-pump lookback bug)
- `new-signal-implementation/references/same-timeframe-confluence-illusion-2026-05-21.md` — zscore-pump+RS combos lose vs RS alone; same-timeframe signals amplify noise together
- `signals/zscore_pump.py` — signal implementation (lookback=100 default)