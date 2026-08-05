# rs.py Signals Stopped After Code Changes — June 14, 2026

## Problem
RS signals were firing previously but stopped after recent code changes (commits 868add3 and 4d8c96c). The assumption was "ATR threshold too tight" — **but that is wrong**. The ATR threshold was never changed and is not the root cause.

## What Actually Happened

### Change 1: Bounce confirmation became a HARD gate (commit 868add3)
**Before:** A level that was recently broken could fire via the broken-path signal even with `bounce=False`. The `rs-s-broken` and `rs-r-broken` paths existed as independent signals.

**After:** `if not bounces: nearest_support = None` — if no bounce confirmation exists, the level is completely rejected BEFORE the broken-path logic runs. Levels that previously fired as `rs-s-broken` (SHORT) or `rs-r-broken` (LONG) are now blocked entirely.

```python
# CURRENT CODE — bounces is a hard gate
if not bounces:
    nearest_support = None   # ← blocks ALL broken-path signals
else:
    if broken and price > level:
        broken = False; bounces = True  # recovery path
    if broken:
        if not RS_BROKEN_SHORT_ENABLED:
            nearest_support = None     # still blocked
```

### Change 2: Swing high/low detection is more restrictive (commit 868add3)
**Before:** any point at or above the trailing rolling max qualified as a swing high.
**After:** requires `no higher price in the window ahead` (forward-looking check). Fewer swing levels are found.

```python
# OLD — trailing only
swing_highs = [(i, highs[i]) for i in range(window, n - window)
               if highs[i] == roll_high[i]]

# NEW — centered (trailing + forward confirmation)
swing_highs = [(i, highs[i]) for i in range(window, n - window - 1)
               if highs[i] == roll_high[i] and highs[i] >= forward_high[i]]
```

### Change 3: Level selection — recency replaced distance as primary filter (commit 868add3)
**Before:** distance was primary — all levels within 0.7 ATR ranked by proximity.
**After:** recency_score is primary, distance only breaks ties.

```python
# OLD — distance primary
if _price_near_level(...) and dist_pct < best_support_dist:
    best_support_dist = dist_pct
    nearest_support = (level, touch_count)

# NEW — recency primary
if recency > best_support_recency or \
   (recency == best_support_recency and dist_pct < best_support_dist):
    best_support_recency = recency
    best_support_dist = dist_pct
    nearest_support = (level, touch_count)
```

### Change 4: Recency score formula flipped (commit 868add3)
**Before:** `recent + K × ancient` (ancient touches weighted more)
**After:** `recent × K + ancient` (recent touches weighted more)
```python
# OLD (ancient weighted more)
recency_score = recency_touches + RS_RECENCY_BOOST_K * ancient_touches

# NEW (recent weighted more)
recency_score = recency_touches * RS_RECENCY_BOOST_K + ancient_touches
```

### Change 5: Bounce path simplified (commit 868add3)
**Before:** checked both candle body direction (close > open for LONG) AND follow-through.
**After:** only the follow-through path remains. On synthesized candles (open=close), this is the only valid path, but it makes the bounce requirement harder to satisfy.

### Change 6: Cluster anchor vs running average (commit 4d8c96c)
**Before:** new levels compared against running average of current cluster.
**After:** new levels compared against the anchor (first level) of the cluster.

This creates MORE clusters (not fewer), which means fewer levels pass `RS_MIN_TOUCHES` after clustering, since touches are aggregated per cluster.

## Why the Threshold Hypothesis Was Wrong
- RS_PROXIMITY_K was 0.7 before the code changes and 0.7 after
- The audit tested 83 tokens and found closest levels at 2.7–76 ATR away — same would have been true before the changes
- The signal previously fired despite the same threshold because the broken-path signals (rs-s-broken, rs-r-broken) didn't require bounce confirmation
- Those paths are now blocked, so the threshold was never the blocking factor — the bounce gate is

## Diagnostic
If RS signals stopped after a code change and the audit shows "closest level X ATR away":
1. Do NOT assume threshold calibration is the fix
2. Check if bounce confirmation (`_bounce_confirmation`) is the blocker
3. Check if the broken-path signals (rs-s-broken, rs-r-broken) were the ones previously firing
4. The threshold (RS_PROXIMITY_K) is a separate calibration question from the logic gate changes

## Key Files
- `/root/.hermes/scripts/signals/rs.py`
- `/root/.hermes/scripts/hermes_constants.py` — RS_PROXIMITY_K, RS_BROKEN_SHORT_ENABLED, RS_BROKEN_RESISTANCE_LONG_ENABLED