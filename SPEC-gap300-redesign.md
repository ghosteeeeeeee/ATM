# SPEC: gap-300 Signal Redesign — State Machine Model

## Overview

The gap-300 signal tracks EMA(300)/SMA(300) widening between price bars. Unlike the
original one-shot-cross detection, the redesigned signal uses a state machine that
"keeps the ball in play" — once a cross is detected, the system tracks the gap
through widening and contracting phases, firing when widening resumes.

## Constants

| Constant | Value | Note |
|----------|-------|------|
| PERIOD | 300 | EMA/SMA lookback |
| MIN_GAP_PCT | 0.05 | Threshold to detect cross |
| COOLDOWN_MIN | 5 | Min bars between fires |
| MOMENTUM_BARS | 10 | Lookback for momentum check |
| COLLAPSE_PCT | 0.70 | Fire only if gap > peak × this |
| LOOKBACK_1M | 700 | 1m price bars to fetch |

## State Machine

```
                    ┌─────────────────────────────────────────────────────┐
                    │                                                     │
                    │   gap falls below threshold                          │
                    │   (below MIN_GAP_PCT)                                │
                    │                                                     ▼
NO_SIGNAL ──────► TRACKING_LONG ◄─────────────────────────────────────┐ │
      ▲           │             │                                        │ │
      │           │      gap cross above                                │ │
      │           │      MIN_GAP_PCT                                     │ │
      │           ▼             │                                        │ │
      │     TRACKING_SHORT      │ opposite cross replaces               │ │
      │             │           ▼                                        │ │
      │             │    (any direction)                                 │ │
      │             │                                                     │ │
      │             │    All conditions met:                              │ │
      │             │    - gap widening (gap_pct > prev_gap_pct)         │ │
      │             │    - momentum agrees                                │ │
      │             │    - not collapsed (gap > peak × 0.70)             │ │
      │             │    - cooldown expired                              │ │
      │             │                                                     │ │
      │             ▼                                                     │ │
      │    SIGNAL_ACTIVE_LONG ◄──────────────────────────────────────────┘ │
      │           │             │                                          │
      │           │       gap contracts                                    │
      │           │       (gap_pct ≤ prev_gap_pct)                         │
      │           │       or opposite cross                                │
      │           ▼       or collapsed                                     │
      │    back to TRACKING_LONG ───────────────────────────────────────────►│
      │           │                                                         │
      └───────────┴─────────────────────────────────────────────────────────┘
                          (gap falls below MIN_GAP_PCT)
```

## States

### NO_SIGNAL
- Initial/idle state
- No valid cross in the current direction
- Gap is below MIN_GAP_PCT threshold
- Transitions: any cross above threshold → TRACKING_[DIR]

### TRACKING_[DIR]
- Cross detected, tracking gap
- Not yet firing
- Cross is "alive" — ball is in play
- Conditions evaluated each bar to fire:
  - `gap_pct > prev_bar_gap_pct` (widening)
  - `momentum_ret` agrees with direction (positive for LONG, negative for SHORT)
  - `gap_pct > peak_gap_since_cross × COLLAPSE_PCT` (not collapsed)
  - `cooldown_expired`
- Transitions:
  - All conditions met → SIGNAL_ACTIVE_[DIR]
  - Opposite cross → TRACKING_[OPPOSITE] (replace, reset peak tracking)
  - Gap below threshold → NO_SIGNAL (reset completely)

### SIGNAL_ACTIVE_[DIR]
- Gap conditions met, signal is firing
- Peak gap is tracked (not reset during this active phase)
- Transitions:
  - Gap contracts (gap_pct ≤ prev_bar_gap_pct) → TRACKING_[DIR] (signal stops, cross still alive, peak preserved)
  - Opposite cross → TRACKING_[OPPOSITE] (replace signal, new cross resets peak)
  - Gap below threshold → NO_SIGNAL (reset completely)
  - Collapsed (gap_pct < peak × 0.70) → TRACKING_[DIR] (stops firing, cross still alive, peak preserved, NOT reset)

## Per-Bar Checks (each scan tick)

For each token, for the most recent completed 1m bar:

```
1. Compute gap_pct (current and previous bar)
2. If state == NO_SIGNAL:
     - If gap_pct crosses above MIN_GAP_PCT → set TRACKING_[DIR]
     - Else do nothing
3. If state == TRACKING_[DIR] or SIGNAL_ACTIVE_[DIR]:
     - Check opposite cross: if opposite direction gap_pct crosses above MIN_GAP_PCT
       → replace state with TRACKING_[OPPOSITE], reset peak tracking
     - Else if gap_pct below MIN_GAP_PCT → reset to NO_SIGNAL
     - Else:
       - widening = gap_pct > prev_gap_pct
       - momentum_ok = dir_sign × ret >= 0 (ret over last MOMENTUM_BARS)
       - not_collapsed = gap_pct > peak_gap × COLLAPSE_PCT
       - cooldown_ok = now > cooldown_until
       - if widening AND momentum_ok AND not_collapsed AND cooldown_ok:
         → fire signal, set cooldown, transition to SIGNAL_ACTIVE_[DIR]
       - elif gap contracted OR collapsed:
         → transition to TRACKING_[DIR] (cross still alive)
```

## Persistence

State is tracked per-token in a DB table `gap300_state`:

```sql
CREATE TABLE gap300_state (
    token      TEXT PRIMARY KEY,
    state      TEXT NOT NULL,          -- 'NO_SIGNAL','TRACKING_LONG','TRACKING_SHORT',
                                        -- 'SIGNAL_ACTIVE_LONG','SIGNAL_ACTIVE_SHORT'
    direction  TEXT,                   -- 'LONG' or 'SHORT' or NULL
    peak_gap   REAL DEFAULT 0,         -- peak gap_pct since cross
    cross_ts   INTEGER,                -- unix timestamp of cross detection
    cooldown_until INTEGER,            -- unix timestamp of cooldown expiry
    updated_at  INTEGER                -- last update time
);
```

State is written to DB after every scan tick (every 1 minute).

## Gap and Momentum Calculations

```
gap_pct(i)    = |EMA(i) - SMA(i)| / close(i) × 100
raw_gap(i)    = EMA(i) - SMA(i)          -- signed; positive = LONG
gap_widening  = gap_pct(current) > gap_pct(previous)
momentum_ret  = (close(last) / close(last - MOMENTUM_BARS) - 1) × 100
momentum_ok   = (direction == 'LONG' and momentum_ret >= 0)
             OR (direction == 'SHORT' and momentum_ret <= 0)
```

## Signal Output

When firing, emit to signal DB via `add_signal()`:

```
signal_type = 'ema_sma_gap_300_long'  or 'ema_sma_gap_300_short'
source      = 'gap-300+'              or 'gap-300-'
direction   = 'LONG'                  or 'SHORT'
confidence  = 60 + min(15, (gap_pct - 0.05) × 200)  -- 60-75 range
```

## Edge Cases

1. **Quick flip (LONG fires, SHORT crosses 2 bars later):** SHORT replaces LONG immediately.
   No minimum time gate — the gap itself acts as the filter (shortening gap can't
   satisfy widening conditions for SHORT at the same time as it breaks them for LONG).

2. **Collapse then re-widen same direction:** If gap collapses 30%+, SIGNAL_ACTIVE
   reverts to TRACKING. If gap re-widens before an opposite cross, it fires again.
   Peak is reset only on a new cross or opposite cross.

3. **Gap below threshold then re-crosses same direction:** If gap falls below 0.05%
   entirely → NO_SIGNAL. New cross = fresh TRACKING.

4. **Warmup:** First PERIOD valid gap bars are required before any cross can fire.
   The window-span guard and bar-gap guard in the original code are preserved.

5. **Data gap (missing 1m bars):** If the bar-gap guard triggers, skip the scan tick
   entirely. State is preserved in DB. When prices resume, state is picked up from DB.

## Decisions Made

- **Momentum:** Returns-based (close[-1]/close[-N] - 1) × 100, same as original
- **Peak on collapse:** peak_gap is NOT reset on collapse. The original cross's peak
  is preserved. The ball is still in play (no opposite cross), but re-firing requires
  the gap to re-widen back toward the ORIGINAL peak (within 30% of it). This sets a higher
  bar for re-firing after a collapse, which filters out choppy/thin signals.
- **Cooldown:** 5 minutes from last fire (not from last bar where conditions were met)
- **Confidence:** `60 + min(15, (gap_pct - 0.05) × 200)` — gap strength maps to 60-75 confidence
- **Opposite cross:** ALLOW on any sign flip (raw_gap changes sign). Opposite cross
  REPLACES tracked direction immediately when raw_gap crosses zero, regardless of gap
  width. Blocking (requiring gap_prev < MIN_GAP_PCT) was tested and rejected:
  - Backtested across 24 tokens, ~56 days of data
  - Blocking fires the WRONG direction during gap transitions around MIN_GAP_PCT
  - BTC 03-24 case: Blocking fires 21 LONG fires during the actual SHORT trend
  - Allow fires 39 SHORT fires correctly — 0 LONG
  - Allow adds 3,787 more fires total; fires 2,880 more SHORTs (better trend capture)
  - 844 bars where the two strategies fire opposite directions — Allow is correct in
    all observed cases because it doesn't lock into wrong-direction trends
  - The sign-flip condition is: `raw_gap × opp_sign < 0` (raw_gap changes sign)
