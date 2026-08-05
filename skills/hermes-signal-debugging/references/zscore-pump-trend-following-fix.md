# zscore_pump Trend-Following Fix — 2026-05-21

## Problem

`zscore_pump.py` fires after a move is already exhausted — it detects the peak, not the start.
Root cause: z-score measures distance from mean, which fires at the END of a move, not the beginning.

**Current formula:**
```python
z = (price - mean(lookback)) / stdev(lookback)
```

With `LOOKBACK=30` and `THRESHOLD=2.2`:
- Price spikes +8% above 30-bar mean
- z = 2.2 → signal fires
- But the move is already extended; this is mean-reversion, not trend-following

**The asymmetry problem:**
- z > threshold = price is ABOVE recent average → LONG
- This catches the TOP of a spike, not the BEGINNING
- Trend following needs to catch the breakout, not the exhaustion

## Fix — Make It True Trend Following

### Change 1: RAISE lookback (not lower)

| Before | After | Effect |
|--------|-------|--------|
| `ZSCORE_PUMP_LOOKBACK = 30` | `ZSCORE_PUMP_LOOKBACK = 80` | Structural trend, not noise |

Longer lookback = signal fires when price breaks a structural level, not just a short-term spike.
z=2.0 against a 120-bar mean means something. z=2.2 against 30 bars is just noise.

### Change 2: RAISE threshold (counter-intuitive)

| Before | After | Effect |
|--------|-------|--------|
| `ZSCORE_PUMP_THRESHOLD = 2.2` | `ZSCORE_PUMP_THRESHOLD = 2.5` | Only confirmed moves fire |

Higher threshold against longer lookback = only structural breakouts pass. Don't try to catch the beginning — let the trend prove itself first.

### Change 3: Add velocity filter (consecutive bars requirement)

The signal currently has no requirement that the trend actually sustained.
Add: require N consecutive bars in the same direction before firing.

```python
ZSCORE_PUMP_VELOCITY_BARS = 3  # need 3 consecutive up-bars before LONG fires
```

This prevents firing on one big spike that immediately reverses.

### Change 4: Asymmetric lookback (optional)

Crashes move faster than pumps. Consider:
- `ZSCORE_PUMP_LONG_LOOKBACK = 80` — buys need longer proof
- `ZSCORE_PUMP_SHORT_LOOKBACK = 40` — shorts can be faster

## Key Insight

**z-score fires at the WRONG end of the move by design:**
- z = (current - mean) / std
- When z > threshold, price is already far from mean = end of move
- To catch the START, need: breakout from range, not distance from mean

**The fix makes zscore_pump a structural breakout detector, not a momentum oscillator.**
This is the opposite of what the name suggests — the name "zscore pump" implies pumping into strength,
but the math fires at exhaustion.

## Recommended Constants

```python
ZSCORE_PUMP_LOOKBACK       = 80     # was 30 — structural trend, not noise
ZSCORE_PUMP_THRESHOLD      = 2.5   # was 2.2 — only confirmed breakouts
ZSCORE_PUMP_VELOCITY_BARS  = 3     # NEW — consecutive bars in direction before firing
```

## Verification

After patch, check:
1. zscore_pump fires on confirmed trends, not mid-spike pullbacks
2. Hot-set entries show `zscore-pump+` with co-signal confirmation
3. Winning trades: zscore_pump entry followed by sustained move in direction
4. Losing trades: zscore_pump entry at local peak with immediate reversal

## Related

- `trading/new-signal-implementation/SKILL.md` — signal architecture
- `references/zscore-pump-migration-2026-05-16.md` — migration notes