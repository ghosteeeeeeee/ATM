# Breakout Ignition Signal — Spec

**Author:** CEO (Heres Trading System)
**Date:** 2026-09-08
**Type:** Early-stage breakout signal (LONG-only)
**Reference:** ATOM 2026-09-08 — open-skies fired at $1.8143 (11.6% into move)

---

## 1. Problem

Open-skies fires AFTER the trend is established:
- ATOM moved from $1.628 to $1.817 (+11.6%) before open-skies fired
- The breakout started at 11:25 with a volume spike (70K vs normal 5-10K)
- Open-skies fired at 18:14 — 7 hours later

We need a signal that catches the **exact moment** the breakout starts.

---

## 2. The Breakout Pattern (ATOM Reference)

```
00:00-11:20  Consolidation: $1.628-$1.680 (flat, low volume)
11:25        VOLUME SPIKE: 70K (7-14x normal) ← THIS IS THE MOMENT
11:30        Price breaks above $1.68 resistance
11:35        Rally continues: $1.692 → $1.753 (+4.6% in 30min)
12:40        pump-chain fires at $1.758 (1h late)
18:14        open-skies fires at $1.814 (7h late)
```

**The ideal entry:** 11:25-11:30, when volume spikes and price breaks resistance.

---

## 3. Signal Concept: Breakout Ignition

**Thesis:** The first volume spike that breaks above a consolidation range is the ignition point for a new trend. Catch it early, ride the move.

### Detection Logic

```python
def detect(token):
    """
    1. Volume spike: current bar volume > 3x 20-bar average
    2. Sustained: at least 2 of last 3 bars have elevated volume (>2x avg)
    3. Price breakout: close > 20-bar high (breaks above consolidation)
    4. Trend filter: close > 20-bar EMA (aligned with trend)
    5. RSI filter: 40 < RSI < 70 (not overbought, room to run)
    6. No resistance nearby: nearest resistance > 1% above (open skies ahead)
    """
```

### Why This Works (vs Open-Skies)

| | Open-Skies | Breakout Ignition |
|---|---|---|
| **Entry timing** | After trend established | At the START of breakout |
| **Requires** | 0 resistance, 20-bar return > 1.5% | Volume spike + price break |
| **ATOM entry** | $1.814 (11.6% into move) | $1.680 (0% — start of move) |
| **Missed move** | 11.6% | 0% |

---

## 4. Comparison with Existing Signals

### vs pump_catcher
- pump_catcher uses velocity (price change over N bars)
- Breakout ignition uses VOLUME as primary trigger
- Volume spike is a leading indicator — price follows volume
- pump_catcher can fire on moves that are already extended

### vs volume_breakout
- volume_breakout checks for volume > threshold
- Breakout ignition requires SUSTAINED volume (2+ bars) + price confirmation
- More reliable than single-bar volume spikes

### vs pump-chain
- pump-chain tracks capital rotation flows
- Breakout ignition is simpler — just volume + price action
- Fires 1h earlier than pump-chain (11:30 vs 12:40 for ATOM)

---

## 5. Detection Details

### Condition 1: Volume Spike
```python
vol_current = candles[-1][5]  # current bar volume
vol_avg = mean(candles[-20:])  # 20-bar average
vol_spike = vol_current / vol_avg
# Must be > 3x average
```

### Condition 2: Sustained Volume
```python
# At least 2 of last 3 bars must have volume > 2x average
recent_vols = [c[5] for c in candles[-3:]]
elevated_count = sum(1 for v in recent_vols if v > vol_avg * 2)
# Must be >= 2
```

### Condition 3: Price Breakout
```python
# Close must exceed the 20-bar high (breaks above consolidation)
high_20 = max(c['high'] for c in candles[-20:])
# Current close must be above this
```

### Condition 4: Trend Filter
```python
# Price must be above 20-bar EMA
ema20 = EMA(closes, 20)
# close > ema20
```

### Condition 5: RSI Filter
```python
# RSI must be between 40-70 (not overbought)
rsi = RSI(closes, 14)
# 40 < rsi < 70
```

### Condition 6: Open Skies Ahead
```python
# Nearest resistance must be > 1% above current price
sr_map = build_sr_map(token, price)
resistance_levels = [l for l in sr_map if l['type'] == 'resistance']
# If resistance exists, nearest must be > 1% above
```

---

## 6. Confidence Scoring

| Component | Points | Logic |
|-----------|--------|-------|
| Volume spike magnitude | 30 | 3x=15pts, 5x=25pts, 10x+=30pts |
| Sustained volume | 15 | 2/3 bars=10pts, 3/3=15pts |
| Price breakout strength | 20 | % above 20-bar high |
| RSI sweet spot | 15 | 50-60=15pts, 40-50 or 60-70=10pts |
| Support below | 10 | # of support levels |
| Trend alignment | 10 | Distance above EMA20 |
| **Total** | **100** | |

**Grade thresholds:**
- A (80+): High-conviction breakout
- B (65-79): Good setup
- C (50-64): Adequate
- Below 50: Don't fire

---

## 7. Exit Strategy

- **SL:** Below the breakout level (20-bar high) or 1.5 × ATR
- **TP:** Trail-based (open skies ahead = no fixed target)
- **Time stop:** Auto-close after 4 hours if no follow-through

---

## 8. Constants (for hermes_constants.py)

```python
# Breakout Ignition Signal
BREAKOUT_IGNITION_ENABLED = True
BREAKOUT_IGNITION_PLUS_ENABLED = True
BREAKOUT_IGNITION_MINUS_ENABLED = False  # LONG only

# Volume
BREAKOUT_IGNITION_VOL_SPIKE_MIN = 3.0    # minimum volume spike ratio
BREAKOUT_IGNITION_VOL_SUSTAINED_MIN = 2  # minimum bars with elevated volume
BREAKOUT_IGNITION_VOL_ELEVATED_RATIO = 2.0  # "elevated" = 2x average

# Price
BREAKOUT_IGNITION_BREAKOUT_PERIOD = 20   # bars for consolidation high
BREAKOUT_IGNITION_BREAKOUT_MIN_PCT = 0.1 # minimum % above consolidation high

# Trend
BREAKOUT_IGNITION_EMA_PERIOD = 20        # trend filter EMA

# RSI
BREAKOUT_IGNITION_RSI_MIN = 40
BREAKOUT_IGNITION_RSI_MAX = 70

# S/R
BREAKOUT_IGNITION_RESISTANCE_MIN_PCT = 1.0  # minimum distance to resistance

# Cooldown
BREAKOUT_IGNITION_COOLDOWN_HOURS = 1

# Confidence
BREAKOUT_IGNITION_CONF_BASE = 75
BREAKOUT_IGNITION_CONF_CAP = 92
```

---

## 9. Backtest Plan

1. Query all tokens with volume spikes > 3x in the last 30 days
2. Check which ones had sustained volume + price breakout
3. Measure: what % resulted in profitable moves within 4 hours?
4. Compare: breakout_ignition vs open-skies entry timing
5. Validate: ATOM specifically — would it have fired at 11:30?

---

## 10. Integration

Same as open-skies:
- `scripts/signals/breakout_ignition.py` (new)
- `scripts/hermes_constants.py` (new constants)
- `scripts/signals/__init__.py` (registry)
- `scripts/signal_schema.py` (Layer 2)
- `scripts/signal_compactor.py` (source weight)
- `scripts/volatility_gate.py` (REGIME_SIGNALS)
- STANDALONE_BYPASS_SIGNALS (works solo)
- PROFIT_MONSTER_BYPASS_SIGNALS (ATR-managed)
