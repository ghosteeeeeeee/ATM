# accel_300 Silent Failure: Sustained Grind LOOKBACK/STALE_BARS Conflict (2026-06-14)

## Session Summary
UMA drove +3.74% over 5 hours. Clean one-bar EMA cross at bar ~170 (19:26 UTC).
accel_300 never fired. Root cause: LOOKBACK=30 is a hard gate that fires before STALE_BARS=60.

## The Debugging Process

1. Pulled price_history from `signals_hermes.db` (token, timestamp, price)
2. Computed EMA(300) from full history, extracted gap_pct series for last 550 bars
3. Simulated every gate step-by-step at each bar — identified G2 (was_below) as the blocking gate
4. Traced gap_pct back: first bar above EMA was bar ~170, but LOOKBACK=30 checks within 30 bars
5. Confirmed: every bar from 171-470 fails the was_below check (cross was 280 bars ago)

## Key Finding

```
ACCEL_300_LOOKBACK (G2 check) = 30  ← "was price below EMA in last 30 bars?"
ACCEL_300_STALE_BARS (late gate) = 60 ← "is cross older than 60 bars?"

On a clean sustained grind like UMA:
  - Cross at bar 170 (gap goes positive)
  - Bars 171-470: G2 always fails (never below EMA in last 30 bars)
  - STALE_BARS never gets a chance to matter (signal is blocked at G2)
```

The fix requires BOTH parameters to change together — raising LOOKBACK alone won't work
because the cross at 280 bars ago would then pass G2 but fail STALE_BARS=60.

## Practical Debugging Recipe

When accel_300 fires zero signals on a trending token:

```python
# Step 1: Identify if price is above EMA and when it crossed
# Step 2: Simulate G2 (was_below in LOOKBACK window) at each bar
# Step 3: If G2 blocks everything, the cross is too old for current LOOKBACK
# Step 4: Check STALE_BARS — does the stale gate even matter here?
# Step 5: The fix is LOOKBACK + STALE_BARS both raised, or the pattern is not accel-300able
```

## Fix (not applied — for T approval)
- `ACCEL_300_LOOKBACK`: 30 → 150
- `ACCEL_300_STALE_BARS`: 60 → 80

## Related Files
- `/root/.hermes/scripts/signals/accel_300.py` — detect_accel_300(), lines ~290-340 (G2 check)
- `/root/.hermes/data/signals_hermes.db` — price_history table (token, timestamp, price)
