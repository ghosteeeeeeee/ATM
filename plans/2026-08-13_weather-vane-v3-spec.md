# Weather Vane v3 — Predictive Detection (CEO-Verified)

**Date:** 2026-08-13
**Status:** CEO-BACKTESTED — Z-Score + Acceleration is the winning approach
**Key Finding:** Surfing.md quadrants are REAL — z-score + acceleration together predict outcomes better than either alone

---

## CEO Backtest Results (Corrected)

### Method 5: Price Extremes — REVERSED from earlier analysis

Our earlier backtest had data alignment issues. CEO's corrected data:

| Position | Trades | WR | Total PnL |
|----------|--------|-----|-----------|
| LONG at extreme | 99 | **71.7%** | **+$4.00** |
| SHORT at extreme | 82 | **79.3%** | **+$3.23** |
| LONG normal | 329 | 40.7% | -$3.26 |
| SHORT normal | 357 | 36.4% | -$5.13 |

**Extreme positions are the WINNERS.** Chasing works in this system. Do NOT suppress extremes.

### Idea A: Z-Score + Acceleration — THE PREDICTIVE SIGNAL

From surfing.md wave-turn detection. Data validated by CEO:

| Quadrant | Trades | WR | Avg PnL | Interpretation |
|----------|--------|-----|---------|----------------|
| LONG z>0 + accel>0 | 89 | **76.4%** | **+$0.041** | Momentum building → BEST for LONG |
| LONG z>0 + accel<0 | 70 | 52.9% | +$0.013 | Top forming → weaker |
| LONG z<0 + accel>0 | 68 | 30.9% | -$0.022 | Bottom building → too early |
| LONG z<0 + accel<0 | 97 | **24.7%** | **-$0.027** | Collapsing → WORST for LONG |
| SHORT z>0 + accel>0 | 101 | **23.8%** | **-$0.032** | Wrong direction → WORST for SHORT |
| SHORT z>0 + accel<0 | 47 | 36.2% | -$0.020 | Overbought fading → weak |
| SHORT z<0 + accel>0 | 93 | 52.7% | +$0.005 | Oversold bouncing → mediocre |
| SHORT z<0 + accel<0 | 79 | **63.3%** | **+$0.018** | Downward momentum → BEST for SHORT |

**The pattern is crystal clear:**
- LONG wins when z>0 AND accel>0 (momentum building)
- SHORT wins when z<0 AND accel<0 (downward momentum)
- Both lose when z and accel disagree (wrong direction)

---

## The Surfing.md Quadrant System — Explained

From `brain/surfing.md`:

```
Z-Score  = (current_price - 20h_mean) / 20h_std
           → How far price has drifted from recent average
           → Positive = price high relative to history
           → Negative = price low relative to history

Speed    = price_velocity_5m
           → How fast price is moving RIGHT NOW

Accel    = price_acceleration (rate of change of velocity)
           → Is velocity increasing or decreasing?
```

### The 4 Quadrants:

| Z-Score | Speed | Accel | Meaning | Action |
|---------|-------|-------|---------|--------|
| Near 0 | Low | Flat | Range-bound, no wave | Sit out |
| Negative | HIGH | Positive | Wave building UP — bottom picked | Paddle for LONG |
| Negative | LOW | Positive | Wave building but slow | Wait, too early |
| Positive | HIGH | Negative | Wave cresting — top in | Take SHORT |
| Positive | LOW | Negative | Wave collapsing from high | Exit LONGs |
| Near 0 | HIGH | Positive | Mid-range explosion building | Confirm with confluence |

**The key insight:** Z-score tells you WHERE in the range price is. Acceleration tells you if the wave is building or collapsing. Together they predict the NEXT move.

**Example from real data:**
- LONG at z>0 + accel>0: 76.4% WR (price is high AND accelerating up → strong trend)
- SHORT at z>0 + accel>0: 23.8% WR (price is high AND accelerating up → wrong direction for SHORT)

---

## Data Already Available

From `token_speeds` table (populated by speed_tracker.py):

```sql
SELECT token, 
    price_velocity_5m,      -- speed
    price_acceleration,     -- acceleration
    speed_percentile,       -- rank vs universe
    is_stale,               -- flat for 3+ hours
    wave_phase,             -- 'accelerating', 'falling', 'neutral'
    momentum_score          -- 0-100 momentum score
FROM token_speeds;
```

And from `signals` table:
```sql
SELECT token, z_score, z_score_tier FROM signals;
```

**No new data sources needed.** The predictive data is already being collected.

---

## Implementation: Z-Score + Acceleration Filter

### New function in signal_compactor.py:

```python
def get_zscore_accel_penalty(token: str, direction: str) -> float:
    """
    Surfing.md quadrant-based penalty.
    Returns penalty multiplier based on z-score + acceleration alignment.
    
    Aligned (momentum with direction): 1.0 (no penalty)
    Misaligned (momentum against direction): 0.7 (penalty)
    """
    from hermes_constants import ZSCORE_ACCEL_ENABLED, ZSCORE_ACCEL_PENALTY
    if not ZSCORE_ACCEL_ENABLED:
        return 1.0
    
    # Get z-score from token_speeds or signals
    conn = sqlite3.connect(RUNTIME_DB, timeout=5)
    cur = conn.cursor()
    cur.execute("""
        SELECT price_acceleration, speed_percentile, wave_phase
        FROM token_speeds WHERE token = ?
    """, (token.upper(),))
    speed_row = cur.fetchone()
    
    cur.execute("""
        SELECT z_score FROM signals
        WHERE token = ? ORDER BY created_at DESC LIMIT 1
    """, (token.upper(),))
    z_row = cur.fetchone()
    conn.close()
    
    if not speed_row or not z_row:
        return 1.0
    
    accel = speed_row[0] or 0
    z_score = z_row[0] or 0
    
    # Surfing.md quadrants:
    # Aligned: LONG + z>0 + accel>0, SHORT + z<0 + accel<0
    # Misaligned: LONG + z<0 + accel<0, SHORT + z>0 + accel>0
    
    if direction == 'LONG':
        if z_score > 0.5 and accel > 0:
            return 1.0  # aligned — momentum building for LONG
        elif z_score < -0.5 and accel < 0:
            return ZSCORE_ACCEL_PENALTY  # collapsing — wrong for LONG
    elif direction == 'SHORT':
        if z_score < -0.5 and accel < 0:
            return 1.0  # aligned — downward momentum for SHORT
        elif z_score > 0.5 and accel > 0:
            return ZSCORE_ACCEL_PENALTY  # rising — wrong for SHORT
    
    return 1.0  # neutral quadrant — no penalty
```

### Integration in _score_signal():

```python
# Surfing.md quadrant filter: z-score + acceleration alignment
zscore_accel_mult = get_zscore_accel_penalty(token, direction)
dir_outcome_mult = min(dir_outcome_mult, zscore_accel_mult)
```

### Params

```python
ZSCORE_ACCEL_ENABLED = True
ZSCORE_ACCEL_PENALTY = 0.7    # penalty when z-score + accel disagree with direction
```

---

## Updated Detection Layers

| Layer | Indicator | Predictive Power | Status |
|-------|-----------|-----------------|--------|
| 0. Z-Score + Acceleration | Surfing.md quadrants | **HIGH** (76% vs 24% WR) | **IMPLEMENT NOW** |
| 1. Structure shift | Market structure flip | Medium | PROPOSED (14d backtest needed) |
| 2. Consecutive losses | Per-token loss streaks | Moderate (5pt WR gap) | PROPOSED |
| 3. Loss cluster | Directional outcome tracker | Proven (v2) | ✅ DONE |

**Z-Score + Acceleration is the strongest predictive signal** — 52-point WR gap between best and worst quadrants. And the data is already being collected.

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add ZSCORE_ACCEL_* params |
| `scripts/signal_compactor.py` | Add `get_zscore_accel_penalty()`, integrate into `_score_signal()` |
