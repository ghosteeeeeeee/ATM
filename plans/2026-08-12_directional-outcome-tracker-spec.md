# Weather Vane: Directional Outcome Tracker — Spec

**Date:** 2026-08-12 (created), 2026-08-13 (implemented)
**Status:** IMPLEMENTED — Component 1 live, Component 2 unblocked

---

## Problem

When SHORT signals on a winning streak start losing in clusters, the market regime has shifted (bearish → bullish). The existing regime scanners (4h/15m) are lagging — they use slope-based detection and run on slow cycles. By the time they register the shift, the system has already eaten 3+ losses.

The trade outcomes themselves are a LEADING indicator — they tell you the weather changed before any slope calculation can.

## Solution: Weather Vane (3 Components)

### Component 1: Signal Gate — IMPLEMENTED

Monitors recent trade outcomes per direction (LONG/SHORT). When one direction starts losing in clusters, suppresses new signals in that direction via a score penalty.

**How it works:**
1. Every compaction round, `get_directional_outcome(direction)` queries the last 5 trades for that direction within a 30-minute rolling window
2. If 3+ of those 5 trades are losses OR win rate drops below 40%, a 0.7x score multiplier is applied to all signals in that direction
3. As old losses age out of the window and new wins come in, the penalty lifts automatically — no reset needed

**Params (hermes_constants.py):**
```python
DIRECTIONAL_OUTCOME_ENABLED = True
DIRECTIONAL_OUTCOME_WINDOW = 5            # last N trades per direction
DIRECTIONAL_OUTCOME_TIME_WINDOW = 30      # minutes (rolling window)
DIRECTIONAL_OUTCOME_LOSS_THRESHOLD = 3    # N losses to trigger
DIRECTIONAL_OUTCOME_WR_THRESHOLD = 40     # backup trigger: WR below this
DIRECTIONAL_OUTCOME_PENALTY = 0.7         # score multiplier when triggered
DIRECTIONAL_OUTCOME_MIN_TRADES = 3        # minimum trades before activating
```

**Integration:** `signal_compactor.py` — `_score_signal()` function, after `reg_mult`, before `source_mult`.

```python
final_score = score * survival_bonus * staleness_mult * reg_mult * dir_outcome_mult * source_mult * speed_mult
```

**Files:**
- `scripts/signal_compactor.py` — `get_directional_outcome()` + `dir_outcome_mult` in scoring
- `scripts/hermes_constants.py` — params (lines 614-620)

### Component 2: Position Shield — UNBLOCKED (not yet implemented)

When Weather Vane detects a regime shift, tighten trailing stops on existing counter-regime LOSING positions.

**How it would work:**
1. Weather Vane triggers → query open positions in losing direction
2. For each losing counter-regime position: tighten trailing stop from 0.80% to 0.30%
3. Set max_hold_minutes (30min) for counter-regime positions
4. Winners left alone — trailing already protecting them

**Status:** Was blocked by tpsl_utils.py bug (used global TRAILING_DISTANCE_PCT, not per-trade DB value). Bug fixed 2026-08-12 — `trailing_distance` parameter added to `compute_atr_sl_tp()`. Now unblocked.

**Params (proposed):**
```python
WEATHER_VANE_SHIELD_ENABLED = True
WEATHER_VANE_SHIELD_TRAILING_PCT = 0.0030   # 0.30% tightened from 0.80%
WEATHER_VANE_SHIELD_MAX_HOLD_MIN = 30
WEATHER_VANE_SHIELD_LOSING_ONLY = True
```

### Component 3: Recovery — INHERENT

No explicit recovery mechanism needed. The rolling window naturally recovers:
- Old losses age out of the 30-minute window
- New wins raise the win rate above threshold
- `dir_outcome_mult` returns to 1.0 automatically

## Data Flow

```
Trade closes → signal_outcomes table updated
    ↓
get_directional_outcome() queries last 5 trades per direction in 30min window
    ↓
3+ losses detected OR WR < 40%?
    ├─ YES → dir_outcome_mult = 0.7x (suppress signals in this direction)
    └─ NO  → dir_outcome_mult = 1.0 (normal operation)
    ↓
Rolling window recovers → unsuppress → normal operation
```

## Interaction with Existing Systems

| System | Relationship |
|--------|-------------|
| Regime scanners | Weather vane is faster (real-time vs 4h/15min lagging). Both coexist. |
| Loss cooldown | Per-token cooldown blocks re-entry on same token. Weather vane blocks ALL signals in losing direction. |
| Wrong-side learning | Complementary — wrong-side tracks per-token history, weather vane tracks per-direction recent outcomes. |
| Self-learner | Independent — self-learner adjusts params daily, weather vane responds in real-time. |

## What We Built (Summary)

The Weather Vane is a real-time regime shift detector that uses trade outcomes (not price slope) as its signal. It answers: "Is this direction still winning?" with a rolling 5-trade, 30-minute window.

**Key insight:** The regime scanners tell you what WAS happening (lagging slope). Trade outcomes tell you what IS happening (leading indicator).

**When it fires:** 3+ losses in last 5 trades within 30 minutes → suppress all new signals in that direction (0.7x score penalty).

**When it recovers:** Old losses age out, new wins come in → penalty lifts automatically.

**What it prevents:** The TIA/CFX pattern — entering SHORT at spike highs after the market shifted bullish. Also catches the PEOPLE pattern — low-price noise coins generating false signals.
