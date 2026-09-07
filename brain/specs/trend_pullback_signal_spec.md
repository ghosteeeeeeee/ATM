# Trend Pullback Signal — Spec

**Author:** CEO (Hermes Trading System)
**Date:** 2026-09-07
**Type:** LONG pullback entry in established uptrends
**Reference:** INJ LONG 2026-09-07 — +40.57% (5x), entry on pullback

---

## 1. Thesis

Big wins come from entering AFTER the initial move, on a pullback. The open-skies signal fires when the breakout happens, but the real money is made by buying the dip in an established trend. This signal specifically detects pullback entries in clean uptrends.

**Core insight from INJ:**
- Signal fired at $6.09 (price already up 5%)
- Entry at $5.80 (pulled back 4.8% from signal)
- Exit at $6.27 (+8.11% raw, +40.57% 5x)
- **The pullback IS the opportunity**

---

## 2. The INJ Pattern (Reference Case)

```
INJ LONG — 2026-09-07
Entry: $5.7975 | Exit: $6.2679 | +40.57% (5x)

Timeline:
18:00  $5.81  ── uptrend established
18:30  $5.92  ── +1.9%
19:00  $6.00  ── +3.3%
19:09  $5.96  ← PULLBACK LOW (-2.1% from high)
19:30  $6.09  ← signal fires (recovery underway)
20:02  $6.29  ← peak (+3.3% from signal)
20:39  $5.80  ← ENTRY (limit order filled on pullback)
        │
        ▼
20:39  $6.27  ← EXIT (+8.11% raw, +40.57% 5x)

Key: Entry was $0.30 BELOW signal price
     Limit order caught the pullback
```

---

## 3. Signal Logic

### Detection (LONG only)

```python
def detect(token):
    """
    1. Confirm uptrend (price > SMA20 > SMA50)
    2. Detect pullback (price dipped from recent high)
    3. Check pullback quality (not too deep, not too shallow)
    4. Verify support holds (price above key support)
    5. Check momentum (RSI cooling but not dead)
    6. Volume confirmation (still active)
    """
```

### Conditions

| # | Condition | Threshold | Rationale |
|---|-----------|-----------|-----------|
| 1 | Uptrend | Price > SMA20 > SMA50 | Confirmed trend |
| 2 | Pullback from high | 1.5-5% from 20-bar high | Enough dip to buy, not a crash |
| 3 | Above SMA20 | Price > SMA20 (or within 0.5%) | Trend intact |
| 4 | RSI cooling | RSI 40-70 | Pulled back from overbought, not dead |
| 5 | Support holds | ≥2 support levels below | Floor in place |
| 6 | Volume active | avg vol > 50 | Real market, not dead |
| 7 | Not overextended | 20-bar return < 8% | Move hasn't already happened |

### Entry Strategy

**This signal is designed for LIMIT ORDERS, not market orders:**

```python
# Entry zone: SMA20 or recent support (whichever is closer)
entry_zone = max(sma20, nearest_support)

# If current price is above entry zone → set limit order at entry_zone
# If current price is at entry zone → enter now
# If current price is below entry zone → too late, skip
```

### Exit

- **Primary:** Trailing stop (0.5% activation, 0.3% distance)
- **Secondary:** ATR SL hit
- **Tertiary:** Price closes below SMA20 (trend broken)

---

## 4. Data Sources

| Data | Source | Freshness |
|------|--------|-----------|
| Candles (5m, 1m) | `candles.db` | ~1 min |
| S/R map | `risk_reward_engine.build_sr_map()` | 5 min cache |
| ATR% | `volatility_gate.get_atr_pct()` | ~1 min |
| Volume | `candles_5m.volume` | ~1 min |

---

## 5. Confidence Scoring

| Component | Points | Logic |
|-----------|--------|-------|
| Pullback quality | 30 | 2-3% dip = optimal (30), 1.5% = decent (20), 4-5% = risky (15) |
| Trend strength | 25 | Above SMA20+SMA50 + positive slope |
| Support confirmation | 20 | Number and proximity of support levels |
| RSI positioning | 15 | 50-60 = optimal (15), 40-50 = good (10), 60-70 = OK (5) |
| Volume | 10 | Above average volume |
| **Total** | **100** | |

---

## 6. Constants

```python
# ── Trend Pullback Signal ─────────────────────────────────────────────
TREND_PULLBACK_ENABLED = True
TREND_PULLBACK_PLUS_ENABLED = True    # LONG only
TREND_PULLBACK_MINUS_ENABLED = False  # SHORT not applicable

# Trend filters
TREND_PULLBACK_SMA_FAST = 20
TREND_PULLBACK_SMA_SLOW = 50

# Pullback detection
TREND_PULLBACK_MIN_DIP_PCT = 1.5     # % — minimum pullback from high
TREND_PULLBACK_MAX_DIP_PCT = 5.0     # % — maximum pullback (deeper = trend broken)
TREND_PULLBACK_LOOKBACK = 20         # bars to find recent high

# Entry zone
TREND_PULLBACK_ENTRY_BUFFER = 0.002  # 0.2% above SMA20/support for limit order

# RSI
TREND_PULLBACK_RSI_MIN = 40          # RSI must be above this (not dead)
TREND_PULLBACK_RSI_MAX = 70          # RSI must be below this (not overbought)

# Momentum
TREND_PULLBACK_MAX_RETURN_20 = 8.0   # % — max 20-bar return (don't chase extended moves)

# Volume
TREND_PULLBACK_MIN_AVG_VOL = 50      # minimum average volume

# Support
TREND_PULLBACK_MIN_SUPPORT = 2       # minimum support levels below

# Cooldown
TREND_PULLBACK_COOLDOWN_HOURS = 2    # per-token cooldown

# Confidence
TREND_PULLBACK_CONF_BASE = 75
TREND_PULLBACK_CONF_CAP = 92

# Pullback quality scoring
TREND_PULLBACK_OPTIMAL_DIP_LOW = 2.0   # % — optimal pullback low
TREND_PULLBACK_OPTIMAL_DIP_HIGH = 3.0  # % — optimal pullback high
TREND_PULLBACK_DIP_BONUS_OPTIMAL = 30  # points for optimal dip
TREND_PULLBACK_DIP_BONUS_GOOD = 20     # points for good dip
TREND_PULLBACK_DIP_BONUS_RISKY = 15    # points for risky dip
```

---

## 7. File Changes

| File | Change |
|------|--------|
| `scripts/signals/trend_pullback.py` | **NEW** — signal generator |
| `scripts/hermes_constants.py` | Add `TREND_PULLBACK_*` constants |
| `scripts/signals/__init__.py` | Register signal |

---

## 8. How This Complements Open Skies

| Signal | When it fires | Entry style | Target |
|--------|--------------|-------------|--------|
| **open-skies** | Breakout happens | Market/limit at signal | Ride the breakout |
| **trend-pullback** | Pullback in established trend | Limit order at support/SMA | Ride the continuation |

**Together they capture the full lifecycle:**
1. Open-skies fires on breakout → signal the trend
2. Trend-pullback fires on pullback → enter at better price
3. Both ride the same trend with trailing stops

---

## 9. Risk Management

**Why this is safe:**
1. LONG only — no shorting pullbacks (catching knives)
2. SL below SMA20 or support — structured stop
3. Pullback must be 1.5-5% — not too deep (trend broken) not too shallow (no edge)
4. RSI 40-70 — momentum confirmed but not exhausted
5. Volume confirmation — real buying, not noise

**Why this is powerful:**
1. Enters at better price than open-skies (pullback vs chase)
2. Trend already established (higher probability)
3. Support floor in place (defined risk)
4. RSI cooling = momentum ready to resume

---

## 10. Integration with RR Engine

Trend-pullback signals benefit from the RR engine:
- Pullback to support = clear SL level (below support)
- Uptrend with open skies = clear TP target (next resistance)
- RSI 40-70 = neutral zone (no extreme readings)
- Score gets full S/R Clarity points (support below, resistance above)
