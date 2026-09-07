# Mean Reversion Dip Signal — Spec (v3)

**Author:** CEO (Hermes Trading System)
**Date:** 2026-09-07
**Type:** LONG — buy pullback to SMA20 in established uptrend
**Reference:** INJ LONG 2026-09-07 — +40.57% (5x), entry at SMA20

---

## 1. The Pattern (INJ Entry at 18:00 UTC)

**At entry (18:00 UTC, $5.8140) — computed from 1m candles:**

| Parameter | Value | What it means |
|-----------|-------|---------------|
| Price | $5.8140 | Entry price |
| SMA5 | $5.85 (-0.7%) | Pulled back below SMA5 |
| SMA10 | $5.83 (-0.3%) | Near SMA10 |
| SMA20 | $5.81 (**exact touch**) | At SMA20 — the buy zone |
| SMA50 | $5.77 (+0.8%) | Above SMA50 — uptrend |
| RSI(14) | 74.5 | Bullish momentum |
| BB Position | 0.833 | Strong trend (near upper band) |
| Ret 20 | +1.26% | Uptrend intact |
| HH(10) | 5/10 | More highs than lows |
| Volume | 0.54x avg | Quiet pullback (not chasing) |

> Note: All values computed from **1m candles** at the exact entry timestamp.
> 5m candles give different values due to different SMA windows (20×1m vs 20×5m).
> Signal detection uses 1m candles for precision.

**The pattern:** In an established uptrend (price > SMA50), price pulls back from SMA5 to touch SMA20. RSI is bullish (74.5) but not extreme. BB shows strong trend (0.833). Volume is quiet (0.54x). Entry at SMA20, hold for trend continuation.

---

## 2. Why This Works

1. **SMA20 acts as dynamic support** — in uptrends, price bounces off SMA20
2. **RSI 74.5 = bullish momentum** — trend has energy, not exhausted
3. **BB 0.833 = strong trend** — price near upper band confirms uptrend strength
4. **Low volume = quiet entry** — not chasing, buying calmly
5. **SMA20 > SMA50** — trend structure intact (not a reversal)

---

## 3. Conditions (verified against INJ)

| # | Condition | Threshold | INJ Value | Pass? |
|---|-----------|-----------|-----------|-------|
| 1 | Price > SMA50 | Uptrend | +0.8% | ✅ |
| 2 | Price within 0.5% of SMA20 | At buy zone | 0.001% | ✅ |
| 3 | SMA20 > SMA50 | Trend intact | +0.8% | ✅ |
| 4 | RSI 60-85 | Bullish | 74.5 | ✅ |
| 5 | BB position > 0.60 | Strong trend | 0.833 | ✅ |
| 6 | Avg volume > 50 | Real market | 3921 | ✅ |

**All 6 conditions pass on INJ at 18:00 UTC.**

---

## 4. Entry/Exit

- **Entry:** Market order at current price
- **SL:** Below SMA50 (or 1.5 × ATR)
- **TP:** SMA10 or trailing stop
- **Hold:** Multi-hour (INJ held 7 hours)

---

## 5. Constants

```python
MRDIP_ENABLED = True
MRDIP_PLUS_ENABLED = True
MRDIP_MINUS_ENABLED = False

MRDIP_SMA_FAST = 20            # pullback target
MRDIP_SMA_SLOW = 50            # trend filter
MRDIP_MAX_SMA20_DIST = 0.5     # % — price within this of SMA20

MRDIP_RSI_MIN = 60             # bullish momentum
MRDIP_RSI_MAX = 85             # not extreme

MRDIP_BB_MIN_POSITION = 0.60   # strong trend

MRDIP_MIN_AVG_VOL = 50
MRDIP_SL_ATR_MULT = 1.5
MRDIP_TP_TARGET = 'SMA10'
MRDIP_COOLDOWN_HOURS = 2
MRDIP_CONF_BASE = 80
MRDIP_CONF_CAP = 92
```

---

## 6. How It Differs from Open-Skies

| | Open-Skies | Mean Reversion Dip |
|---|---|---|
| **Entry point** | Breakout (price above SMAs) | Pullback (price at SMA20) |
| **RSI** | >50 (bullish) | 60-85 (bullish) |
| **BB position** | >0.5 (middle) | >0.60 (strong trend) |
| **Ret 20** | >1.5% (extended) | >0% (uptrend) |
| **Volume** | Spike (breakout confirmation) | Quiet (pullback entry) |
| **Holding time** | Hours (ride breakout) | Hours (ride continuation) |

**Open-skies fires when the move starts. Mean reversion dip fires during the move (pullback).**
