# VVV LONG Reversal Trap — 2026-05-18

## What Happened

VVV trade: **LONG** entered at **$14.136**, hit SL at **$14.0365**, loss **-$0.35 (-0.70%)**, 3x leverage.

**Signal sources:** `rs-s213,zscore-pump+` — confidence **98%**

**Timeline (UTC):**
- ~02:55-03:10 — VVV pumped from ~$13.80 to ~$14.40
- 03:12:07 — LONG entered at $14.136 (peak of the bounce attempt)
- 03:15:06 — SL hit, price was already crashing through $14.00

## Root Cause

**The two signals conflicted in hidden direction:**

1. `rs-s213`: Support signal with **213 historical touches** — very old level. Source encodes touch count as `rs-s{touch_count}`. This level was BROKEN when price sliced through ~$14.00 on the way up to $14.40. The 213 touches are ancient/stale history — the level had 0 valid touches at time of signal.

2. `zscore-pump+`: Uses 20-bar z-score of closes. When price spiked to $14.40 then crashed back toward $14.00, the z-score would have turned **NEGATIVE** (current price below the inflated mean from the pump). This means the two signals were giving conflicting directional reads.

**The RS signal fires because** price bounced back to the $14.00 area — but this bounce was into a BROKEN support (dead cat bounce pattern). RS's `_level_recently_broken()` checks last 20 candles, but in a fast pump-and-dump the break may have happened just outside the window.

**The compounding error:** A support with 213 historical touches that was just sliced looks "strong" but is actually a trap. The high touch count is a red herring — validity (recency of touches) matters more than total count.

## Key Failure Modes

1. **Broken-level bounce trap**: RS detects a support near price, but doesn't properly invalidate when that support was sliced through in the same move
2. **Touch count as quality signal**: `rs-s213` encodes 213 touches as "strong level" — but 213 touches spread over days means most are stale; recency matters
3. **No cross-signal momentum gate**: RS and zscore-pump+ were BOTH positive but for different reasons — they should have been checked for conflict
4. **No "entry at exhaustion" filter**: Entry at $14.136 was exactly at the moment price failed to break out and reversed

## The Fix — Cross-Signal Momentum Gate

In `rs.py`'s `detect_rs_signal()`, add a momentum-confirmation check against z-score:

```
IF rs_direction == LONG and zscore < 0:  # conflicting momentum
    REJECT entry — bouncing into broken support, momentum fading
IF rs_direction == SHORT and zscore > 0:
    REJECT entry — rejecting against strength, likely to breakout higher
```

This catches the VVV case: RS fires LONG (support bounce), but zscore was already negative → reject.

## Files Involved

- `/root/.hermes/scripts/signals/rs.py` — R&S signal (source: `rs-s{touch_count}`)
- `/root/.hermes/scripts/signals/zscore_pump.py` — z-score momentum signal
- `/root/.hermes/scripts/signal_compactor.py` — hot-set scoring, confluence validation

## Tags

#reversal-trap #broken-level #rs-signal #zscore-pump #momentum-conflict