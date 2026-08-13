# Weather Vane v3 — Predictive Detection + CHoCH Integration

**Date:** 2026-08-13
**Status:** BACKTESTED — CHoCH integration proposed
**Based on:** market structure + signal patterns as leading indicators

---

## CEO Verdict (Original)

**APPROVE with modifications.** Same-hour-yesterday baseline, 65% threshold, 20 min baseline, 30min cooldown. Backtest before deploy.

## Backtest Results (7 days)

### Signal Volume Drop (65% threshold, same-hour-yesterday)
- 13 triggers in 7 days (~2/day)
- In triggered hours: 4W/3L, PnL +$0.07 (flat)
- 2 hours after triggers: 5W/4L, PnL -$0.07 (slightly negative)
- **Verdict: NOT a strong predictor.** Volume drops for many reasons (time of day, quiet market) not just regime shifts. Supplementary only.

### Confidence Trend (5+ point drop)
- Only 2 triggers in 7 days — too rare to be useful
- Both triggers had NO trades or WINNING trades
- Counter-intuitive: low-confidence SHORT trades actually have HIGHER WR (58.3% vs 51.5%)
- **Verdict: NOT useful.** Skip.

### What Worked vs What Didn't

| Layer | Predictive Power | Verdict |
|-------|-----------------|---------|
| Signal volume drop | Weak — too many false positives | Supplementary only (0.85x) |
| Confidence trend | Near-zero — too rare, counter-intuitive | Skip |
| Loss cluster (v2) | Strong — proven | Keep as primary |

---

## CHoCH Integration: Market Structure as Leading Indicator

### New Insight

CHoCH (Change of Character) is a **structural** leading indicator — it detects market structure shifts (HH_HL → LH_LL or vice versa) BEFORE losses accumulate. This is fundamentally different from signal volume (which measures our system's output) — CHoCH measures the MARKET's structure.

When a bullish CHoCH fires (LH_LL → HH_HL), the market structure has shifted bullish. SHORT signals will start losing. This happens BEFORE the loss cluster appears.

### How CHoCH Works

From `signals/hh_hl.py`:
- Detects swing highs/lows over last 8 swings
- Previous structure: swings[-8:-4] → HH_HL (bullish) or LH_LL (bearish)
- Current structure: swings[-4:] → HH_HL or LH_LL
- If structures differ → CHoCH confirmed

**CHoCH+ (bullish):** LH_LL → HH_HL (market turned bullish)
**CHoCH- (bearish):** HH_HL → LH_LL (market turned bearish)

### Weather Vane Integration

When a CHoCH fires AGAINST the current trade direction, suppress that direction:

```
CHoCH+ fires (bullish) → SHORT is now counter-structure → suppress SHORT
CHoCH- fires (bearish) → LONG is now counter-structure → suppress LONG
```

This is a STRUCTURAL prediction — the market has changed character, and trades against the new character will lose.

### Why This Is Better Than Signal Volume

| Signal Volume | CHoCH |
|--------------|-------|
| Measures our system's output | Measures market structure |
| Drops for many reasons (noise) | Only fires on genuine structure shifts |
| Reactive to signal generators | Leading indicator of price action |
| High false positive rate | Low false positive rate (structural) |

### Implementation

New function in signal_compactor.py:

```python
def get_choch_suppression(direction: str) -> float:
    """
    Check if a CHoCH signal has fired against this direction.
    Returns penalty multiplier (1.0 = no suppression, 0.75 = suppressed).
    """
    from hermes_constants import (
        CHOCH_WEATHER_VANE_ENABLED, CHOCH_WEATHER_VANE_PENALTY,
        CHOCH_WEATHER_VANE_WINDOW, CHOCH_WEATHER_VANE_MIN_CONFIDENCE,
    )
    if not CHOCH_WEATHER_VANE_ENABLED:
        return 1.0

    conn = sqlite3.connect(RUNTIME_DB, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT direction, confidence, created_at FROM signals
        WHERE signal_type = 'hh_hl_choch'
          AND created_at > datetime('now', '-' || ? || ' minutes')
        ORDER BY created_at DESC
    """, (CHOCH_WEATHER_VANE_WINDOW,))
    rows = cur.fetchall()
    conn.close()

    for choch_dir, conf, ts in rows:
        if conf < CHOCH_WEATHER_VANE_MIN_CONFIDENCE:
            continue
        # CHoCH fired AGAINST our direction
        if (choch_dir == 'LONG' and direction == 'SHORT') or \
           (choch_dir == 'SHORT' and direction == 'LONG'):
            conf_factor = min(conf / 88.0, 1.0)
            penalty = 1.0 - (1.0 - CHOCH_WEATHER_VANE_PENALTY) * conf_factor
            return penalty

    return 1.0
```

### Integration in _score_signal()

```python
# Layer 0: CHoCH structural prediction (NEW — highest predictive power)
choch_mult = get_choch_suppression(direction)
dir_outcome_mult = min(dir_outcome_mult, choch_mult)

# Layer 1: Signal volume drop (supplementary — weak predictor)
# Layer 2: Confidence trend (SKIP — not useful)
# Layer 3: Loss cluster (primary — proven reactive fallback)
```

### Params

```python
CHOCH_WEATHER_VANE_ENABLED = True
CHOCH_WEATHER_VANE_PENALTY = 0.75       # score multiplier when CHoCH fires against direction
CHOCH_WEATHER_VANE_WINDOW = 120          # minutes — how recent must the CHoCH be
CHOCH_WEATHER_VANE_MIN_CONFIDENCE = 70   # only suppress if CHoCH confidence >= this
```

---

## Updated Detection Layers

| Layer | Indicator | Speed | Predictive? | Status |
|-------|-----------|-------|-------------|--------|
| 0. CHoCH | Market structure flip | Fast (structural) | ✅ YES | **PROPOSED** |
| 1. Signal volume | SHORT signals/hour dropping | Fast | ✅ Yes (weak) | Backtested — supplementary |
| 2. Confidence trend | SHORT avg_conf declining | Fast | ❌ No | Backtested — **SKIP** |
| 3. Loss cluster | 3+ losses in 5 trades | Slow | ❌ No (reactive) | ✅ DONE (v2) |

**Recommended deployment:** CHoCH layer first (strongest predictor), signal volume as supplementary, skip confidence trend, keep loss cluster as fallback.

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add CHOCH_WEATHER_VANE_* params |
| `scripts/signal_compactor.py` | Add `get_choch_suppression()`, integrate into `_score_signal()` |
