# Mean Reversion Dip Signal — Spec (v4)

**Author:** CEO (Hermes Trading System)
**Date:** 2026-09-07
**Type:** LONG — buy pullback to SMA20 zone in established uptrend
**Reference:** INJ LONG 2026-09-07 — +40.57% (5x)

---

## 1. What Actually Happened (INJ)

**18:00 UTC candle (1m data):**
- Open: $5.8100, High: $5.8200, Low: $5.8030, Close: $5.8480
- **Intraday low touched SMA20** ($5.8140) — the buy zone
- **Close above SMA20** — price bounced off SMA20 support
- RSI: 74.5, BB Position: 0.833 (at close)

**The signal fires when price is near SMA20, not exactly at it.**
The "exact touch" was intraday — the close confirms the bounce.

---

## 2. Conditions (corrected)

| # | Condition | Threshold | Rationale |
|---|-----------|-----------|-----------|
| 1 | Price > SMA50 | Uptrend | Established trend |
| 2 | Price within 1% of SMA20 | Near buy zone | Mean reversion target |
| 3 | SMA20 > SMA50 | Trend intact | Not a reversal |
| 4 | RSI 55-75 | Bullish but not extreme | Momentum with room |
| 5 | BB position > 0.50 | Above middle band | Strong trend |
| 6 | Avg volume > 50 | Real market | Not dead |

**Note on BB position:** BB middle = SMA20. So BB > 0.50 = price above SMA20.
The signal fires when price is WITHIN 1% of SMA20 from above — i.e., pulling back toward SMA20 but still in uptrend.

---

## 3. Why INJ Worked

1. Price pulled back from SMA5 ($5.85) toward SMA20 ($5.81) — 0.7% dip
2. SMA20 acted as dynamic support — price bounced
3. RSI 74.5 = bullish momentum (not exhausted)
4. BB 0.833 = strong trend (price near upper band at close)
5. Volume quiet (0.54x) = not chasing
6. Held 7 hours for +8.11% raw move

---

## 4. Key Distinction from Open-Skies

| | Open-Skies | Mean Reversion Dip |
|---|---|---|
| Entry | Breakout (price surges above SMAs) | Pullback (price dips toward SMA20) |
| RSI | >50 | 55-75 |
| BB | >0.50 | >0.50 |
| Volume | Spike (breakout confirmation) | Quiet (dip entry) |
| Ret 20 | >1.5% (extended) | >0% (uptrend) |

**Open-skies = buy the breakout. Mean reversion dip = buy the pullback to the MA.**

---

## 5. Constants

```python
MRDIP_ENABLED = True
MRDIP_PLUS_ENABLED = True
MRDIP_MINUS_ENABLED = False

MRDIP_SMA_FAST = 20
MRDIP_SMA_SLOW = 50
MRDIP_MAX_SMA20_DIST = 1.0     # % — price within this of SMA20

MRDIP_RSI_MIN = 55
MRDIP_RSI_MAX = 75

MRDIP_BB_MIN_POSITION = 0.50   # above BB middle (= above SMA20)

MRDIP_MIN_AVG_VOL = 50
MRDIP_SL_ATR_MULT = 1.5
MRDIP_TP_TARGET = 'SMA10'
MRDIP_COOLDOWN_HOURS = 2
MRDIP_CONF_BASE = 80
MRDIP_CONF_CAP = 92
```
