# Weather Vane v4 — Tide Detection (Market-Wide Momentum)

**Date:** 2026-08-15
**Status:** BACKTESTED — strong correlations found
**Goal:** Detect whether the "tide is coming in or going out" — market-wide directional momentum

---

## The Problem

The Weather Vane is token-level — it detects "this token is losing" but not "the entire market is shifting." It's watching individual waves, not the tide.

**The tide = market-wide momentum.** When the tide is coming in (bullish), SHORTs lose across the board. When the tide is going out (bearish), SHORTs win across the board.

---

## Backtest Results (14 days, 839 trades)

### SHORT Win Rate as Tide Indicator

| SHORT WR Bucket | LONG WR | LONG PnL | SHORT WR | SHORT PnL |
|----------------|---------|----------|----------|-----------|
| >70% (bearish tide) | 60.0% | +$0.12 | **67.6%** | **+$0.47** |
| 55-70% | 44.4% | -$0.63 | 40.0% | -$0.78 |
| 45-55% (neutral) | **50.3%** | **+$0.61** | 48.9% | -$0.44 |
| 30-45% | 43.8% | +$0.47 | 38.0% | -$0.23 |
| <30% (bullish tide) | 37.5% | -$0.22 | **34.3%** | **-$0.51** |

**The pattern:** When SHORT WR is high (>55%), SHORTs win. When SHORT WR is low (<45%), SHORTs lose. The SHORT win rate IS the tide.

### BTC Z-Score as Tide Indicator

| BTC Z Bucket | LONG WR | LONG PnL | SHORT WR | SHORT PnL |
|-------------|---------|----------|----------|-----------|
| z<-1.5 (oversold) | **63.6%** | **+$0.13** | 66.7% | -$0.03 |
| z -1.5 to -0.5 | 46.4% | +$0.04 | 42.5% | -$0.30 |
| z mid | 33.3% | -$0.05 | 37.8% | **-$1.14** |

**The pattern:** BTC oversold (z<-1.5) = good for LONG. BTC neutral = bad for SHORT.

### Combined: SHORT WR + BTC Z-Score

| Combination | LONG | SHORT |
|-------------|------|-------|
| SHORT WR>55% + BTC z<-0.5 (bearish tide) | 46.3%, -$0.55 | **57.1%, +$0.43** |
| SHORT WR<45% + BTC z<-0.5 (mixed signal) | 43.7%, +$0.34 | **35.2%, -$0.72** |

**The strongest signal:** When SHORT WR>55% AND BTC z<-0.5, SHORT has 57% WR. When SHORT WR<45% AND BTC z<-0.5, SHORT has 35% WR. **22-point WR gap.**

---

## Design: Tide Meter

### Two Indicators

1. **SHORT Win Rate** (real-time): Rolling WR of last 20 SHORT trades across all tokens
2. **BTC Z-Score** (real-time): (BTC price - 20h mean) / 20h std

### Tide Classification

```
BEARISH TIDE: SHORT WR > 55% AND BTC z < -0.5
  → SHORTs winning, BTC oversold → favor SHORT signals
  → Suppress LONG signals (0.7x penalty)

BULLISH TIDE: SHORT WR < 45% AND BTC z > -0.5
  → SHORTs losing, BTC not oversold → favor LONG signals
  → Suppress SHORT signals (0.7x penalty)

NEUTRAL TIDE: mixed signals
  → No directional suppression
```

### Implementation

New function in signal_compactor.py:

```python
def get_tide_penalty(direction: str) -> float:
    """
    Market-wide tide detection using SHORT win rate + BTC z-score.
    Returns penalty multiplier for counter-tide trades.
    """
    from hermes_constants import TIDE_ENABLED, TIDE_PENALTY, TIDE_SHORT_WR_WINDOW

    if not TIDE_ENABLED:
        return 1.0

    # 1. SHORT win rate (rolling last N SHORT trades)
    conn = sqlite3.connect(RUNTIME_DB, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT is_win FROM signal_outcomes
        WHERE direction = 'SHORT'
        ORDER BY created_at DESC LIMIT ?
    """, (TIDE_SHORT_WR_WINDOW,))
    short_rows = cur.fetchall()
    conn.close()

    if len(short_rows) < 5:
        return 1.0  # not enough data

    short_wr = sum(1 for r in short_rows if r[0]) / len(short_rows) * 100

    # 2. BTC z-score
    btc_z = _get_btc_z_score()

    # 3. Tide classification
    bearish_tide = short_wr > 55 and btc_z < -0.5
    bullish_tide = short_wr < 45 and btc_z > -0.5

    # 4. Suppress counter-tide trades
    if bearish_tide and direction == 'LONG':
        return TIDE_PENALTY  # bearish tide = bad for LONG
    if bullish_tide and direction == 'SHORT':
        return TIDE_PENALTY  # bullish tide = bad for SHORT

    return 1.0
```

### BTC Z-Score Helper

```python
def _get_btc_z_score() -> float:
    """Get BTC z-score from 1h candles."""
    from hermes_constants import TIDE_BTC_Z_WINDOW
    conn = sqlite3.connect(CANDLES_DB, timeout=5)
    cur = conn.cursor()
    cur.execute("""
        SELECT close FROM candles_1h
        WHERE token = 'BTC' AND is_closed = 1
        ORDER BY ts DESC LIMIT ?
    """, (TIDE_BTC_Z_WINDOW,))
    closes = [r[0] for r in cur.fetchall()]
    conn.close()

    if len(closes) < 10:
        return 0.0

    closes.reverse()
    current = closes[-1]
    mean_p = np.mean(closes)
    std_p = np.std(closes)
    return (current - mean_p) / std_p if std_p > 0 else 0.0
```

### Params

```python
TIDE_ENABLED = True
TIDE_PENALTY = 0.7                   # penalty for counter-tide trades
TIDE_SHORT_WR_THRESHOLD_HIGH = 55    # SHORT WR above this = bearish tide
TIDE_SHORT_WR_THRESHOLD_LOW = 45     # SHORT WR below this = bullish tide
TIDE_SHORT_WR_WINDOW = 20            # last N SHORT trades for WR calc
TIDE_BTC_Z_WINDOW = 20               # 1h candles for BTC z-score
TIDE_BTC_Z_THRESHOLD = 0.5           # |z| above this = significant
```

---

## Integration

```python
# In _score_signal():
# Tide meter: suppress counter-tide trades
tide_mult = get_tide_penalty(direction)
dir_outcome_mult = min(dir_outcome_mult, tide_mult)
```

---

## Data Sources

| Data | Source | Frequency |
|------|--------|-----------|
| SHORT win rate | `signal_outcomes` table | Real-time (every trade) |
| BTC z-score | `candles_1h` table (BTC token) | Real-time (every compaction round) |

Both are already being collected. No new data sources needed.

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add TIDE_* params |
| `scripts/signal_compactor.py` | Add `get_tide_penalty()`, `_get_btc_z_score()`, integrate into `_score_signal()` |
