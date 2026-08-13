# Weather Vane v3 — Predictive Signal Volume Detection

**Date:** 2026-08-13
**Status:** PROPOSED
**Based on:** signal generation rate as leading indicator of regime shifts

---

## Core Insight

The current Weather Vane is **reactive** — waits for losses to happen, then suppresses. But losses are a LAGGING indicator. By the time 3 losses accumulate, the regime has already shifted.

A better leading indicator: **signal generation rate per direction**. When the market turns bullish:
1. Signal generators stop finding SHORT setups (fewer SHORT signals generated)
2. SHORT signals that do fire get blocked by spike/RSI filters (higher rejection rate)
3. SHORT signal confidences trend down (weaker conviction)

These happen BEFORE losses. The market tells us the weather changed before our trades tell us.

---

## Three Detection Layers

| Layer | Indicator | Speed | Data Source |
|-------|-----------|-------|-------------|
| 1. **Signal Volume** | SHORT signals/hour dropping | Fastest (real-time) | `signals` table |
| 2. **Confidence Trend** | SHORT avg_conf declining | Fast (within hours) | `signals` table |
| 3. **Loss Cluster** | 3+ losses in 5 trades | Slow (after damage) | `signal_outcomes` table |

Layers 1-2 are **predictive** (detect before losses). Layer 3 is the existing **reactive** fallback.

---

## Layer 1: Signal Volume Detection

### How it works

Track the rolling average of SHORT (or LONG) signals generated per hour. When the rate drops significantly below the baseline, flag it as a potential regime shift.

### Baseline calculation

```python
# Baseline: average signals/hour over last 24 hours
baseline = total_signals_last_24h / 24

# Current: signals/hour in last 2 hours
current = total_signals_last_2h / 2

# Drop ratio: how much has the rate dropped?
drop_ratio = 1.0 - (current / baseline)  # 0.0 = no drop, 0.5 = 50% drop
```

### Trigger threshold

```python
SIGNAL_VOLUME_DROP_THRESHOLD = 0.5  # 50% drop from baseline → flag
```

If SHORT signals/hour drops by 50%+ from the 24h baseline, the market may have shifted bullish.

### Example

```
Baseline (24h avg): 200 SHORT signals/hour
Current (last 2h): 80 SHORT signals/hour
Drop ratio: 1.0 - (80/200) = 0.6 = 60% drop → TRIGGER
```

### Edge cases

- **Low activity hours (e.g., 3-5 AM):** Signal volume is naturally lower. Use time-of-day adjusted baseline (compare to same hour yesterday, not 24h average).
- **New token added:** Sudden volume spike followed by normalcy. Baseline adjusts over 24h.
- **System restart:** Gap in signal data. Skip detection until 24h of data accumulated.

### Params

```python
SIGNAL_VOLUME_ENABLED = True
SIGNAL_VOLUME_BASELINE_WINDOW = 24    # hours for baseline calculation
SIGNAL_VOLUME_CURRENT_WINDOW = 2      # hours for current rate
SIGNAL_VOLUME_DROP_THRESHOLD = 0.5    # 50% drop → flag
SIGNAL_VOLUME_MIN_BASELINE = 10       # minimum signals/hour to have a valid baseline
SIGNAL_VOLUME_PENALTY = 0.8           # score multiplier when triggered (milder than loss-based)
```

---

## Layer 2: Confidence Trend Detection

### How it works

Track the rolling average confidence of SHORT signals. When confidence trends down, the signal generators are less convinced about SHORT setups.

### Metric

```python
# Confidence trend: compare avg_conf of last 10 SHORT signals vs previous 10
recent_conf = avg(confidence of last 10 SHORT signals)
older_conf = avg(confidence of previous 10 SHORT signals)
conf_delta = recent_conf - older_conf  # negative = declining
```

### Trigger threshold

```python
SIGNAL_CONF_TREND_THRESHOLD = -5.0  # confidence dropped by 5+ points → flag
```

### Why this works

Signal generators assign confidence based on how well the setup matches their criteria. When the market shifts bullish:
- SHORT setups match fewer criteria → lower confidence scores
- The signal generators are "uncertain" about SHORT → confidence drops
- This happens BEFORE the signals start losing

### Params

```python
SIGNAL_CONF_TREND_ENABLED = True
SIGNAL_CONF_TREND_WINDOW = 10         # signals to compare
SIGNAL_CONF_TREND_THRESHOLD = -5.0    # confidence drop to trigger
SIGNAL_CONF_TREND_PENALTY = 0.85      # score multiplier (mild)
```

---

## Integration with Existing Weather Vane

The predictive layers (1-2) feed into the same `_score_signal()` function as the reactive layer (3):

```python
# In _score_signal():
dir_outcome_mult = 1.0

# Layer 1: Signal volume drop
if SIGNAL_VOLUME_ENABLED:
    vol_drop = get_signal_volume_drop(direction)
    if vol_drop >= SIGNAL_VOLUME_DROP_THRESHOLD:
        dir_outcome_mult = min(dir_outcome_mult, SIGNAL_VOLUME_PENALTY)

# Layer 2: Confidence trend
if SIGNAL_CONF_TREND_ENABLED:
    conf_delta = get_signal_conf_trend(direction)
    if conf_delta <= SIGNAL_CONF_TREND_THRESHOLD:
        dir_outcome_mult = min(dir_outcome_mult, SIGNAL_CONF_TREND_PENALTY)

# Layer 3: Loss cluster (existing)
if DIRECTIONAL_OUTCOME_ENABLED:
    losses, total, wr = get_directional_outcome(direction)
    # ... existing trigger + hysteresis + velocity logic ...
    dir_outcome_mult = min(dir_outcome_mult, loss_based_penalty)
```

The **minimum** penalty wins — if ANY layer flags the direction, the penalty applies. This means:
- Predictive layers can trigger BEFORE losses happen
- If predictive layers are wrong (false positive), the milder penalty (0.8x) is less damaging than the loss-based penalty (0.7x or 0.5x)
- If both predictive and reactive layers trigger, the stronger penalty (0.7x) applies

---

## Data Flow

```
Signal generated → signals table updated
    ↓
get_signal_volume_drop() queries signals/hour for this direction
    ↓
50%+ drop from 24h baseline?
    ├─ YES → dir_outcome_mult = 0.8 (mild penalty, early warning)
    └─ NO  → no action
    ↓
get_signal_conf_trend() queries confidence trend
    ↓
Confidence dropped 5+ points?
    ├─ YES → dir_outcome_mult = min(current, 0.85)
    └─ NO  → no action
    ↓
Existing loss-based Weather Vane (layers 3+)
    ↓
Minimum penalty applies
```

---

## Performance Considerations

The signal volume and confidence queries hit the `signals` table which can be large. Optimizations:

1. **Hourly aggregation:** Pre-compute signals/hour per direction every hour (new function `update_signal_volume_cache()`). Store in `data/signal_volume_cache.json`.
2. **Index:** Ensure `signals(created_at, direction)` index exists.
3. **Cache TTL:** Recompute volume stats every 5 minutes (not every compaction round).

### Cache structure

```json
{
  "SHORT": {
    "baseline_24h": 200,
    "current_2h": 80,
    "drop_ratio": 0.6,
    "avg_conf_recent": 81.2,
    "avg_conf_older": 86.5,
    "conf_delta": -5.3,
    "updated_at": "2026-08-13T22:00:00"
  },
  "LONG": { ... }
}
```

---

## Backtest Plan

1. Query last 7 days of signals table
2. For each hour, compute signal volume drop and confidence trend
3. Check if predictive triggers would have fired BEFORE loss clusters
4. Measure: how many hours of early warning did we get? How many false positives?

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add v3 params |
| `scripts/signal_compactor.py` | Add `get_signal_volume_drop()`, `get_signal_conf_trend()`, integrate into `_score_signal()` |
| `data/signal_volume_cache.json` | New: hourly signal volume cache |

---

## Risk

**False positives:** Signal volume can drop for reasons other than regime shift (system restart, low-activity period, new token onboarding). The milder penalty (0.8x) limits damage from false positives.

**Depends on signal quality:** If signal generators fire garbage signals regardless of market conditions, volume won't drop. The loss-based fallback (Layer 3) catches this.

**Cache staleness:** If the cache isn't updated regularly, the baseline becomes stale. Mitigated by 5-minute TTL and timestamp check.
